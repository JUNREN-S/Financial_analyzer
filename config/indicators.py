# 金融企业智能分析系统 - 指标体系配置
# Financial Enterprise Intelligent Analysis System - Indicator Configuration

# 企业池配置：精选实体经济龙头，覆盖制造业、消费、医药、金融、基建
# 避开概念炒作，注重稳健经营的企业

DEFAULT_COMPANY_POOL = [
    # 消费/制造业
    "600519",  # 贵州茅台 - 白酒龙头
    "000858",  # 五粮液 - 白酒
    "000333",  # 美的集团 - 家电
    "000651",  # 格力电器 - 家电
    "600690",  # 海尔智家 - 家电
    "002594",  # 比亚迪 - 新能源汽车
    "600660",  # 福耀玻璃 - 汽车玻璃
    
    # 医药
    "600276",  # 恒瑞医药 - 创新药
    "000538",  # 云南白药 - 中药
    "603259",  # 药明康德 - CXO
    
    # 金融
    "600036",  # 招商银行 - 零售银行
    "000001",  # 平安银行 - 银行
    "601318",  # 中国平安 - 保险
    
    # 基建/周期
    "600585",  # 海螺水泥 - 水泥龙头
    "601668",  # 中国建筑 - 建筑
    "601088",  # 中国神华 - 煤炭
    
    # 科技/制造
    "000725",  # 京东方A - 面板
    "601012",  # 隆基绿能 - 光伏
    "300124",  # 汇川技术 - 工业自动化
    "002415",  # 海康威视 - 安防
]

# 五大评估维度指标体系
INDICATORS = {
    "运营能力": {
        "description": "企业资产使用效率",
        "indicators": {
            "总资产周转率": {
                "code": "turnover_ratio",
                "field": "total_assets_turnover",
                "direction": "positive",  # 正向指标，越大越好
                "weight": 0.25,
                "description": "营业收入/平均总资产，反映资产运营效率"
            },
            "存货周转率": {
                "code": "inventory_turnover",
                "field": "inventory_turnover",
                "direction": "positive",
                "weight": 0.25,
                "description": "营业成本/平均存货，反映存货管理效率"
            },
            "应收账款周转率": {
                "code": "receivables_turnover",
                "field": "receivable_turnover",
                "direction": "positive",
                "weight": 0.25,
                "description": "营业收入/平均应收账款，反映回款能力"
            },
            "营业周期": {
                "code": "operating_cycle",
                "field": "operating_cycle",
                "direction": "negative",  # 负向指标，越小越好
                "weight": 0.25,
                "description": "存货周转天数+应收账款周转天数"
            }
        }
    },
    
    "盈利能力": {
        "description": "企业赚钱能力",
        "indicators": {
            "ROE_净资产收益率": {
                "code": "roe",
                "field": "roe",
                "direction": "positive",
                "weight": 0.30,
                "description": "净利润/净资产，股东回报率"
            },
            "ROA_总资产收益率": {
                "code": "roa",
                "field": "roa",
                "direction": "positive",
                "weight": 0.25,
                "description": "净利润/总资产，资产利用效率"
            },
            "销售毛利率": {
                "code": "gross_margin",
                "field": "grossprofit_margin",
                "direction": "positive",
                "weight": 0.25,
                "description": "(营收-成本)/营收，产品盈利能力"
            },
            "销售净利率": {
                "code": "net_margin",
                "field": "netprofit_margin",
                "direction": "positive",
                "weight": 0.20,
                "description": "净利润/营收，最终盈利能力"
            }
        }
    },
    
    "偿债能力": {
        "description": "企业财务风险与偿债安全",
        "indicators": {
            "资产负债率": {
                "code": "debt_ratio",
                "field": "debt_asset_ratio",
                "direction": "negative",  # 负向指标，越低越好
                "weight": 0.30,
                "description": "总负债/总资产，财务杠杆水平"
            },
            "流动比率": {
                "code": "current_ratio",
                "field": "current_ratio",
                "direction": "positive",
                "weight": 0.25,
                "description": "流动资产/流动负债，短期偿债能力"
            },
            "速动比率": {
                "code": "quick_ratio",
                "field": "quick_ratio",
                "direction": "positive",
                "weight": 0.25,
                "description": "(流动资产-存货)/流动负债，更严格的短期偿债指标"
            },
            "利息保障倍数": {
                "code": "interest_coverage",
                "field": "interest_cover",
                "direction": "positive",
                "weight": 0.20,
                "description": "息税前利润/利息费用，长期偿债能力"
            }
        }
    },
    
    "成长能力": {
        "description": "企业未来发展潜力",
        "indicators": {
            "营业收入增长率": {
                "code": "revenue_growth",
                "field": "revenue_growth_rate",
                "direction": "positive",
                "weight": 0.30,
                "description": "(本期营收-上期营收)/上期营收"
            },
            "净利润增长率": {
                "code": "profit_growth",
                "field": "profit_growth_rate",
                "direction": "positive",
                "weight": 0.30,
                "description": "(本期净利-上期净利)/上期净利"
            },
            "总资产增长率": {
                "code": "asset_growth",
                "field": "assets_growth_rate",
                "direction": "positive",
                "weight": 0.20,
                "description": "反映企业扩张速度"
            },
            "净资产增长率": {
                "code": "equity_growth",
                "field": "equity_growth_rate",
                "direction": "positive",
                "weight": 0.20,
                "description": "反映股东权益积累"
            }
        }
    },
    
    "现金流健康": {
        "description": "企业现金创造能力",
        "indicators": {
            "经营现金流比率": {
                "code": "ocf_ratio",
                "field": "operating_cash_flow_ratio",
                "direction": "positive",
                "weight": 0.30,
                "description": "经营现金流/营业收入，收入质量"
            },
            "自由现金流": {
                "code": "fcf",
                "field": "free_cash_flow",
                "direction": "positive",
                "weight": 0.25,
                "description": "经营现金流-资本支出，可自由支配现金"
            },
            "现金流动负债比": {
                "code": "cash_debt_ratio",
                "field": "cash_flow_to_debt",
                "direction": "positive",
                "weight": 0.25,
                "description": "经营现金流/流动负债，现金偿债能力"
            },
            "净利润现金含量": {
                "code": "profit_cash_ratio",
                "field": "cash_to_profit_ratio",
                "direction": "positive",
                "weight": 0.20,
                "description": "经营现金流/净利润，利润真实性"
            }
        }
    }
}

# 风险等级阈值配置
RISK_THRESHOLDS = {
    "low": {
        "debt_ratio_max": 0.50,  # 资产负债率上限50%
        "current_ratio_min": 1.5,  # 流动比率下限
        "roe_min": 0.10,  # ROE下限10%
        "ocf_ratio_min": 0.10,  # 现金流比率下限
    },
    "medium": {
        "debt_ratio_max": 0.65,
        "current_ratio_min": 1.0,
        "roe_min": 0.05,
        "ocf_ratio_min": 0.05,
    },
    "high": {
        # 超过medium阈值即为高风险
    }
}

# 输出配置
OUTPUT_CONFIG = {
    "charts": {
        "radar_chart": True,  # 雷达图 - 展示各维度得分
        "ranking_chart": True,  # 排名图 - 综合得分排序
        "heatmap": True,  # 热力图 - 指标对比
        "risk_matrix": True,  # 风险矩阵 - 风险-收益散点
        "dimension_scores": True,  # 各维度得分柱状图
    },
    "tables": {
        "indicator_weights": True,  # 指标权重表
        "company_scores": True,  # 企业得分表
        "risk_assessment": True,  # 风险评估表
    },
    "format": "png",  # 图表格式
    "dpi": 150
}
