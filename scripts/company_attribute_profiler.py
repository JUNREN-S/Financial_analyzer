#!/usr/bin/env python3
"""基于紧凑型指标表的企业属性画像工具。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile


HEADER_ALIASES = {
    "company_name": ["company_name", "公司简称", "企业名称", "证券简称", "公司名称"],
    "growth": [
        "growth",
        "growth_i",
        "营收增长率",
        "营业收入增长率",
        "营业收入增长率（%）",
        "成长性",
        "资产周转率（Growth，%）",
        "资产周转率(Growth,%)",
    ],
    "rd_intensity": [
        "rd_intensity",
        "rdi",
        "研发投入强度",
        "研发投入强度（RDi，%）",
        "研发投入强度(RDi,%)",
    ],
    "roe": ["roe", "净资产收益率", "净资产收益率（ROE，%）", "净资产收益率(ROE,%)"],
    "asset_liability_ratio": [
        "asset_liability_ratio",
        "资产负债率",
        "资产负债率（%）",
    ],
    "industry": ["industry", "所属行业", "行业"],
    "track": ["track", "赛道", "所处赛道"],
    "main_business": ["main_business", "主营业务", "主营"],
}

THEME_KEYWORDS = {
    "人工智能",
    "ai",
    "大模型",
    "算力",
    "半导体",
    "芯片",
    "工业软件",
    "工业互联网",
    "高端装备",
    "智能制造",
    "机器人",
    "数据要素",
    "新能源",
    "储能",
    "新材料",
    "生物医药",
    "创新药",
    "医疗器械",
    "低空经济",
}

XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="企业属性画像与相似企业识别工具")
    parser.add_argument("--data", required=True, help="输入文件路径，支持 CSV/XLSX")
    parser.add_argument("--company", required=True, help="目标企业名称")
    parser.add_argument("--sheet", default=None, help="XLSX 工作表名称，默认取第一个 sheet")
    parser.add_argument("--similar-top-n", type=int, default=5, help="输出相似企业数量")
    parser.add_argument("--output-dir", default="output", help="输出目录")
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_header(value: str) -> str:
    return (
        normalize_text(value)
        .replace(" ", "")
        .replace("\u3000", "")
        .replace("（", "(")
        .replace("）", ")")
        .lower()
    )


def parse_optional_float(value: Any) -> float | None:
    text = normalize_text(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def excel_col_to_index(cell_ref: str) -> int:
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char.upper())
        else:
            break
    result = 0
    for char in letters:
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def read_shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for si in root.findall("main:si", XML_NS):
        values.append("".join(node.text or "" for node in si.iterfind(".//main:t", XML_NS)))
    return values


def workbook_sheets(zf: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {}
    for rel in rels.findall("pkg:Relationship", XML_NS):
        rel_map[rel.attrib["Id"]] = rel.attrib["Target"]

    sheets = []
    relation_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for sheet in workbook.findall("main:sheets/main:sheet", XML_NS):
        target = rel_map[sheet.attrib[relation_key]]
        sheet_path = target if target.startswith("xl/") else f"xl/{target}"
        sheets.append((sheet.attrib["name"], sheet_path))
    return sheets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", XML_NS)
    if cell_type == "inlineStr":
        inline = cell.find("main:is", XML_NS)
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iterfind(".//main:t", XML_NS))
    if value_node is None:
        return ""
    value = value_node.text or ""
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return value
    return value


def read_xlsx(path: Path, sheet_name: str | None) -> list[dict[str, Any]]:
    with ZipFile(path) as zf:
        sheets = workbook_sheets(zf)
        if not sheets:
            raise ValueError(f"未找到工作表: {path}")

        target_sheet = sheets[0] if sheet_name is None else None
        if sheet_name is not None:
            for name, sheet_path in sheets:
                if name == sheet_name:
                    target_sheet = (name, sheet_path)
                    break
        if target_sheet is None:
            available = "、".join(name for name, _ in sheets)
            raise ValueError(f"未找到工作表 {sheet_name}，可选：{available}")

        shared_strings = read_shared_strings(zf)
        root = ET.fromstring(zf.read(target_sheet[1]))
        rows = root.findall("main:sheetData/main:row", XML_NS)
        if not rows:
            return []

        table: list[list[str]] = []
        max_col = 0
        for row in rows:
            indexed: dict[int, str] = {}
            for cell in row.findall("main:c", XML_NS):
                ref = cell.attrib.get("r", "")
                col_index = excel_col_to_index(ref) if ref else len(indexed)
                indexed[col_index] = cell_value(cell, shared_strings)
                max_col = max(max_col, col_index)
            table.append([indexed.get(index, "") for index in range(max_col + 1)])

    headers = [normalize_text(value) for value in table[0]]
    records = []
    for raw_row in table[1:]:
        if not any(normalize_text(value) for value in raw_row):
            continue
        record = {}
        for idx, header in enumerate(headers):
            if header:
                record[header] = raw_row[idx] if idx < len(raw_row) else ""
        records.append(record)
    return records


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{normalize_text(k): normalize_text(v) for k, v in row.items()} for row in reader]


def load_records(path: Path, sheet_name: str | None) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        rows = read_csv(path)
    elif path.suffix.lower() == ".xlsx":
        rows = read_xlsx(path, sheet_name)
    else:
        raise ValueError(f"暂不支持的文件类型: {path.suffix}")
    if not rows:
        raise ValueError(f"数据为空: {path}")
    return rows


def build_column_mapping(headers: list[str]) -> dict[str, str]:
    normalized_headers = {normalize_header(header): header for header in headers}
    mapping = {}
    for internal_key, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            source = normalized_headers.get(normalize_header(alias))
            if source:
                mapping[internal_key] = source
                break
    return mapping


def row_to_standard_record(row: dict[str, Any], column_mapping: dict[str, str]) -> dict[str, Any]:
    record = {}
    for internal_key in HEADER_ALIASES:
        source_key = column_mapping.get(internal_key)
        record[internal_key] = normalize_text(row.get(source_key)) if source_key else ""

    for key in ("growth", "rd_intensity", "roe", "asset_liability_ratio"):
        record[key] = parse_optional_float(record.get(key))

    record["company_name"] = normalize_text(record.get("company_name"))
    if not record["company_name"]:
        raise ValueError(f"发现缺少企业名称的记录: {row}")
    return record


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def thresholds_for(values: list[float]) -> dict[str, float]:
    return {
        "q1": round(percentile(values, 0.25), 4),
        "q2": round(percentile(values, 0.50), 4),
        "q3": round(percentile(values, 0.75), 4),
    }


def percentile_rank(value: float | None, values: list[float], reverse: bool = False) -> float | None:
    if value is None or not values:
        return None
    if len(values) == 1:
        return 100.0
    less_equal = sum(1 for item in values if item <= value)
    rank = (less_equal - 1) / (len(values) - 1) * 100
    rank = max(0.0, min(rank, 100.0))
    return round(100 - rank if reverse else rank, 2)


def metric_tier(
    value: float | None,
    thresholds: dict[str, float],
    labels: tuple[str, str, str, str],
    reverse: bool = False,
) -> str:
    if value is None:
        return "缺失"
    q1 = thresholds["q1"]
    q2 = thresholds["q2"]
    q3 = thresholds["q3"]
    if reverse:
        if value <= q1:
            return labels[0]
        if value <= q2:
            return labels[1]
        if value <= q3:
            return labels[2]
        return labels[3]
    if value >= q3:
        return labels[0]
    if value >= q2:
        return labels[1]
    if value >= q1:
        return labels[2]
    return labels[3]


def theme_fit_from_text(record: dict[str, Any]) -> dict[str, Any]:
    text_fields = [
        normalize_text(record.get("industry")),
        normalize_text(record.get("track")),
        normalize_text(record.get("main_business")),
    ]
    non_empty_fields = [field for field in text_fields if field]
    corpus = " ".join(non_empty_fields).lower()
    hits = sorted(keyword for keyword in THEME_KEYWORDS if keyword.lower() in corpus)
    if not non_empty_fields:
        return {
            "theme_fit": "待人工复核",
            "theme_confidence": "low",
            "theme_reason": ["缺少行业/赛道/主营字段，不能仅凭财务指标判断主题归属"],
        }
    if len(hits) >= 2:
        return {
            "theme_fit": "高度匹配",
            "theme_confidence": "high",
            "theme_reason": hits,
        }
    if len(hits) == 1:
        return {
            "theme_fit": "中度匹配",
            "theme_confidence": "medium",
            "theme_reason": hits,
        }
    return {
        "theme_fit": "待人工复核",
        "theme_confidence": "low",
        "theme_reason": ["文本字段存在，但未命中新质生产力关键词"],
    }


def profile_type(record: dict[str, Any], thresholds: dict[str, dict[str, float]]) -> str:
    growth = record.get("growth")
    rd = record.get("rd_intensity")
    roe = record.get("roe")
    debt = record.get("asset_liability_ratio")

    g3 = thresholds["growth"]["q3"]
    g1 = thresholds["growth"]["q1"]
    r3 = thresholds["rd_intensity"]["q3"]
    r2 = thresholds["rd_intensity"]["q2"]
    p3 = thresholds["roe"]["q3"]
    p2 = thresholds["roe"]["q2"]
    p1 = thresholds["roe"]["q1"]
    d2 = thresholds["asset_liability_ratio"]["q2"]
    d3 = thresholds["asset_liability_ratio"]["q3"]

    if rd is not None and growth is not None and rd >= r3 and growth >= g3:
        if roe is not None and roe >= p2:
            return "技术扩张领跑型"
        return "高投入换增长型"
    if rd is not None and rd >= r3 and growth is not None and growth <= g1:
        return "研发蓄力转化型"
    if growth is not None and growth >= g3 and debt is not None and debt >= d2:
        return "扩张进攻型"
    if roe is not None and roe >= p3 and debt is not None and debt <= d2:
        return "盈利稳健兑现型"
    if debt is not None and debt >= d3 and roe is not None and roe <= p2:
        return "财务承压型"
    if growth is not None and growth <= g1 and roe is not None and roe <= p1:
        return "成长承压型"
    if rd is not None and rd >= r2 and roe is not None and roe >= p2 and debt is not None and debt <= d2:
        return "研发驱动稳健型"
    return "均衡发展型"


def risk_level(record: dict[str, Any], thresholds: dict[str, dict[str, float]]) -> str:
    debt = record.get("asset_liability_ratio")
    roe = record.get("roe")
    growth = record.get("growth")
    d1 = thresholds["asset_liability_ratio"]["q1"]
    d2 = thresholds["asset_liability_ratio"]["q2"]
    d3 = thresholds["asset_liability_ratio"]["q3"]
    p1 = thresholds["roe"]["q1"]
    p2 = thresholds["roe"]["q2"]
    g1 = thresholds["growth"]["q1"]

    if debt is None:
        return "待补充"
    if debt >= d3 and ((roe is not None and roe <= p2) or (growth is not None and growth <= g1)):
        return "高风险"
    if debt >= d3 or (roe is not None and roe <= p1):
        return "偏高风险"
    if debt <= d1 and (roe is None or roe >= p2):
        return "低风险"
    if debt <= d2:
        return "可控风险"
    return "中等风险"


def feature_level(score: float | None) -> str:
    if score is None:
        return "待补充"
    if score >= 75:
        return "强"
    if score >= 55:
        return "中上"
    if score >= 40:
        return "中等"
    return "偏弱"


def case_priority(score: float | None, risk: str, theme_fit: str) -> str:
    if score is None:
        return "待补充样本"
    if theme_fit == "高度匹配" and score >= 70 and risk in {"低风险", "可控风险"}:
        return "核心案例候选"
    if score >= 55 and risk != "高风险":
        return "可比样本"
    return "观察样本"


def completeness(record: dict[str, Any]) -> float:
    required = ["company_name", "growth", "rd_intensity", "roe", "asset_liability_ratio"]
    present = 0
    for field in required:
        value = record.get(field)
        if isinstance(value, float):
            present += 1
        elif normalize_text(value):
            present += 1
    return round(present / len(required), 4)


def enrich_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    thresholds = {
        key: thresholds_for([record[key] for record in records if record.get(key) is not None])
        for key in ("growth", "rd_intensity", "roe", "asset_liability_ratio")
    }
    growth_values = [record["growth"] for record in records if record.get("growth") is not None]
    rd_values = [record["rd_intensity"] for record in records if record.get("rd_intensity") is not None]
    roe_values = [record["roe"] for record in records if record.get("roe") is not None]
    debt_values = [
        record["asset_liability_ratio"]
        for record in records
        if record.get("asset_liability_ratio") is not None
    ]

    enriched = []
    for record in records:
        theme_profile = theme_fit_from_text(record)
        growth_rank = percentile_rank(record.get("growth"), growth_values)
        rd_rank = percentile_rank(record.get("rd_intensity"), rd_values)
        roe_rank = percentile_rank(record.get("roe"), roe_values)
        debt_safety_rank = percentile_rank(record.get("asset_liability_ratio"), debt_values, reverse=True)

        feature_score = None
        if None not in (growth_rank, rd_rank, roe_rank, debt_safety_rank):
            feature_score = round(
                0.30 * growth_rank
                + 0.35 * rd_rank
                + 0.20 * roe_rank
                + 0.15 * debt_safety_rank,
                2,
            )

        growth_tag = metric_tier(
            record.get("growth"),
            thresholds["growth"],
            ("高成长", "成长较强", "成长稳健", "成长偏弱"),
        )
        innovation_tag = metric_tier(
            record.get("rd_intensity"),
            thresholds["rd_intensity"],
            ("高研发投入", "研发驱动", "研发中等", "研发偏弱"),
        )
        profitability_tag = metric_tier(
            record.get("roe"),
            thresholds["roe"],
            ("盈利效率突出", "盈利能力较强", "盈利能力稳健", "盈利效率偏弱"),
        )
        leverage_tag = metric_tier(
            record.get("asset_liability_ratio"),
            thresholds["asset_liability_ratio"],
            ("低杠杆", "杠杆可控", "杠杆偏高", "高杠杆"),
            reverse=True,
        )

        current = dict(record)
        current["completeness"] = completeness(record)
        current["growth_rank"] = growth_rank
        current["rd_rank"] = rd_rank
        current["roe_rank"] = roe_rank
        current["debt_safety_rank"] = debt_safety_rank
        current["growth_tag"] = growth_tag
        current["innovation_tag"] = innovation_tag
        current["profitability_tag"] = profitability_tag
        current["leverage_tag"] = leverage_tag
        current["risk_tag"] = risk_level(record, thresholds)
        current["profile_type"] = profile_type(record, thresholds)
        current["theme_fit"] = theme_profile["theme_fit"]
        current["theme_confidence"] = theme_profile["theme_confidence"]
        current["theme_reason"] = "；".join(theme_profile["theme_reason"])
        current["feature_score"] = feature_score
        current["feature_level"] = feature_level(feature_score)
        current["case_priority"] = case_priority(feature_score, current["risk_tag"], current["theme_fit"])
        current["attribute_summary"] = (
            f"{innovation_tag}、{growth_tag}、{profitability_tag}，"
            f"{leverage_tag}，归为{current['profile_type']}，风险判断为{current['risk_tag']}"
        )
        enriched.append(current)

    enriched.sort(
        key=lambda item: (
            item["feature_score"] if item["feature_score"] is not None else -1,
            item["company_name"],
        ),
        reverse=True,
    )
    return enriched, thresholds


def similarity_score(target: dict[str, Any], candidate: dict[str, Any]) -> float:
    features = [
        ("growth_rank", 0.30),
        ("rd_rank", 0.35),
        ("roe_rank", 0.20),
        ("debt_safety_rank", 0.15),
    ]
    similarity = 0.0
    weight_sum = 0.0
    for key, weight in features:
        target_value = target.get(key)
        candidate_value = candidate.get(key)
        if target_value is None or candidate_value is None:
            continue
        distance = abs(target_value - candidate_value) / 100
        similarity += max(0.0, 1 - distance) * weight
        weight_sum += weight

    similarity = similarity / weight_sum if weight_sum else 0.0
    if target.get("profile_type") == candidate.get("profile_type"):
        similarity += 0.08
    if target.get("risk_tag") == candidate.get("risk_tag"):
        similarity += 0.05
    if target.get("theme_fit") == candidate.get("theme_fit"):
        similarity += 0.02
    return round(min(similarity, 1.0) * 100, 2)


def build_similarity_table(
    enriched_records: list[dict[str, Any]],
    company_name: str,
    limit: int,
) -> list[dict[str, Any]]:
    target = next(record for record in enriched_records if record["company_name"] == company_name)
    rows = []
    for record in enriched_records:
        if record["company_name"] == company_name:
            continue
        rows.append(
            {
                "company_name": record["company_name"],
                "similarity_score": similarity_score(target, record),
                "profile_type": record["profile_type"],
                "feature_score": record["feature_score"],
                "risk_tag": record["risk_tag"],
                "case_priority": record["case_priority"],
            }
        )
    rows.sort(key=lambda item: item["similarity_score"], reverse=True)
    return rows[:limit]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def report_stem(company_name: str) -> str:
    digest = hashlib.md5(company_name.encode("utf-8")).hexdigest()[:8]
    return f"profile_{digest}"


def main() -> None:
    args = parse_args()
    data_path = Path(args.data).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_records = load_records(data_path, args.sheet)
    column_mapping = build_column_mapping(list(raw_records[0].keys()))
    required = ["company_name", "growth", "rd_intensity", "roe", "asset_liability_ratio"]
    missing = [key for key in required if key not in column_mapping]
    if missing:
        raise SystemExit(f"缺少必要字段映射: {missing}\n检测到表头: {list(raw_records[0].keys())}")

    records = [row_to_standard_record(row, column_mapping) for row in raw_records]
    company_names = [record["company_name"] for record in records]
    if args.company not in company_names:
        available = "、".join(sorted(company_names))
        raise SystemExit(f"未找到目标企业：{args.company}\n可用企业：{available}")

    enriched_records, thresholds = enrich_records(records)
    target = next(record for record in enriched_records if record["company_name"] == args.company)
    similar_companies = build_similarity_table(enriched_records, args.company, args.similar_top_n)

    stem = report_stem(args.company)
    enriched_path = output_dir / f"{stem}_attribute_profiles.csv"
    report_path = output_dir / f"{stem}_attribute_report.json"
    similar_path = output_dir / f"{stem}_similar_companies.csv"

    report = {
        "input": {
            "data_path": str(data_path),
            "sheet": args.sheet,
            "target_company": args.company,
        },
        "field_mapping": column_mapping,
        "sample_thresholds": thresholds,
        "target_company": {
            "company_name": target["company_name"],
            "theme_fit": target["theme_fit"],
            "theme_confidence": target["theme_confidence"],
            "theme_reason": target["theme_reason"],
            "feature_score": target["feature_score"],
            "feature_level": target["feature_level"],
            "case_priority": target["case_priority"],
            "profile_type": target["profile_type"],
            "risk_tag": target["risk_tag"],
            "attribute_summary": target["attribute_summary"],
            "metric_snapshot": {
                "growth": target["growth"],
                "rd_intensity": target["rd_intensity"],
                "roe": target["roe"],
                "asset_liability_ratio": target["asset_liability_ratio"],
            },
            "metric_ranks": {
                "growth_rank": target["growth_rank"],
                "rd_rank": target["rd_rank"],
                "roe_rank": target["roe_rank"],
                "debt_safety_rank": target["debt_safety_rank"],
            },
            "attribute_tags": {
                "growth_tag": target["growth_tag"],
                "innovation_tag": target["innovation_tag"],
                "profitability_tag": target["profitability_tag"],
                "leverage_tag": target["leverage_tag"],
            },
        },
        "similar_companies": similar_companies,
        "note": (
            "若缺少行业、赛道、主营字段，本报告只输出新质生产力表征强度，"
            "不替代人工对主题归属的最终判断。"
        ),
    }

    write_csv(enriched_path, enriched_records)
    write_csv(similar_path, similar_companies)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"目标企业：{args.company}")
    print(f"属性类型：{target['profile_type']}")
    print(f"新质表征强度：{target['feature_level']} ({target['feature_score']})")
    print(f"案例优先级：{target['case_priority']}")
    print(f"风险标签：{target['risk_tag']}")
    print("结果文件已生成。")


if __name__ == "__main__":
    main()
