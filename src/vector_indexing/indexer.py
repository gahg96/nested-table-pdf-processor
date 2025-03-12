import numpy as np
import os
import json
import pickle
try:
    import hnswlib
    HNSW_AVAILABLE = True
except ImportError:
    HNSW_AVAILABLE = False
    print("Warning: hnswlib not installed. Falling back to brute force search.")

class VectorIndexBuilder:
    """构建表格向量索引，支持高效检索"""
    
    def __init__(self, use_hnsw=True):
        self.use_hnsw = use_hnsw and HNSW_AVAILABLE
        self.index = None
        self.id_to_data = {}
        self.embedding_size = None
    
    def build_index(self, embeddings):
        """根据嵌入向量构建索引"""
        if not embeddings:
            print("No embeddings provided to build index")
            return None
        
        # 提取embedding向量
        vectors = [e['embedding'] for e in embeddings]
        self.embedding_size = len(vectors[0])
        
        if self.use_hnsw:
            print(f"Building HNSW index with {len(vectors)} vectors of dimension {self.embedding_size}")
            self.index = self._build_hnsw_index(vectors)
        else:
            print(f"Building brute force index with {len(vectors)} vectors")
            self.index = np.array(vectors)
        
        # 构建ID到数据的映射
        for i, embedding_data in enumerate(embeddings):
            self.id_to_data[i] = {
                'table_idx': embedding_data['table_idx'],
                'chunk_type': embedding_data['chunk_type'],
                'content': embedding_data['content'],
                'metadata': embedding_data['metadata']
            }
        
        return {
            'index': self.index,
            'id_to_data': self.id_to_data,
            'embedding_size': self.embedding_size,
            'index_type': 'hnsw' if self.use_hnsw else 'brute_force'
        }
    
    def _build_hnsw_index(self, vectors):
        """构建HNSW索引"""
        # 初始化HNSW索引
        index = hnswlib.Index(space='cosine', dim=self.embedding_size)
        
        # 设置索引参数
        index.init_index(max_elements=len(vectors), ef_construction=200, M=16)
        
        # 添加项目到索引
        index.add_items(np.array(vectors), np.arange(len(vectors)))
        
        # 优化检索参数
        index.set_ef(50)  # 较高的ef值会提高召回率但降低速度
        
        return index
    
    def search(self, query_vector, top_k=5):
        """搜索最相似的向量"""
        if self.index is None:
            print("Index not built. Call build_index first.")
            return []
        
        if self.use_hnsw:
            # HNSW搜索
            ids, distances = self.index.knn_query(query_vector, k=top_k)
            results = []
            
            for i, (idx, dist) in enumerate(zip(ids[0], distances[0])):
                results.append({
                    'id': idx,
                    'distance': dist,
                    'score': 1 - dist,  # 将距离转换为相似度得分
                    'rank': i,
                    'data': self.id_to_data[idx]
                })
        else:
            # 暴力搜索
            query_vector = np.array(query_vector)
            
            # 计算余弦相似度
            dots = np.dot(self.index, query_vector)
            norms = np.linalg.norm(self.index, axis=1) * np.linalg.norm(query_vector)
            cosine_similarities = dots / norms
            
            # 获取前k个结果
            top_indices = np.argsort(-cosine_similarities)[:top_k]
            
            results = []
            for i, idx in enumerate(top_indices):
                results.append({
                    'id': idx,
                    'distance': 1 - cosine_similarities[idx],
                    'score': cosine_similarities[idx],
                    'rank': i,
                    'data': self.id_to_data[idx]
                })
        
        return results
    
    def save_index(self, path):
        """保存索引到文件"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # 保存索引数据
        index_data = {
            'embedding_size': self.embedding_size,
            'index_type': 'hnsw' if self.use_hnsw else 'brute_force',
            'id_to_data': self.id_to_data
        }
        
        # 保存元数据
        with open(f"{path}_metadata.json", 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # 保存实际索引
        if self.use_hnsw:
            self.index.save_index(f"{path}_hnsw.bin")
        else:
            with open(f"{path}_brute.pkl", 'wb') as f:
                pickle.dump(self.index, f)
        
        print(f"Index saved to {path}")
    
    def load_index(self, path):
        """从文件加载索引"""
        # 加载元数据
        with open(f"{path}_metadata.json", 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        self.embedding_size = index_data['embedding_size']
        self.id_to_data = index_data['id_to_data']
        index_type = index_data['index_type']
        
        # 加载实际索引
        if index_type == 'hnsw' and self.use_hnsw:
            self.index = hnswlib.Index(space='cosine', dim=self.embedding_size)
            self.index.load_index(f"{path}_hnsw.bin")
        else:
            with open(f"{path}_brute.pkl", 'rb') as f:
                self.index = pickle.load(f)
            
            if index_type == 'hnsw' and not self.use_hnsw:
                print("Warning: Index was built with HNSW but hnswlib is not available. Using brute force search.")
        
        print(f"Index loaded from {path}")
        
        return {
            'index': self.index,
            'id_to_data': self.id_to_data,
            'embedding_size': self.embedding_size,
            'index_type': index_type
        }
