#!/usr/bin/env python3
"""金融分析师竞赛案例筛选与数据准备工具。

该脚本聚焦三个问题：
1. 某家企业是否适合作为“新质生产力”主题案例企业；
2. 若不适合，哪些相似企业更值得进入候选池；
3. 为熵权法 + TOPSIS 和一元线性回归预先整理哪些数据。

说明：
- 默认读取本地 CSV，不直接调用外部 API。
- 附带的 demo 数据仅用于演示流程，不代表真实财务数据。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any


YES_VALUES = {"1", "true", "yes", "y", "是", "相关", "属于", "匹配"}
BASE_PROFILE_FIELDS = [
    "company_name",
    "industry",
    "main_business",
    "core_products",
    "track",
]
TEXT_FIELDS = [
    "annual_report_summary",
    "risk_disclosure",
    "website_intro",
    "major_events",
]
NUMERIC_FIELDS = [
    "revenue",
    "net_profit",
    "roe",
    "asset_liability_ratio",
    "operating_cashflow",
    "rd_expense",
    "patent_count",
    "industry_growth_space",
    "customer_concentration",
    "policy_sensitivity",
    "sentiment_risk",
]
NEW_QUALITY_KEYWORDS = {
    "人工智能",
    "AI",
    "大模型",
    "算力",
    "机器人",
    "半导体",
    "芯片",
    "工业软件",
    "工业互联网",
    "高端装备",
    "智能制造",
    "数据要素",
    "自动驾驶",
    "低空经济",
    "新材料",
    "生物制造",
}


@dataclass(frozen=True)
class Indicator:
    key: str
    label: str
    category: str
    direction: str


INDICATORS = [
    Indicator("roe", "ROE", "财务质量", "benefit"),
    Indicator("operating_cashflow", "经营现金流", "财务质量", "benefit"),
    Indicator("rd_intensity", "研发投入强度", "创新成长", "benefit"),
    Indicator("revenue_growth", "营业收入增长率", "创新成长", "benefit"),
    Indicator("patent_count", "专利数量", "创新成长", "benefit"),
    Indicator("industry_growth_space", "行业成长空间", "创新成长", "benefit"),
    Indicator("asset_liability_ratio", "资产负债率", "风险控制", "cost"),
    Indicator("cashflow_volatility", "现金流波动", "风险控制", "cost"),
    Indicator("customer_concentration", "客户集中度", "风险控制", "cost"),
    Indicator("policy_sensitivity", "政策敏感度", "风险控制", "cost"),
    Indicator("sentiment_risk", "舆情风险", "风险控制", "cost"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="企业案例筛选、相似企业推荐、TOPSIS/回归输入准备工具"
    )
    parser.add_argument(
        "--data",
        default="data/companies_demo.csv",
        help="输入 CSV 文件路径",
    )
    parser.add_argument(
        "--company",
        required=True,
        help="目标企业名称",
    )
    parser.add_argument(
        "--min-years",
        type=int,
        default=3,
        help="判定连续性所需的最少年份数，默认 3",
    )
    parser.add_argument(
        "--min-regression-obs",
        type=int,
        default=3,
        help="判定回归可用性所需的最小观测数，默认 3",
    )
    parser.add_argument(
        "--min-indicator-coverage",
        type=float,
        default=0.7,
        help="最新年度指标覆盖率阈值，默认 0.7",
    )
    parser.add_argument(
        "--similar-top-n",
        type=int,
        default=5,
        help="输出相似企业数量，默认 5",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录，默认 output",
    )
    return parser.parse_args()


def parse_optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def yes_like(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in YES_VALUES


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def keyword_hits(*parts: str) -> tuple[int, list[str]]:
    corpus = " ".join(part for part in parts if part).lower()
    hits = []
    for keyword in NEW_QUALITY_KEYWORDS:
        if keyword.lower() in corpus:
            hits.append(keyword)
    return len(hits), sorted(hits)


def coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean_value = statistics.fmean(values)
    if math.isclose(mean_value, 0.0, abs_tol=1e-12):
        return None
    std_value = statistics.pstdev(values)
    return abs(std_value / mean_value)


def percentage(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value * 100, digits)


def round_optional(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def load_dataset(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, Any]] = []
        for raw_row in reader:
            row: dict[str, Any] = {}
            for key, value in raw_row.items():
                row[key] = normalize_text(value)
            if not row.get("company_name"):
                continue
            try:
                row["year"] = int(row["year"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"无效年份记录: {raw_row}") from exc
            for field in NUMERIC_FIELDS:
                row[field] = parse_optional_float(row.get(field))
            rows.append(row)
    if not rows:
        raise ValueError(f"数据文件为空: {path}")
    return rows


def group_by_company(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["company_name"], []).append(row)

    for company_rows in grouped.values():
        company_rows.sort(key=lambda item: item["year"])
        cashflows = [
            row["operating_cashflow"]
            for row in company_rows
            if row["operating_cashflow"] is not None
        ]
        cashflow_volatility = coefficient_of_variation(cashflows)
        previous_revenue: float | None = None

        for row in company_rows:
            row["rd_intensity"] = safe_ratio(row["rd_expense"], row["revenue"])
            if previous_revenue in (None, 0) or row["revenue"] is None:
                row["revenue_growth"] = None
            else:
                row["revenue_growth"] = (row["revenue"] - previous_revenue) / previous_revenue
            previous_revenue = row["revenue"]
            row["cashflow_volatility"] = cashflow_volatility

            hit_count, hit_keywords = keyword_hits(
                normalize_text(row.get("industry")),
                normalize_text(row.get("main_business")),
                normalize_text(row.get("core_products")),
                normalize_text(row.get("track")),
                normalize_text(row.get("annual_report_summary")),
                normalize_text(row.get("website_intro")),
            )
            row["keyword_hit_count"] = hit_count
            row["keyword_hits"] = hit_keywords
            row["is_new_quality_related"] = yes_like(row.get("new_quality_direction")) or hit_count >= 2
    return grouped


def latest_row(company_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return company_rows[-1]


def coverage_ratio(row: dict[str, Any], indicators: list[Indicator]) -> float:
    available = 0
    for indicator in indicators:
        if row.get(indicator.key) is not None:
            available += 1
    return available / len(indicators)


def profile_completeness(row: dict[str, Any]) -> float:
    completed = 0
    for field in BASE_PROFILE_FIELDS:
        if normalize_text(row.get(field)):
            completed += 1
    return completed / len(BASE_PROFILE_FIELDS)


def text_coverage(row: dict[str, Any]) -> float:
    completed = 0
    for field in TEXT_FIELDS:
        if normalize_text(row.get(field)):
            completed += 1
    return completed / len(TEXT_FIELDS)


def build_company_summary(
    company_name: str,
    company_rows: list[dict[str, Any]],
    min_years: int,
    min_regression_obs: int,
    min_indicator_coverage: float,
) -> dict[str, Any]:
    current = latest_row(company_rows)
    available_years = len(company_rows)
    latest_indicator_coverage = coverage_ratio(current, INDICATORS)
    regression_observations = sum(
        1
        for row in company_rows
        if row.get("rd_intensity") is not None and row.get("revenue_growth") is not None
    )

    profile_score = profile_completeness(current)
    text_score = text_coverage(current)
    relevance_score = 1.0 if current["is_new_quality_related"] else min(current["keyword_hit_count"] / 3, 1.0)

    gating = {
        "is_new_quality_related": current["is_new_quality_related"],
        "has_min_years": available_years >= min_years,
        "latest_indicator_coverage_ok": latest_indicator_coverage >= min_indicator_coverage,
        "regression_ready": regression_observations >= min_regression_obs,
        "profile_complete": profile_score >= 0.8,
        "text_support_ok": text_score >= 0.5,
    }

    suitability = (
        0.25 * relevance_score
        + 0.2 * profile_score
        + 0.2 * min(available_years / max(min_years, 1), 1.0)
        + 0.2 * latest_indicator_coverage
        + 0.1 * min(regression_observations / max(min_regression_obs, 1), 1.0)
        + 0.05 * text_score
    ) * 100

    gaps = []
    if not gating["is_new_quality_related"]:
        gaps.append("与新质生产力主题关联度不足")
    if not gating["has_min_years"]:
        gaps.append(f"连续年份不足 {min_years} 年")
    if not gating["latest_indicator_coverage_ok"]:
        gaps.append("最新年度综合指标覆盖率不足")
    if not gating["regression_ready"]:
        gaps.append(f"回归可用观测数不足 {min_regression_obs}")
    if not gating["profile_complete"]:
        gaps.append("企业基础画像字段不完整")
    if not gating["text_support_ok"]:
        gaps.append("文本背景资料不足")

    case_status = "recommended"
    if gaps:
        case_status = "conditional" if suitability >= 60 else "not_recommended"

    return {
        "company_name": company_name,
        "years": [row["year"] for row in company_rows],
        "latest_year": current["year"],
        "industry": current.get("industry", ""),
        "track": current.get("track", ""),
        "relevance_reason": current["keyword_hits"],
        "profile_completeness": round_optional(profile_score),
        "text_coverage": round_optional(text_score),
        "latest_indicator_coverage": round_optional(latest_indicator_coverage),
        "regression_observations": regression_observations,
        "suitability_score": round(suitability, 2),
        "case_status": case_status,
        "gating": gating,
        "gaps": gaps,
        "latest_metrics": {
            "revenue": current.get("revenue"),
            "net_profit": current.get("net_profit"),
            "roe": current.get("roe"),
            "asset_liability_ratio": current.get("asset_liability_ratio"),
            "operating_cashflow": current.get("operating_cashflow"),
            "rd_expense": current.get("rd_expense"),
            "rd_intensity": round_optional(current.get("rd_intensity")),
            "revenue_growth_pct": percentage(current.get("revenue_growth")),
            "cashflow_volatility": round_optional(current.get("cashflow_volatility")),
        },
        "latest_profile": {
            "main_business": current.get("main_business", ""),
            "core_products": current.get("core_products", ""),
            "track": current.get("track", ""),
            "new_quality_direction": current.get("new_quality_direction", ""),
        },
    }


def similarity_score(target: dict[str, Any], candidate: dict[str, Any]) -> float:
    score = 0.0

    if target["industry"] and target["industry"] == candidate["industry"]:
        score += 0.35
    elif target["industry"] and (
        target["industry"] in candidate["industry"] or candidate["industry"] in target["industry"]
    ):
        score += 0.2

    if target["track"] and target["track"] == candidate["track"]:
        score += 0.25
    elif target["track"] and (
        target["track"] in candidate["track"] or candidate["track"] in target["track"]
    ):
        score += 0.15

    if target["gating"]["is_new_quality_related"] == candidate["gating"]["is_new_quality_related"]:
        score += 0.15

    target_revenue = target["latest_metrics"]["revenue"]
    candidate_revenue = candidate["latest_metrics"]["revenue"]
    if target_revenue not in (None, 0) and candidate_revenue not in (None, 0):
        distance = abs(target_revenue - candidate_revenue) / max(target_revenue, candidate_revenue)
        score += max(0.0, 0.15 * (1 - distance))

    target_rd = target["latest_metrics"]["rd_intensity"]
    candidate_rd = candidate["latest_metrics"]["rd_intensity"]
    if target_rd is not None and candidate_rd is not None:
        rd_distance = abs(target_rd - candidate_rd)
        score += max(0.0, 0.1 * (1 - min(rd_distance / 0.2, 1.0)))

    return round(score * 100, 2)


def build_similarity_table(
    target_company: str,
    summaries: dict[str, dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    target = summaries[target_company]
    candidates = []
    for name, summary in summaries.items():
        if name == target_company:
            continue
        row = {
            "company_name": name,
            "similarity_score": similarity_score(target, summary),
            "case_status": summary["case_status"],
            "suitability_score": summary["suitability_score"],
            "industry": summary["industry"],
            "track": summary["track"],
            "latest_year": summary["latest_year"],
        }
        candidates.append(row)

    candidates.sort(
        key=lambda item: (item["similarity_score"], item["suitability_score"]),
        reverse=True,
    )
    return candidates[:limit]


def select_topsis_candidates(summaries: dict[str, dict[str, Any]]) -> list[str]:
    selected = []
    for name, summary in summaries.items():
        gating = summary["gating"]
        if (
            gating["is_new_quality_related"]
            and gating["has_min_years"]
            and gating["latest_indicator_coverage_ok"]
        ):
            selected.append(name)
    return selected


def retain_indicators(
    latest_rows: list[dict[str, Any]],
    coverage_threshold: float,
) -> tuple[list[Indicator], list[dict[str, Any]]]:
    retained: list[Indicator] = []
    coverage_report: list[dict[str, Any]] = []
    total_rows = len(latest_rows)
    for indicator in INDICATORS:
        present = sum(1 for row in latest_rows if row.get(indicator.key) is not None)
        coverage = present / total_rows if total_rows else 0.0
        coverage_report.append(
            {
                "indicator": indicator.key,
                "label": indicator.label,
                "coverage": round(coverage, 4),
                "retained": coverage >= coverage_threshold,
            }
        )
        if coverage >= coverage_threshold:
            retained.append(indicator)
    return retained, coverage_report


def entropy_topsis(
    company_rows: list[dict[str, Any]],
    indicators: list[Indicator],
) -> dict[str, Any]:
    if len(company_rows) < 2:
        return {
            "weights": [],
            "rankings": [],
            "imputations": [],
            "message": "可用于 TOPSIS 的企业数量不足 2 家",
        }

    matrix: dict[str, list[float]] = {}
    imputations: list[dict[str, Any]] = []
    for indicator in indicators:
        available_values = [
            row[indicator.key] for row in company_rows if row.get(indicator.key) is not None
        ]
        if not available_values:
            continue
        fill_value = statistics.median(available_values)
        column = []
        for row in company_rows:
            value = row.get(indicator.key)
            if value is None:
                value = fill_value
                imputations.append(
                    {
                        "company_name": row["company_name"],
                        "indicator": indicator.key,
                        "imputed_value": round_optional(fill_value),
                    }
                )
            column.append(float(value))
        matrix[indicator.key] = column

    if not matrix:
        return {
            "weights": [],
            "rankings": [],
            "imputations": imputations,
            "message": "没有可用指标用于 TOPSIS 计算",
        }

    company_names = [row["company_name"] for row in company_rows]
    standardized: dict[str, list[float]] = {}
    weight_source: list[tuple[Indicator, list[float]]] = []

    for indicator in indicators:
        values = matrix.get(indicator.key)
        if not values:
            continue
        min_value = min(values)
        max_value = max(values)
        if math.isclose(max_value, min_value, rel_tol=1e-12, abs_tol=1e-12):
            scaled = [1.0 for _ in values]
        else:
            if indicator.direction == "benefit":
                scaled = [(value - min_value) / (max_value - min_value) for value in values]
            else:
                scaled = [(max_value - value) / (max_value - min_value) for value in values]
        scaled = [value + 1e-12 for value in scaled]
        standardized[indicator.key] = scaled
        weight_source.append((indicator, scaled))

    entropy_weights = []
    divergence_sum = 0.0
    entropy_values = []
    sample_count = len(company_rows)
    k = 1.0 / math.log(sample_count)

    for indicator, values in weight_source:
        total = sum(values)
        proportions = [value / total for value in values]
        entropy = -k * sum(p * math.log(p) for p in proportions if p > 0)
        divergence = 1 - entropy
        entropy_values.append((indicator, divergence))
        divergence_sum += divergence

    if math.isclose(divergence_sum, 0.0, abs_tol=1e-12):
        equal_weight = 1 / len(entropy_values)
        weights = {indicator.key: equal_weight for indicator, _ in entropy_values}
    else:
        weights = {
            indicator.key: divergence / divergence_sum
            for indicator, divergence in entropy_values
        }

    weighted_matrix: dict[str, list[float]] = {}
    for indicator, values in weight_source:
        weighted_matrix[indicator.key] = [value * weights[indicator.key] for value in values]
        entropy_weights.append(
            {
                "indicator": indicator.key,
                "label": indicator.label,
                "category": indicator.category,
                "direction": indicator.direction,
                "weight": round(weights[indicator.key], 6),
            }
        )

    rankings = []
    for row_index, company_name in enumerate(company_names):
        positive_distance = 0.0
        negative_distance = 0.0
        for indicator in indicators:
            values = weighted_matrix.get(indicator.key)
            if not values:
                continue
            positive_ideal = max(values)
            negative_ideal = min(values)
            current = values[row_index]
            positive_distance += (current - positive_ideal) ** 2
            negative_distance += (current - negative_ideal) ** 2

        positive_distance = math.sqrt(positive_distance)
        negative_distance = math.sqrt(negative_distance)
        denominator = positive_distance + negative_distance
        closeness = negative_distance / denominator if denominator else 0.0
        rankings.append(
            {
                "company_name": company_name,
                "topsis_score": round(closeness, 6),
            }
        )

    rankings.sort(key=lambda item: item["topsis_score"], reverse=True)
    for rank, item in enumerate(rankings, start=1):
        item["rank"] = rank

    return {
        "weights": entropy_weights,
        "rankings": rankings,
        "imputations": imputations,
        "message": "ok",
    }


def build_regression_dataset(
    grouped_rows: dict[str, list[dict[str, Any]]],
    candidate_names: list[str],
) -> list[dict[str, Any]]:
    dataset = []
    for company_name in candidate_names:
        for row in grouped_rows[company_name]:
            if row.get("rd_intensity") is None or row.get("revenue_growth") is None:
                continue
            dataset.append(
                {
                    "company_name": company_name,
                    "year": row["year"],
                    "rd_expense": row.get("rd_expense"),
                    "revenue": row.get("revenue"),
                    "rd_intensity": round_optional(row.get("rd_intensity")),
                    "revenue_growth": round_optional(row.get("revenue_growth")),
                }
            )
    return dataset


def simple_linear_regression(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) < 2:
        return {"message": "样本量不足，无法计算一元线性回归"}

    xs = [row["rd_intensity"] for row in rows if row["rd_intensity"] is not None]
    ys = [row["revenue_growth"] for row in rows if row["revenue_growth"] is not None]
    if len(xs) != len(rows) or len(ys) != len(rows):
        return {"message": "回归输入存在缺失值"}

    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    sxx = sum((value - mean_x) ** 2 for value in xs)
    if math.isclose(sxx, 0.0, abs_tol=1e-12):
        return {"message": "研发投入强度没有波动，无法估计斜率"}

    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    beta_1 = sxy / sxx
    beta_0 = mean_y - beta_1 * mean_x

    fitted = [beta_0 + beta_1 * x for x in xs]
    residual_sum = sum((y - y_hat) ** 2 for y, y_hat in zip(ys, fitted))
    total_sum = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1 - residual_sum / total_sum if not math.isclose(total_sum, 0.0) else 0.0

    return {
        "n": len(rows),
        "beta_0": round(beta_0, 6),
        "beta_1": round(beta_1, 6),
        "r_squared": round(r_squared, 6),
        "equation": "Growth_i = beta_0 + beta_1 * RD_i + u_i",
        "message": "ok",
    }


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
    return f"case_{digest}"


def main() -> None:
    args = parse_args()
    data_path = Path(args.data).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_dataset(data_path)
    grouped_rows = group_by_company(rows)
    if args.company not in grouped_rows:
        available = "、".join(sorted(grouped_rows))
        raise SystemExit(f"未找到目标企业：{args.company}\n可用企业：{available}")

    summaries = {
        company_name: build_company_summary(
            company_name=company_name,
            company_rows=company_rows,
            min_years=args.min_years,
            min_regression_obs=args.min_regression_obs,
            min_indicator_coverage=args.min_indicator_coverage,
        )
        for company_name, company_rows in grouped_rows.items()
    }

    target_summary = summaries[args.company]
    similarity_rows = build_similarity_table(args.company, summaries, args.similar_top_n)
    topsis_candidates = select_topsis_candidates(summaries)
    latest_candidate_rows = []
    for company_name in topsis_candidates:
        current = dict(latest_row(grouped_rows[company_name]))
        current["company_name"] = company_name
        latest_candidate_rows.append(current)

    retained_indicators, indicator_screening = retain_indicators(
        latest_candidate_rows,
        coverage_threshold=args.min_indicator_coverage,
    )
    topsis_result = entropy_topsis(latest_candidate_rows, retained_indicators)

    regression_candidates = [
        company_name
        for company_name, summary in summaries.items()
        if summary["gating"]["is_new_quality_related"] and summary["gating"]["regression_ready"]
    ]
    regression_rows = build_regression_dataset(grouped_rows, regression_candidates)
    regression_preview = simple_linear_regression(regression_rows)

    stem = report_stem(args.company)
    report_path = output_dir / f"{stem}_report.json"
    topsis_input_path = output_dir / f"{stem}_topsis_input.csv"
    regression_input_path = output_dir / f"{stem}_regression_input.csv"
    similar_path = output_dir / f"{stem}_similar_companies.csv"
    summary_path = output_dir / f"{stem}_company_summary.csv"

    topsis_export_rows = []
    for row in latest_candidate_rows:
        export_row = {"company_name": row["company_name"], "year": row["year"]}
        for indicator in retained_indicators:
            export_row[indicator.key] = round_optional(row.get(indicator.key))
        topsis_export_rows.append(export_row)

    summary_rows = []
    for summary in summaries.values():
        summary_rows.append(
            {
                "company_name": summary["company_name"],
                "case_status": summary["case_status"],
                "suitability_score": summary["suitability_score"],
                "industry": summary["industry"],
                "track": summary["track"],
                "latest_year": summary["latest_year"],
                "latest_indicator_coverage": summary["latest_indicator_coverage"],
                "regression_observations": summary["regression_observations"],
                "is_new_quality_related": summary["gating"]["is_new_quality_related"],
            }
        )
    summary_rows.sort(key=lambda item: item["suitability_score"], reverse=True)

    report = {
        "input": {
            "data_path": str(data_path),
            "target_company": args.company,
            "min_years": args.min_years,
            "min_regression_obs": args.min_regression_obs,
            "min_indicator_coverage": args.min_indicator_coverage,
        },
        "target_company_analysis": target_summary,
        "similar_companies": similarity_rows,
        "indicator_screening": indicator_screening,
        "topsis": {
            "candidate_companies": topsis_candidates,
            "retained_indicators": [indicator.key for indicator in retained_indicators],
            "weights": topsis_result["weights"],
            "rankings": topsis_result["rankings"],
            "imputations": topsis_result["imputations"],
            "message": topsis_result["message"],
        },
        "regression": {
            "candidate_companies": regression_candidates,
            "sample_size": len(regression_rows),
            "preview": regression_preview,
        },
        "recommendation": {
            "case_company": args.company,
            "decision": target_summary["case_status"],
            "next_action": (
                "可直接进入第三部分模型构建"
                if target_summary["case_status"] == "recommended"
                else "建议优先比较相似企业，再决定案例企业"
            ),
        },
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(topsis_input_path, topsis_export_rows)
    write_csv(regression_input_path, regression_rows)
    write_csv(similar_path, similarity_rows)
    write_csv(summary_path, summary_rows)

    print(f"目标企业：{args.company}")
    print(f"案例判定：{target_summary['case_status']}")
    print(f"适配评分：{target_summary['suitability_score']}")
    print(f"推荐动作：{report['recommendation']['next_action']}")
    print(f"TOPSIS 候选企业数：{len(topsis_candidates)}")
    print(f"回归样本量：{len(regression_rows)}")
    print("结果文件已生成。")


if __name__ == "__main__":
    main()
