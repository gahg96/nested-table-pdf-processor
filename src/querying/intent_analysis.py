import re

class QueryIntentAnalyzer:
    """分析表格相关查询的意图"""
    
    def __init__(self):
        # 财务术语关键词
        self.financial_terms = {
            'balance_sheet': ['资产负债表', '资产', '负债', '权益', 'balance sheet', 'asset', 'liability', 'equity'],
            'income_statement': ['损益表', '利润表', '收入', '支出', '盈利', '利润', 'income statement', 'profit', 'revenue', 'expense'],
            'cash_flow': ['现金流量表', '现金流', '经营活动', '投资活动', '筹资活动', 'cash flow', 'operating', 'investing', 'financing']
        }
        
        # 查询粒度关键词
        self.granularity_terms = {
            'overview': ['整体', '概览', '概述', '总体', '全部', 'overview', 'summary', 'entire'],
            'specific': ['具体', '详细', '明细', '详情', 'specific', 'detail', 'detailed'],
            'metric': ['指标', '比率', '占比', '比例', '百分比', 'ratio', 'percentage', 'proportion']
        }
        
        # 比较关键词
        self.comparison_terms = ['对比', '比较', '差异', '变化', '增长', '下降', 'compare', 'comparison', 'difference', 'growth', 'decrease']
        
        # 计算关键词
        self.calculation_terms = ['计算', '求', '多少', '总计', '总额', '总数', 'calculate', 'compute', 'sum', 'total']
        
        # 时间相关关键词
        self.time_terms = ['年', '月', '季度', '去年', '今年', '同期', 'year', 'month', 'quarter', 'last year', 'this year']
    
    def analyze_intent(self, query):
        """分析查询意图"""
        query_lower = query.lower()
        
        # 初始化意图字典
        intent = {
            'data_type': self._detect_data_type(query_lower),
            'granularity': self._detect_granularity(query_lower),
            'time_focus': self._detect_time_focus(query),
            'comparison': self._detect_comparison(query_lower),
            'calculation': self._detect_calculation(query_lower),
            'original_query': query
        }
        
        return intent
    
    def _detect_data_type(self, query_lower):
        """检测查询涉及的数据类型"""
        for data_type, terms in self.financial_terms.items():
            if any(term in query_lower for term in terms):
                return data_type
        
        return 'unknown'
    
    def _detect_granularity(self, query_lower):
        """检测查询的粒度级别"""
        for granularity, terms in self.granularity_terms.items():
            if any(term in query_lower for term in terms):
                return granularity
        
        # 如果是问"多少"类问题，通常是具体指标
        if any(term in query_lower for term in ['多少', '多大', '多么', '是什么', 'how much', 'what is']):
            return 'metric'
        
        # 默认返回"specific"
        return 'specific'
    
    def _detect_time_focus(self, query):
        """检测查询的时间焦点"""
        # 匹配年份
        year_pattern = r'(19|20)\d{2}'
        years = re.findall(year_pattern, query)
        
        if years:
            return years
        
        # 检查相对时间表达
        relative_time_terms = {
            'current': ['今年', '本年', '当前', '现在', 'current', 'this year'],
            'previous': ['去年', '上年', '上一年', 'last year', 'previous year'],
            'next': ['明年', '下一年', 'next year'],
            'recent': ['近年', '最近', '近期', 'recent', 'lately']
        }
        
        for time_type, terms in relative_time_terms.items():
            if any(term in query for term in terms):
                return time_type
        
        return None
    
    def _detect_comparison(self, query_lower):
        """检测是否需要比较"""
        # 检查比较关键词
        if any(term in query_lower for term in self.comparison_terms):
            return True
        
        # 检查比较句式
        comparison_patterns = [
            r'比.*多',
            r'比.*少',
            r'高于',
            r'低于',
            r'大于',
            r'小于',
            r'超过',
            r'不如',
            r'胜过',
            r'不及',
            r'增长',
            r'下降',
            r'rise',
            r'drop',
            r'higher than',
            r'lower than',
            r'more than',
            r'less than'
        ]
        
        for pattern in comparison_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def _detect_calculation(self, query_lower):
        """检测是否需要计算"""
        # 检查计算关键词
        if any(term in query_lower for term in self.calculation_terms):
            return True
        
        # 检查计算句式
        calculation_patterns = [
            r'百分之',
            r'占比',
            r'比例',
            r'总和',
            r'平均',
            r'增长率',
            r'下降率',
            r'平均值',
            r'总计',
            r'percentage',
            r'ratio',
            r'sum',
            r'average',
            r'growth rate',
            r'decline rate',
            r'total'
        ]
        
        for pattern in calculation_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
