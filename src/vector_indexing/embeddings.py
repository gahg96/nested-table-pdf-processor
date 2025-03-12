import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
import torch

class TableEmbeddingGenerator:
    """为表格内容生成嵌入向量"""
    
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
    def generate_embeddings(self, enhanced_tables):
        """为增强表格生成嵌入向量"""
        print(f"Generating embeddings using {self.model_name} on {self.device}")
        
        all_embeddings = []
        
        for table_idx, table in enumerate(enhanced_tables):
            table_embeddings = self._process_table(table, table_idx)
            all_embeddings.extend(table_embeddings)
            
        print(f"Generated {len(all_embeddings)} embeddings in total")
        return all_embeddings
    
    def _process_table(self, table, table_idx):
        """处理单个表格及其子块"""
        table_embeddings = []
        
        # 1. 整表表示
        table_text = self._create_table_representation(table)
        table_embedding = {
            'embedding': self.model.encode(table_text),
            'table_idx': table_idx,
            'chunk_type': 'table_full',
            'content': table_text,
            'metadata': {
                'table_id': table['table_data']['metadata']['table_id'],
                'page': table['table_data']['metadata']['page'],
                'table_type': table['table_type'],
                'nesting_level': table['table_data']['metadata']['nesting_level']
            }
        }
        table_embeddings.append(table_embedding)
        
        # 2. 表格标题
        if 'title' in table['table_data'] and table['table_data']['title']:
            title_text = f"表格标题: {table['table_data']['title']}"
            title_embedding = {
                'embedding': self.model.encode(title_text),
                'table_idx': table_idx,
                'chunk_type': 'table_title',
                'content': title_text,
                'metadata': {
                    'table_id': table['table_data']['metadata']['table_id'],
                    'page': table['table_data']['metadata']['page']
                }
            }
            table_embeddings.append(title_embedding)
        
        # 3. 关键指标
        for metric in table['key_metrics']:
            metric_text = f"{metric['name']}: {metric['value']}"
            metric_embedding = {
                'embedding': self.model.encode(metric_text),
                'table_idx': table_idx,
                'chunk_type': 'table_metric',
                'content': metric_text,
                'metadata': {
                    'table_id': table['table_data']['metadata']['table_id'],
                    'page': table['table_data']['metadata']['page'],
                    'metric_name': metric['name'],
                    'metric_value': metric['value']
                }
            }
            table_embeddings.append(metric_embedding)
        
        # 4. 行级别表示
        if 'dataframe' in table['table_data'] and not isinstance(table['table_data']['dataframe'], list):
            df = table['table_data']['dataframe']
            # 只处理前10行，避免生成太多嵌入
            max_rows = min(10, len(df))
            
            for row_idx in range(max_rows):
                row_data = df.iloc[row_idx]
                row_text = self._create_row_representation(row_data, df.columns)
                
                row_embedding = {
                    'embedding': self.model.encode(row_text),
                    'table_idx': table_idx,
                    'chunk_type': 'table_row',
                    'content': row_text,
                    'metadata': {
                        'table_id': table['table_data']['metadata']['table_id'],
                        'page': table['table_data']['metadata']['page'],
                        'row_idx': row_idx
                    }
                }
                table_embeddings.append(row_embedding)
        
        # 5. 列级别表示
        if 'dataframe' in table['table_data'] and not isinstance(table['table_data']['dataframe'], list):
            df = table['table_data']['dataframe']
            # 只处理前5列，避免生成太多嵌入
            max_cols = min(5, len(df.columns))
            
            for col_idx in range(max_cols):
                col_name = df.columns[col_idx]
                col_data = df.iloc[:, col_idx]
                col_text = self._create_column_representation(col_data, col_name)
                
                col_embedding = {
                    'embedding': self.model.encode(col_text),
                    'table_idx': table_idx,
                    'chunk_type': 'table_column',
                    'content': col_text,
                    'metadata': {
                        'table_id': table['table_data']['metadata']['table_id'],
                        'page': table['table_data']['metadata']['page'],
                        'column_name': str(col_name)
                    }
                }
                table_embeddings.append(col_embedding)
        
        # 6. 表格描述
        if 'description' in table:
            desc_text = f"表格描述: {table['description']}"
            desc_embedding = {
                'embedding': self.model.encode(desc_text),
                'table_idx': table_idx,
                'chunk_type': 'table_description',
                'content': desc_text,
                'metadata': {
                    'table_id': table['table_data']['metadata']['table_id'],
                    'page': table['table_data']['metadata']['page']
                }
            }
            table_embeddings.append(desc_embedding)
        
        return table_embeddings
    
    def _create_table_representation(self, table):
        """创建表格的文本表示"""
        parts = []
        
        # 添加标题
        if 'title' in table['table_data'] and table['table_data']['title']:
            parts.append(f"表格标题: {table['table_data']['title']}")
        
        # 添加表格类型
        parts.append(f"表格类型: {table['table_type']}")
        
        # 添加表格描述
        if 'description' in table:
            parts.append(f"表格描述: {table['description']}")
        
        # 添加关键指标
        if table['key_metrics']:
            metrics_text = ", ".join([f"{m['name']}: {m['value']}" for m in table['key_metrics']])
            parts.append(f"关键指标: {metrics_text}")
        
        # 添加数据框表示
        if 'dataframe' in table['table_data']:
            df = table['table_data']['dataframe']
            if not isinstance(df, list):  # 确保是DataFrame对象
                # 添加列名
                columns_text = ", ".join([str(col) for col in df.columns])
                parts.append(f"表格列: {columns_text}")
                
                # 添加数据预览(前3行)
                preview_rows = min(3, len(df))
                preview_text = []
                for i in range(preview_rows):
                    row = df.iloc[i]
                    row_text = ", ".join([f"{str(col)}={str(val)}" for col, val in zip(df.columns, row)])
                    preview_text.append(row_text)
                
                parts.append(f"数据预览: {'; '.join(preview_text)}")
        
        return " ".join(parts)
    
    def _create_row_representation(self, row_data, columns):
        """创建行的文本表示"""
        row_items = []
        for col, val in zip(columns, row_data):
            row_items.append(f"{str(col)}={str(val)}")
        
        return f"行数据: {', '.join(row_items)}"
    
    def _create_column_representation(self, col_data, col_name):
        """创建列的文本表示"""
        # 获取列值的统计信息
        try:
            if pd.api.types.is_numeric_dtype(col_data):
                avg = col_data.mean()
                min_val = col_data.min()
                max_val = col_data.max()
                return f"列名: {str(col_name)}, 平均值: {avg:.2f}, 最小值: {min_val}, 最大值: {max_val}"
            else:
                unique_vals = col_data.nunique()
                sample_vals = ", ".join([str(x) for x in col_data.head(3).tolist()])
                return f"列名: {str(col_name)}, 不同值数量: {unique_vals}, 示例值: {sample_vals}"
        except:
            # 出错时提供简单表示
            sample_vals = ", ".join([str(x) for x in col_data.head(3).tolist()])
            return f"列名: {str(col_name)}, 示例值: {sample_vals}"
