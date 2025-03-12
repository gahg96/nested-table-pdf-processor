import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io
import base64
from PIL import Image

def visualize_table_detection(pdf_image, tables_info, output_path=None):
    """可视化表格检测结果"""
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 显示图像
    ax.imshow(pdf_image)
    
    # 添加表格边界框
    for table in tables_info:
        bbox = table['bbox']
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        # 嵌套级别决定颜色
        level = table.get('nesting_level', 0)
        colors = ['r', 'g', 'b', 'c', 'm', 'y']
        color = colors[level % len(colors)]
        
        # 创建矩形
        rect = Rectangle((x1, y1), width, height, 
                         linewidth=2, edgecolor=color, facecolor='none')
        ax.add_patch(rect)
        
        # 添加标签
        table_id = table.get('table_id', 'Unknown')
        ax.text(x1, y1-10, f"Table {table_id} (L{level})", 
                color=color, fontsize=10, weight='bold')
    
    ax.axis('off')
    plt.tight_layout()
    
    # 保存或返回
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        return output_path
    else:
        # 转换为内存中的图像
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf

def visualize_table_structure(table_data, output_path=None):
    """可视化表格结构"""
    if not isinstance(table_data.get('dataframe'), pd.DataFrame):
        print("No valid DataFrame to visualize")
        return None
    
    df = table_data['dataframe']
    title = table_data.get('title', 'Table Structure Visualization')
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 隐藏轴
    ax.axis('off')
    
    # 创建表格
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center',
        cellLoc='center',
        colColours=['#E6F3FF'] * len(df.columns)
    )
    
    # 设置表格属性
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)
    
    # 添加标题
    plt.title(title)
    
    plt.tight_layout()
    
    # 保存或返回
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        return output_path
    else:
        # 转换为内存中的图像
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf

def create_heatmap_for_table(df, output_path=None):
    """为表格数据创建热图"""
    # 尝试将表格数据转换为数值型
    numeric_df = pd.DataFrame()
    
    for col in df.columns:
        try:
            # 尝试转换为数值，忽略错误
            numeric_df[col] = pd.to_numeric(df[col], errors='coerce')
        except:
            # 如果失败，跳过该列
            pass
    
    # 如果没有数值列，返回None
    if numeric_df.empty or numeric_df.isnull().all().all():
        print("No numeric data to visualize")
        return None
    
    # 删除全为NaN的列
    numeric_df = numeric_df.dropna(axis=1, how='all')
    
    # 创建热图
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 用Seaborn更好看，但这里只用Matplotlib以减少依赖
    im = ax.imshow(numeric_df.values, cmap='YlOrRd')
    
    # 添加标签
    ax.set_xticks(np.arange(len(numeric_df.columns)))
    ax.set_yticks(np.arange(len(numeric_df.index)))
    ax.set_xticklabels(numeric_df.columns, rotation=45, ha='right')
    ax.set_yticklabels(numeric_df.index)
    
    # 添加颜色条
    plt.colorbar(im)
    
    plt.title("表格数据热图")
    plt.tight_layout()
    
    # 保存或返回
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        return output_path
    else:
        # 转换为内存中的图像
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf

def encode_image_to_base64(image_buf):
    """将图像缓冲区编码为base64字符串"""
    return base64.b64encode(image_buf.getvalue()).decode('utf-8')

def plot_table_hierarchy(enhanced_tables, output_path=None):
    """绘制表格层次结构图"""
    # 创建表格结构图
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 节点位置
    positions = {}
    labels = {}
    levels = {}
    
    # 计算表格的嵌套层级和关系
    for table in enhanced_tables:
        table_id = table['table_data']['metadata']['table_id']
        parent_id = table['table_data']['metadata'].get('parent_id')
        level = table['table_data']['metadata'].get('nesting_level', 0)
        
        levels[table_id] = level
        labels[table_id] = table['table_data'].get('title', f"Table {table_id}")
    
    # 按层级排序
    max_level = max(levels.values()) if levels else 0
    level_tables = [[] for _ in range(max_level + 1)]
    
    for table_id, level in levels.items():
        level_tables[level].append(table_id)
    
    # 计算位置
    y_spacing = 1.0
    
    for level, tables in enumerate(level_tables):
        x_spacing = 1.0 / (len(tables) + 1) if tables else 0
        for i, table_id in enumerate(tables):
            x = (i + 1) * x_spacing
            y = 1.0 - (level * y_spacing / (max_level + 1))
            positions[table_id] = (x, y)
    
    # 绘制连接线
    for table in enhanced_tables:
        table_id = table['table_data']['metadata']['table_id']
        parent_id = table['table_data']['metadata'].get('parent_id')
        
        if parent_id in positions:
            x1, y1 = positions[parent_id]
            x2, y2 = positions[table_id]
            ax.plot([x1, x2], [y1, y2], 'k-', alpha=0.5)
    
    # 绘制节点
    for table_id, (x, y) in positions.items():
        level = levels.get(table_id, 0)
        colors = ['#FFC107', '#4CAF50', '#2196F3', '#9C27B0', '#F44336']
        color = colors[level % len(colors)]
        
        ax.scatter(x, y, s=300, color=color, edgecolor='black', zorder=10)
        ax.text(x, y, table_id, ha='center', va='center', color='white', 
                fontweight='bold', fontsize=8, zorder=11)
        
        # 添加标签
        label = labels.get(table_id, '')
        if len(label) > 20:
            label = label[:17] + '...'
        ax.text(x, y-0.03, label, ha='center', va='top', fontsize=9)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.title('表格层次结构')
    
    plt.tight_layout()
    
    # 保存或返回
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        return output_path
    else:
        # 转换为内存中的图像
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf
