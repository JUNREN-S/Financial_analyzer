#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试脚本 - 测试数据接口"""

import akshare as ak
import pandas as pd

# 测试贵州茅台
test_code = "600519"

print(f"测试获取 {test_code} 财务数据\n")

# 测试1: 财务分析指标
print("=" * 60)
print("测试1: stock_financial_analysis_indicator")
print("=" * 60)
try:
    df1 = ak.stock_financial_analysis_indicator(symbol=test_code)
    print(f"数据形状: {df1.shape}")
    print(f"列名: {list(df1.columns)}")
    if not df1.empty:
        print("\n第一行数据:")
        print(df1.iloc[0])
except Exception as e:
    print(f"错误: {e}")

# 测试2: 新浪财务摘要
print("\n" + "=" * 60)
print("测试2: stock_financial_report_sina")
print("=" * 60)
try:
    df2 = ak.stock_financial_report_sina(stock=test_code)
    print(f"数据形状: {df2.shape}")
    print(f"列名: {list(df2.columns)}")
    if not df2.empty:
        print("\n前几行:")
        print(df2.head(3))
except Exception as e:
    print(f"错误: {e}")

# 测试3: 主要财务指标
print("\n" + "=" * 60)
print("测试3: stock_main_indicator")
print("=" * 60)
try:
    df3 = ak.stock_main_indicator(symbol=test_code)
    print(f"数据形状: {df3.shape}")
    print(f"列名: {list(df3.columns)}")
    if not df3.empty:
        print("\n第一行数据:")
        print(df3.iloc[0])
except Exception as e:
    print(f"错误: {e}")

# 测试4: 个股指标
print("\n" + "=" * 60)
print("测试4: stock_individual_info")
print("=" * 60)
try:
    df4 = ak.stock_individual_info(symbol=test_code)
    print(f"数据形状: {df4.shape}")
    print(df4)
except Exception as e:
    print(f"错误: {e}")
