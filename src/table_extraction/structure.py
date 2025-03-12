import pandas as pd
import numpy as np
import pdfplumber
import camelot

class TableStructureAnalyzer:
    """分析表格结构，处理标题、表头和数据"""
    
    def __init__(self, use_camelot=True):
        self.use_camelot = use_camelot
    
    def extract_table_structure(self, pdf_path, table_info):
        """提取表格结构，包括表头和内容"""
        page_num = table_info['page']
        bbox = table_info['bbox']
        
        if self.use_camelot:
            return self._extract_with_camelot(pdf_path, page_num, bbox)
        else:
            return self._extract_with_pdfplumber(pdf_path, page_num, bbox)
    
    def _extract_with_pdfplumber(self, pdf_path, page_num, bbox):
        """使用pdfplumber提取表格结构"""
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            
            # 裁剪区域
            x1, y1, x2, y2 = bbox
            cropped_area = page.within_bbox((x1, y1, x2, y2))
            
            # 提取表格
            table = cropped_area.extract_table()
            
            if table:
                # 转换为DataFrame
                df = pd.DataFrame(table)
                
                # 假设第一行是表头
                headers = df.iloc[0].tolist()
                df.columns = headers
                df = df.iloc[1:]
                
                # 清理数据
                df = self._clean_dataframe(df)
                
                # 提取表格标题和脚注
                title = self._extract_table_title(cropped_area)
                footnotes = self._extract_table_footnotes(cropped_area)
                
                return {
                    'dataframe': df,
                    'headers': headers,
                    'title': title,
                    'footnotes': footnotes
                }
            
            return None
    
    def _extract_with_camelot(self, pdf_path, page_num, bbox):
        """使用camelot提取表格结构"""
        # Camelot页码从1开始
        camelot_page = page_num + 1
        
        # 转换坐标格式
        x1, y1, x2, y2 = bbox
        
        # 提取表格
        tables = camelot.read_pdf(
            pdf_path, 
            pages=str(camelot_page), 
            flavor='lattice',
            table_areas=[f"{x1},{y1},{x2},{y2}"]
        )
        
        if len(tables) > 0:
            # 获取第一个匹配的表格
            table = tables[0]
            df = table.df
            
            # 假设第一行是表头
            headers = df.iloc[0].tolist()
            df.columns = headers
            df = df.iloc[1:]
            
            # 清理数据
            df = self._clean_dataframe(df)
            
            # 使用pdfplumber提取表格标题和脚注
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num]
                cropped_area = page.within_bbox((x1, y1, x2, y2))
                title = self._extract_table_title(cropped_area)
                footnotes = self._extract_table_footnotes(cropped_area)
            
            return {
                'dataframe': df,
                'headers': headers,
                'title': title,
                'footnotes': footnotes
            }
        
        return None
    
    def _clean_dataframe(self, df):
        """清理DataFrame数据"""
        # 删除完全空行
        df = df.dropna(how='all')
        
        # 替换None为NaN
        df = df.replace([None], np.nan)
        
        # 清理字符串值
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].str.strip() if hasattr(df[col], 'str') else df[col]
        
        return df
    
    def _extract_table_title(self, cropped_area):
        """尝试提取表格标题"""
        # 简单实现：假设表格上方的文本是标题
        # 在实际应用中，这需要更复杂的逻辑
        try:
            # 获取裁剪区域的文本
            text = cropped_area.extract_text()
            if text:
                # 取第一行作为标题
                lines = text.split('\n')
                return lines[0] if lines else ""
            return ""
        except:
            return ""
    
    def _extract_table_footnotes(self, cropped_area):
        """尝试提取表格脚注"""
        # 简单实现：假设表格下方的小字文本是脚注
        # 在实际应用中，这需要更复杂的逻辑
        try:
            # 获取裁剪区域的文本
            text = cropped_area.extract_text()
            if text:
                # 取最后一行作为脚注
                lines = text.split('\n')
                return lines[-1] if lines and len(lines) > 1 else ""
            return ""
        except:
            return ""
    
    def identify_multi_level_headers(self, df):
        """识别多级表头"""
        # 检查前几行是否构成多级表头
        potential_header_rows = min(3, len(df))  # 最多检查前3行
        
        # 简单启发式方法：如果前几行有很多空值或重复值，可能是多级表头
        header_candidates = []
        
        for i in range(potential_header_rows):
            row = df.iloc[i]
            empty_ratio = row.isna().mean()
            
            if empty_ratio > 0.3:  # 如果超过30%的单元格为空
                header_candidates.append(i)
        
        # 如果找到候选行，构建多级表头
        if header_candidates:
            headers = pd.MultiIndex.from_arrays([df.iloc[i] for i in header_candidates])
            clean_df = df.iloc[max(header_candidates) + 1:]
            clean_df.columns = headers
            return headers, clean_df
        
        return df.columns, df
