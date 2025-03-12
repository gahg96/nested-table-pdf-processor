import pdfplumber
import PyPDF2
import fitz  # PyMuPDF
import re
import os
from pathlib import Path

def extract_text_from_pdf(pdf_path, method='pdfplumber'):
    """从PDF文件中提取文本内容"""
    if method == 'pdfplumber':
        return extract_text_with_pdfplumber(pdf_path)
    elif method == 'pymupdf':
        return extract_text_with_pymupdf(pdf_path)
    elif method == 'hybrid':
        return extract_text_hybrid(pdf_path)
    else:
        raise ValueError(f"Unsupported extraction method: {method}")

def extract_text_with_pdfplumber(pdf_path):
    """使用pdfplumber提取文本"""
    text_by_page = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_by_page.append(text)
    except Exception as e:
        print(f"Error extracting text with pdfplumber: {e}")
    
    return text_by_page

def extract_text_with_pymupdf(pdf_path):
    """使用PyMuPDF提取文本"""
    text_by_page = []
    
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            text_by_page.append(text)
    except Exception as e:
        print(f"Error extracting text with PyMuPDF: {e}")
    
    return text_by_page

def extract_text_hybrid(pdf_path):
    """使用多种方法提取文本并合并结果"""
    # 首先尝试pdfplumber
    pdfplumber_results = extract_text_with_pdfplumber(pdf_path)
    
    # 然后尝试PyMuPDF
    pymupdf_results = extract_text_with_pymupdf(pdf_path)
    
    # 合并结果，选择更好的提取结果
    merged_results = []
    for i in range(min(len(pdfplumber_results), len(pymupdf_results))):
        plumber_text = pdfplumber_results[i]
        pymupdf_text = pymupdf_results[i]
        
        # 简单启发式：选择内容更多的文本
        if len(plumber_text) > len(pymupdf_text):
            merged_results.append(plumber_text)
        else:
            merged_results.append(pymupdf_text)
    
    # 处理长度不一致的情况
    if len(pdfplumber_results) > len(merged_results):
        merged_results.extend(pdfplumber_results[len(merged_results):])
    elif len(pymupdf_results) > len(merged_results):
        merged_results.extend(pymupdf_results[len(merged_results):])
    
    return merged_results

def extract_text_around_table(pdf_path, page_num, table_bbox, context_lines=3):
    """提取表格周围的文本上下文"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            page_text = page.extract_text()
            
            if not page_text:
                return {"before": "", "after": ""}
            
            # 分割成行
            lines = page_text.split('\n')
            
            # 使用表格位置在页面上估计对应的文本行
            # 这是一个粗略的估计，实际应用中可能需要更精确的方法
            x1, y1, x2, y2 = table_bbox
            
            # 根据y坐标找出表格可能对应的文本行
            page_height = page.height
            line_height = page_height / len(lines)
            
            # 估计表格开始和结束的行号
            start_line = int(y1 / line_height)
            end_line = int(y2 / line_height)
            
            # 提取表格前后的文本
            before_text = '\n'.join(lines[max(0, start_line - context_lines):start_line])
            after_text = '\n'.join(lines[end_line:min(len(lines), end_line + context_lines)])
            
            return {
                "before": before_text,
                "after": after_text
            }
    except Exception as e:
        print(f"Error extracting context around table: {e}")
        return {"before": "", "after": ""}

def get_pdf_metadata(pdf_path):
    """获取PDF文件的元数据"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            info = reader.metadata
            
            # 提取基本信息
            metadata = {
                "title": info.title if info.title else None,
                "author": info.author if info.author else None,
                "subject": info.subject if info.subject else None,
                "creator": info.creator if info.creator else None,
                "producer": info.producer if info.producer else None,
                "page_count": len(reader.pages)
            }
            
            return metadata
    except Exception as e:
        print(f"Error getting PDF metadata: {e}")
        return {
            "title": None,
            "author": None,
            "subject": None,
            "creator": None,
            "producer": None,
            "page_count": 0
        }

def is_scanned_pdf(pdf_path, sample_pages=5):
    """检测PDF是否为扫描件"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            check_pages = min(page_count, sample_pages)
            
            text_characters = 0
            for i in range(check_pages):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                text_characters += len(text)
                
                # 如果页面包含图像但几乎没有文本，可能是扫描件
                images = page.images
                if len(images) > 0 and len(text) < 100:
                    return True
            
            # 如果平均每页字符数很少，可能是扫描件
            avg_chars_per_page = text_characters / check_pages
            if avg_chars_per_page < 200:
                return True
            
            return False
    except Exception as e:
        print(f"Error detecting if PDF is scanned: {e}")
        return None

def clean_table_text(text):
    """清理表格文本"""
    if not text:
        return ""
    
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符
    text = re.sub(r'[^\w\s.,;:()%-]', '', text)
    
    return text.strip()
