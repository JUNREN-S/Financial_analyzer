#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熵权法 + TOPSIS 计算模块
Entropy Weight Method + TOPSIS Calculator Module
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class EntropyTOPSISCalculator:
    """
    基于熵权法的TOPSIS综合评价计算器
    
    算法流程：
    1. 数据标准化（Min-Max归一化）
    2. 计算熵权（确定指标权重）
    3. 构建加权标准化矩阵
    4. 确定正负理想解
    5. 计算欧氏距离
    6. 计算贴近度并排序
    """
    
    def __init__(self):
        self.raw_data = None
        self.normalized_data = None
        self.weights = None
        self.weighted_matrix = None
        self.positive_ideal = None
        self.negative_ideal = None
        self.scores = None
        self.ranks = None
        
    def normalize(self, data: pd.DataFrame, indicator_config: Dict) -> pd.DataFrame:
        """
        数据标准化处理
        
        Args:
            data: 原始数据DataFrame
            indicator_config: 指标配置，包含direction信息
            
        Returns:
            标准化后的DataFrame
        """
        normalized = pd.DataFrame()
        
        for col in data.columns:
            if col not in indicator_config:
                normalized[col] = data[col]
                continue
            
            config = indicator_config[col]
            values = data[col].astype(float)
            
            # Min-Max标准化
            min_val = values.min()
            max_val = values.max()
            
            if max_val - min_val == 0:
                normalized[col] = 0.5  # 所有值相同，设为中间值
            else:
                if config.get('direction', 'positive') == 'positive':
                    # 正向指标：越大越好
                    normalized[col] = (values - min_val) / (max_val - min_val)
                else:
                    # 负向指标：越小越好
                    normalized[col] = (max_val - values) / (max_val - min_val)
        
        self.normalized_data = normalized
        return normalized
    
    def calculate_entropy_weights(self, data: pd.DataFrame, epsilon: float = 1e-10) -> Dict[str, float]:
        """
        计算熵权
        
        步骤：
        1. 计算各指标值的比重 p_ij
        2. 计算信息熵 e_j
        3. 计算差异系数 d_j = 1 - e_j
        4. 计算权重 w_j = d_j / sum(d_j)
        
        Args:
            data: 标准化后的数据
            epsilon: 极小值，避免log(0)
            
        Returns:
            各指标权重字典
        """
        weights = {}
        n = len(data)  # 企业数量
        
        for col in data.columns:
            values = data[col].astype(float)
            
            # 处理缺失值
            values = values.fillna(values.mean() if values.mean() == values.mean() else 0)
            
            # 确保所有值为正（加极小值）
            values = values + epsilon
            
            # 计算比重 p_ij
            p = values / values.sum()
            
            # 计算信息熵 e_j = -k * sum(p_ij * ln(p_ij))
            k = 1 / np.log(n) if n > 1 else 1
            e = -k * (p * np.log(p)).sum()
            
            # 计算差异系数（冗余度）
            d = 1 - e
            
            weights[col] = {
                'entropy': e,
                'diversity': d,
                'weight': d  # 暂存，后面归一化
            }
        
        # 权重归一化
        total_diversity = sum(w['diversity'] for w in weights.values())
        
        if total_diversity == 0:
            # 所有指标熵相同，平均分配权重
            for col in weights:
                weights[col]['weight'] = 1 / len(weights)
        else:
            for col in weights:
                weights[col]['weight'] = weights[col]['diversity'] / total_diversity
        
        self.weights = {col: w['weight'] for col, w in weights.items()}
        self.weight_details = weights
        
        return self.weights
    
    def build_weighted_matrix(self, data: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
        """
        构建加权标准化矩阵
        
        V_ij = w_j * Z_ij
        """
        weighted = pd.DataFrame()
        
        for col in data.columns:
            if col in weights:
                weighted[col] = data[col] * weights[col]
            else:
                weighted[col] = data[col]
        
        self.weighted_matrix = weighted
        return weighted
    
    def find_ideal_solutions(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        确定正负理想解
        
        A+ = [max(v_1), max(v_2), ..., max(v_n)]  最优解
        A- = [min(v_1), min(v_2), ..., min(v_n)]  最劣解
        """
        self.positive_ideal = data.max()
        self.negative_ideal = data.min()
        
        return self.positive_ideal, self.negative_ideal
    
    def calculate_distances(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        计算各企业与正负理想解的欧氏距离
        
        D+ = sqrt(sum((v_ij - A+_j)^2))
        D- = sqrt(sum((v_ij - A-_j)^2))
        """
        # 计算与正理想解的距离
        d_positive = np.sqrt(((data - self.positive_ideal) ** 2).sum(axis=1))
        
        # 计算与负理想解的距离
        d_negative = np.sqrt(((data - self.negative_ideal) ** 2).sum(axis=1))
        
        return d_positive, d_negative
    
    def calculate_closeness(self, d_positive: pd.Series, d_negative: pd.Series) -> pd.Series:
        """
        计算贴近度（综合评价得分）
        
        C_i = D-_i / (D+_i + D-_i)
        
        C_i ∈ [0, 1]，越接近1表示越接近最优水平
        """
        closeness = d_negative / (d_positive + d_negative)
        
        # 处理可能的除零问题
        closeness = closeness.fillna(0.5)
        
        self.scores = closeness
        return closeness
    
    def rank_companies(self, scores: pd.Series, company_names: pd.Series) -> pd.DataFrame:
        """
        根据得分排序
        """
        result = pd.DataFrame({
            '排名': range(1, len(scores) + 1),
            '公司名称': company_names,
            '综合得分': scores.values,
        })
        
        # 按得分降序排序
        result = result.sort_values('综合得分', ascending=False).reset_index(drop=True)
        result['排名'] = range(1, len(result) + 1)
        
        self.ranks = result
        return result
    
    def calculate_dimension_scores(self, data: pd.DataFrame, dimensions: Dict[str, List[str]], 
                                    company_names: pd.Series) -> pd.DataFrame:
        """
        计算各维度得分
        
        Args:
            data: 加权标准化矩阵
            dimensions: 维度配置，如 {'运营能力': ['指标1', '指标2']}
            company_names: 企业名称
            
        Returns:
            各维度得分DataFrame
        """
        dimension_scores = pd.DataFrame({'公司名称': company_names})
        
        for dim_name, indicators in dimensions.items():
            # 获取该维度的指标列
            dim_cols = [col for col in indicators if col in data.columns]
            if dim_cols:
                # 计算维度内各指标的平均值作为维度得分
                dimension_scores[dim_name] = data[dim_cols].mean(axis=1)
        
        return dimension_scores
    
    def run_analysis(self, raw_data: pd.DataFrame, indicator_config: Dict,
                     dimensions: Dict[str, List[str]], company_col: str = '股票名称') -> Dict:
        """
        执行完整的分析流程
        
        Returns:
            包含所有结果的字典
        """
        # 1. 分离企业信息和指标数据
        company_info = raw_data[['股票代码', '股票名称']] if '股票代码' in raw_data.columns else raw_data[[company_col]]
        
        # 获取指标列（排除元数据列）
        exclude_cols = ['股票代码', '股票名称', '报告期']
        indicator_cols = [col for col in raw_data.columns if col not in exclude_cols]
        
        # 过滤出配置中定义的指标
        valid_indicators = {col: indicator_config[col] for col in indicator_cols if col in indicator_config}
        indicator_data = raw_data[list(valid_indicators.keys())]
        
        print(f"分析指标: {list(valid_indicators.keys())}")
        
        # 2. 数据标准化
        print("正在进行数据标准化...")
        normalized = self.normalize(indicator_data, valid_indicators)
        
        # 3. 计算熵权
        print("正在计算熵权...")
        weights = self.calculate_entropy_weights(normalized)
        
        # 打印权重信息
        print("\n指标权重:")
        for col, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            detail = self.weight_details[col]
            print(f"  {col}: 权重={weight:.4f}, 熵值={detail['entropy']:.4f}")
        
        # 4. 构建加权矩阵
        weighted = self.build_weighted_matrix(normalized, weights)
        
        # 5. 确定理想解
        self.find_ideal_solutions(weighted)
        
        # 6. 计算距离
        d_pos, d_neg = self.calculate_distances(weighted)
        
        # 7. 计算贴近度
        scores = self.calculate_closeness(d_pos, d_neg)
        
        # 8. 排序
        ranks = self.rank_companies(scores, company_info[company_col])
        
        # 9. 计算各维度得分
        dimension_scores = self.calculate_dimension_scores(weighted, dimensions, company_info[company_col])
        
        # 10. 整合结果
        results = {
            'raw_data': raw_data,
            'normalized_data': normalized,
            'weights': weights,
            'weight_details': self.weight_details,
            'weighted_matrix': weighted,
            'positive_ideal': self.positive_ideal,
            'negative_ideal': self.negative_ideal,
            'distances_positive': d_pos,
            'distances_negative': d_neg,
            'scores': scores,
            'ranks': ranks,
            'dimension_scores': dimension_scores,
            'company_info': company_info
        }
        
        return results


if __name__ == "__main__":
    # 测试代码
    calculator = EntropyTOPSISCalculator()
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '000333'],
        '股票名称': ['平安银行', '万科A', '美的集团'],
        'ROE': [0.10, 0.15, 0.18],
        '资产负债率': [0.92, 0.80, 0.65],
        '营收增长率': [0.05, 0.12, 0.08],
    })
    
    indicator_config = {
        'ROE': {'direction': 'positive'},
        '资产负债率': {'direction': 'negative'},
        '营收增长率': {'direction': 'positive'},
    }
    
    dimensions = {
        '盈利能力': ['ROE'],
        '偿债能力': ['资产负债率'],
        '成长能力': ['营收增长率'],
    }
    
    results = calculator.run_analysis(test_data, indicator_config, dimensions)
    
    print("\n排名结果:")
    print(results['ranks'])
