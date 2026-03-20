#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集模块 - Data Fetcher Module (使用新浪财务报表)
从新浪财经财务报表获取数据
"""

import akshare as ak
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class DataFetcher:
    """金融数据采集器 - 新浪财务报表版"""
    
    def __init__(self):
        self.stock_list = None
        
    def get_stock_list(self) -> pd.DataFrame:
        """获取A股上市公司列表"""
        try:
            self.stock_list = ak.stock_info_a_code_name()
            return self.stock_list
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_company_name(self, stock_code: str) -> str:
        """根据股票代码获取公司名称"""
        if self.stock_list is None:
            self.get_stock_list()
        
        name = self.stock_list[self.stock_list['code'] == stock_code]['name']
        return name.values[0] if len(name) > 0 else stock_code
    
    def fetch_financial_data(self, stock_code: str) -> Dict:
        """
        获取企业财务数据 - 使用财务摘要API获取完整指标
        """
        try:
            # 使用财务摘要API获取完整指标
            abstract_df = ak.stock_financial_abstract(symbol=stock_code)
            
            # 获取新浪财务报表（资产负债表）
            try:
                report_df = ak.stock_financial_report_sina(stock=stock_code)
            except:
                report_df = pd.DataFrame()
            
            # 获取现金流量表
            try:
                cashflow_df = ak.stock_cash_flow_sheet_by_report_em(symbol=stock_code)
            except:
                cashflow_df = pd.DataFrame()
            
            return {
                'abstract': abstract_df,
                'report': report_df,
                'cashflow': cashflow_df
            }
        except Exception as e:
            print(f"  获取报表失败: {e}")
            return {}
    
    def calculate_indicators(self, stock_code: str, data: Dict) -> Dict:
        """
        从财务摘要数据计算财务指标
        """
        if not data:
            return {}
        
        company_name = self.get_company_name(stock_code)
        abstract = data.get('abstract', pd.DataFrame())
        
        if abstract.empty:
            return {}
        
        indicators_dict = {
            '股票代码': stock_code,
            '股票名称': company_name,
        }
        
        try:
            # 设置指标列为索引以便查找
            abstract_indexed = abstract.set_index('指标')
            
            # 获取最新报告期数据（第2列，第0列是"选项"，第1列是"指标"）
            latest_col = abstract.columns[2]  # 最新的报告期
            prev_col = abstract.columns[3] if len(abstract.columns) > 3 else None  # 上一期
            
            def get_value(idx, col=latest_col):
                """安全获取指标值"""
                try:
                    if idx in abstract_indexed.index:
                        val = abstract_indexed.loc[idx, col]
                        return self._safe_float(val)
                    return None
                except:
                    return None
            
            # ========== 1. 偿债能力指标 ==========
            # 资产负债率
            debt_ratio = get_value('资产负债率')
            if not pd.isna(debt_ratio):
                indicators_dict['资产负债率'] = debt_ratio / 100 if debt_ratio > 1 else debt_ratio
            
            # 流动比率
            current_ratio = get_value('流动比率')
            if not pd.isna(current_ratio):
                indicators_dict['流动比率'] = current_ratio
            
            # 速动比率
            quick_ratio = get_value('速动比率')
            if not pd.isna(quick_ratio):
                indicators_dict['速动比率'] = quick_ratio
            
            # ========== 2. 盈利能力指标 ==========
            # ROE
            roe = get_value('净资产收益率(ROE)')
            if pd.isna(roe):
                roe = get_value('净资产收益率(ROE)', latest_col)
            if not pd.isna(roe):
                indicators_dict['净资产收益率ROE'] = roe / 100 if roe > 1 else roe
            
            # ROA
            roa = get_value('总资产报酬率')
            if not pd.isna(roa):
                indicators_dict['总资产收益率ROA'] = roa / 100 if roa > 1 else roa
            
            # 毛利率
            gross_margin = get_value('毛利率')
            if not pd.isna(gross_margin):
                indicators_dict['销售毛利率'] = gross_margin / 100 if gross_margin > 1 else gross_margin
            
            # 销售净利率
            net_margin = get_value('销售净利率')
            if not pd.isna(net_margin):
                indicators_dict['销售净利率'] = net_margin / 100 if net_margin > 1 else net_margin
            
            # ========== 3. 运营能力指标 ==========
            # 总资产周转率
            asset_turnover = get_value('总资产周转率')
            if not pd.isna(asset_turnover):
                indicators_dict['总资产周转率'] = asset_turnover
            
            # 存货周转率
            inventory_turnover = get_value('存货周转率')
            if not pd.isna(inventory_turnover):
                indicators_dict['存货周转率'] = inventory_turnover
            
            # 应收账款周转率
            receivable_turnover = get_value('应收账款周转率')
            if not pd.isna(receivable_turnover):
                indicators_dict['应收账款周转率'] = receivable_turnover
            
            # 营业周期 = 存货周转天数 + 应收账款周转天数
            inventory_days = get_value('存货周转天数')
            receivable_days = get_value('应收账款周转天数')
            if not pd.isna(inventory_days) and not pd.isna(receivable_days):
                indicators_dict['营业周期'] = inventory_days + receivable_days
            
            # ========== 4. 成长能力指标 ==========
            # 营业总收入增长率
            revenue_growth = get_value('营业总收入增长率')
            if not pd.isna(revenue_growth):
                indicators_dict['营业收入增长率'] = revenue_growth / 100 if revenue_growth > 1 else revenue_growth
            
            # 净利润增长率
            profit_growth = get_value('归属母公司净利润增长率')
            if not pd.isna(profit_growth):
                indicators_dict['净利润增长率'] = profit_growth / 100 if profit_growth > 1 else profit_growth
            
            # 计算总资产增长率（需要从报告中获取）
            report = data.get('report', pd.DataFrame())
            if not report.empty:
                latest = report.iloc[0]
                prev = report.iloc[1] if len(report) > 1 else None
                
                total_assets = self._safe_float(latest.get('资产总计'))
                prev_total_assets = self._safe_float(prev.get('资产总计')) if prev is not None else None
                
                equity = self._safe_float(latest.get('所有者权益(或股东权益)合计'))
                if pd.isna(equity):
                    equity = self._safe_float(latest.get('归属于母公司股东权益合计'))
                
                prev_equity = self._safe_float(prev.get('所有者权益(或股东权益)合计')) if prev is not None else None
                if prev is not None and pd.isna(prev_equity):
                    prev_equity = self._safe_float(prev.get('归属于母公司股东权益合计'))
                
                if not pd.isna(total_assets) and prev_total_assets is not None and prev_total_assets > 0:
                    indicators_dict['总资产增长率'] = (total_assets - prev_total_assets) / prev_total_assets
                
                if not pd.isna(equity) and prev_equity is not None and prev_equity > 0:
                    indicators_dict['净资产增长率'] = (equity - prev_equity) / prev_equity
            
            # ========== 5. 现金流指标 ==========
            # 从资产负债表获取负债数据
            report = data.get('report', pd.DataFrame())
            
            current_liabilities = None
            if not report.empty:
                latest_report = report.iloc[0]
                current_liabilities = self._safe_float(latest_report.get('流动负债合计'))
            
            # 从财务摘要获取现金流数据
            # 经营现金流量净额
            operating_cash_flow = get_value('经营现金流量净额')
            
            # 营业收入（用于计算经营现金流比率）
            revenue = get_value('营业总收入')
            
            # 净利润（用于计算净利润现金含量）
            net_profit = get_value('归母净利润')
            
            # 现金流动负债比 = 经营现金流 / 流动负债
            if not pd.isna(operating_cash_flow) and not pd.isna(current_liabilities) and current_liabilities > 0:
                indicators_dict['现金流动负债比'] = operating_cash_flow / current_liabilities
            
            # 经营现金流比率 = 经营现金流 / 营业收入
            if not pd.isna(operating_cash_flow) and not pd.isna(revenue) and revenue > 0:
                indicators_dict['经营现金流比率'] = operating_cash_flow / revenue
            
            # 净利润现金含量 = 经营现金流 / 净利润
            if not pd.isna(operating_cash_flow) and not pd.isna(net_profit) and net_profit != 0:
                indicators_dict['净利润现金含量'] = operating_cash_flow / net_profit
            
            # 自由现金流（用每股自由现金流 * 总股本估算，或直接从财务摘要获取）
            fcf_per_share = get_value('每股企业自由现金流量')
            if not pd.isna(fcf_per_share):
                # 从财务摘要获取总股本
                total_shares = get_value('实收资本(或股本)')
                if not pd.isna(total_shares):
                    indicators_dict['自由现金流'] = fcf_per_share * total_shares * 10000  # 转换为元（股本单位通常是万元）
                else:
                    indicators_dict['自由现金流'] = fcf_per_share  # 保留每股数据
            
            # 统计有效指标数
            valid_count = sum(1 for k, v in indicators_dict.items() if k not in ['股票代码', '股票名称'] and v is not None and not pd.isna(v))
            
            if valid_count >= 4:
                print(f"✓ (获取 {valid_count} 个指标)")
                return indicators_dict
            else:
                print(f"✗ (数据不足: {valid_count} 个指标)")
                return {}
                
        except Exception as e:
            print(f"✗ 计算错误: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _safe_float(self, value, default=None):
        """安全转换为浮点数"""
        if value is None or value == '' or value == '--' or value == 'NaN' or pd.isna(value):
            return default
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace('%', '').strip()
                if value == '' or value == '--':
                    return default
            return float(value)
        except:
            return default
    
    def extract_key_indicators(self, stock_code: str) -> Dict:
        """提取关键财务指标"""
        data = self.fetch_financial_data(stock_code)
        return self.calculate_indicators(stock_code, data)
    
    def fetch_batch(self, stock_codes: List[str]) -> pd.DataFrame:
        """批量获取多家企业数据"""
        results = []
        total = len(stock_codes)
        
        print(f"开始获取 {total} 家企业数据...")
        
        for i, code in enumerate(stock_codes, 1):
            print(f"[{i}/{total}] {code} {self.get_company_name(code)}... ", end='', flush=True)
            
            indicators = self.extract_key_indicators(code)
            if indicators and len(indicators) > 2:
                results.append(indicators)
        
        print(f"\n成功获取 {len(results)}/{total} 家企业数据")
        
        if results:
            df = pd.DataFrame(results)
            return df
        else:
            print("未能获取到有效数据")
            return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    fetcher = DataFetcher()
    
    test_code = "600519"
    print(f"\n测试获取 {test_code} 数据:")
    
    data = fetcher.extract_key_indicators(test_code)
    for key, value in data.items():
        if value is not None and not pd.isna(value):
            print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
