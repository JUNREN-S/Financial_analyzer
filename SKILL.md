---
name: financial-analyzer
description: 基于熵权法+TOPSIS的企业综合评价与风险评估系统,支持AkShare在线A股数据采集和Excel本地导入。Use when asked to comprehensively evaluate/score/rank companies, assess financial risk (五维度), screen 新质生产力 cases, profile enterprises (9种类型), recommend comparable firms, or prepare regression data from Chinese A-share financial data.
---

# Financial Analyzer Skill

基于 **熵权法 + TOPSIS** 的企业综合评价与风险评估系统，支持在线 A 股数据采集和本地 Excel 数据导入。

## 功能概述

| 功能 | 说明 |
|------|------|
| **数据采集** | AkShare 在线获取 / Excel 本地导入 |
| **权重计算** | 熵权法客观赋权 |
| **综合评价** | TOPSIS 逼近理想解排序 |
| **风险评估** | 五维度风险识别 |
| **案例筛选** | 新质生产力主题案例适配性评估 |
| **企业画像** | 基于核心指标的企业属性分类（9种类型） |
| **相似推荐** | 智能推荐相似可比企业 |
| **回归准备** | RD强度-Growth回归分析数据准备 |
| **可视化** | 雷达图、热力图、排名图等 |

---

## 快速开始

### 安装依赖

```bash
cd ~/.openclaw/workspace/skills/financial-analyzer
pip install -r requirements.txt
```

### 运行方式

#### 方式一：在线 A 股数据（默认）

```bash
cd scripts

# 演示模式（5家企业快速测试）
python main.py --demo

# 完整分析（37家企业池）
python main.py

# 自定义企业
python main.py -c 600519 000858 000333
```

#### 方式二：本地 Excel 数据（智能修复）

```bash
# 基本用法
python main.py --excel /path/to/data.xlsx

# 指定企业名称列
python main.py -e /path/to/data.xlsx --index-col "公司名称"

# 指定工作表（多 sheet 文件）
python main.py -e data.xlsx --sheet Sheet1

# 自定义输出目录
python main.py -e data.xlsx -o ./result
```

**Excel 格式支持：**
- **标准格式**：行=企业，列=财务指标（自动识别）
- **非标准格式**：即使文件格式不规范，也能智能提取企业名称并在线获取数据
- **多工作表**：使用 `--sheet` 参数指定工作表名称

| 公司简称 | ROE | 资产负债率 | 营收增长率 |
|---------|-----|-----------|-----------|
| 茅台 | 0.25 | 0.25 | 0.15 |
| 五粮液 | 0.20 | 0.30 | 0.12 |

**智能数据修复**：当 Excel 文件数据不完整或格式非标准时，系统会自动：
1. 从文件中提取企业名称
2. 匹配对应的股票代码
3. 在线获取完整的财务数据
4. 继续执行 TOPSIS 分析

**自动过滤**：自动识别并过滤 Excel 中的空行（如你的文件自动过滤了 100万+ 空行）

示例场景：你上传了一个回归分析结果的 Excel 文件，只要文件中出现 "茅台"、"600519" 等企业信息，系统就能自动识别并获取完整数据进行财务分析。

---

### 方式三：自然语言输入（智能解析）

```bash
# 用自然语言描述分析需求，系统自动解析公司并在线查找数据
python main.py --query "分析一下茅台、五粮液和美的集团"
python main.py -q "对比600519和000858这两家公司"

# 支持多种表达方式
python main.py -q "看看新能源行业的比亚迪、宁德时代"
python main.py -q "研究一下白酒行业的贵州茅台、泸州老窖"
```

**支持的自然语言模式：**
- 公司名称：茅台、五粮液、美的集团、比亚迪...
- 股票代码：600519、000858、000333...
- 行业提示：新能源、白酒、医药、科技...
- 动词引导：分析、对比、看看、研究、比较...

---

### 方式四：前置筛选模式（新质生产力主题）

```bash
# 前置筛选 + TOPSIS 分析完整流程
python main.py --screening data/companies.csv --target "智算云科"

# 只进行筛选，不指定目标企业
python main.py -s data/companies.csv

# 指定推荐相似企业数量
python main.py -s data.csv -t "边缘感知" --similar-n 3
```

**筛选流程：**
1. 评估企业是否适合作为"新质生产力"主题案例
2. 若目标企业不合适，推荐相似的可替代企业
3. 筛选后的企业池进入 TOPSIS 分析

**判定标准：**
- 是否与新质生产力相关（AI、算力、芯片、机器人等关键词）
- 数据完整性（指标覆盖率 ≥ 70%）
- 年份连续性（≥ 3年）
- 回归可用性（有 RD 强度和营收增长率数据）

**输入 CSV 格式：**
```csv
company_name,year,industry,revenue,rd_expense,...
智算云科,2023,人工智能软件,1780,275,...
```

---

#### 方式五：案例筛选与相似企业推荐（AI_Agents 集成）

```bash
# 评估目标企业是否适合作为案例，并推荐相似企业
cd scripts
python finance_case_tool.py --data data/companies.csv --company "智算云科"

# 参数说明
# --data: 输入CSV文件路径（company-year格式）
# --company: 目标企业名称
# --min-years: 最少年份数（默认3）
# --min-indicator-coverage: 指标覆盖率阈值（默认0.7）
# --similar-top-n: 推荐相似企业数量（默认5）
```

**输入CSV格式（company-year面板数据）：**
```csv
company_name,year,industry,main_business,revenue,rd_expense,roe,asset_liability_ratio,...
智算云科,2022,人工智能,AI软件,1500,200,0.15,0.40,...
智算云科,2023,人工智能,AI软件,1780,275,0.18,0.38,...
智算云科,2024,人工智能,AI软件,2100,350,0.20,0.35,...
```

**输出文件（5份）：**
| 文件 | 说明 |
|------|------|
| `*_report.json` | 目标企业分析总报告 |
| `*_topsis_input.csv` | TOPSIS分析输入数据 |
| `*_regression_input.csv` | RD-Growth回归输入数据 |
| `*_similar_companies.csv` | 相似企业推荐列表 |
| `*_company_summary.csv` | 全部企业案例适配概览 |

**案例适配判定标准：**
- 新质生产力关联度（AI、算力、芯片等关键词匹配）
- 数据连续性（≥3年）
- 指标覆盖率（≥70%）
- 回归可用性（有RD强度和Growth数据）

---

#### 方式六：企业属性画像（紧凑型指标表）

适用于已有精简指标（Growth、RDi、ROE、资产负债率）的场景：

```bash
# 基于4个核心指标生成企业属性画像
cd scripts
python company_attribute_profiler.py --data data/companies.xlsx --company "中芯国际"

# 参数说明
# --data: 输入文件（支持CSV/XLSX）
# --company: 目标企业名称
# --sheet: XLSX工作表名称（可选）
# --similar-top-n: 推荐相似企业数量（默认5）
```

**输入格式：**
| 公司简称 | Growth | RDi | ROE | 资产负债率 | 所属行业 | 所处赛道 |
|---------|--------|-----|-----|-----------|---------|---------|
| 中芯国际 | 0.25 | 0.15 | 0.10 | 0.35 | 半导体 | 晶圆代工 |
| 宁德时代 | 0.30 | 0.08 | 0.20 | 0.50 | 新能源 | 动力电池 |

**9种企业属性类型：**
| 类型 | 特征描述 |
|------|---------|
| 技术扩张领跑型 | 高研发投入 + 高成长 + 较好盈利 |
| 高投入换增长型 | 高研发投入 + 高成长 + 盈利一般 |
| 研发蓄力转化型 | 高研发投入 + 低成长（储备期） |
| 扩张进攻型 | 高成长 + 高杠杆 |
| 盈利稳健兑现型 | 高盈利 + 低杠杆 |
| 财务承压型 | 高杠杆 + 低盈利 |
| 成长承压型 | 低成长 + 低盈利 |
| 研发驱动稳健型 | 中高研发 + 较好盈利 + 可控杠杆 |
| 均衡发展型 | 各项指标中等均衡 |

**输出文件（3份）：**
| 文件 | 说明 |
|------|------|
| `*_attribute_profiles.csv` | 全部企业属性画像总表 |
| `*_similar_companies.csv` | 与目标企业最接近的可比企业 |
| `*_attribute_report.json` | 目标企业详细属性判断报告 |

**属性标签体系：**
- 创新属性：`高研发投入` / `研发驱动` / `研发中等` / `研发偏弱`
- 成长属性：`高成长` / `成长较强` / `成长稳健` / `成长偏弱`
- 盈利属性：`盈利效率突出` / `盈利能力较强` / `盈利能力稳健` / `盈利效率偏弱`
- 杠杆属性：`低杠杆` / `杠杆可控` / `杠杆偏高` / `高杠杆`
- 风险等级：`低风险` / `可控风险` / `中等风险` / `偏高风险` / `高风险`
- 案例优先级：`核心案例候选` / `可比样本` / `观察样本` / `待补充样本`

---

## 算法原理

### 1. 数据标准化（Min-Max）

正向指标：$Z_{ij} = \frac{X_{ij} - X_{min}}{X_{max} - X_{min}}$

负向指标：$Z_{ij} = \frac{X_{max} - X_{ij}}{X_{max} - X_{min}}$

### 2. 熵权法计算权重

- 计算比重：$p_{ij} = \frac{Z_{ij}}{\sum Z_{ij}}$
- 信息熵：$e_j = -k \sum p_{ij} \cdot \ln(p_{ij})$
- 差异系数：$d_j = 1 - e_j$
- 权重：$w_j = \frac{d_j}{\sum d_j}$

### 3. TOPSIS 综合评价

- 加权矩阵：$V_{ij} = w_j \cdot Z_{ij}$
- 正理想解：$A^+ = \max(V_j)$
- 负理想解：$A^- = \min(V_j)$
- 欧氏距离：$D^+ = \sqrt{\sum(V_{ij} - A^+_j)^2}$
- 贴近度：$C_i = \frac{D^-}{D^+ + D^-}$

---

## 输出格式

### Excel 模式（简洁版，对齐 a.py）

```
==================================================
原始数据：
       ROE  资产负债率  营收增长率  总资产周转率
股票名称
茅台    0.25   0.25   0.15    0.50
五粮液   0.20   0.30   0.12    0.45
...
--------------------------------------------------
标准化后的数据：
...
--------------------------------------------------
各指标权重（熵权法）：
  资产负债率: 0.2723
  营收增长率: 0.2562
  ...
--------------------------------------------------
最终TOPSIS评分及排名（按得分降序）：
           得分  排名
茅台   0.609816   1
美的   0.498849   2
...
==================================================
```

### 在线模式（完整版）

输出目录结构：
```
result/test_x/
├── raw_data.csv              # 原始数据
├── ranking.csv               # 综合排名
├── indicator_weights.csv     # 指标权重
├── dimension_scores.csv      # 各维度得分
├── risk_assessment.csv       # 风险评估
├── analysis_report.txt       # 文本报告
├── radar_chart.png           # 雷达图
├── ranking_chart.png         # 排名图
├── heatmap.png               # 热力图
├── risk_matrix.png           # 风险矩阵
├── dimension_comparison.png  # 维度对比
└── weight_distribution.png   # 权重分布
```

---

## 评估体系

### 五维度指标

| 维度 | 核心指标 |
|------|----------|
| **运营能力** | 总资产周转率、存货周转率、应收账款周转率、营业周期 |
| **盈利能力** | ROE、ROA、销售毛利率、销售净利率 |
| **偿债能力** | 资产负债率、流动比率、速动比率、利息保障倍数 |
| **成长能力** | 营收增长率、净利润增长率、总资产增长率、净资产增长率 |
| **现金流健康** | 经营现金流比率、自由现金流、现金流动负债比、净利润现金含量 |

### 预设企业池（37家）

涵盖消费/制造、医药、金融、基建/周期、科技/制造等行业龙头企业。

---

## 文件结构

```
financial-analyzer/
├── scripts/
│   ├── main.py                    # 主程序入口
│   ├── data_fetcher.py            # AkShare 数据采集
│   ├── nlp_input.py               # 自然语言输入处理器
│   ├── case_selector.py           # 前置筛选模块
│   ├── excel_loader.py            # Excel 数据加载
│   ├── intelligent_repair.py      # 智能数据修复
│   ├── calculator.py              # 熵权法+TOPSIS计算
│   ├── risk_assessor.py           # 风险评估
│   ├── visualizer.py              # 可视化生成
│   ├── new_quality_checker.py     # 新质生产力企业筛选
│   ├── finance_case_tool.py       # 案例筛选与相似推荐（AI_Agents）
│   └── company_attribute_profiler.py  # 企业属性画像（AI_Agents）
├── config/
│   └── indicators.py              # 指标体系配置
├── requirements.txt               # Python依赖
├── SKILL.md                       # 本文件
└── README.md                      # 项目文档
```

---

## 技术栈

- **数据源**: AkShare / Excel
- **计算**: NumPy, Pandas
- **可视化**: Matplotlib, Seaborn
- **字体**: 自动适配 macOS(PingFang SC) / Linux / Windows

---

## 使用建议

1. **论文引用**: 方法论说明使用熵权法+TOPSIS
2. **图表使用**: 生成的图表可直接用于论文
3. **结果解读**: 结合行业特点分析维度得分
4. **数据准备**: Excel 模式适合已有数据快速分析

---

## 更新日志

| 日期 | 变更 |
|------|------|
| **2026-03-21** | **NEW** 集成 AI_Agents 功能：`finance_case_tool.py`（案例筛选与相似推荐）、`company_attribute_profiler.py`（企业属性画像9种类型） |
| 2026-03-21 | **NEW** 新质生产力企业筛选功能 (`new_quality_checker.py`)，自动识别8大产业领域企业 |
| 2026-03-20 | **NEW** 智能数据修复功能 (`intelligent_repair.py`)：当 Excel 文件数据不完整或格式非标准时，自动提取企业名称并在线获取完整财务数据 |
| 2026-03-20 | **NEW** 新增自然语言输入功能 (`nlp_input.py`)，支持用自然语言描述分析需求，自动解析公司名称并在线查找数据 |
| 2026-03-20 | **NEW** 接入 AI_Agents 前置筛选模块 (`case_selector.py`)，支持新质生产力主题案例筛选与相似企业推荐 |
| 2026-03-20 | 接入 a.py Excel 数据加载功能，支持简洁输出格式 |
| 2026-03-17 | 扩展企业池至 37 家，新增自动目录命名(test_x)，修复中文字体显示 |
| 2026-03-16 | 创建金融分析师大赛项目，完整实现熵权法+TOPSIS评价系统 |
