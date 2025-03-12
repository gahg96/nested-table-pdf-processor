import os
import sys
import json
import pandas as pd
from sentence_transformers import SentenceTransformer

# 添加项目根目录到路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.querying.intent_analysis import QueryIntentAnalyzer
from src.querying.search import TableQueryProcessor
from src.querying.response import ResponseGenerator
from src.vector_indexing.embeddings import TableEmbeddingGenerator
from src.vector_indexing.indexer import VectorIndexBuilder

def load_processed_results(json_path):
    """加载处理后的表格结果"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def prepare_enhanced_tables(results_json):
    """从JSON结果准备增强表格数据"""
    tables = results_json['tables']
    enhanced_tables = []
    
    for table_data in tables:
        # 转换为程序内部使用的格式
        enhanced_table = {
            'table_data': {
                'metadata': table_data['metadata'],
                'title': table_data.get('title', ''),
                'footnotes': table_data.get('footnotes', ''),
                'dataframe': pd.DataFrame() # 无法从JSON直接恢复DataFrame，先用空的代替
            },
            'table_type': table_data['type'],
            'description': table_data['description'],
            'key_metrics': table_data['key_metrics'],
            'context': table_data.get('context', {})
        }
        enhanced_tables.append(enhanced_table)
    
    return enhanced_tables

def build_vector_index(enhanced_tables):
    """构建向量索引"""
    # 生成嵌入向量
    embedder = TableEmbeddingGenerator()
    embeddings = embedder.generate_embeddings(enhanced_tables)
    
    # 构建索引
    indexer = VectorIndexBuilder()
    index = indexer.build_index(embeddings)
    
    return index, embedder

def query_tables(query, index, embedder, enhanced_tables):
    """查询表格数据"""
    # 分析查询意图
    intent_analyzer = QueryIntentAnalyzer()
    intent = intent_analyzer.analyze_intent(query)
    
    print(f"Query: {query}")
    print(f"Detected intent: {intent}")
    
    # 处理查询
    query_processor = TableQueryProcessor(index, embedder)
    results = query_processor.process_query(query, intent)
    
    # 生成响应
    response_generator = ResponseGenerator(enhanced_tables)
    response = response_generator.generate_response(results, intent)
    
    return response

def run_example_queries(results_json_path):
    """运行示例查询"""
    # 加载处理后的表格结果
    results_json = load_processed_results(results_json_path)
    
    # 准备增强表格数据
    enhanced_tables = prepare_enhanced_tables(results_json)
    
    # 构建向量索引
    print("Building vector index...")
    index, embedder = build_vector_index(enhanced_tables)
    
    # 示例查询
    example_queries = [
        "这份文档包含哪些表格?",
        "2022年的总资产是多少?",
        "流动资产占总资产的比例是多少?",
        "净利润在2021年和2022年之间有什么变化?",
        "营业收入和营业成本的关系如何?"
    ]
    
    print("\nRunning example queries...")
    for query in example_queries:
        print("\n" + "="*50)
        response = query_tables(query, index, embedder, enhanced_tables)
        print("\nResponse:")
        print(response['text'])
        print("\nSource tables:")
        for table in response['source_tables']:
            print(f" - {table['title']} (Page {table['page']})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_examples.py <results_json_path>")
        sys.exit(1)
    
    results_json_path = sys.argv[1]
    run_example_queries(results_json_path)
