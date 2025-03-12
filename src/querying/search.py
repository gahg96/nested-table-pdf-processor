from sentence_transformers import SentenceTransformer
import numpy as np

class TableQueryProcessor:
    """处理表格相关的查询"""
    
    def __init__(self, index, embedder=None):
        self.index = index
        
        # 初始化嵌入模型
        if embedder is None:
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            self.embedder = embedder
    
    def process_query(self, query, intent, top_k=10):
        """处理查询并返回相关表格信息"""
        # 1. 查询增强 - 根据意图优化查询
        enhanced_query = self._enhance_query(query, intent)
        
        # 2. 生成查询向量
        query_vector = self.embedder.encode(enhanced_query)
        
        # 3. 检索相关内容
        raw_results = self.index.search(query_vector, top_k=top_k)
        
        # 4. 结果后处理 - 根据意图调整结果排序
        processed_results = self._post_process_results(raw_results, intent)
        
        return processed_results
    
    def _enhance_query(self, query, intent):
        """根据查询意图增强查询"""
        enhanced_parts = [query]
        
        # 根据数据类型增强
        if intent['data_type'] == 'balance_sheet':
            enhanced_parts.append("资产负债表 资产 负债 权益 balance sheet")
        elif intent['data_type'] == 'income_statement':
            enhanced_parts.append("损益表 收入 利润 盈利 income statement profit revenue")
        elif intent['data_type'] == 'cash_flow':
            enhanced_parts.append("现金流量表 现金流 经营活动 cash flow statement")
        
        # 根据粒度增强
        if intent['granularity'] == 'overview':
            enhanced_parts.append("整体 概览 总体 summary overview")
        elif intent['granularity'] == 'specific':
            enhanced_parts.append("具体 详细 明细 specific details")
        elif intent['granularity'] == 'metric':
            enhanced_parts.append("指标 比率 占比 ratio percentage")
        
        # 根据其他特征增强
        if intent['comparison']:
            enhanced_parts.append("对比 比较 差异 变化 comparison difference")
        
        if intent['calculation']:
            enhanced_parts.append("计算 总计 计算结果 calculation total")
        
        # 如果有时间焦点，添加时间信息
        if intent['time_focus']:
            if isinstance(intent['time_focus'], list):
                # 列表表示具体年份
                years_str = " ".join(intent['time_focus'])
                enhanced_parts.append(f"年份 {years_str} year")
            else:
                # 字符串表示相对时间
                enhanced_parts.append(f"时间 {intent['time_focus']} time period")
        
        # 合并增强后的查询
        enhanced_query = " ".join(enhanced_parts)
        
        return enhanced_query
    
    def _post_process_results(self, raw_results, intent):
        """根据意图对检索结果进行后处理"""
        # 构建更丰富的结果信息
        processed_results = []
        
        # 临时存储表格ID，用于去重
        seen_table_ids = set()
        
        for result in raw_results:
            # 提取结果数据
            result_data = result['data']
            table_id = result_data['metadata'].get('table_id')
            
            # 构建增强结果
            enhanced_result = {
                'score': result['score'],
                'rank': result['rank'],
                'content': result_data['content'],
                'chunk_type': result_data['chunk_type'],
                'metadata': result_data['metadata'],
                'table_idx': result_data['table_idx'],
                'relevance_explanation': self._explain_relevance(result_data, intent)
            }
            
            # 如果是表格全视图，优先级提高
            if result_data['chunk_type'] == 'table_full':
                enhanced_result['score'] *= 1.1  # 提高10%的得分
            
            # 根据查询意图调整排名
            self._adjust_by_intent(enhanced_result, intent)
            
            # 添加到结果集，避免同一表格的多次出现（但保留不同类型的块）
            if table_id not in seen_table_ids or enhanced_result['chunk_type'] != 'table_full':
                processed_results.append(enhanced_result)
                if enhanced_result['chunk_type'] == 'table_full':
                    seen_table_ids.add(table_id)
        
        # 重新排序结果
        processed_results.sort(key=lambda x: x['score'], reverse=True)
        
        # 更新排名
        for i, result in enumerate(processed_results):
            result['rank'] = i + 1
        
        return processed_results
    
    def _adjust_by_intent(self, result, intent):
        """根据意图调整结果的得分"""
        # 根据粒度调整
        if intent['granularity'] == 'overview' and result['chunk_type'] in ['table_full', 'table_description']:
            result['score'] *= 1.2  # 提高得分
        elif intent['granularity'] == 'specific' and result['chunk_type'] in ['table_row', 'table_column']:
            result['score'] *= 1.2  # 提高得分
        elif intent['granularity'] == 'metric' and result['chunk_type'] == 'table_metric':
            result['score'] *= 1.3  # 显著提高得分
        
        # 如果查询涉及计算且结果是指标，提高得分
        if intent['calculation'] and result['chunk_type'] == 'table_metric':
            result['score'] *= 1.2
        
        # 根据数据类型调整
        if intent['data_type'] != 'unknown':
            # 提取表格类型，通常保存在metadata或content中
            table_type = self._extract_table_type(result)
            if table_type and intent['data_type'] in table_type:
                result['score'] *= 1.15  # 适度提高得分
    
    def _extract_table_type(self, result):
        """从结果中提取表格类型"""
        # 尝试从metadata中获取
        if 'table_type' in result['metadata']:
            return result['metadata']['table_type']
        
        # 尝试从内容中推断
        content_lower = result['content'].lower()
        if any(term in content_lower for term in ['资产负债表', 'balance sheet', '资产', '负债']):
            return 'balance_sheet'
        elif any(term in content_lower for term in ['损益表', 'income statement', '利润', '收入']):
            return 'income_statement'
        elif any(term in content_lower for term in ['现金流量表', 'cash flow', '现金']):
            return 'cash_flow'
        
        return None
    
    def _explain_relevance(self, result_data, intent):
        """解释结果与查询的相关性"""
        content = result_data['content']
        chunk_type = result_data['chunk_type']
        
        # 基本解释模板
        explanations = []
        
        # 根据块类型提供不同解释
        if chunk_type == 'table_full':
            explanations.append("此结果显示完整表格信息")
        elif chunk_type == 'table_metric':
            explanations.append("此结果包含您可能关注的具体指标")
        elif chunk_type == 'table_row':
            explanations.append("此结果展示表格中的特定行数据")
        elif chunk_type == 'table_column':
            explanations.append("此结果展示表格中的特定列数据")
        elif chunk_type == 'table_description':
            explanations.append("此结果提供表格的整体描述")
        
        # 根据意图添加额外解释
        if intent['granularity'] == 'metric' and 'metric_name' in result_data['metadata']:
            metric_name = result_data['metadata']['metric_name']
            explanations.append(f"包含您查询的指标类型: {metric_name}")
        
        if intent['comparison'] and any(term in content.lower() for term in ['增长', '下降', '变化', '比较', '对比']):
            explanations.append("包含可用于比较分析的数据")
        
        if intent['time_focus']:
            time_info = intent['time_focus']
            if isinstance(time_info, list) and any(year in content for year in time_info):
                matched_years = [year for year in time_info if year in content]
                explanations.append(f"包含相关年份数据: {', '.join(matched_years)}")
            elif isinstance(time_info, str) and time_info in content:
                explanations.append(f"包含相关时间段: {time_info}")
        
        return "; ".join(explanations)
