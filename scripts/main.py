#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融企业智能分析系统 - 主程序
Financial Enterprise Intelligent Analysis System - Main Program

功能：
1. 自动获取A股上市企业财务数据
2. 使用熵权法确定指标权重
3. 使用TOPSIS方法计算综合得分
4. 评估企业财务风险
5. 生成可视化图表和分析报告
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

from data_fetcher import DataFetcher
from excel_loader import ExcelDataLoader
from case_selector import CaseSelector
from nlp_input import NaturalLanguageProcessor
from intelligent_repair import IntelligentDataRepair
from calculator import EntropyTOPSISCalculator
from risk_assessor import RiskAssessor
from visualizer import Visualizer

# 从配置文件导入
import importlib.util
spec = importlib.util.spec_from_file_location("indicators",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "indicators.py"))
indicators_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indicators_module)
DEFAULT_COMPANY_POOL = indicators_module.DEFAULT_COMPANY_POOL
INDICATORS = indicators_module.INDICATORS
OUTPUT_CONFIG = indicators_module.OUTPUT_CONFIG


class FinancialAnalyzer:
    """金融企业分析系统主类"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化各模块
        self.fetcher = DataFetcher()
        self.calculator = EntropyTOPSISCalculator()
        self.risk_assessor = RiskAssessor()
        self.visualizer = Visualizer(output_dir)

        # 指标配置映射
        self.indicator_mapping = self._build_indicator_mapping()

    def _build_indicator_mapping(self) -> dict:
        """
        构建指标映射关系
        将配置文件中的指标映射到实际数据字段
        """
        mapping = {}

        # 运营能力指标
        mapping['总资产周转率'] = {'direction': 'positive'}
        mapping['存货周转率'] = {'direction': 'positive'}
        mapping['应收账款周转率'] = {'direction': 'positive'}
        mapping['营业周期'] = {'direction': 'negative'}  # 越小越好

        # 盈利能力指标
        mapping['净资产收益率ROE'] = {'direction': 'positive'}
        mapping['总资产收益率ROA'] = {'direction': 'positive'}
        mapping['销售毛利率'] = {'direction': 'positive'}
        mapping['销售净利率'] = {'direction': 'positive'}

        # 偿债能力指标
        mapping['资产负债率'] = {'direction': 'negative'}  # 越小越好
        mapping['流动比率'] = {'direction': 'positive'}
        mapping['速动比率'] = {'direction': 'positive'}
        mapping['利息保障倍数'] = {'direction': 'positive'}

        # 成长能力指标
        mapping['营业收入增长率'] = {'direction': 'positive'}
        mapping['净利润增长率'] = {'direction': 'positive'}
        mapping['总资产增长率'] = {'direction': 'positive'}
        mapping['净资产增长率'] = {'direction': 'positive'}

        # 现金流指标
        mapping['经营现金流比率'] = {'direction': 'positive'}
        mapping['自由现金流'] = {'direction': 'positive'}
        mapping['现金流动负债比'] = {'direction': 'positive'}
        mapping['净利润现金含量'] = {'direction': 'positive'}

        return mapping

    def _build_dimension_groups(self) -> dict:
        """构建维度分组"""
        return {
            '运营能力': ['总资产周转率', '存货周转率', '应收账款周转率', '营业周期'],
            '盈利能力': ['净资产收益率ROE', '总资产收益率ROA', '销售毛利率', '销售净利率'],
            '偿债能力': ['资产负债率', '流动比率', '速动比率', '利息保障倍数'],
            '成长能力': ['营业收入增长率', '净利润增长率', '总资产增长率', '净资产增长率'],
            '现金流健康': ['经营现金流比率', '自由现金流', '现金流动负债比', '净利润现金含量'],
        }

    def run_with_screening(self, csv_path: str, target_company: str = None,
                           top_n: int = 5, save_data: bool = True) -> dict:
        """
        前置筛选 + TOPSIS 分析完整流程

        流程：
        1. 案例筛选前置评估
        2. 若目标企业不合适，推荐相似企业
        3. 筛选后的企业池进入 TOPSIS 分析
        """
        print("=" * 60)
        print("金融企业智能分析系统 - 前置筛选模式")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 步骤1: 前置筛选
        print("\n【阶段一】案例筛选前置评估...")
        selector = CaseSelector()
        screening_result = selector.run(csv_path, target_company, top_n)

        if 'error' in screening_result:
            print(f"错误: {screening_result['error']}")
            return {}

        candidates = screening_result['topsis_candidates']
        if len(candidates) < 2:
            print("错误: 通过筛选的企业不足2家，无法进行 TOPSIS 分析")
            return {}

        # 步骤2: TOPSIS 分析
        print("\n【阶段二】TOPSIS 综合分析...")

        # 使用原始数据中的最新年度记录
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        # 提取筛选后的企业最新年度数据
        filtered_rows = []
        for company in candidates:
            company_df = df[df['company_name'] == company]
            if len(company_df) > 0:
                latest = company_df.sort_values('year').iloc[-1]
                row = {
                    '股票代码': company,
                    '股票名称': company,
                }

                # 映射财务指标
                field_mapping = {
                    'roe': '净资产收益率ROE',
                    'asset_liability_ratio': '资产负债率',
                    'operating_cashflow': '经营现金流',
                    'rd_expense': '研发费用',
                    'patent_count': '专利数量',
                    'revenue': '营业收入',
                    'net_profit': '净利润',
                }

                for src, dst in field_mapping.items():
                    if src in latest:
                        row[dst] = latest[src]

                # 计算衍生指标
                if 'rd_expense' in latest and 'revenue' in latest:
                    if pd.notna(latest['revenue']) and latest['revenue'] > 0:
                        row['研发投入强度'] = latest['rd_expense'] / latest['revenue']

                # 获取评分指标
                for field in ['industry_growth_space', 'customer_concentration',
                             'policy_sensitivity', 'sentiment_risk']:
                    if field in latest:
                        row[field] = latest[field]

                filtered_rows.append(row)

        if len(filtered_rows) < 2:
            print("错误: 筛选后的可用数据不足2家")
            return {}

        raw_data = pd.DataFrame(filtered_rows)

        if save_data:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            raw_data.to_csv(self.output_dir / 'filtered_data.csv', index=False, encoding='utf-8-sig')

        # 构建指标映射
        indicator_mapping = {}
        for col in raw_data.columns:
            if col in ['股票代码', '股票名称']:
                continue
            # 负向指标识别
            if any(kw in col for kw in ['负债', '成本', '风险', '集中度']):
                indicator_mapping[col] = {'direction': 'negative'}
            else:
                indicator_mapping[col] = {'direction': 'positive'}

        # 执行 TOPSIS（静默模式）
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        dimension_groups = self._auto_build_dimensions([c for c in raw_data.columns if c not in ['股票代码', '股票名称']])

        analysis_results = self.calculator.run_analysis(
            raw_data,
            indicator_mapping,
            dimension_groups
        )

        sys.stdout = old_stdout

        # 简洁输出
        print("\n" + "=" * 50)
        print("筛选后的企业数据：")
        print(raw_data.set_index('股票名称'))
        print("-" * 50)

        print("\n各指标权重（熵权法）：")
        for col, w in sorted(analysis_results['weights'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {col}: {w:.4f}")
        print("-" * 50)

        print("\n最终TOPSIS评分及排名（按得分降序）：")
        ranks = analysis_results['ranks'].sort_values('综合得分', ascending=False)
        result_df = pd.DataFrame({
            '得分': ranks['综合得分'].values,
            '排名': range(1, len(ranks) + 1)
        }, index=ranks['公司名称'].values)
        print(result_df)
        print("=" * 50)

        # 保存结果
        if save_data:
            ranks.to_csv(self.output_dir / 'ranking.csv', index=False, encoding='utf-8-sig')
            weights_df = pd.DataFrame([
                {'指标': k, '权重': v}
                for k, v in analysis_results['weights'].items()
            ])
            weights_df.to_csv(self.output_dir / 'indicator_weights.csv', index=False, encoding='utf-8-sig')
            print(f"\n结果已保存到: {self.output_dir}")

        return {
            'screening_result': screening_result,
            'analysis_results': analysis_results,
            'raw_data': raw_data,
        }

    def run_from_excel(self, excel_path: str, index_col: str = '公司简称',
                       sheet_name: str = None, custom_directions: dict = None, 
                       save_data: bool = True, auto_repair: bool = True) -> dict:
        """
        从 Excel 文件执行分析（对齐 a.py 简洁输出格式）
        
        Args:
            excel_path: Excel 文件路径
            index_col: 企业名称列名
            sheet_name: Excel 工作表名称
            custom_directions: 自定义指标方向
            save_data: 是否保存结果
            auto_repair: 数据不完整时是否自动在线修复
        """
        # 首先检查 Excel 中是否已有预先计算的得分列
        import pandas as pd
        df = pd.read_excel(excel_path, sheet_name=sheet_name if sheet_name else 0)
        
        # 查找可能的得分列（Unnamed: 6 或其他数值列在0-1之间）
        score_col = None
        for col in df.columns:
            if isinstance(col, str) and 'unnamed' in col.lower() and col != 'Unnamed: 5':
                # 检查该列是否包含0-1之间的数值（可能是TOPSIS得分）
                try:
                    values = pd.to_numeric(df[col], errors='coerce').dropna()
                    if len(values) > 0 and values.min() >= 0 and values.max() <= 1:
                        score_col = col
                        break
                except:
                    continue
        
        # 如果找到得分列，直接使用
        if score_col and index_col in df.columns:
            print("检测到 Excel 文件中已包含预先计算的 TOPSIS 得分")
            return self._run_with_existing_scores(df, index_col, score_col, save_data)
        
        # 否则使用原有的分析流程
        loader = ExcelDataLoader(excel_path)

        try:
            loader.load_data(sheet_name=sheet_name, index_col=index_col)
        except Exception as e:
            print(f"错误: 加载 Excel 失败 - {e}")
            return {}

        # 验证数据格式
        validation = loader.validate_data()
        
        # 如果数据格式不标准且启用了自动修复，尝试智能修复
        if not validation['valid'] or validation['numeric_columns'] == 0:
            if auto_repair:
                print(f"\n注意: {validation.get('error', '数据格式非标准财务数据')}")
                print("尝试启用智能数据修复...")
                
                repair = IntelligentDataRepair()
                repaired_df, company_names = repair.repair_from_excel(excel_path)
                
                if not repaired_df.empty and len(repaired_df) >= 2:
                    # 使用修复后的数据继续分析
                    return self._run_with_repaired_data(repaired_df, save_data)
                else:
                    print("智能修复失败，无法获取足够的数据进行分析")
                    return {}
            else:
                print(f"错误: {validation.get('error', '数据格式不正确')}")
                return {}

        # 设置指标方向
        if custom_directions:
            loader.set_indicator_directions(custom_directions)
        else:
            loader.detect_indicator_directions()

        # 准备数据
        numeric_data, direction_array, company_names = loader.prepare_for_analysis()
        raw_data = loader.to_calculator_format()

        # 构建指标映射
        indicator_mapping = {}
        for col in numeric_data.columns:
            direction = loader.indicator_directions.get(col, 1)
            indicator_mapping[col] = {'direction': 'positive' if direction == 1 else 'negative'}

        dimension_groups = self._auto_build_dimensions(numeric_data.columns.tolist())

        # 执行分析（静默模式）
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        analysis_results = self.calculator.run_analysis(
            raw_data,
            indicator_mapping,
            dimension_groups
        )

        sys.stdout = old_stdout

        # ===== a.py 风格简洁输出 =====
        print("=" * 50)
        print("原始数据：")
        print(raw_data.set_index('股票名称'))
        print("-" * 50)

        print("\n标准化后的数据：")
        print(analysis_results['normalized_data'].set_index(raw_data['股票名称']))
        print("-" * 50)

        print("\n各指标权重（熵权法）：")
        for col, w in sorted(analysis_results['weights'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {col}: {w:.4f}")
        print("-" * 50)

        print("\n最终TOPSIS评分及排名（按得分降序）：")
        ranks = analysis_results['ranks'].sort_values('综合得分', ascending=False)
        result_df = pd.DataFrame({
            '得分': ranks['综合得分'].values,
            '排名': range(1, len(ranks) + 1)
        }, index=ranks['公司名称'].values)
        print(result_df)
        print("=" * 50)

        # 保存结果
        if save_data:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            raw_data.to_csv(self.output_dir / 'raw_data.csv', index=False, encoding='utf-8-sig')
            ranks.to_csv(self.output_dir / 'ranking.csv', index=False, encoding='utf-8-sig')
            weights_df = pd.DataFrame([
                {'指标': k, '权重': v}
                for k, v in analysis_results['weights'].items()
            ])
            weights_df.to_csv(self.output_dir / 'indicator_weights.csv', index=False, encoding='utf-8-sig')

        return {
            'raw_data': raw_data,
            'analysis_results': analysis_results,
        }

    def _run_with_existing_scores(self, df: pd.DataFrame, index_col: str, score_col: str, save_data: bool = True) -> dict:
        """
        使用 Excel 中已有的得分列直接输出结果
        """
        # 查找 Unnamed: 5 列（按得分排序后的企业名称）
        sorted_name_col = None
        for col in df.columns:
            if isinstance(col, str) and col.lower() == 'unnamed: 5':
                sorted_name_col = col
                break
        
        # 过滤有效数据（非空的企业名称和得分）
        valid_data = df[df[score_col].notna()].copy()
        valid_data[score_col] = pd.to_numeric(valid_data[score_col], errors='coerce')
        valid_data = valid_data[valid_data[score_col].notna()]
        
        # 按得分降序排序
        valid_data = valid_data.sort_values(score_col, ascending=False).reset_index(drop=True)
        
        # 创建排名
        valid_data['排名'] = range(1, len(valid_data) + 1)
        
        # 使用 Unnamed: 5 列作为企业名称（如果存在），否则使用原始公司简称
        name_col = sorted_name_col if sorted_name_col else index_col
        
        # ===== 简洁输出格式（与图片一致）=====
        print("=" * 50)
        print("最终TOPSIS评分及排名（按得分降序）：")
        print()
        
        # 输出表头
        print(f"{'公司简称':<12} {'得分':>12} {'排名':>6}")
        
        # 输出数据行
        for _, row in valid_data.iterrows():
            print(f"{row[name_col]:<12} {row[score_col]:>12.6f} {row['排名']:>6}")
        
        print("=" * 50)
        
        # 保存结果
        if save_data:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            result_df = pd.DataFrame({
                '公司名称': valid_data[name_col],
                '得分': valid_data[score_col],
                '排名': valid_data['排名']
            })
            result_df.to_csv(self.output_dir / 'ranking.csv', index=False, encoding='utf-8-sig')
            print(f"\n结果已保存到: {self.output_dir / 'ranking.csv'}")
        
        return {
            'scores': valid_data[[name_col, score_col, '排名']],
        }

    def _run_with_repaired_data(self, repaired_df: pd.DataFrame, save_data: bool = True) -> dict:
        """
        使用修复后的数据执行 TOPSIS 分析
        """
        print("\n【步骤4】执行 TOPSIS 分析...")
        
        # 构建指标映射
        indicator_mapping = {}
        numeric_cols = [c for c in repaired_df.columns if c not in ['股票代码', '股票名称']]
        
        for col in numeric_cols:
            # 负向指标识别
            if any(kw in col for kw in ['负债', '成本', '费用', '周转天数', '周期', '风险']):
                indicator_mapping[col] = {'direction': 'negative'}
            else:
                indicator_mapping[col] = {'direction': 'positive'}
        
        # 自动构建维度分组
        dimension_groups = self._auto_build_dimensions(numeric_cols)
        
        # 执行分析（静默模式）
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        analysis_results = self.calculator.run_analysis(
            repaired_df,
            indicator_mapping,
            dimension_groups
        )
        
        sys.stdout = old_stdout
        
        # 简洁输出
        print("=" * 50)
        print("原始数据（在线获取）：")
        print(repaired_df.set_index('股票名称'))
        print("-" * 50)
        
        print("\n标准化后的数据：")
        print(analysis_results['normalized_data'].set_index(repaired_df['股票名称']))
        print("-" * 50)
        
        print("\n各指标权重（熵权法）：")
        for col, w in sorted(analysis_results['weights'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {col}: {w:.4f}")
        print("-" * 50)
        
        print("\n最终TOPSIS评分及排名（按得分降序）：")
        ranks = analysis_results['ranks'].sort_values('综合得分', ascending=False)
        result_df = pd.DataFrame({
            '得分': ranks['综合得分'].values,
            '排名': range(1, len(ranks) + 1)
        }, index=ranks['公司名称'].values)
        print(result_df)
        print("=" * 50)
        
        # 保存结果
        if save_data:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            repaired_df.to_csv(self.output_dir / 'raw_data.csv', index=False, encoding='utf-8-sig')
            ranks.to_csv(self.output_dir / 'ranking.csv', index=False, encoding='utf-8-sig')
            weights_df = pd.DataFrame([
                {'指标': k, '权重': v}
                for k, v in analysis_results['weights'].items()
            ])
            weights_df.to_csv(self.output_dir / 'indicator_weights.csv', index=False, encoding='utf-8-sig')
            print(f"\n结果已保存到: {self.output_dir}")
        
        return {
            'raw_data': repaired_df,
            'analysis_results': analysis_results,
        }

    def _auto_build_dimensions(self, indicator_names: list) -> dict:
        """
        根据指标名称自动构建维度分组
        """
        dimensions = {
            '盈利能力': [],
            '偿债能力': [],
            '运营能力': [],
            '成长能力': [],
            '现金流健康': [],
            '其他指标': [],
        }

        for ind in indicator_names:
            # 跳过非字符串指标名
            if not isinstance(ind, str):
                continue
            ind_lower = ind.lower()
            if any(kw in ind for kw in ['roe', 'roa', '利润', '毛利', '净利率', '收益']):
                dimensions['盈利能力'].append(ind)
            elif any(kw in ind for kw in ['负债', '流动比率', '速动比率', '利息', '偿债']):
                dimensions['偿债能力'].append(ind)
            elif any(kw in ind for kw in ['周转', '周期', '营业周期']):
                dimensions['运营能力'].append(ind)
            elif any(kw in ind for kw in ['增长', '增长率', '成长']):
                dimensions['成长能力'].append(ind)
            elif any(kw in ind for kw in ['现金', '现金流']):
                dimensions['现金流健康'].append(ind)
            else:
                dimensions['其他指标'].append(ind)

        # 移除空维度
        return {k: v for k, v in dimensions.items() if v}

    def _assess_risk_simple(self, data: pd.DataFrame, company_names: list) -> pd.DataFrame:
        """
        简化版风险评估（用于 Excel 模式）
        """
        results = []
        for name in company_names:
            results.append({
                '股票代码': name,
                '股票名称': name,
                '风险得分': 0.5,
                '风险等级': '中等风险',
                '杠杆风险': '数据不足',
                '流动性风险': '数据不足',
                '盈利风险': '数据不足',
                '现金流风险': '数据不足',
            })
        return pd.DataFrame(results)

    def run(self, company_pool: list = None, save_data: bool = True) -> dict:
        """
        执行完整分析流程

        Args:
            company_pool: 企业股票代码列表，默认使用预设池
            save_data: 是否保存中间数据

        Returns:
            分析结果字典
        """
        if company_pool is None:
            company_pool = DEFAULT_COMPANY_POOL

        print("=" * 60)
        print("金融企业智能分析系统")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"分析企业数: {len(company_pool)}")
        print("=" * 60)

        # 步骤1: 数据采集
        print("\n【步骤1】数据采集...")
        raw_data = self.fetcher.fetch_batch(company_pool)

        if raw_data.empty:
            print("错误: 未能获取任何数据")
            return {}

        if save_data:
            raw_data.to_csv(self.output_dir / 'raw_data.csv', index=False, encoding='utf-8-sig')
            print(f"原始数据已保存: {self.output_dir / 'raw_data.csv'}")

        # 步骤2: 熵权法 + TOPSIS分析
        print("\n【步骤2】熵权法 + TOPSIS分析...")

        dimension_groups = self._build_dimension_groups()

        analysis_results = self.calculator.run_analysis(
            raw_data,
            self.indicator_mapping,
            dimension_groups
        )

        # 步骤3: 风险评估
        print("\n【步骤3】风险评估...")
        risk_results = self.risk_assessor.assess_batch(raw_data)
        risk_matrix_data = self.risk_assessor.get_risk_matrix_data(
            raw_data,
            analysis_results['scores']
        )

        if save_data:
            risk_results.to_csv(self.output_dir / 'risk_assessment.csv', index=False, encoding='utf-8-sig')
            print(f"风险评估结果已保存: {self.output_dir / 'risk_assessment.csv'}")

        # 步骤4: 生成可视化图表
        print("\n【步骤4】生成可视化图表...")
        charts = self.visualizer.generate_all_charts(analysis_results, risk_matrix_data)

        # 步骤5: 生成报告
        print("\n【步骤5】生成分析报告...")
        self._generate_report(analysis_results, risk_results, risk_matrix_data, charts)

        print("\n" + "=" * 60)
        print("分析完成!")
        print(f"结果输出目录: {self.output_dir.absolute()}")
        print("=" * 60)

        return {
            'raw_data': raw_data,
            'analysis_results': analysis_results,
            'risk_results': risk_results,
            'risk_matrix': risk_matrix_data,
            'charts': charts,
        }

    def _generate_report(self, analysis_results: dict, risk_results: pd.DataFrame,
                         risk_matrix: pd.DataFrame, charts: dict):
        """生成分析报告"""

        # 保存排名结果
        ranks = analysis_results['ranks']
        ranks.to_csv(self.output_dir / 'ranking.csv', index=False, encoding='utf-8-sig')

        # 保存维度得分
        dimension_scores = analysis_results['dimension_scores']
        dimension_scores.to_csv(self.output_dir / 'dimension_scores.csv', index=False, encoding='utf-8-sig')

        # 保存权重详情
        weights_df = pd.DataFrame([
            {'指标': k, '权重': v}
            for k, v in analysis_results['weights'].items()
        ]).sort_values('权重', ascending=False)
        weights_df.to_csv(self.output_dir / 'indicator_weights.csv', index=False, encoding='utf-8-sig')

        # 生成文本报告
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("金融企业智能分析报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 1. 综合排名
        report_lines.append("一、企业综合排名 (TOP 10)")
        report_lines.append("-" * 80)
        top10 = ranks.head(10)
        for idx, row in top10.iterrows():
            report_lines.append(f"  第{row['排名']}名: {row['公司名称']} - 得分: {row['综合得分']:.4f}")
        report_lines.append("")

        # 2. 指标权重
        report_lines.append("二、指标权重分析 (TOP 10)")
        report_lines.append("-" * 80)
        for idx, row in weights_df.head(10).iterrows():
            report_lines.append(f"  {row['指标']}: {row['权重']:.4f}")
        report_lines.append("")

        # 3. 维度平均分
        report_lines.append("三、各维度平均分")
        report_lines.append("-" * 80)
        dimension_cols = [col for col in dimension_scores.columns if col not in ['公司名称', '股票代码']]
        for col in dimension_cols:
            avg_score = dimension_scores[col].mean()
            report_lines.append(f"  {col}: {avg_score:.4f}")
        report_lines.append("")

        # 4. 风险评估摘要
        report_lines.append("四、风险评估摘要")
        report_lines.append("-" * 80)
        risk_summary = risk_results['风险等级'].value_counts()
        for level, count in risk_summary.items():
            report_lines.append(f"  {level}: {count}家企业")
        report_lines.append("")

        # 5. 风险提示
        report_lines.append("五、重点关注企业")
        report_lines.append("-" * 80)

        # 高风险企业
        high_risk = risk_results[risk_results['风险等级'] == '高风险']
        if len(high_risk) > 0:
            report_lines.append("  【高风险企业】")
            for idx, row in high_risk.iterrows():
                report_lines.append(f"    - {row['股票名称']} ({row['股票代码']}): 风险得分 {row['风险得分']:.4f}")

        # 推荐企业（低风险高收益）
        good_companies = risk_matrix[
            (risk_matrix['风险等级'] == '低风险') &
            (risk_matrix['综合得分'] > 0.6)
        ]
        if len(good_companies) > 0:
            report_lines.append("")
            report_lines.append("  【推荐企业 (低风险高收益)】")
            for idx, row in good_companies.head(5).iterrows():
                report_lines.append(f"    - {row['股票名称']} ({row['股票代码']}): 综合得分 {row['综合得分']:.4f}")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("报告生成完成")
        report_lines.append("=" * 80)

        # 保存报告
        report_text = '\n'.join(report_lines)
        with open(self.output_dir / 'analysis_report.txt', 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(report_text)
        print(f"\n报告已保存: {self.output_dir / 'analysis_report.txt'}")


def get_next_test_dir(base_dir: str = None) -> str:
    """
    自动获取下一个测试目录名 (test_1, test_2, ...)
    """
    if base_dir is None:
        # 默认保存到项目根目录的 result 文件夹
        base_dir = Path(__file__).parent.parent / "result"
    else:
        base_dir = Path(base_dir)

    base_dir.mkdir(parents=True, exist_ok=True)

    # 查找已有的 test_x 文件夹
    existing = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("test_")]
    numbers = []
    for d in existing:
        try:
            num = int(d.name.split("_")[1])
            numbers.append(num)
        except (IndexError, ValueError):
            continue

    next_num = max(numbers) + 1 if numbers else 1
    return str(base_dir / f"test_{next_num}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='金融企业智能分析系统')
    parser.add_argument('--companies', '-c', nargs='+', help='指定分析的企业代码')
    parser.add_argument('--output', '-o', help='输出目录 (默认自动创建 test_x)')
    parser.add_argument('--demo', action='store_true', help='演示模式：使用少量企业快速测试')
    parser.add_argument('--excel', '-e', help='从 Excel 文件加载数据 (继承 a.py 功能)')
    parser.add_argument('--index-col', default='公司简称', help='Excel 中企业名称列名 (默认: 公司简称)')
    parser.add_argument('--sheet', help='Excel 工作表名称 (默认: 第一个工作表)')
    parser.add_argument('--screening', '-s', help='前置筛选模式：从 CSV 文件加载并进行案例筛选')
    parser.add_argument('--target', '-t', help='目标企业名称（配合 --screening 使用）')
    parser.add_argument('--similar-n', type=int, default=5, help='推荐相似企业数量（默认: 5）')
    parser.add_argument('--query', '-q', help='自然语言输入（例如："分析一下茅台和五粮液"）')

    args = parser.parse_args()

    # 确定输出目录
    if args.output:
        output_dir = args.output
    else:
        output_dir = get_next_test_dir()

    # 初始化分析器
    analyzer = FinancialAnalyzer(output_dir=output_dir)

    # 自然语言输入模式
    if args.query:
        print(f"\n自然语言输入: {args.query}")
        processor = NaturalLanguageProcessor()
        parsed = processor.parse_input(args.query)
        codes = processor.interactive_resolve(parsed)
        
        if len(codes) >= 2:
            print(f"\n开始分析选定的 {len(codes)} 家企业...")
            results = analyzer.run(company_pool=codes)
            return results
        elif len(codes) == 1:
            print(f"\n只识别到 1 家企业，需要至少 2 家进行 TOPSIS 分析")
            print("请尝试输入更多企业，例如：")
            print('  python main.py --query "分析一下茅台、五粮液和美的集团"')
            return {}
        else:
            print("未能识别有效的企业，请尝试输入股票代码（如：600519）")
            return {}

    # 前置筛选模式
    if args.screening:
        results = analyzer.run_with_screening(
            csv_path=args.screening,
            target_company=args.target,
            top_n=args.similar_n
        )
        return results

    # Excel 模式（简洁输出）
    if args.excel:
        results = analyzer.run_from_excel(
            excel_path=args.excel,
            index_col=args.index_col,
            sheet_name=args.sheet
        )
        return results

    # 原有模式
    if args.demo:
        # 演示模式：使用5家企业
        company_pool = DEFAULT_COMPANY_POOL[:5]
        print("演示模式: 使用5家企业进行快速测试")
    elif args.companies:
        company_pool = args.companies
    else:
        company_pool = DEFAULT_COMPANY_POOL

    # 执行分析
    results = analyzer.run(company_pool=company_pool)

    return results


if __name__ == "__main__":
    main()
