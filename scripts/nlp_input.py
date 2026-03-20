#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然语言输入处理器 - Natural Language Input Processor
支持用户用自然语言描述需求，自动解析公司信息并在线查找数据

功能：
1. 解析自然语言输入，提取公司名称/股票代码
2. 在线搜索匹配的企业
3. 自动获取企业财务数据
4. 整合到 TOPSIS 分析流程
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedInput:
    """解析后的输入结构"""
    company_names: List[str]  # 提取的公司名称
    stock_codes: List[str]    # 提取的股票代码
    industry_hint: Optional[str]  # 行业提示（如果有）
    year_range: Optional[Tuple[int, int]]  # 年份范围（如果有）
    raw_input: str            # 原始输入


class NaturalLanguageProcessor:
    """
    自然语言输入处理器
    
    支持输入示例：
    - "分析一下茅台、五粮液和美的集团"
    - "帮我看看600519和000858这两家公司"
    - "对比一下白酒行业的贵州茅台、泸州老窖"
    - "分析比亚迪、宁德时代、隆基绿能这三家新能源企业"
    """
    
    def __init__(self):
        self.stock_list = None
        self._load_stock_list()
        
    def _load_stock_list(self):
        """加载A股上市公司列表"""
        try:
            from data_fetcher import DataFetcher
            fetcher = DataFetcher()
            self.stock_list = fetcher.get_stock_list()
            # 构建名称到代码的映射
            self.name_to_code = {}
            self.code_to_name = {}  # 反向映射
            for _, row in self.stock_list.iterrows():
                code = row['code']
                name = row['name']
                self.code_to_name[code] = name
                
                # 存储多种形式的名称
                self.name_to_code[name] = code
                self.name_to_code[name.replace(' ', '')] = code  # 去空格版本
                
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
            }
            for short_name, code in common_short_names.items():
                if code in self.code_to_name:
                    self.name_to_code[short_name] = code
                    
        except Exception as e:
            print(f"加载股票列表失败: {e}")
            self.stock_list = pd.DataFrame()
            self.name_to_code = {}
            self.code_to_name = {}
    
    def parse_input(self, text: str) -> ParsedInput:
        """
        解析自然语言输入
        
        Args:
            text: 用户输入的自然语言文本
            
        Returns:
            ParsedInput 结构
        """
        text = text.strip()
        
        # 1. 提取股票代码（6位数字）
        stock_codes = self._extract_stock_codes(text)
        
        # 2. 提取公司名称
        company_names = self._extract_company_names(text)
        
        # 3. 提取行业提示
        industry_hint = self._extract_industry_hint(text)
        
        # 4. 提取年份范围
        year_range = self._extract_year_range(text)
        
        return ParsedInput(
            company_names=company_names,
            stock_codes=stock_codes,
            industry_hint=industry_hint,
            year_range=year_range,
            raw_input=text
        )
    
    def _extract_stock_codes(self, text: str) -> List[str]:
        """提取文本中的股票代码（6位数字）"""
        # 匹配6位数字，可能是股票代码
        pattern = r'\b(\d{6})\b'
        codes = re.findall(pattern, text)
        # 验证是否是有效的A股代码（以0/3/6开头）
        valid_codes = [c for c in codes if c[0] in '036']
        return list(set(valid_codes))  # 去重
    
    def _extract_company_names(self, text: str) -> List[str]:
        """提取公司名称 - 使用简单直接的匹配"""
        names = []
        
        # 方法1: 直接从映射表中匹配所有已知公司名称
        if self.name_to_code:
            # 按名称长度降序排序，优先匹配长名称
            sorted_names = sorted(self.name_to_code.keys(), key=len, reverse=True)
            
            for name in sorted_names:
                if len(name) < 2:
                    continue
                if name in ['分析', '对比', '看看', '比较', '研究', '评价', '一下', '股份', '集团', '公司']:
                    continue
                
                # 检查文本中是否包含该名称
                if name in text:
                    names.append(name)
        
        # 方法2: 尝试解析顿号或逗号分隔的列表
        if len(names) < 2:
            # 去除常见动词后的文本
            cleaned = text
            for verb in ['分析一下', '分析', '对比', '看看', '比较', '研究', '评价']:
                if cleaned.startswith(verb):
                    cleaned = cleaned[len(verb):].strip()
                    break
            
            # 按分隔符分割
            parts = re.split(r'[、,，]|\s+和\s+|\s+与\s+', cleaned)
            for part in parts:
                part = part.strip()
                if len(part) >= 2 and part not in names:
                    if part not in ['分析', '对比', '看看', '比较', '研究', '评价', '一下']:
                        names.append(part)
        
        return names
    
    def _extract_industry_hint(self, text: str) -> Optional[str]:
        """提取行业提示词"""
        industry_keywords = {
            '白酒': ['白酒', '酒业', '酒类'],
            '新能源': ['新能源', '光伏', '锂电', '储能', '电动车'],
            '医药': ['医药', '医疗', '生物', '制药'],
            '科技': ['科技', '芯片', '半导体', 'AI', '人工智能'],
            '金融': ['金融', '银行', '保险', '证券'],
            '制造': ['制造', '工业', '机械', '装备'],
        }
        
        for industry, keywords in industry_keywords.items():
            if any(kw in text for kw in keywords):
                return industry
        return None
    
    def _extract_year_range(self, text: str) -> Optional[Tuple[int, int]]:
        """提取年份范围"""
        # 匹配年份模式
        years = re.findall(r'20(\d{2})[年]?', text)
        if len(years) >= 2:
            start = int('20' + years[0])
            end = int('20' + years[-1])
            return (min(start, end), max(start, end))
        return None
    
    def search_company(self, query: str, top_n: int = 5) -> List[Dict]:
        """
        模糊搜索公司
        
        Args:
            query: 搜索关键词
            top_n: 返回结果数量
            
        Returns:
            匹配的公司列表
        """
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
            
            # 模糊匹配名称
            if query in name or query in name.replace(' ', ''):
                score = 80 if query == name else 60
                results.append({'code': code, 'name': name, 'score': score})
        
        # 按匹配度排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]
    
    def resolve_companies(self, parsed: ParsedInput) -> List[str]:
        """
        解析并返回最终的股票代码列表
        
        Args:
            parsed: 解析后的输入
            
        Returns:
            股票代码列表
        """
        codes = []
        
        # 1. 直接使用提取的股票代码
        codes.extend(parsed.stock_codes)
        
        # 2. 通过公司名称查找代码
        for name in parsed.company_names:
            # 精确匹配
            if name in self.name_to_code:
                codes.append(self.name_to_code[name])
            else:
                # 模糊搜索
                search_results = self.search_company(name, top_n=1)
                if search_results:
                    codes.append(search_results[0]['code'])
        
        # 去重
        return list(set(codes))
    
    def interactive_resolve(self, parsed: ParsedInput) -> List[str]:
        """
        交互式解析，当匹配不明确时提供选项
        
        Args:
            parsed: 解析后的输入
            
        Returns:
            最终确认的股票代码列表
        """
        codes = []
        
        print("\n【输入解析结果】")
        print(f"原始输入: {parsed.raw_input}")
        
        # 处理提取的代码
        if parsed.stock_codes:
            print(f"\n识别到股票代码: {', '.join(parsed.stock_codes)}")
            codes.extend(parsed.stock_codes)
        
        # 处理公司名称
        for name in parsed.company_names:
            print(f"\n处理公司: {name}")
            
            # 精确匹配
            if name in self.name_to_code:
                code = self.name_to_code[name]
                full_name = self.stock_list[self.stock_list['code'] == code]['name'].values[0]
                print(f"  ✓ 精确匹配: {full_name} ({code})")
                codes.append(code)
            else:
                # 模糊搜索
                results = self.search_company(name, top_n=3)
                if results:
                    print(f"  找到 {len(results)} 个匹配结果:")
                    for i, r in enumerate(results, 1):
                        print(f"    {i}. {r['name']} ({r['code']}) - 匹配度: {r['score']}")
                    # 选择第一个作为默认
                    codes.append(results[0]['code'])
                else:
                    print(f"  ✗ 未找到匹配的公司")
        
        # 去重
        unique_codes = list(set(codes))
        print(f"\n最终选定 {len(unique_codes)} 家企业:")
        for code in unique_codes:
            name = self.stock_list[self.stock_list['code'] == code]['name'].values[0] if not self.stock_list.empty else 'Unknown'
            print(f"  - {name} ({code})")
        
        return unique_codes


def demo():
    """演示功能"""
    processor = NaturalLanguageProcessor()
    
    test_inputs = [
        "分析一下茅台、五粮液和美的集团",
        "帮我看看600519和000858这两家公司",
        "对比一下白酒行业的贵州茅台、泸州老窖",
        "分析比亚迪、宁德时代、隆基绿能这三家新能源企业",
        "研究一下000333的经营状况",
    ]
    
    print("=" * 60)
    print("自然语言输入处理器 - 功能演示")
    print("=" * 60)
    
    for text in test_inputs:
        print(f"\n输入: {text}")
        print("-" * 60)
        
        parsed = processor.parse_input(text)
        print(f"解析结果:")
        print(f"  - 股票代码: {parsed.stock_codes}")
        print(f"  - 公司名称: {parsed.company_names}")
        print(f"  - 行业提示: {parsed.industry_hint}")
        print(f"  - 年份范围: {parsed.year_range}")
        
        codes = processor.resolve_companies(parsed)
        print(f"  → 最终代码: {codes}")


if __name__ == "__main__":
    demo()
