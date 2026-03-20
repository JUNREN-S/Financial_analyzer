#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案例筛选前置模块 - Case Selector Module
基于 AI_Agents 工具，实现企业案例适配性评估与相似企业推荐

功能：
1. 评估企业是否适合作为分析案例
2. 若不合适，推荐相似的可替代企业
3. 为 TOPSIS 分析准备筛选后的企业池
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json


# 新质生产力关键词（用于判定企业是否属于该领域）
NEW_QUALITY_KEYWORDS = {
    "人工智能", "AI", "大模型", "算力", "机器人", "半导体", "芯片",
    "工业软件", "工业互联网", "高端装备", "智能制造", "数据要素",
    "自动驾驶", "低空经济", "新材料", "生物制造"
}


@dataclass
class Indicator:
    """指标定义"""
    key: str
    label: str
    category: str
    direction: str  # 'benefit' = 越大越好, 'cost' = 越小越好


# 核心评估指标（用于案例筛选）
SCREENING_INDICATORS = [
    Indicator("roe", "ROE", "财务质量", "benefit"),
    Indicator("operating_cashflow", "经营现金流", "财务质量", "benefit"),
    Indicator("rd_intensity", "研发投入强度", "创新成长", "benefit"),
    Indicator("revenue_growth", "营业收入增长率", "创新成长", "benefit"),
    Indicator("patent_count", "专利数量", "创新成长", "benefit"),
    Indicator("industry_growth_space", "行业成长空间", "创新成长", "benefit"),
    Indicator("asset_liability_ratio", "资产负债率", "风险控制", "cost"),
    Indicator("customer_concentration", "客户集中度", "风险控制", "cost"),
    Indicator("policy_sensitivity", "政策敏感度", "风险控制", "cost"),
    Indicator("sentiment_risk", "舆情风险", "风险控制", "cost"),
]


class CaseSelector:
    """
    企业案例筛选器
    
    前置筛选流程：
    1. 读取企业年度面板数据
    2. 计算衍生指标（RD强度、营收增长率）
    3. 评估企业适配性（新质生产力关联、数据完整性、连续性）
    4. 若目标企业不合适，推荐相似企业
    5. 输出筛选后的企业池供 TOPSIS 分析
    """
    
    def __init__(self, 
                 min_years: int = 3,
                 min_indicator_coverage: float = 0.7,
                 min_regression_obs: int = 3):
        self.min_years = min_years
        self.min_indicator_coverage = min_indicator_coverage
        self.min_regression_obs = min_regression_obs
        
    def load_data(self, csv_path: str) -> pd.DataFrame:
        """加载企业数据 CSV"""
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        print(f"数据加载完成: {len(df)} 条记录，{df['company_name'].nunique()} 家企业")
        return df
    
    def preprocess(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        数据预处理
        - 按企业分组
        - 计算衍生指标（RD强度、营收增长率）
        - 识别新质生产力关联
        """
        grouped = {}
        
        for company in df['company_name'].unique():
            company_df = df[df['company_name'] == company].sort_values('year')
            records = []
            
            prev_revenue = None
            for _, row in company_df.iterrows():
                record = row.to_dict()
                
                # 计算 RD 强度
                if pd.notna(row.get('rd_expense')) and pd.notna(row.get('revenue')) and row['revenue'] > 0:
                    record['rd_intensity'] = row['rd_expense'] / row['revenue']
                else:
                    record['rd_intensity'] = None
                
                # 计算营收增长率
                if prev_revenue is not None and prev_revenue > 0 and pd.notna(row.get('revenue')):
                    record['revenue_growth'] = (row['revenue'] - prev_revenue) / prev_revenue
                else:
                    record['revenue_growth'] = None
                
                prev_revenue = row.get('revenue')
                
                # 判定新质生产力关联
                record['is_new_quality'] = self._check_new_quality(row)
                
                # 关键词命中
                record['keyword_hits'] = self._keyword_hits(row)
                
                records.append(record)
            
            grouped[company] = records
        
        return grouped
    
    def _check_new_quality(self, row: pd.Series) -> bool:
        """检查企业是否与新质生产力相关"""
        # 检查显式标记
        if str(row.get('new_quality_direction', '')).strip().lower() in ['是', 'yes', 'y', '1', 'true']:
            return True
        
        # 检查关键词命中
        text_fields = ['industry', 'main_business', 'core_products', 'track', 
                      'annual_report_summary', 'website_intro']
        corpus = ' '.join([str(row.get(f, '')) for f in text_fields]).lower()
        
        hits = sum(1 for kw in NEW_QUALITY_KEYWORDS if kw.lower() in corpus)
        return hits >= 2  # 命中2个以上关键词视为相关
    
    def _keyword_hits(self, row: pd.Series) -> List[str]:
        """返回命中的新质生产力关键词"""
        text_fields = ['industry', 'main_business', 'core_products', 'track',
                      'annual_report_summary', 'website_intro']
        corpus = ' '.join([str(row.get(f, '')) for f in text_fields]).lower()
        
        return [kw for kw in NEW_QUALITY_KEYWORDS if kw.lower() in corpus]
    
    def evaluate_company(self, company_name: str, records: List[Dict]) -> Dict:
        """
        评估单个企业的案例适配性
        """
        if not records:
            return {'error': '无数据'}
        
        latest = records[-1]  # 最新年度数据
        
        # 基础信息完整性
        profile_fields = ['industry', 'main_business', 'core_products', 'track']
        profile_complete = sum(1 for f in profile_fields if pd.notna(latest.get(f)) and str(latest.get(f)).strip()) / len(profile_fields)
        
        # 指标覆盖率
        indicator_coverage = sum(1 for ind in SCREENING_INDICATORS if pd.notna(latest.get(ind.key))) / len(SCREENING_INDICATORS)
        
        # 年份连续性
        available_years = len(records)
        
        # 回归可用观测数（有 RD 强度和营收增长率的数据点）
        regression_obs = sum(1 for r in records if pd.notna(r.get('rd_intensity')) and pd.notna(r.get('revenue_growth')))
        
        # 新质生产力关联
        is_new_quality = any(r.get('is_new_quality') for r in records)
        keyword_hits = latest.get('keyword_hits', [])
        
        # 适配评分计算（加权）
        relevance_score = 1.0 if is_new_quality else min(len(keyword_hits) / 3, 1.0)
        suitability = (
            0.25 * relevance_score +
            0.2 * profile_complete +
            0.2 * min(available_years / max(self.min_years, 1), 1.0) +
            0.2 * indicator_coverage +
            0.1 * min(regression_obs / max(self.min_regression_obs, 1), 1.0)
        ) * 100
        
        # 判定是否通过筛选
        gating = {
            'is_new_quality': is_new_quality,
            'has_min_years': available_years >= self.min_years,
            'indicator_coverage_ok': indicator_coverage >= self.min_indicator_coverage,
            'regression_ready': regression_obs >= self.min_regression_obs,
            'profile_complete': profile_complete >= 0.8,
        }
        
        # 找出不足项
        gaps = []
        if not gating['is_new_quality']:
            gaps.append("与新质生产力主题关联度不足")
        if not gating['has_min_years']:
            gaps.append(f"连续年份不足 {self.min_years} 年")
        if not gating['indicator_coverage_ok']:
            gaps.append("指标覆盖率不足")
        if not gating['regression_ready']:
            gaps.append(f"回归可用观测数不足 {self.min_regression_obs}")
        
        # 案例状态
        if not gaps:
            case_status = "recommended"  # 推荐
        elif suitability >= 60:
            case_status = "conditional"  # 有条件可用
        else:
            case_status = "not_recommended"  # 不推荐
        
        return {
            'company_name': company_name,
            'case_status': case_status,
            'suitability_score': round(suitability, 2),
            'years': [r['year'] for r in records],
            'latest_year': latest['year'],
            'industry': latest.get('industry', ''),
            'track': latest.get('track', ''),
            'is_new_quality': is_new_quality,
            'keyword_hits': keyword_hits,
            'indicator_coverage': round(indicator_coverage, 4),
            'regression_obs': regression_obs,
            'gating': gating,
            'gaps': gaps,
            'latest_metrics': {
                'revenue': latest.get('revenue'),
                'net_profit': latest.get('net_profit'),
                'roe': latest.get('roe'),
                'asset_liability_ratio': latest.get('asset_liability_ratio'),
                'rd_intensity': round(latest.get('rd_intensity'), 4) if pd.notna(latest.get('rd_intensity')) else None,
                'revenue_growth_pct': round(latest.get('revenue_growth') * 100, 2) if pd.notna(latest.get('revenue_growth')) else None,
            },
            'records': records,
        }
    
    def calculate_similarity(self, target: Dict, candidate: Dict) -> float:
        """计算两家企业的相似度分数"""
        score = 0.0
        
        # 行业匹配
        if target['industry'] and target['industry'] == candidate['industry']:
            score += 35
        elif target['industry'] and target['industry'] in candidate.get('industry', ''):
            score += 20
        
        # 赛道匹配
        if target['track'] and target['track'] == candidate['track']:
            score += 25
        elif target['track'] and target['track'] in candidate.get('track', ''):
            score += 15
        
        # 新质生产力关联一致性
        if target['is_new_quality'] == candidate['is_new_quality']:
            score += 15
        
        # 营收规模接近度
        t_rev = target['latest_metrics'].get('revenue')
        c_rev = candidate['latest_metrics'].get('revenue')
        if t_rev and c_rev and t_rev > 0 and c_rev > 0:
            distance = abs(t_rev - c_rev) / max(t_rev, c_rev)
            score += max(0, 15 * (1 - distance))
        
        # 研发强度接近度
        t_rd = target['latest_metrics'].get('rd_intensity')
        c_rd = candidate['latest_metrics'].get('rd_intensity')
        if t_rd is not None and c_rd is not None:
            rd_dist = abs(t_rd - c_rd)
            score += max(0, 10 * (1 - min(rd_dist / 0.2, 1.0)))
        
        return round(score, 2)
    
    def find_similar_companies(self, target_name: str, summaries: Dict[str, Dict], top_n: int = 5) -> List[Dict]:
        """为目标企业找相似企业"""
        if target_name not in summaries:
            return []
        
        target = summaries[target_name]
        candidates = []
        
        for name, summary in summaries.items():
            if name == target_name:
                continue
            
            candidates.append({
                'company_name': name,
                'similarity_score': self.calculate_similarity(target, summary),
                'case_status': summary['case_status'],
                'suitability_score': summary['suitability_score'],
                'industry': summary['industry'],
                'track': summary['track'],
                'latest_year': summary['latest_year'],
            })
        
        # 按相似度和适配评分排序
        candidates.sort(key=lambda x: (x['similarity_score'], x['suitability_score']), reverse=True)
        return candidates[:top_n]
    
    def select_for_topsis(self, summaries: Dict[str, Dict]) -> List[str]:
        """筛选适合 TOPSIS 分析的企业"""
        selected = []
        for name, summary in summaries.items():
            gating = summary['gating']
            if (gating['is_new_quality'] and 
                gating['has_min_years'] and 
                gating['indicator_coverage_ok']):
                selected.append(name)
        return selected
    
    def run(self, csv_path: str, target_company: Optional[str] = None, top_n: int = 5) -> Dict:
        """
        执行完整筛选流程
        
        Args:
            csv_path: 数据 CSV 路径
            target_company: 目标企业（可选）
            top_n: 推荐相似企业数量
            
        Returns:
            筛选结果字典
        """
        print("=" * 60)
        print("案例筛选前置模块")
        print("=" * 60)
        
        # 1. 加载数据
        print("\n【步骤1】加载企业数据...")
        df = self.load_data(csv_path)
        
        # 2. 预处理
        print("【步骤2】数据预处理...")
        grouped = self.preprocess(df)
        print(f"  - 计算 RD 强度、营收增长率")
        print(f"  - 识别新质生产力关联")
        
        # 3. 评估所有企业
        print("\n【步骤3】评估企业适配性...")
        summaries = {}
        for company, records in grouped.items():
            summaries[company] = self.evaluate_company(company, records)
        
        # 显示评估结果摘要
        recommended = [s for s in summaries.values() if s['case_status'] == 'recommended']
        conditional = [s for s in summaries.values() if s['case_status'] == 'conditional']
        not_recommended = [s for s in summaries.values() if s['case_status'] == 'not_recommended']
        
        print(f"\n  评估结果:")
        print(f"  - 推荐: {len(recommended)} 家")
        print(f"  - 有条件可用: {len(conditional)} 家")
        print(f"  - 不推荐: {len(not_recommended)} 家")
        
        # 4. 如果指定了目标企业，进行专项分析
        similar_companies = []
        if target_company:
            print(f"\n【步骤4】目标企业分析: {target_company}")
            
            if target_company not in summaries:
                print(f"  错误: 未找到目标企业 '{target_company}'")
                available = "、".join(sorted(summaries.keys()))
                print(f"  可用企业: {available}")
                return {'error': f'未找到目标企业: {target_company}'}
            
            target_summary = summaries[target_company]
            print(f"\n  案例判定: {target_summary['case_status']}")
            print(f"  适配评分: {target_summary['suitability_score']}")
            
            if target_summary['gaps']:
                print(f"\n  不足项:")
                for gap in target_summary['gaps']:
                    print(f"    - {gap}")
            
            # 如果不推荐，找相似企业
            if target_summary['case_status'] != 'recommended':
                print(f"\n【步骤5】推荐相似企业（Top {top_n}）...")
                similar_companies = self.find_similar_companies(target_company, summaries, top_n)
                
                print(f"\n  {'排名':<4} {'企业名称':<12} {'相似度':<8} {'适配评分':<8} {'状态':<10}")
                print(f"  {'-'*50}")
                for i, sim in enumerate(similar_companies, 1):
                    print(f"  {i:<4} {sim['company_name']:<12} {sim['similarity_score']:<8} {sim['suitability_score']:<8} {sim['case_status']:<10}")
        
        # 5. 筛选适合 TOPSIS 的企业
        topsis_candidates = self.select_for_topsis(summaries)
        print(f"\n【步骤6】筛选 TOPSIS 候选企业...")
        print(f"  符合条件: {len(topsis_candidates)} 家")
        
        # 6. 准备输出
        result = {
            'summaries': summaries,
            'target_company': target_company,
            'target_summary': summaries.get(target_company) if target_company else None,
            'similar_companies': similar_companies,
            'topsis_candidates': topsis_candidates,
            'statistics': {
                'total': len(summaries),
                'recommended': len(recommended),
                'conditional': len(conditional),
                'not_recommended': len(not_recommended),
                'topsis_ready': len(topsis_candidates),
            }
        }
        
        print("\n" + "=" * 60)
        print("筛选完成!")
        print("=" * 60)
        
        return result
    
    def export_for_topsis(self, result: Dict, output_path: str):
        """
        导出筛选后的数据供 TOPSIS 分析
        """
        summaries = result['summaries']
        candidates = result['topsis_candidates']
        
        # 提取最新年度数据
        rows = []
        for company in candidates:
            summary = summaries[company]
            latest_record = summary['records'][-1] if summary['records'] else {}
            
            row = {
                '股票名称': company,
                '年份': summary['latest_year'],
                '行业': summary['industry'],
            }
            
            # 添加指标数据
            for ind in SCREENING_INDICATORS:
                row[ind.label] = latest_record.get(ind.key)
            
            rows.append(row)
        
        # 保存 CSV
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\nTOPSIS 输入数据已保存: {output_path}")
        
        return df


def main():
    """测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='案例筛选前置模块')
    parser.add_argument('--data', '-d', required=True, help='输入 CSV 文件路径')
    parser.add_argument('--company', '-c', help='目标企业名称')
    parser.add_argument('--output', '-o', help='TOPSIS 输出文件路径')
    parser.add_argument('--top-n', type=int, default=5, help='推荐相似企业数量')
    
    args = parser.parse_args()
    
    # 执行筛选
    selector = CaseSelector()
    result = selector.run(args.data, args.company, args.top_n)
    
    # 导出 TOPSIS 数据
    if args.output and result.get('topsis_candidates'):
        selector.export_for_topsis(result, args.output)


if __name__ == "__main__":
    main()
