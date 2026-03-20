#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据修复模块 - Intelligent Data Repair Module
当 Excel 文件数据不完整时，自动上网查找相关数据补足
"""

import re
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class IntelligentDataRepair:
    """
    智能数据修复器
    
    功能：
    1. 从非标准格式的 Excel 中提取企业名称
    2. 将企业名称映射为股票代码
    3. 在线获取完整的财务数据
    """
    
    def __init__(self):
        self.stock_list = None
        self.name_to_code = {}
        self.code_to_name = {}
        self._load_stock_list()
    
    def _load_stock_list(self):
        """加载A股上市公司列表"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from data_fetcher import DataFetcher
            fetcher = DataFetcher()
            self.stock_list = fetcher.get_stock_list()
            
            # 构建名称到代码的映射
            for _, row in self.stock_list.iterrows():
                code = row['code']
                name = row['name']
                self.code_to_name[code] = name
                
                # 存储多种形式的名称
                self.name_to_code[name] = code
                self.name_to_code[name.replace(' ', '')] = code
                
                # 存储简称（去掉"股份"、"集团"等后缀）
                short_name = name.replace('股份', '').replace('集团', '').replace('有限', '').replace('公司', '')
                if short_name and short_name != name:
                    self.name_to_code[short_name] = code
            
            # 添加常见简称映射
            common_short_names = {
                '茅台': '600519',
                '五粮液': '000858',
                '美的': '000333',
                '格力': '000651',
                '比亚迪': '002594',
                '宁德': '300750',
                '隆基': '601012',
                '招行': '600036',
                '平安': '601318',
                '恒瑞': '600276',
                '海康': '002415',
                '云南白药': '000538',
                '药明康德': '603259',
                '海螺水泥': '600585',
                '中国建筑': '601668',
                '京东方': '000725',
                '汇川技术': '300124',
            }
            for short_name, code in common_short_names.items():
                self.name_to_code[short_name] = code
                
        except Exception as e:
            print(f"加载股票列表失败: {e}")
            self.stock_list = pd.DataFrame()
    
    def extract_company_names_from_df(self, df: pd.DataFrame) -> List[str]:
        """
        从 DataFrame 中提取可能的企业名称
        
        策略：
        1. 搜索所有文本列，查找已知的公司名称
        2. 使用正则匹配可能的股票代码（6位数字）
        3. 查找常见企业简称
        """
        found_names = []
        found_codes = []
        
        # 遍历所有单元格
        for col in df.columns:
            for val in df[col].dropna():
                if not isinstance(val, str):
                    val = str(val)
                
                # 1. 尝试匹配股票代码（6位数字）
                codes = re.findall(r'\b(\d{6})\b', val)
                for code in codes:
                    if code[0] in '036' and code in self.code_to_name:
                        if code not in found_codes:
                            found_codes.append(code)
                            found_names.append(self.code_to_name[code])
                
                # 2. 尝试匹配公司名称
                for name, code in self.name_to_code.items():
                    if len(name) >= 2 and name in val and code not in found_codes:
                        # 验证这不是部分匹配（比如"茅台"匹配到"茅台镇"）
                        if name == val or f'公司名称:{name}' in f'公司名称:{val}' or \
                           f'企业名称:{name}' in f'企业名称:{val}' or \
                           re.search(rf'\b{name}\b', val):
                            found_codes.append(code)
                            found_names.append(self.code_to_name.get(code, name))
                            break
        
        return list(dict.fromkeys(found_names))  # 保持顺序去重
    
    def fuzzy_search_company(self, query: str, top_n: int = 3) -> List[Dict]:
        """模糊搜索公司"""
        if self.stock_list.empty:
            return []
        
        results = []
        query_lower = query.lower()
        
        for _, row in self.stock_list.iterrows():
            code = row['code']
            name = row['name']
            
            # 精确匹配代码
            if query == code:
                results.append({'code': code, 'name': name, 'score': 100})
                continue
            
            # 精确匹配名称
            if query == name or query == name.replace(' ', ''):
                results.append({'code': code, 'name': name, 'score': 95})
                continue
            
            # 模糊匹配
            if query in name or query in name.replace(' ', ''):
                score = 80 if len(query) >= 3 else 60
                results.append({'code': code, 'name': name, 'score': score})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]
    
    def repair_from_excel(self, excel_path: str, 
                          sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, List[str]]:
        """
        从 Excel 文件智能修复数据
        
        Returns:
            (修复后的数据, 企业名称列表)
        """
        print("\n【智能数据修复模式】")
        print("检测到 Excel 文件格式非标准财务数据，尝试提取企业名称并在线获取数据...")
        
        # 读取 Excel
        df = pd.read_excel(excel_path, sheet_name=sheet_name if sheet_name else 0)
        
        # 提取企业名称
        print("\n步骤1: 从文件中提取企业名称...")
        company_names = self.extract_company_names_from_df(df)
        
        if len(company_names) < 2:
            print("未能从文件中提取到足够的企业名称")
            print("请尝试：")
            print("  1. 使用自然语言输入: python main.py --query '分析茅台和五粮液'")
            print("  2. 提供标准格式的 Excel 文件（包含企业名称列和财务指标列）")
            return pd.DataFrame(), []
        
        print(f"识别到 {len(company_names)} 家企业:")
        for name in company_names:
            print(f"  - {name}")
        
        # 获取股票代码
        print("\n步骤2: 匹配股票代码...")
        stock_codes = []
        for name in company_names:
            # 先尝试直接匹配
            code = self.name_to_code.get(name)
            if not code:
                # 模糊搜索
                results = self.fuzzy_search_company(name, top_n=1)
                if results:
                    code = results[0]['code']
                    print(f"  {name} → {results[0]['name']} ({code})")
                else:
                    print(f"  {name} → 未找到匹配")
            else:
                full_name = self.code_to_name.get(code, name)
                print(f"  {name} → {full_name} ({code})")
            
            if code and code not in stock_codes:
                stock_codes.append(code)
        
        if len(stock_codes) < 2:
            print("匹配到的企业不足2家，无法进行分析")
            return pd.DataFrame(), []
        
        # 在线获取财务数据
        print(f"\n步骤3: 在线获取 {len(stock_codes)} 家企业的财务数据...")
        from data_fetcher import DataFetcher
        fetcher = DataFetcher()
        
        results = []
        for code in stock_codes:
            indicators = fetcher.extract_key_indicators(code)
            if indicators and len(indicators) > 2:
                results.append(indicators)
        
        if not results:
            print("未能获取到任何企业的财务数据")
            return pd.DataFrame(), []
        
        repaired_df = pd.DataFrame(results)
        
        print(f"\n✓ 数据修复完成！成功获取 {len(results)} 家企业数据")
        print(f"  指标数量: {len(repaired_df.columns) - 2} 个")
        
        return repaired_df, company_names
    
    def is_standard_format(self, df: pd.DataFrame, index_col: str = '公司简称') -> bool:
        """
        检查 DataFrame 是否为标准财务数据格式
        
        标准格式要求：
        1. 包含指定的企业名称列
        2. 包含数值型财务指标列
        """
        # 检查是否有数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return False
        
        # 检查是否有企业名称列
        name_cols = ['公司简称', '公司名称', '股票名称', '企业名称', 'name', 'company']
        has_name_col = any(col in df.columns for col in name_cols)
        
        # 或者第一列是字符串类型（可能是企业名称）
        first_col = df.columns[0]
        first_col_is_string = df[first_col].dtype == 'object'
        
        return has_name_col or first_col_is_string


def demo():
    """演示功能"""
    repair = IntelligentDataRepair()
    
    # 测试从非标准文件提取
    test_df = pd.DataFrame({
        'A': ['分析对象', '贵州茅台', '五粮液', '美的集团'],
        'B': ['说明', '白酒龙头', '浓香型白酒', '家电巨头'],
        'C': [1, 2, 3, 4],
    })
    
    names = repair.extract_company_names_from_df(test_df)
    print(f"提取到的企业名称: {names}")


if __name__ == "__main__":
    demo()
