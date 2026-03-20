#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险评估模块 - Risk Assessment Module
基于财务指标的企业风险评估模型
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class RiskLevel:
    """风险等级定义"""
    name: str
    code: str
    color: str
    description: str
    score_range: Tuple[float, float]


RISK_LEVELS = {
    'low': RiskLevel('低风险', 'LOW', '#2ecc71', '财务状况稳健，各项指标良好', (0.7, 1.0)),
    'medium': RiskLevel('中等风险', 'MEDIUM', '#f39c12', '财务状况一般，需关注部分指标', (0.4, 0.7)),
    'high': RiskLevel('高风险', 'HIGH', '#e74c3c', '财务状况较差，存在明显风险', (0.0, 0.4)),
}


class RiskAssessor:
    """
    企业综合风险评估器
    
    评估维度：
    1. 财务杠杆风险（资产负债率）
    2. 流动性风险（流动比率、速动比率）
    3. 盈利质量风险（ROE稳定性、现金流质量）
    4. 经营风险（营收波动、成本控制能力）
    5. 成长可持续性风险（增长质量）
    """
    
    def __init__(self):
        self.risk_thresholds = {
            'debt_ratio': {'safe': 0.50, 'warning': 0.65, 'danger': 0.80},
            'current_ratio': {'safe': 2.0, 'warning': 1.5, 'danger': 1.0},
            'quick_ratio': {'safe': 1.5, 'warning': 1.0, 'danger': 0.8},
            'roe': {'safe': 0.15, 'warning': 0.10, 'danger': 0.05},
            'ocf_ratio': {'safe': 0.20, 'warning': 0.10, 'danger': 0.05},
            'interest_coverage': {'safe': 5.0, 'warning': 3.0, 'danger': 1.5},
        }
    
    def assess_financial_leverage_risk(self, debt_ratio: float) -> Dict:
        """
        评估财务杠杆风险（资产负债率）
        """
        if pd.isna(debt_ratio):
            return {'score': 0.5, 'level': 'unknown', 'desc': '数据缺失'}
        
        thresholds = self.risk_thresholds['debt_ratio']
        
        if debt_ratio < thresholds['safe']:
            return {'score': 1.0, 'level': 'low', 'desc': '杠杆水平健康'}
        elif debt_ratio < thresholds['warning']:
            return {'score': 0.7, 'level': 'medium', 'desc': '杠杆水平适中'}
        elif debt_ratio < thresholds['danger']:
            return {'score': 0.4, 'level': 'medium-high', 'desc': '杠杆水平偏高'}
        else:
            return {'score': 0.2, 'level': 'high', 'desc': '杠杆水平过高，偿债压力大'}
    
    def assess_liquidity_risk(self, current_ratio: float, quick_ratio: float) -> Dict:
        """
        评估流动性风险
        """
        if pd.isna(current_ratio) and pd.isna(quick_ratio):
            return {'score': 0.5, 'level': 'unknown', 'desc': '数据缺失'}
        
        # 使用流动比率和速动比率的加权评分
        current_score = 0
        quick_score = 0
        
        if not pd.isna(current_ratio):
            if current_ratio >= 2.0:
                current_score = 1.0
            elif current_ratio >= 1.5:
                current_score = 0.8
            elif current_ratio >= 1.0:
                current_score = 0.5
            else:
                current_score = 0.2
        
        if not pd.isna(quick_ratio):
            if quick_ratio >= 1.5:
                quick_score = 1.0
            elif quick_ratio >= 1.0:
                quick_score = 0.8
            elif quick_ratio >= 0.8:
                quick_score = 0.5
            else:
                quick_score = 0.2
        
        # 综合评分
        if current_score > 0 and quick_score > 0:
            avg_score = (current_score * 0.6 + quick_score * 0.4)
        else:
            avg_score = max(current_score, quick_score)
        
        if avg_score >= 0.8:
            return {'score': avg_score, 'level': 'low', 'desc': '流动性充裕'}
        elif avg_score >= 0.5:
            return {'score': avg_score, 'level': 'medium', 'desc': '流动性一般'}
        else:
            return {'score': avg_score, 'level': 'high', 'desc': '流动性紧张'}
    
    def assess_profitability_risk(self, roe: float, roa: float, net_margin: float) -> Dict:
        """
        评估盈利质量风险
        """
        if pd.isna(roe):
            return {'score': 0.5, 'level': 'unknown', 'desc': 'ROE数据缺失'}
        
        # ROE评分
        if roe >= 0.15:
            roe_score = 1.0
        elif roe >= 0.10:
            roe_score = 0.8
        elif roe >= 0.05:
            roe_score = 0.5
        else:
            roe_score = 0.2
        
        # ROA评分（如果有数据）
        roa_score = 0.5
        if not pd.isna(roa):
            if roa >= 0.08:
                roa_score = 1.0
            elif roa >= 0.05:
                roa_score = 0.7
            elif roa >= 0.02:
                roa_score = 0.4
            else:
                roa_score = 0.2
        
        # 净利率评分（如果有数据）
        margin_score = 0.5
        if not pd.isna(net_margin):
            if net_margin >= 0.20:
                margin_score = 1.0
            elif net_margin >= 0.10:
                margin_score = 0.7
            elif net_margin >= 0.05:
                margin_score = 0.4
            else:
                margin_score = 0.2
        
        avg_score = (roe_score + roa_score + margin_score) / 3
        
        if avg_score >= 0.8:
            return {'score': avg_score, 'level': 'low', 'desc': '盈利能力优秀'}
        elif avg_score >= 0.5:
            return {'score': avg_score, 'level': 'medium', 'desc': '盈利能力一般'}
        else:
            return {'score': avg_score, 'level': 'high', 'desc': '盈利能力较弱'}
    
    def assess_cashflow_risk(self, ocf_ratio: float, profit_cash_ratio: float) -> Dict:
        """
        评估现金流风险
        """
        if pd.isna(ocf_ratio) and pd.isna(profit_cash_ratio):
            return {'score': 0.5, 'level': 'unknown', 'desc': '现金流数据缺失'}
        
        # 经营现金流比率评分
        ocf_score = 0.5
        if not pd.isna(ocf_ratio):
            if ocf_ratio >= 0.20:
                ocf_score = 1.0
            elif ocf_ratio >= 0.10:
                ocf_score = 0.7
            elif ocf_ratio >= 0.05:
                ocf_score = 0.4
            else:
                ocf_score = 0.2
        
        # 净利润现金含量评分
        cash_score = 0.5
        if not pd.isna(profit_cash_ratio):
            if profit_cash_ratio >= 1.2:
                cash_score = 1.0
            elif profit_cash_ratio >= 1.0:
                cash_score = 0.8
            elif profit_cash_ratio >= 0.8:
                cash_score = 0.5
            else:
                cash_score = 0.2
        
        avg_score = (ocf_score + cash_score) / 2 if not pd.isna(ocf_ratio) and not pd.isna(profit_cash_ratio) else max(ocf_score, cash_score)
        
        if avg_score >= 0.8:
            return {'score': avg_score, 'level': 'low', 'desc': '现金流健康'}
        elif avg_score >= 0.5:
            return {'score': avg_score, 'level': 'medium', 'desc': '现金流一般'}
        else:
            return {'score': avg_score, 'level': 'high', 'desc': '现金流紧张'}
    
    def assess_operation_risk(self, turnover_ratio: float, inventory_turnover: float) -> Dict:
        """
        评估经营效率风险
        """
        if pd.isna(turnover_ratio):
            return {'score': 0.5, 'level': 'unknown', 'desc': '周转率数据缺失'}
        
        # 总资产周转率评分
        if turnover_ratio >= 1.0:
            score = 1.0
        elif turnover_ratio >= 0.7:
            score = 0.8
        elif turnover_ratio >= 0.4:
            score = 0.5
        else:
            score = 0.3
        
        if score >= 0.8:
            return {'score': score, 'level': 'low', 'desc': '运营效率优秀'}
        elif score >= 0.5:
            return {'score': score, 'level': 'medium', 'desc': '运营效率一般'}
        else:
            return {'score': score, 'level': 'high', 'desc': '运营效率较低'}
    
    def assess_company_risk(self, company_data: pd.Series) -> Dict:
        """
        综合评估单个企业风险
        """
        # 各维度评估
        leverage = self.assess_financial_leverage_risk(company_data.get('资产负债率'))
        liquidity = self.assess_liquidity_risk(
            company_data.get('流动比率'),
            company_data.get('速动比率')
        )
        profitability = self.assess_profitability_risk(
            company_data.get('净资产收益率ROE'),
            company_data.get('总资产收益率ROA'),
            company_data.get('销售净利率')
        )
        cashflow = self.assess_cashflow_risk(
            company_data.get('经营现金流比率'),
            company_data.get('净利润现金含量')
        )
        operation = self.assess_operation_risk(
            company_data.get('总资产周转率'),
            company_data.get('存货周转率')
        )
        
        # 综合风险评分（加权平均）
        weights = {
            'leverage': 0.25,
            'liquidity': 0.20,
            'profitability': 0.25,
            'cashflow': 0.20,
            'operation': 0.10,
        }
        
        risk_scores = {
            'leverage': leverage['score'],
            'liquidity': liquidity['score'],
            'profitability': profitability['score'],
            'cashflow': cashflow['score'],
            'operation': operation['score'],
        }
        
        # 计算加权风险得分
        total_weight = 0
        weighted_score = 0
        for key, weight in weights.items():
            if risk_scores[key] > 0:  # 排除缺失数据
                weighted_score += risk_scores[key] * weight
                total_weight += weight
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.5
        
        # 确定整体风险等级
        if overall_score >= 0.7:
            overall_level = 'low'
            overall_desc = '低风险'
        elif overall_score >= 0.4:
            overall_level = 'medium'
            overall_desc = '中等风险'
        else:
            overall_level = 'high'
            overall_desc = '高风险'
        
        return {
            'company_name': company_data.get('股票名称', 'Unknown'),
            'company_code': company_data.get('股票代码', 'Unknown'),
            'overall_score': overall_score,
            'overall_level': overall_level,
            'overall_desc': overall_desc,
            'dimension_scores': {
                '财务杠杆': leverage,
                '流动性': liquidity,
                '盈利能力': profitability,
                '现金流': cashflow,
                '运营效率': operation,
            },
            'risk_weights': weights
        }
    
    def assess_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        批量评估企业风险
        """
        results = []
        
        for idx, row in data.iterrows():
            assessment = self.assess_company_risk(row)
            results.append({
                '股票代码': assessment['company_code'],
                '股票名称': assessment['company_name'],
                '风险得分': assessment['overall_score'],
                '风险等级': assessment['overall_desc'],
                '杠杆风险': assessment['dimension_scores']['财务杠杆']['desc'],
                '流动性风险': assessment['dimension_scores']['流动性']['desc'],
                '盈利风险': assessment['dimension_scores']['盈利能力']['desc'],
                '现金流风险': assessment['dimension_scores']['现金流']['desc'],
            })
        
        return pd.DataFrame(results)
    
    def get_risk_matrix_data(self, data: pd.DataFrame, topsis_scores: pd.Series) -> pd.DataFrame:
        """
        生成风险-收益矩阵数据（用于散点图）
        """
        risk_results = self.assess_batch(data)
        
        matrix_data = pd.DataFrame({
            '股票代码': risk_results['股票代码'],
            '股票名称': risk_results['股票名称'],
            '风险得分': risk_results['风险得分'],
            '综合得分': topsis_scores.values if len(topsis_scores) == len(risk_results) else [0.5] * len(risk_results),
            '风险等级': risk_results['风险等级'],
        })
        
        return matrix_data


if __name__ == "__main__":
    # 测试代码
    assessor = RiskAssessor()
    
    # 测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002'],
        '股票名称': ['平安银行', '万科A'],
        '资产负债率': [0.92, 0.80],
        '流动比率': [1.2, 1.5],
        '速动比率': [1.0, 0.8],
        '净资产收益率ROE': [0.10, 0.12],
    })
    
    results = assessor.assess_batch(test_data)
    print(results)
