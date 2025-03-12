import pandas as pd
import numpy as np
import re

class ResponseGenerator:
    """生成表格查询的响应"""
    
    def __init__(self, enhanced_tables=None):
        self.enhanced_tables = enhanced_tables or []
        self.table_index = {}
        
        # 初始化表格索引，方便查找
        if enhanced_tables:
            for i, table in enumerate(enhanced_tables):
                table_id = table['table_data']['metadata']['table_id']
                self.table_index[table_id] = i
    
    def generate_response(self, query_results, intent, enhanced_tables=None):
        """根据查询结果和意图生成响应"""
        if enhanced_tables:
            self.enhanced_tables = enhanced_tables
            # 更新表格索引
            self.table_index = {}
            for i, table in enumerate(enhanced_tables):
                table_id = table['table_data']['metadata']['table_id']
                self.table_index[table_id] = i
        
        if not query_results:
            return {
                'text': "未找到与您查询相关的表格信息。请尝试使用不同的关键词或更具体的问题。",
                'source_tables': []
            }
        
        # 确定响应类型
        if intent['granularity'] == 'overview':
            return self._generate_overview_response(query_results, intent)
        elif intent['granularity'] == 'metric':
            return self._generate_metric_response(query_results, intent)
        elif intent['calculation']:
            return self._generate_calculation_response(query_results, intent)
        elif intent['comparison']:
            return self._generate_comparison_response(query_results, intent)
        else:
            return self._generate_specific_response(query_results, intent)
    
    def _generate_overview_response(self, query_results, intent):
        """生成概览类型的响应"""
        # 取得分最高的几个结果
        top_results = query_results[:3]
        relevant_tables = []
        
        response_parts = ["根据您的查询，找到以下相关表格："]
        
        for i, result in enumerate(top_results):
            table_id = result['metadata'].get('table_id')
            
            # 获取完整表格数据
            if table_id and table_id in self.table_index:
                table_idx = self.table_index[table_id]
                table_data = self.enhanced_tables[table_idx]
                
                # 表格基本信息
                table_title = table_data['table_data'].get('title', f"表格 {i+1}")
                page_number = table_data['table_data']['metadata']['page'] + 1  # 转为从1开始的页码
                
                # 表格描述
                description = table_data.get('description', '')
                
                # 添加到响应
                response_parts.append(f"\n{i+1}. {table_title} (第{page_number}页)")
                response_parts.append(f"   {description}")
                
                # 记录相关表格
                relevant_tables.append({
                    'table_id': table_id,
                    'title': table_title,
                    'page': page_number,
                    'score': result['score']
                })
        
        # 添加建议
        response_parts.append("\n您可以查询这些表格的具体指标，如：")
        
        # 从结果中找出一些指标建议
        suggested_metrics = self._extract_suggested_metrics(top_results)
        if suggested_metrics:
            for i, metric in enumerate(suggested_metrics[:3]):
                response_parts.append(f"- {metric}")
        else:
            # 默认建议
            response_parts.append("- 表格中的具体数值")
            response_parts.append("- 某一年度的特定指标")
            response_parts.append("- 不同年份之间的增长情况")
        
        return {
            'text': "\n".join(response_parts),
            'source_tables': relevant_tables
        }
    
    def _generate_metric_response(self, query_results, intent):
        """生成指标类型的响应"""
        # 优先使用指标类型的结果
        metric_results = [r for r in query_results if r['chunk_type'] == 'table_metric']
        
        if not metric_results:
            # 如果没有指标结果，使用其他相关结果
            metric_results = query_results[:3]
        
        response_parts = []
        relevant_tables = []
        
        # 提取查询中可能的指标名称
        metric_name = self._extract_metric_from_query(intent['original_query'])
        
        if metric_name:
            response_parts.append(f"关于"{metric_name}"的查询结果：")
        else:
            response_parts.append("您查询的指标信息如下：")
        
        for result in metric_results[:3]:
            table_id = result['metadata'].get('table_id')
            
            if result['chunk_type'] == 'table_metric' and 'metric_name' in result['metadata']:
                # 直接使用指标结果
                metric_name = result['metadata']['metric_name']
                metric_value = result['metadata'].get('metric_value', '未提供')
                page_number = result['metadata'].get('page', 0) + 1
                
                response_parts.append(f"\n- {metric_name}: {metric_value}")
                response_parts.append(f"  (数据来源: 第{page_number}页表格)")
                
                # 如果有表格信息，添加上下文
                if table_id and table_id in self.table_index:
                    table_idx = self.table_index[table_id]
                    table_data = self.enhanced_tables[table_idx]
                    table_title = table_data['table_data'].get('title', f"表格")
                    
                    # 记录表格
                    if not any(t['table_id'] == table_id for t in relevant_tables):
                        relevant_tables.append({
                            'table_id': table_id,
                            'title': table_title,
                            'page': page_number,
                            'score': result['score']
                        })
            else:
                # 使用普通结果
                content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                page_number = result['metadata'].get('page', 0) + 1
                
                response_parts.append(f"\n- {content_preview}")
                response_parts.append(f"  (数据来源: 第{page_number}页)")
                
                # 记录表格
                if table_id and table_id in self.table_index and not any(t['table_id'] == table_id for t in relevant_tables):
                    table_idx = self.table_index[table_id]
                    table_data = self.enhanced_tables[table_idx]
                    table_title = table_data['table_data'].get('title', f"表格")
                    
                    relevant_tables.append({
                        'table_id': table_id,
                        'title': table_title,
                        'page': page_number,
                        'score': result['score']
                    })
        
        # 添加额外上下文
        if metric_name and intent['time_focus']:
            # 如果查询涉及特定时间点的特定指标，尝试添加趋势信息
            time_info = self._format_time_info(intent['time_focus'])
            response_parts.append(f"\n该指标在{time_info}的数据如上所示。")
            
            # 尝试添加趋势信息
            trend_info = self._extract_trend_info(metric_results, metric_name)
            if trend_info:
                response_parts.append(trend_info)
        
        return {
            'text': "\n".join(response_parts),
            'source_tables': relevant_tables
        }
    
    def _generate_calculation_response(self, query_results, intent):
        """生成计算类型的响应"""
        # 提取查询中的计算需求
        calculation_type = self._extract_calculation_type(intent['original_query'])
        response_parts = []
        relevant_tables = []
        
        # 提取可能的指标和时间
        metric_name = self._extract_metric_from_query(intent['original_query']) 
        time_info = self._format_time_info(intent['time_focus']) if intent['time_focus'] else "相关时期"
        
        if calculation_type == 'percentage':
            # 百分比计算
            response_parts.append(f"关于{metric_name}在{time_info}的占比计算：")
            
            # 查找指标结果
            metric_results = [r for r in query_results if r['chunk_type'] == 'table_metric'
                             and metric_name.lower() in r['content'].lower()]
            
            if metric_results:
                # 找到直接指标
                result = metric_results[0]
                metric_value = self._extract_numeric_value(result['content'])
                page_number = result['metadata'].get('page', 0) + 1
                
                # 尝试找出总值
                total_value = self._find_related_total(result, metric_name)
                
                if metric_value and total_value:
                    percentage = (metric_value / total_value) * 100
                    response_parts.append(f"\n{metric_name}为{metric_value}，占总值{total_value}的{percentage:.2f}%。")
                    response_parts.append(f"(数据来源: 第{page_number}页表格)")
                else:
                    response_parts.append(f"\n{metric_name}为{metric_value}。")
                    response_parts.append("无法确定总值，无法计算占比。")
                    response_parts.append(f"(数据来源: 第{page_number}页表格)")
                
                # 记录表格
                table_id = result['metadata'].get('table_id')
                if table_id and table_id in self.table_index:
                    table_idx = self.table_index[table_id]
                    table_data = self.enhanced_tables[table_idx]
                    table_title = table_data['table_data'].get('title', f"表格")
                    
                    relevant_tables.append({
                        'table_id': table_id,
                        'title': table_title,
                        'page': page_number,
                        'score': result['score']
                    })
            else:
                # 未找到直接匹配的指标
                response_parts.append(f"\n未找到关于{metric_name}的直接数据，无法计算占比。")
                response_parts.append("您可以尝试查询更具体的指标名称。")
        
        elif calculation_type == 'growth':
            # 增长率计算
            response_parts.append(f"关于{metric_name}的增长率计算：")
            
            # 查找指标结果
            metric_results = [r for r in query_results if
                             (r['chunk_type'] == 'table_metric' or r['chunk_type'] == 'table_row')
                             and metric_name.lower() in r['content'].lower()]
            
            if len(metric_results) >= 2:
                # 尝试提取不同时期的值
                values_by_time = self._extract_values_by_time(metric_results, metric_name)
                
                if len(values_by_time) >= 2:
                    # 计算增长率
                    times = sorted(values_by_time.keys())
                    earliest_time = times[0]
                    latest_time = times[-1]
                    
                    earlier_value = values_by_time[earliest_time]
                    later_value = values_by_time[latest_time]
                    
                    if earlier_value != 0:
                        growth_rate = ((later_value - earlier_value) / earlier_value) * 100
                        growth_direction = "增长" if growth_rate >= 0 else "下降"
                        
                        response_parts.append(f"\n{metric_name}从{earliest_time}的{earlier_value}到{latest_time}的{later_value}，")
                        response_parts.append(f"总计{growth_direction}了{abs(growth_rate):.2f}%。")
                    else:
                        response_parts.append(f"\n{metric_name}从{earliest_time}的{earlier_value}到{latest_time}的{later_value}。")
                        response_parts.append("由于初始值为0，无法计算增长率。")
                else:
                    response_parts.append(f"\n找到了关于{metric_name}的数据，但无法获取不同时期的值，无法计算增长率。")
            else:
                response_parts.append(f"\n未找到足够的{metric_name}时间序列数据，无法计算增长率。")
        
        elif calculation_type == 'sum':
            # 求和计算
            response_parts.append(f"关于{metric_name}的求和计算：")
            
            # TODO: 实现求和计算逻辑
            response_parts.append(f"\n此类计算需要提取表格中的具体数据并进行求和。")
            response_parts.append("当前无法执行精确计算，请查看原始表格数据。")
        
        else:
            # 其他通用计算
            response_parts.append("您的计算查询需要更精确的表格数据分析：")
            response_parts.append("\n以下是与您查询相关的信息：")
            
            for result in query_results[:3]:
                content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                page_number = result['metadata'].get('page', 0) + 1
                
                response_parts.append(f"\n- {content_preview}")
                response_parts.append(f"  (数据来源: 第{page_number}页表格)")
                
                # 记录表格
                table_id = result['metadata'].get('table_id')
                if table_id and table_id in self.table_index and not any(t['table_id'] == table_id for t in relevant_tables):
                    table_idx = self.table_index[table_id]
                    table_data = self.enhanced_tables[table_idx]
                    table_title = table_data['table_data'].get('title', f"表格")
                    
                    relevant_tables.append({
                        'table_id': table_id,
                        'title': table_title,
                        'page': page_number,
                        'score': result['score']
                    })
        
        return {
            'text': "\n".join(response_parts),
            'source_tables': relevant_tables
        }
    
    def _generate_comparison_response(self, query_results, intent):
        """生成比较类型的响应"""
        # 提取查询中的比较元素
        response_parts = []
        relevant_tables = []
        
        metric_name = self._extract_metric_from_query(intent['original_query'])
        comparison_entities = self._extract_comparison_entities(intent['original_query'])
        
        if metric_name and comparison_entities and len(comparison_entities) >= 2:
            # 有明确的比较需求
            entity1, entity2 = comparison_entities[:2]
            response_parts.append(f"关于{metric_name}在{entity1}和{entity2}之间的比较：")
            
            # 查找包含这两个实体的结果
            relevant_results = [r for r in query_results if 
                              all(entity.lower() in r['content'].lower() for entity in comparison_entities)]
            
            if relevant_results:
                # 从结果中提取比较值
                comparison_data = self._extract_comparison_values(relevant_results[0], entity1, entity2, metric_name)
                
                if comparison_data:
                    value1, value2 = comparison_data
                    diff = value2 - value1
                    diff_percent = (diff / value1) * 100 if value1 != 0 else float('inf')
                    
                    response_parts.append(f"\n{entity1}的{metric_name}为{value1}，")
                    response_parts.append(f"{entity2}的{metric_name}为{value2}。")
                    
                    if diff > 0:
                        response_parts.append(f"\n{entity2}比{entity1}高{diff:.2f}，增幅为{diff_percent:.2f}%。")
                    elif diff < 0:
                        response_parts.append(f"\n{entity2}比{entity1}低{abs(diff):.2f}，降幅为{abs(diff_percent):.2f}%。")
                    else:
                        response_parts.append(f"\n两者{metric_name}相同。")
                else:
                    # 无法提取具体的比较值
                    result = relevant_results[0]
                    content_preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
                    response_parts.append(f"\n找到与比较相关的信息，但无法提取精确的比较值。以下是相关内容：")
                    response_parts.append(f"\n{content_preview}")
                
                # 记录表格信息
                for result in relevant_results[:2]:
                    table_id = result['metadata'].get('table_id')
                    page_number = result['metadata'].get('page', 0) + 1
                    
                    if table_id and table_id in self.table_index and not any(t['table_id'] == table_id for t in relevant_tables):
                        table_idx = self.table_index[table_id]
                        table_data = self.enhanced_tables[table_idx]
                        table_title = table_data['table_data'].get('title', f"表格")
                        
                        relevant_tables.append({
                            'table_id': table_id,
                            'title': table_title,
                            'page': page_number,
                            'score': result['score']
                        })
            else:
                # 找不到同时包含两个实体的结果
                response_parts.append(f"\n无法找到同时包含{entity1}和{entity2}的{metric_name}数据，无法进行直接比较。")
                
                # 尝试分别查找每个实体
                for entity in comparison_entities:
                    entity_results = [r for r in query_results if entity.lower() in r['content'].lower()]
                    if entity_results:
                        result = entity_results[0]
                        content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                        response_parts.append(f"\n关于{entity}的信息：{content_preview}")
                        
                        # 记录表格
                        table_id = result['metadata'].get('table_id')
                        page_number = result['metadata'].get('page', 0) + 1
                        
                        if table_id and table_id in self.table_index and not any(t['table_id'] == table_id for t in relevant_tables):
                            table_idx = self.table_index[table_id]
                            table_data = self.enhanced_tables[table_idx]
                            table_title = table_data['table_data'].get('title', f"表格")
                            
                            relevant_tables.append({
                                'table_id': table_id,
                                'title': table_title,
                                'page': page_number,
                                'score': result['score']
                            })
        else:
            # 没有明确的比较元素，可能是时间比较
            if intent['time_focus'] and isinstance(intent['time_focus'], list) and len(intent['time_focus']) >= 2:
                # 有多个时间点，可能是时间比较
                times = intent['time_focus']
                response_parts.append(f"关于{metric_name or '相关指标'}在{times[0]}和{times[1]}之间的比较：")
                
                # 查找时间相关结果
                time_results = [r for r in query_results if 
                              all(time in r['content'] for time in times[:2])]
                
                if time_results:
                    result = time_results[0]
                    content_preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
                    response_parts.append(f"\n{content_preview}")
                    
                    # 记录表格
                    table_id = result['metadata'].get('table_id')
                    page_number = result['metadata'].get('page', 0) + 1
                    
                    if table_id and table_id in self.table_index:
                        table_idx = self.table_index[table_id]
                        table_data = self.enhanced_tables[table_idx]
                        table_title = table_data['table_data'].get('title', f"表格")
                        
                        relevant_tables.append({
                            'table_id': table_id,
                            'title': table_title,
                            'page': page_number,
                            'score': result['score']
                        })
                else:
                    response_parts.append(f"\n未找到同时包含{times[0]}和{times[1]}的比较数据。")
            else:
                # 通用比较响应
                response_parts.append("您的比较查询需要更明确的比较对象：")
                
                # 使用前几个最相关的结果
                for result in query_results[:3]:
                    content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                    page_number = result['metadata'].get('page', 0) + 1
                    
                    response_parts.append(f"\n- {content_preview}")
                    response_parts.append(f"  (数据来源: 第{page_number}页表格)")
                    
                    # 记录表格
                    table_id = result['metadata'].get('table_id')
                    if table_id and table_id in self.table_index and not any(t['table_id'] == table_id for t in relevant_tables):
                        table_idx = self.table_index[table_id]
                        table_data = self.enhanced_tables[table_idx]
                        table_title = table_data['table_data'].get('title', f"表格")
                        
                        relevant_tables.append({
                            'table_id': table_id,
                            'title': table_title,
                            'page': page_number,
                            'score': result['score']
                        })
        
        return {
            'text': "\n".join(response_parts),
            'source_tables': relevant_tables
        }
    
    def _generate_specific_response(self, query_results, intent):
        """生成特定查询的响应"""
        response_parts = ["关于您查询的具体信息："]
        relevant_tables = []
        
        # 使用前几个最相关的结果
        for i, result in enumerate(query_results[:3]):
            content = result['content']
            page_number = result['metadata'].get('page', 0) + 1
            
            # 针对不同类型的块提供不同格式的响应
            if result['chunk_type'] == 'table_full':
                response_parts.append(f"\n{i+1}. 找到相关表格 (第{page_number}页)：")
                # 显示表格摘要而不是全部内容
                preview = content[:150] + "..." if len(content) > 150 else content
                response_parts.append(f"   {preview}")
            elif result['chunk_type'] == 'table_metric':
                response_parts.append(f"\n{i+1}. 找到相关指标 (第{page_number}页)：")
                response_parts.append(f"   {content}")
            elif result['chunk_type'] in ['table_row', 'table_column']:
                response_parts.append(f"\n{i+1}. 找到相关数据 (第{page_number}页)：")
                response_parts.append(f"   {content}")
            else:
                response_parts.append(f"\n{i+1}. 相关信息 (第{page_number}页)：")
                preview = content[:150] + "..." if len(content) > 150 else content
                response_parts.append(f"   {preview}")
            
            # 添加相关表格信息
            table_id = result['metadata'].get('table_id')
            if table_id and table_id in self.table_index and not any(t['table_id'] == table_id for t in relevant_tables):
                table_idx = self.table_index[table_id]
                table_data = self.enhanced_tables[table_idx]
                table_title = table_data['table_data'].get('title', f"表格")
                
                relevant_tables.append({
                    'table_id': table_id,
                    'title': table_title,
                    'page': page_number,
                    'score': result['score']
                })
        
        # 添加一些上下文信息
        if intent['time_focus']:
            time_info = self._format_time_info(intent['time_focus'])
            response_parts.append(f"\n以上数据涉及{time_info}的信息。")
        
        response_parts.append("\n您可以查看相关表格以获取更详细的信息。")
        
        return {
            'text': "\n".join(response_parts),
            'source_tables': relevant_tables
        }
    
    # 辅助方法
    def _extract_suggested_metrics(self, results):
        """从结果中提取可能的指标建议"""
        metrics = []
        
        for result in results:
            if result['chunk_type'] == 'table_metric' and 'metric_name' in result['metadata']:
                metrics.append(result['metadata']['metric_name'])
            elif 'key_metrics' in result:
                # 从表格元数据中提取
                for metric in result.get('key_metrics', []):
                    metrics.append(metric['name'])
        
        # 去重
        return list(set(metrics))
    
    def _extract_metric_from_query(self, query):
        """从查询中提取可能的指标名称"""
        # 常见财务指标
        common_metrics = [
            '资产', '负债', '权益', '收入', '利润', '成本', '费用', '现金流',
            '流动资产', '非流动资产', '流动负债', '非流动负债', '营业收入',
            '净利润', '毛利率', '营业利润', '税前利润', '每股收益',
            'assets', 'liabilities', 'equity', 'revenue', 'profit', 'cost',
            'expense', 'cash flow', 'current assets', 'current liabilities'
        ]
        
        # 检查常见指标
        for metric in common_metrics:
            if metric in query:
                return metric
        
        # 使用模式匹配查找可能的指标名称
        patterns = [
            r'([\w\s]+)是多少',
            r'([\w\s]+)有多少',
            r'([\w\s]+)的(比例|占比|数值|值)',
            r'多少([\w\s]+)',
            r'what is the ([\w\s]+)',
            r'how much ([\w\s]+)'
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, query)
            if matches:
                return matches.group(1).strip()
        
        return None
    
    def _extract_calculation_type(self, query):
        """提取查询中的计算类型"""
        query_lower = query.lower()
        
        # 百分比/占比计算
        if any(term in query_lower for term in ['占比', '比例', '百分比', 'percentage', 'ratio', 'proportion']):
            return 'percentage'
        
        # 增长率计算
        if any(term in query_lower for term in ['增长率', '增长了多少', '下降了多少', '变化率', 'growth rate', 'increase rate']):
            return 'growth'
        
        # 总和计算
        if any(term in query_lower for term in ['总和', '总计', '合计', 'sum', 'total']):
            return 'sum'
        
        # 平均值计算
        if any(term in query_lower for term in ['平均', '平均值', 'average', 'mean']):
            return 'average'
        
        # 默认为通用计算
        return 'general'
    
    def _extract_comparison_entities(self, query):
        """提取查询中的比较实体"""
        # 匹配"A和B"、"A与B"等模式
        patterns = [
            r'([\w\s]+)和([\w\s]+)之?间?的?',
            r'([\w\s]+)与([\w\s]+)之?间?的?',
            r'([\w\s]+)相比([\w\s]+)',
            r'compare ([\w\s]+) and ([\w\s]+)',
            r'([\w\s]+) compared to ([\w\s]+)'
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, query)
            if matches:
                entity1 = matches.group(1).strip()
                entity2 = matches.group(2).strip()
                return [entity1, entity2]
        
        # 检查是否是年份比较
        years_pattern = r'(19|20)\d{2}'
        years = re.findall(years_pattern, query)
        if len(years) >= 2:
            return years
        
        return []
    
    def _format_time_info(self, time_info):
        """格式化时间信息"""
        if isinstance(time_info, list):
            if len(time_info) == 1:
                return f"{time_info[0]}年"
            else:
                return f"{time_info[0]}年到{time_info[-1]}年"
        elif time_info == 'current':
            return "当前年度"
        elif time_info == 'previous':
            return "上一年度"
        elif time_info == 'next':
            return "下一年度"
        elif time_info == 'recent':
            return "近期"
        else:
            return str(time_info)
    
    def _extract_numeric_value(self, text):
        """从文本中提取数值"""
        # 匹配数字，包括千分位分隔符和小数点
        matches = re.findall(r'[-+]?[\d,]+\.?\d*', text)
        if matches:
            # 取第一个匹配，移除千分位分隔符
            value_str = matches[0].replace(',', '')
            try:
                return float(value_str)
            except:
                return None
        return None
    
    def _find_related_total(self, result, metric_name):
        """查找与指标相关的总值"""
        # 尝试从相同表格中查找总值或总计
        table_id = result['metadata'].get('table_id')
        
        if table_id and table_id in self.table_index:
            table_idx = self.table_index[table_id]
            table_data = self.enhanced_tables[table_idx]
            
            # 检查关键指标中是否有"总计"相关的指标
            for metric in table_data.get('key_metrics', []):
                if any(term in metric['name'].lower() for term in ['总', '合计', '总计', '总额', 'total']):
                    value_str = metric['value'].replace(',', '')
                    try:
                        return float(value_str)
                    except:
                        pass
        
        # 如果找不到，返回None
        return None
    
    def _extract_values_by_time(self, results, metric_name):
        """从结果中提取不同时间点的值"""
        values_by_time = {}
        
        for result in results:
            content = result['content']
            
            # 提取年份
            year_pattern = r'(19|20)\d{2}'
            years = re.findall(year_pattern, content)
            
            # 提取数值
            numeric_value = self._extract_numeric_value(content)
            
            if years and numeric_value is not None:
                # 假设最接近指标名称的年份是与该值相关的年份
                year = years[0]
                values_by_time[year] = numeric_value
        
        return values_by_time
    
    def _extract_trend_info(self, results, metric_name):
        """提取指标的趋势信息"""
        values_by_time = self._extract_values_by_time(results, metric_name)
        
        if len(values_by_time) >= 2:
            times = sorted(values_by_time.keys())
            values = [values_by_time[time] for time in times]
            
            # 计算变化趋势
            if values[0] != 0:
                overall_change = ((values[-1] - values[0]) / values[0]) * 100
                
                if overall_change > 0:
                    return f"\n从{times[0]}年到{times[-1]}年，该指标总体呈上升趋势，增长了{overall_change:.2f}%。"
                elif overall_change < 0:
                    return f"\n从{times[0]}年到{times[-1]}年，该指标总体呈下降趋势，下降了{abs(overall_change):.2f}%。"
                else:
                    return f"\n从{times[0]}年到{times[-1]}年，该指标保持稳定，没有明显变化。"
            
            # 如果初始值为0，只描述方向
            else:
                if values[-1] > 0:
                    return f"\n从{times[0]}年到{times[-1]}年，该指标从0增长至{values[-1]}。"
                else:
                    return f"\n从{times[0]}年到{times[-1]}年，该指标保持在0。"
        
        return None
    
    def _extract_comparison_values(self, result, entity1, entity2, metric_name):
        """从结果中提取用于比较的数值"""
        content = result['content']
        
        # 尝试找到包含实体1和指标的部分
        entity1_pattern = f"{entity1}.*?{metric_name}.*?([-+]?[\d,]+\.?\d*)"
        entity1_matches = re.search(entity1_pattern, content, re.IGNORECASE)
        
        # 尝试找到包含实体2和指标的部分
        entity2_pattern = f"{entity2}.*?{metric_name}.*?([-+]?[\d,]+\.?\d*)"
        entity2_matches = re.search(entity2_pattern, content, re.IGNORECASE)
        
        # 如果找到了两个值，返回它们
        if entity1_matches and entity2_matches:
            value1_str = entity1_matches.group(1).replace(',', '')
            value2_str = entity2_matches.group(1).replace(',', '')
            
            try:
                value1 = float(value1_str)
                value2 = float(value2_str)
                return (value1, value2)
            except:
                pass
        
        # 如果上面的方法失败，尝试更宽松的匹配
        all_numbers = re.findall(r'[-+]?[\d,]+\.?\d*', content)
        if len(all_numbers) >= 2:
            # 假设数字的顺序与实体的顺序相关
            try:
                value1 = float(all_numbers[0].replace(',', ''))
                value2 = float(all_numbers[1].replace(',', ''))
                return (value1, value2)
            except:
                pass
        
        return None
