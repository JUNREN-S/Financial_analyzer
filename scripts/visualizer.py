#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化模块 - Visualization Module
生成雷达图、排名图、热力图、风险矩阵等图表
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 无界面环境使用
import numpy as np
import pandas as pd
import seaborn as sns
from typing import Dict, List, Optional
from pathlib import Path

# 设置中文字体 - 优先使用系统可用字体
# macOS: PingFang SC / Hiragino Sans GB / STHeiti
# Linux: Noto Sans CJK SC / WenQuanYi Micro Hei / SimHei
# Windows: SimHei / Microsoft YaHei
plt.rcParams['font.sans-serif'] = [
    'PingFang SC',           # macOS 苹方
    'Hiragino Sans GB',      # macOS 冬青黑体
    'STHeiti',               # macOS 黑体
    'Noto Sans CJK SC',      # Linux 思源黑体
    'WenQuanYi Micro Hei',   # Linux 文泉驿
    'Microsoft YaHei',       # Windows 微软雅黑
    'SimHei',                # Windows 黑体
    'DejaVu Sans',
    'Arial Unicode MS',
    'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class Visualizer:
    """金融分析结果可视化器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 配色方案
        self.colors = {
            'primary': '#3498db',
            'secondary': '#2ecc71',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'info': '#9b59b6',
            'dark': '#2c3e50',
        }
        
        # 维度颜色映射
        self.dimension_colors = {
            '运营能力': '#3498db',
            '盈利能力': '#2ecc71',
            '偿债能力': '#e74c3c',
            '成长能力': '#f39c12',
            '现金流健康': '#9b59b6',
        }
    
    def plot_radar_chart(self, dimension_scores: pd.DataFrame, 
                         top_n: int = 5, save_path: Optional[str] = None) -> str:
        """
        绘制雷达图 - 展示各维度得分
        
        Args:
            dimension_scores: 各维度得分DataFrame
            top_n: 展示前N家企业
            save_path: 保存路径
        """
        # 获取维度列（排除公司名称）
        dimension_cols = [col for col in dimension_scores.columns if col != '公司名称']
        
        # 选择得分最高的企业
        if '综合得分' in dimension_scores.columns:
            plot_data = dimension_scores.nlargest(top_n, '综合得分')
        else:
            # 计算平均维度得分排序
            dimension_cols_only = [c for c in dimension_cols if c != '综合得分']
            dimension_scores['avg'] = dimension_scores[dimension_cols_only].mean(axis=1)
            plot_data = dimension_scores.nlargest(top_n, 'avg')
        
        # 计算数据范围，动态调整显示区间
        dimension_cols_only = [c for c in dimension_cols if c != '综合得分']
        all_values = plot_data[dimension_cols_only].values.flatten()
        data_max = np.max(all_values)
        data_min = np.min(all_values)
        # 设置y轴上限为数据最大值的1.2倍（留出顶部空间），但至少0.3确保可读性
        y_max = max(data_max * 1.2, 0.3)
        # 设置y轴下限为数据最小值的0.8倍或0（取较小值确保数据不贴边）
        y_min = max(data_min * 0.8, 0)
        
        # 设置角度
        angles = np.linspace(0, 2 * np.pi, len(dimension_cols_only), endpoint=False).tolist()
        angles += angles[:1]  # 闭合
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
        
        # 绘制每家企业的雷达图
        colors = plt.cm.Set3(np.linspace(0, 1, top_n))
        
        for idx, (_, row) in enumerate(plot_data.iterrows()):
            values = [row[col] for col in dimension_cols_only]
            values += values[:1]  # 闭合
            
            ax.plot(angles, values, 'o-', linewidth=2, label=row['公司名称'], color=colors[idx])
            ax.fill(angles, values, alpha=0.15, color=colors[idx])
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dimension_cols_only, fontsize=11)
        # 动态设置y轴范围
        ax.set_ylim(y_min, y_max)
        # 根据范围设置刻度
        tick_step = y_max / 5
        yticks = [tick_step * i for i in range(1, 6)]
        yticklabels = [f'{t:.2f}' for t in yticks]
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, fontsize=9)
        
        # 标题和图例
        ax.set_title('企业综合能力雷达图 (TOP {})'.format(top_n), fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        # 保存
        if save_path is None:
            save_path = self.output_dir / 'radar_chart.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def plot_ranking_chart(self, ranks: pd.DataFrame, save_path: Optional[str] = None) -> str:
        """
        绘制综合排名柱状图
        """
        # 取前15名
        plot_data = ranks.head(15).copy()
        
        # 动态计算x轴范围
        score_min = plot_data['综合得分'].min()
        score_max = plot_data['综合得分'].max()
        x_min = max(score_min - 0.05, 0)
        x_max = min(score_max + 0.05, 1.0)
        # 如果范围太小，适当扩展
        if x_max - x_min < 0.3:
            x_min = max(x_min - 0.1, 0)
            x_max = min(x_max + 0.1, 1.0)
        
        # 创建水平柱状图
        fig, ax = plt.subplots(figsize=(12, 8))
        
        colors = plt.cm.RdYlGn(plot_data['综合得分'])
        bars = ax.barh(range(len(plot_data)), plot_data['综合得分'], color=colors)
        
        # 反转Y轴使第1名在顶部
        ax.invert_yaxis()
        
        # 设置标签
        ax.set_yticks(range(len(plot_data)))
        ax.set_yticklabels(plot_data['公司名称'], fontsize=10)
        ax.set_xlabel('综合得分', fontsize=12)
        ax.set_title('企业综合评分排名 (TOP 15)', fontsize=14, fontweight='bold')
        ax.set_xlim(x_min, x_max)
        
        # 添加数值标签
        for i, (idx, row) in enumerate(plot_data.iterrows()):
            ax.text(row['综合得分'] + 0.005, i, f"{row['综合得分']:.3f}", 
                   va='center', fontsize=9)
        
        # 添加网格线
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.output_dir / 'ranking_chart.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def plot_heatmap(self, dimension_scores: pd.DataFrame, 
                     save_path: Optional[str] = None) -> str:
        """
        绘制维度得分热力图
        """
        # 准备数据
        plot_data = dimension_scores.copy()
        
        # 选择前20名
        if '综合得分' in plot_data.columns:
            plot_data = plot_data.nlargest(20, '综合得分')
        
        # 提取维度列
        dimension_cols = [col for col in plot_data.columns 
                         if col not in ['公司名称', '股票代码', '综合得分']]
        
        # 设置索引
        plot_matrix = plot_data.set_index('公司名称')[dimension_cols]
        
        # 处理NaN值 - 用0填充缺失值以便显示
        plot_matrix = plot_matrix.fillna(0)
        
        # 计算数据范围，动态调整颜色映射
        data_min = plot_matrix.values.min()
        data_max = plot_matrix.values.max()
        
        # 如果所有数据都是0，设置默认范围
        if data_max == 0:
            data_max = 0.1
        
        # 留出边界空间
        vmin = max(data_min * 0.9, 0)
        vmax = data_max * 1.1
        # 如果范围太小，确保最小显示范围
        if vmax - vmin < 0.01:
            vmax = vmin + 0.01
        
        # 创建热力图
        fig, ax = plt.subplots(figsize=(12, 10))
        
        sns.heatmap(plot_matrix, annot=True, fmt='.2f', cmap='RdYlGn',
                   center=(vmin + vmax) / 2, vmin=vmin, vmax=vmax, linewidths=0.5,
                   cbar_kws={'label': '得分'}, ax=ax)
        
        ax.set_title('企业各维度得分热力图', fontsize=14, fontweight='bold')
        ax.set_xlabel('评估维度', fontsize=12)
        ax.set_ylabel('企业', fontsize=12)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.output_dir / 'heatmap.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def plot_risk_matrix(self, risk_matrix_data: pd.DataFrame,
                         save_path: Optional[str] = None) -> str:
        """
        绘制风险-收益散点图（风险矩阵）
        """
        fig, ax = plt.subplots(figsize=(12, 9))
        
        # 定义风险等级颜色
        risk_colors = {
            '低风险': '#2ecc71',
            '中等风险': '#f39c12',
            '高风险': '#e74c3c',
        }
        
        # 动态计算坐标轴范围
        risk_min = risk_matrix_data['风险得分'].min()
        risk_max = risk_matrix_data['风险得分'].max()
        score_min = risk_matrix_data['综合得分'].min()
        score_max = risk_matrix_data['综合得分'].max()
        
        x_min = max(risk_min - 0.1, 0)
        x_max = min(risk_max + 0.1, 1.0)
        y_min = max(score_min - 0.1, 0)
        y_max = min(score_max + 0.1, 1.0)
        
        # 确保最小显示范围，避免数据挤在一起
        if x_max - x_min < 0.4:
            x_center = (x_min + x_max) / 2
            x_min = max(x_center - 0.2, 0)
            x_max = min(x_center + 0.2, 1.0)
        if y_max - y_min < 0.4:
            y_center = (y_min + y_max) / 2
            y_min = max(y_center - 0.2, 0)
            y_max = min(y_center + 0.2, 1.0)
        
        # 绘制散点
        for risk_level in risk_colors:
            mask = risk_matrix_data['风险等级'] == risk_level
            subset = risk_matrix_data[mask]
            if len(subset) > 0:
                ax.scatter(subset['风险得分'], subset['综合得分'],
                          c=risk_colors[risk_level], label=risk_level,
                          s=150, alpha=0.7, edgecolors='white', linewidth=1)
        
        # 添加企业标签（只标注极端值）
        for idx, row in risk_matrix_data.iterrows():
            # 标注高风险低收益或低风险高收益的企业
            if (row['风险等级'] == '高风险' and row['综合得分'] < 0.5) or \
               (row['风险等级'] == '低风险' and row['综合得分'] > 0.7):
                ax.annotate(row['股票名称'],
                           (row['风险得分'], row['综合得分']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=9, alpha=0.8)
        
        # 添加象限分割线（基于实际数据范围）
        x_mid = (x_min + x_max) / 2
        y_mid = (y_min + y_max) / 2
        ax.axhline(y=y_mid, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=x_mid, color='gray', linestyle='--', alpha=0.5)
        
        # 添加象限标签
        ax.text(x_min + (x_mid - x_min) / 2, y_max - (y_max - y_mid) / 2, '高风险高收益', fontsize=11, ha='center', 
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
        ax.text(x_mid + (x_max - x_mid) / 2, y_max - (y_max - y_mid) / 2, '低风险高收益\n(理想区域)', fontsize=11, ha='center',
               bbox=dict(boxstyle='round', facecolor='green', alpha=0.3))
        ax.text(x_min + (x_mid - x_min) / 2, y_min + (y_mid - y_min) / 2, '高风险低收益\n(危险区域)', fontsize=11, ha='center',
               bbox=dict(boxstyle='round', facecolor='red', alpha=0.3))
        ax.text(x_mid + (x_max - x_mid) / 2, y_min + (y_mid - y_min) / 2, '低风险低收益', fontsize=11, ha='center',
               bbox=dict(boxstyle='round', facecolor='gray', alpha=0.3))
        
        ax.set_xlabel('风险得分 (越高风险越低)', fontsize=12)
        ax.set_ylabel('综合得分 (TOPSIS)', fontsize=12)
        ax.set_title('企业风险-收益矩阵', fontsize=14, fontweight='bold')
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.legend(title='风险等级', loc='lower left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.output_dir / 'risk_matrix.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def plot_dimension_comparison(self, dimension_scores: pd.DataFrame,
                                   save_path: Optional[str] = None) -> str:
        """
        绘制各维度得分对比柱状图
        """
        # 计算各维度平均分
        dimension_cols = [col for col in dimension_scores.columns 
                         if col not in ['公司名称', '股票代码', '综合得分']]
        
        avg_scores = dimension_scores[dimension_cols].mean().sort_values(ascending=True)
        
        # 动态计算x轴范围 - 更紧凑的显示
        score_min = avg_scores.min()
        score_max = avg_scores.max()
        x_min = 0
        # 根据数据最大值设置上限，留出10%边距
        x_max = score_max * 1.15
        # 如果范围很小，使用更紧凑的显示
        if x_max < 0.1:
            x_max = 0.1
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        colors = [self.dimension_colors.get(col, '#3498db') for col in avg_scores.index]
        bars = ax.barh(range(len(avg_scores)), avg_scores.values, color=colors)
        
        ax.set_yticks(range(len(avg_scores)))
        ax.set_yticklabels(avg_scores.index, fontsize=11)
        ax.set_xlabel('平均得分', fontsize=12)
        ax.set_title('各评估维度平均分对比', fontsize=14, fontweight='bold')
        ax.set_xlim(x_min, x_max)
        
        # 添加数值标签 - 位置基于实际x轴范围
        label_offset = (x_max - x_min) * 0.01
        for i, v in enumerate(avg_scores.values):
            ax.text(v + label_offset, i, f'{v:.3f}', va='center', fontsize=10)
        
        ax.grid(axis='x', alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.output_dir / 'dimension_comparison.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def plot_weight_distribution(self, weights: Dict[str, float],
                                  save_path: Optional[str] = None) -> str:
        """
        绘制指标权重饼图
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # 按维度分组计算权重
        # 这里简化处理，直接按指标名称前缀分组
        dimension_weights = {}
        for indicator, weight in weights.items():
            # 简化：按关键词分组
            if any(x in indicator for x in ['周转', '周期']):
                dim = '运营能力'
            elif any(x in indicator for x in ['ROE', 'ROA', '利润', '毛利']):
                dim = '盈利能力'
            elif any(x in indicator for x in ['负债', '比率', '保障']):
                dim = '偿债能力'
            elif any(x in indicator for x in ['增长']):
                dim = '成长能力'
            elif any(x in indicator for x in ['现金', '现金流']):
                dim = '现金流健康'
            else:
                dim = '其他'
            
            dimension_weights[dim] = dimension_weights.get(dim, 0) + weight
        
        # 左图：维度权重饼图
        colors_pie = [self.dimension_colors.get(dim, '#95a5a6') for dim in dimension_weights.keys()]
        wedges, texts, autotexts = ax1.pie(dimension_weights.values(), 
                                           labels=dimension_weights.keys(),
                                           autopct='%1.1f%%',
                                           colors=colors_pie,
                                           startangle=90)
        ax1.set_title('评估维度权重分布', fontsize=13, fontweight='bold')
        
        # 右图：各指标权重条形图
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        indicators = [x[0] for x in sorted_weights]
        values = [x[1] for x in sorted_weights]
        
        y_pos = np.arange(len(indicators))
        ax2.barh(y_pos, values, color='#3498db')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(indicators, fontsize=9)
        ax2.invert_yaxis()
        ax2.set_xlabel('权重', fontsize=11)
        ax2.set_title('各指标权重排名', fontsize=13, fontweight='bold')
        
        # 添加数值标签
        for i, v in enumerate(values):
            ax2.text(v + 0.005, i, f'{v:.3f}', va='center', fontsize=8)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.output_dir / 'weight_distribution.png'
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def generate_all_charts(self, analysis_results: Dict, risk_matrix_data: pd.DataFrame) -> Dict[str, str]:
        """
        生成所有图表
        """
        print("正在生成可视化图表...")
        
        charts = {}
        
        # 1. 雷达图
        print("  - 生成雷达图...")
        if 'dimension_scores' in analysis_results:
            charts['radar'] = self.plot_radar_chart(analysis_results['dimension_scores'])
        
        # 2. 排名图
        print("  - 生成排名图...")
        if 'ranks' in analysis_results:
            charts['ranking'] = self.plot_ranking_chart(analysis_results['ranks'])
        
        # 3. 热力图
        print("  - 生成热力图...")
        if 'dimension_scores' in analysis_results:
            charts['heatmap'] = self.plot_heatmap(analysis_results['dimension_scores'])
        
        # 4. 风险矩阵
        print("  - 生成风险矩阵...")
        charts['risk_matrix'] = self.plot_risk_matrix(risk_matrix_data)
        
        # 5. 维度对比图
        print("  - 生成维度对比图...")
        if 'dimension_scores' in analysis_results:
            charts['dimension_comparison'] = self.plot_dimension_comparison(analysis_results['dimension_scores'])
        
        # 6. 权重分布图
        print("  - 生成权重分布图...")
        if 'weights' in analysis_results:
            charts['weights'] = self.plot_weight_distribution(analysis_results['weights'])
        
        print(f"\n图表已保存到: {self.output_dir}")
        return charts


if __name__ == "__main__":
    # 测试代码
    viz = Visualizer()
    
    # 测试数据
    test_data = pd.DataFrame({
        '公司名称': ['公司A', '公司B', '公司C'],
        '运营能力': [0.8, 0.6, 0.9],
        '盈利能力': [0.7, 0.8, 0.6],
        '偿债能力': [0.6, 0.7, 0.8],
        '综合得分': [0.75, 0.70, 0.78],
    })
    
    test_ranks = pd.DataFrame({
        '排名': [1, 2, 3],
        '公司名称': ['公司C', '公司A', '公司B'],
        '综合得分': [0.78, 0.75, 0.70],
    })
    
    viz.plot_radar_chart(test_data)
    viz.plot_ranking_chart(test_ranks)
    print("测试图表生成完成")
