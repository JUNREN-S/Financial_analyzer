#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 数据加载模块 - Excel Data Loader Module
支持从 Excel 文件读取企业财务数据进行分析
继承自 a.py 的功能，与原有 skill 体系集成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class ExcelDataLoader:
    """
    Excel 财务数据加载器

    支持格式：
    - 行：企业（公司简称/股票名称/公司名称）
    - 列：财务指标
    - 第一列或指定列为企业名称索引
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.raw_data = None
        self.company_names = None
        self.indicator_names = None
        self.indicator_directions = None

    def load_data(self,
                  sheet_name: Optional[str] = None,
                  index_col: Optional[str] = '公司简称',
                  header_row: int = 0) -> pd.DataFrame:
        """
        从 Excel 加载数据
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        # 读取 Excel
        df = pd.read_excel(
            self.file_path,
            sheet_name=0 if sheet_name is None else sheet_name,
            header=header_row
        )

        # 设置企业名称为索引
        if index_col in df.columns:
            df = df.set_index(index_col)
        elif df.index.name is not None:
            pass
        else:
            for col in ['公司名称', '股票名称', '企业名称', 'name', 'company']:
                if col in df.columns:
                    df = df.set_index(col)
                    break

        self.raw_data = df
        
        # 过滤掉企业名称为空的行（处理 Excel 中多余空行的情况）
        if self.raw_data.index.isna().any():
            print(f"  过滤掉 {self.raw_data.index.isna().sum()} 个空行")
            self.raw_data = self.raw_data[self.raw_data.index.notna()]
        
        # 过滤掉企业名称为空字符串的行
        empty_names = self.raw_data.index == ''
        if empty_names.any():
            print(f"  过滤掉 {empty_names.sum()} 个企业名称为空的行")
            self.raw_data = self.raw_data[~empty_names]
            
        # 使用过滤后的数据更新企业名称和指标名称
        self.company_names = self.raw_data.index.tolist()
        self.indicator_names = self.raw_data.columns.tolist()

        return self.raw_data

    def detect_indicator_directions(self,
                                    negative_keywords: Optional[List[str]] = None,
                                    positive_keywords: Optional[List[str]] = None,
                                    custom_mapping: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """
        自动识别指标方向（正向/负向）
        """
        if negative_keywords is None:
            negative_keywords = [
                '负债', '成本', '费用', '周转天数', '周期', '风险',
                '负债率', '资产负债率', '营业周期', '存货周转天数',
                '应收账款周转天数', '坏账', '减值', '折旧'
            ]

        if positive_keywords is None:
            positive_keywords = [
                '收益率', '利润率', '增长率', '周转率', '比率', 'ROE', 'ROA',
                '毛利率', '净利率', '现金', '收入', '利润', '营收', '权益',
                '流动比率', '速动比率', '利息保障', '现金流'
            ]

        directions = {}

        for col in self.indicator_names:
            # 跳过非字符串列名（如 NaN）
            if not isinstance(col, str):
                continue
                
            # 优先使用自定义映射
            if custom_mapping and col in custom_mapping:
                directions[col] = custom_mapping[col]
                continue

            # 检测负向关键词
            is_negative = any(kw in col for kw in negative_keywords)
            is_positive = any(kw in col for kw in positive_keywords)

            if is_negative and not is_positive:
                directions[col] = -1  # 负向指标
            else:
                directions[col] = 1   # 默认为正向指标

        self.indicator_directions = directions
        return directions

    def set_indicator_directions(self, directions: Dict[str, int]):
        """
        手动设置指标方向

        Args:
            directions: {指标名: 1/-1}  1=正向，-1=负向
        """
        self.indicator_directions = directions

    def prepare_for_analysis(self) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
        """
        准备分析所需的数据格式

        Returns:
            (数据矩阵, 指标方向数组, 企业名称列表)
        """
        if self.raw_data is None:
            raise ValueError("请先调用 load_data() 加载数据")

        if self.indicator_directions is None:
            print("警告: 未设置指标方向，自动检测中...")
            self.detect_indicator_directions()

        # 提取数值数据（排除非数值列）
        numeric_data = self.raw_data.select_dtypes(include=[np.number])

        if len(numeric_data.columns) == 0:
            raise ValueError("未找到数值型指标列，请检查数据格式")

        # 更新指标名称列表为数值列
        self.indicator_names = numeric_data.columns.tolist()

        # 构建方向数组（按列顺序）
        direction_array = np.array([
            self.indicator_directions.get(col, 1)
            for col in numeric_data.columns
        ])

        return numeric_data, direction_array, self.company_names

    def validate_data(self) -> Dict:
        """
        验证数据完整性

        Returns:
            验证报告字典
        """
        if self.raw_data is None:
            return {'valid': False, 'error': '数据未加载'}

        report = {
            'valid': True,
            'companies': len(self.raw_data),
            'indicators': len(self.indicator_names),
            'missing_values': self.raw_data.isnull().sum().sum(),
            'numeric_columns': len(self.raw_data.select_dtypes(include=[np.number]).columns),
            'warnings': []
        }

        # 检查缺失值
        if report['missing_values'] > 0:
            report['warnings'].append(f"存在 {report['missing_values']} 个缺失值，将在标准化时处理")

        # 检查数值列
        if report['numeric_columns'] == 0:
            report['valid'] = False
            report['error'] = '未找到数值型数据列'

        # 检查指标方向
        if self.indicator_directions is None:
            report['warnings'].append('未设置指标方向，将使用自动检测')

        return report

    def get_data_summary(self) -> pd.DataFrame:
        """
        获取数据摘要统计
        """
        if self.raw_data is None:
            return pd.DataFrame()

        numeric_data = self.raw_data.select_dtypes(include=[np.number])
        return numeric_data.describe()

    def to_calculator_format(self) -> pd.DataFrame:
        """
        转换为 calculator.py 所需的格式

        Returns:
            DataFrame with columns: [股票代码/名称, 指标1, 指标2, ...]
        """
        if self.raw_data is None:
            raise ValueError("数据未加载")

        # 复制数据并重置索引
        df = self.raw_data.select_dtypes(include=[np.number]).copy()
        df.insert(0, '股票名称', self.company_names)

        return df.reset_index(drop=True)


def load_excel_for_analysis(file_path: str,
                            index_col: str = '公司简称',
                            custom_directions: Optional[Dict[str, int]] = None) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    """
    快捷函数：加载 Excel 并准备分析数据

    Args:
        file_path: Excel 文件路径
        index_col: 企业名称列
        custom_directions: 自定义指标方向 {指标名: 1/-1}

    Returns:
        (数据矩阵, 指标方向数组, 企业名称列表)
    """
    loader = ExcelDataLoader(file_path)
    loader.load_data(index_col=index_col)

    if custom_directions:
        loader.set_indicator_directions(custom_directions)
    else:
        loader.detect_indicator_directions()

    # 验证数据
    validation = loader.validate_data()
    if not validation['valid']:
        raise ValueError(f"数据验证失败: {validation.get('error')}")

    if validation['warnings']:
        print(f"\n警告: {'; '.join(validation['warnings'])}")

    return loader.prepare_for_analysis()


if __name__ == "__main__":
    # 测试代码
    print("Excel Data Loader 测试")
    print("=" * 50)

    # 创建测试数据
    test_data = pd.DataFrame({
        '公司简称': ['茅台', '五粮液', '美的'],
        'ROE': [0.25, 0.20, 0.18],
        '资产负债率': [0.25, 0.30, 0.50],
        '营收增长率': [0.15, 0.12, 0.10],
    })

    # 保存测试文件
    test_file = Path(__file__).parent / 'test_data.xlsx'
    test_data.to_excel(test_file, index=False)

    # 加载测试
    loader = ExcelDataLoader(test_file)
    df = loader.load_data(index_col='公司简称')

    # 自动检测方向
    directions = loader.detect_indicator_directions()

    # 准备分析
    data, dirs, companies = loader.prepare_for_analysis()

    print(f"\n数据矩阵形状: {data.shape}")
    print(f"指标方向: {dirs}")
    print(f"企业列表: {companies}")

    # 清理测试文件
    test_file.unlink(missing_ok=True)
    print("\n测试完成!")
