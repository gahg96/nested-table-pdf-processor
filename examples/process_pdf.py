import os
import sys
import pandas as pd
import json

# 添加项目根目录到路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.table_extraction.detector import TableDetector
from src.table_extraction.structure import TableStructureAnalyzer
from src.table_processing.semantic_enhancer import TableSemanticEnhancer
from src.vector_indexing.embeddings import TableEmbeddingGenerator
from src.vector_indexing.indexer import VectorIndexBuilder
from src.utils.pdf_utils import extract_text_from_pdf

def process_pdf(pdf_path, output_path=None):
    """处理包含嵌套表格的PDF文件"""
    print(f"Processing PDF: {pdf_path}")
    
    # 1. 提取表格
    print("Step 1: Detecting tables...")
    detector = TableDetector()
    tables_info = detector.detect_tables(pdf_path)
    print(f"Detected {len(tables_info)} tables (including nested tables)")
    
    # 2. 分析表格结构
    print("Step 2: Analyzing table structures...")
    analyzer = TableStructureAnalyzer()
    structured_tables = []
    
    for table_info in tables_info:
        print(f"  Processing table {table_info['table_id']} (nesting level: {table_info['nesting_level']})")
        table_structure = analyzer.extract_table_structure(pdf_path, table_info)
        
        if table_structure:
            # 添加原始表格信息
            table_structure['metadata'] = table_info
            structured_tables.append(table_structure)
    
    print(f"Successfully structured {len(structured_tables)} tables")
    
    # 3. 提取PDF文本（用于上下文）
    print("Step 3: Extracting PDF text...")
    pdf_text = extract_text_from_pdf(pdf_path)
    
    # 4. 增强表格语义
    print("Step 4: Enhancing table semantics...")
    enhancer = TableSemanticEnhancer()
    enhanced_tables = []
    
    for table in structured_tables:
        # 获取表格所在页面的文本
        page_num = table['metadata']['page']
        page_text = pdf_text[page_num] if page_num < len(pdf_text) else ""
        
        # 增强表格
        enhanced_table = enhancer.enhance_table(table, page_text)
        if enhanced_table:
            enhanced_tables.append(enhanced_table)
    
    print(f"Enhanced {len(enhanced_tables)} tables with semantic information")
    
    # 5. 保存结果
    if output_path:
        print(f"Step 5: Saving results to {output_path}")
        save_results(enhanced_tables, output_path)
    
    return enhanced_tables

def save_results(enhanced_tables, output_path):
    """保存处理结果"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 创建结果字典
    results = {
        "tables_count": len(enhanced_tables),
        "tables": []
    }
    
    for i, table in enumerate(enhanced_tables):
        # 将DataFrame转换为可序列化格式
        if 'dataframe' in table['table_data']:
            table['table_data']['dataframe'] = table['table_data']['dataframe'].to_dict(orient='records')
        
        results["tables"].append({
            "id": i,
            "metadata": table['table_data']['metadata'],
            "type": table['table_type'],
            "description": table['description'],
            "key_metrics": table['key_metrics'],
            "title": table['table_data'].get('title', ''),
            "footnotes": table['table_data'].get('footnotes', ''),
            "context": table['context']
        })
    
    # 保存为JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_pdf.py <pdf_path> [output_path]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"
    
    process_pdf(pdf_path, output_path)
