import pandas as pd
import re
import numpy as np

class TableSemanticEnhancer:
    """增强表格语义，添加上下文和说明"""
    
    def __init__(self):
        # 可以根据需要初始化一些参数
        self.financial_terms = [
            "资产", "负债", "权益", "收入", "成本", "利润", "现金流", "销售额",
            "资本", "股东", "税", "费用", "营业", "财务", "投资", "筹资"
        ]
    
    def enhance_table(self, table_data, surrounding_text=""):
        """增强表格语义"""
        # 基本表格信息
        df = table_data.get('dataframe')
        title = table_data.get('title', '')
        footnotes = table_data.get('footnotes', '')
        
        if df is None or df.empty:
            return None
        
        # 1. 表格类型识别
        table_type = self._classify_table_type(df, title)
        
        # 2. 表格描述生成
        description = self._generate_table_description(df, title, table_type)
        
        # 3. 提取关键指标
        key_metrics = self._extract_key_metrics(df, table_type)
        
        # 4. 结构化上下文
        context = self._extract_structured_context(surrounding_text, title)
        
        # 返回增强后的表格
        return {
            'table_data': table_data,
            'table_type': table_type,
            'description': description,
            'key_metrics': key_metrics,
            'context': context
        }
    
    def _classify_table_type(self, df, title):
        """识别表格类型"""
        title_lower = title.lower() if title else ""
        
        # 财务表检测
        if any(term in title_lower for term in ["资产负债", "balance sheet"]):
            return "financial_balance_sheet"
        elif any(term in title_lower for term in ["收益", "income", "profit", "loss", "损益"]):
            return "financial_income_statement"
        elif any(term in title_lower for term in ["现金流", "cash flow"]):
            return "financial_cash_flow"
        
        # 检查列名
        cols = [str(col).lower() for col in df.columns]
        col_text = " ".join(cols)
        
        if any(term in col_text for term in ["资产", "负债", "equity", "asset", "liability"]):
            return "financial_balance_sheet"
        elif any(term in col_text for term in ["revenue", "expense", "收入", "支出", "成本", "利润"]):
            return "financial_income_statement"
        elif any(term in col_text for term in ["cash", "flow", "现金", "流量"]):
            return "financial_cash_flow"
        
        # 检查是否是比较表
        years_pattern = r'(19|20)\d{2}'
        year_matches = re.findall(years_pattern, col_text)
        if len(year_matches) >= 2:
            return "comparison_table"
        
        # 默认为通用表格
        return "generic_table"
    
    def _generate_table_description(self, df, title, table_type):
        """为表格生成自然语言描述"""
        row_count, col_count = df.shape
        
        # 基本描述
        description = f"表格包含{row_count}行和{col_count}列数据"
        if title:
           description += f"，标题为\"{title}\""
        description += "。"
        
        # 添加列信息
        cols_str = ", ".join(str(col) for col in df.columns[:5])
        if len(df.columns) > 5:
            cols_str += f" 等{len(df.columns)}个列"
        description += f" 包含的列有：{cols_str}。"
        
        # 根据表格类型添加特定描述
        if table_type.startswith("financial_"):
            # 财务表格特定描述
            description += self._describe_financial_table(df, table_type)
        elif table_type == "comparison_table":
            # 比较表格特定描述
            description += self._describe_comparison_table(df)
        else:
            # 通用表格描述
            description += self._describe_generic_table(df)
        
        return description
    
    def _describe_financial_table(self, df, table_type):
        """描述财务表格"""
        description = ""
        
        if table_type == "financial_balance_sheet":
            # 尝试找出资产总额和负债总额
            total_assets = self._find_financial_total(df, ["资产总", "总资产", "total asset", "资产合计"])
            total_liabilities = self._find_financial_total(df, ["负债总", "总负债", "total liabilit", "负债合计"])
            equity = self._find_financial_total(df, ["权益总", "总权益", "equity", "股东权益", "所有者权益"])
            
            if total_assets:
                description += f" 资产总额为{total_assets}。"
            if total_liabilities:
                description += f" 负债总额为{total_liabilities}。"
            if equity:
                description += f" 所有者权益为{equity}。"
                
        elif table_type == "financial_income_statement":
            # 尝试找出收入和净利润
            revenue = self._find_financial_total(df, ["营业收入", "总收入", "revenue", "sales", "营业额"])
            net_income = self._find_financial_total(df, ["净利润", "利润总额", "net income", "net profit", "profit"])
            
            if revenue:
                description += f" 营业收入为{revenue}。"
            if net_income:
                description += f" 净利润为{net_income}。"
                
        elif table_type == "financial_cash_flow":
            # 尝试找出现金流量
            operating_cf = self._find_financial_total(df, ["经营活动", "operating"])
            investing_cf = self._find_financial_total(df, ["投资活动", "investing"])
            financing_cf = self._find_financial_total(df, ["筹资活动", "financing"])
            
            if operating_cf:
                description += f" 经营活动现金流量为{operating_cf}。"
            if investing_cf:
                description += f" 投资活动现金流量为{investing_cf}。"
            if financing_cf:
                description += f" 筹资活动现金流量为{financing_cf}。"
        
        return description
    
    def _find_financial_total(self, df, keywords):
        """在财务表格中查找特定指标的总额"""
        # 尝试在行索引中查找关键词
        for idx in df.index:
            idx_str = str(idx).lower()
            if any(keyword.lower() in idx_str for keyword in keywords):
                # 找到了匹配行，返回最后一列的值
                values = df.loc[idx].values
                # 过滤出数值
                numerical_values = [v for v in values if isinstance(v, (int, float)) or 
                                   (isinstance(v, str) and v.replace(',', '').replace('.', '').isdigit())]
                
                if numerical_values:
                    return str(numerical_values[-1])
        
        # 如果在行中没找到，尝试在列名中查找
        for col in df.columns:
            col_str = str(col).lower()
            if any(keyword.lower() in col_str for keyword in keywords):
                # 找到了匹配列，返回最后一行的值
                values = df[col].values
                numerical_values = [v for v in values if isinstance(v, (int, float)) or 
                                  (isinstance(v, str) and v.replace(',', '').replace('.', '').isdigit())]
                
                if numerical_values:
                    return str(numerical_values[-1])
        
        return None
    
    def _describe_comparison_table(self, df):
        """描述比较表格"""
        # 查找年份列
        years_pattern = r'(19|20)\d{2}'
        year_columns = []
        
        for col in df.columns:
            col_str = str(col)
            matches = re.findall(years_pattern, col_str)
            if matches:
                year_columns.append(col)
        
        if len(year_columns) >= 2:
            # 有多个年份列，描述年份范围
            years = [re.findall(years_pattern, str(col))[0] for col in year_columns if re.findall(years_pattern, str(col))]
            years = sorted(years)
            
            if years:
                description = f" 表格对比了从{years[0]}年到{years[-1]}年的数据。"
                
                # 尝试分析增长趋势
                try:
                    # 取第一行数据作为示例
                    row = df.iloc[0]
                    values = [float(str(row[col]).replace(',', '')) 
                             for col in year_columns if pd.notna(row[col]) and str(row[col]).replace(',', '').replace('.', '').isdigit()]
                    
                    if len(values) >= 2 and values[0] != 0:
                        growth_rate = (values[-1] - values[0]) / values[0] * 100
                        trend = "增长" if growth_rate > 0 else "下降"
                        description += f" 在此期间，第一行数据显示有{abs(growth_rate):.2f}%的{trend}。"
                except:
                    pass
                
                return description
        
        return " 此表格包含多组数据的对比。"
    
    def _describe_generic_table(self, df):
        """描述通用表格"""
        description = ""
        
        # 检查是否有数值列
        num_cols = df.select_dtypes(include=np.number).columns
        if len(num_cols) > 0:
            # 计算数值列的均值和范围
            try:
                col = num_cols[0]  # 取第一个数值列作为示例
                avg = df[col].mean()
                min_val = df[col].min()
                max_val = df[col].max()
                
                description += f" 在"{col}"列中，数值平均为{avg:.2f}，范围从{min_val}到{max_val}。"
            except:
                pass
        
        # 检查是否有分类列
        cat_cols = df.select_dtypes(include='object').columns
        if len(cat_cols) > 0:
            try:
                col = cat_cols[0]  # 取第一个分类列作为示例
                unique_vals = df[col].nunique()
                
                description += f" 在"{col}"列中，包含{unique_vals}个不同的类别。"
            except:
                pass
        
        return description
    
    def _extract_key_metrics(self, df, table_type):
        """从表格中提取关键指标"""
        metrics = []
        
        # 根据表格类型提取不同的关键指标
        if table_type == "financial_balance_sheet":
            # 资产负债表关键指标
            keywords_map = {
                "总资产": ["资产总", "总资产", "total asset", "资产合计"],
                "流动资产": ["流动资产", "current asset"],
                "非流动资产": ["非流动资产", "固定资产", "长期资产", "non-current asset"],
                "总负债": ["负债总", "总负债", "total liabilit", "负债合计"],
                "流动负债": ["流动负债", "current liabilit"],
                "非流动负债": ["非流动负债", "长期负债", "non-current liabilit"],
                "所有者权益": ["权益总", "总权益", "equity", "股东权益", "所有者权益"]
            }
        
        elif table_type == "financial_income_statement":
            # 损益表关键指标
            keywords_map = {
                "营业收入": ["营业收入", "总收入", "revenue", "sales", "营业额"],
                "营业成本": ["营业成本", "成本", "cost", "expense"],
                "毛利润": ["毛利", "毛利润", "gross profit"],
                "营业利润": ["营业利润", "operating profit"],
                "净利润": ["净利润", "利润总额", "net income", "net profit", "profit"],
                "每股收益": ["每股收益", "每股盈利", "eps", "earnings per share"]
            }
        
        elif table_type == "financial_cash_flow":
            # 现金流量表关键指标
            keywords_map = {
                "经营活动现金流量": ["经营活动", "operating"],
                "投资活动现金流量": ["投资活动", "investing"],
                "筹资活动现金流量": ["筹资活动", "financing"],
                "现金净增加额": ["现金净增加", "现金净增加额", "net increase"]
            }
        
        else:
            # 通用表格没有预定义的关键指标
            return metrics
        
        # 查找关键指标
        for metric_name, keywords in keywords_map.items():
            value = self._find_financial_total(df, keywords)
            if value:
                metrics.append({
                    "name": metric_name,
                    "value": value,
                    "keywords": keywords
                })
        
        return metrics
    
    def _extract_structured_context(self, surrounding_text, title):
        """从周围文本中提取结构化上下文"""
        context = {
            "preceding_text": "",
            "following_text": "",
            "references": []
        }
        
        if not surrounding_text:
            return context
        
        # 根据表格标题将周围文本分为前后部分
        if title and title in surrounding_text:
            parts = surrounding_text.split(title, 1)
            if len(parts) == 2:
                context["preceding_text"] = parts[0].strip()
                context["following_text"] = parts[1].strip()
        else:
            # 如果找不到标题，则假设前200个字符是前导文本，后200个字符是后续文本
            text_len = len(surrounding_text)
            if text_len <= 400:
                context["preceding_text"] = surrounding_text
            else:
                context["preceding_text"] = surrounding_text[:200].strip()
                context["following_text"] = surrounding_text[-200:].strip()
        
        # 查找对表格的引用
        reference_patterns = [
            r'表\s*\d+',  # 中文表引用
            r'[Tt]able\s*\d+',  # 英文表引用
            r'如[图表]所示',  # 中文一般引用
            r'as shown in the [table|figure]',  # 英文一般引用
        ]
        
        for pattern in reference_patterns:
            matches = re.findall(pattern, surrounding_text)
            context["references"].extend(matches)
        
        return context
