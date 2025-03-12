import cv2
import numpy as np
from pdf2image import convert_from_path
import pdfplumber
import json

class TableDetector:
    """检测PDF中的表格，包括嵌套表格"""
    
    def __init__(self, detection_method="rule_based"):
        self.detection_method = detection_method
        # 如果有GPU且安装了table-transformer，也可以使用深度学习模型
        self.use_deep_learning = False
        try:
            from transformers import TableTransformerForObjectDetection
            import torch
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")
            self.model.to(self.device)
            self.use_deep_learning = True
        except:
            print("Table Transformer not available, using rule-based detection")
    
    def detect_tables(self, pdf_path):
        """检测PDF中所有表格，包括位置信息"""
        tables_info = []
        
        if self.use_deep_learning:
            # 使用深度学习方法
            tables_info = self._detect_with_transformer(pdf_path)
        else:
            # 使用基于规则的方法
            tables_info = self._detect_with_pdfplumber(pdf_path)
        
        # 检测嵌套关系
        self._detect_nested_relationships(tables_info)
        
        return tables_info
    
    def _detect_with_pdfplumber(self, pdf_path):
        """使用pdfplumber检测表格"""
        tables_info = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # 检测表格
                tables = page.find_tables()
                
                for i, table in enumerate(tables):
                    bbox = (table.bbox[0], table.bbox[1], table.bbox[2], table.bbox[3])
                    tables_info.append({
                        'page': page_num,
                        'bbox': bbox,
                        'table_id': f"page_{page_num}_table_{i}",
                        'parent_id': None,
                        'nesting_level': 0
                    })
        
        return tables_info
    
    def _detect_with_transformer(self, pdf_path):
        """使用Table Transformer检测表格"""
        from transformers import TableTransformerForObjectDetection
        import torch
        from torchvision.ops import box_convert
        
        tables_info = []
        
        # 将PDF转换为图像
        images = convert_from_path(pdf_path, dpi=300)
        
        for page_num, img in enumerate(images):
            # 预处理图像
            img_tensor = self._preprocess_image(img)
            
            # 检测表格
            with torch.no_grad():
                outputs = self.model(img_tensor.to(self.device))
            
            # 处理检测结果
            tables = self._process_detection_output(outputs, threshold=0.7, page_num=page_num)
            tables_info.extend(tables)
        
        return tables_info
    
    def _preprocess_image(self, pil_img):
        """预处理图像以适配模型输入"""
        import torch
        from torchvision import transforms
        
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        img_tensor = transform(pil_img).unsqueeze(0)
        return img_tensor
    
    def _process_detection_output(self, outputs, threshold=0.7, page_num=0):
        """处理模型输出，提取表格位置"""
        import torch
        from torchvision.ops import box_convert
        
        tables = []
        
        # 获取预测结果
        probas = outputs.logits.softmax(-1)[0, :, 1].cpu()
        keep = probas > threshold
        
        # 过滤低置信度的预测
        bboxes_scaled = box_convert(outputs.pred_boxes[0, keep].cpu(), 'cxcywh', 'xyxy')
        
        for i, (bbox, score) in enumerate(zip(bboxes_scaled, probas[keep])):
            x1, y1, x2, y2 = bbox.tolist()
            tables.append({
                'page': page_num,
                'bbox': (x1, y1, x2, y2),
                'table_id': f"page_{page_num}_table_{i}",
                'parent_id': None,
                'nesting_level': 0,
                'confidence': score.item()
            })
        
        return tables
    
    def _detect_nested_relationships(self, tables_info):
        """检测表格之间的嵌套关系"""
        # 按页面分组处理表格
        tables_by_page = {}
        for table in tables_info:
            page = table['page']
            if page not in tables_by_page:
                tables_by_page[page] = []
            tables_by_page[page].append(table)
        
        # 处理每个页面的表格
        for page, page_tables in tables_by_page.items():
            # 按面积从大到小排序
            page_tables.sort(key=lambda x: self._calculate_area(x['bbox']), reverse=True)
            
            # 检测嵌套关系
            for i, outer in enumerate(page_tables):
                for j, inner in enumerate(page_tables):
                    if i != j:
                        # 检查inner是否包含在outer内部
                        if self._is_contained(inner['bbox'], outer['bbox']):
                            inner['parent_id'] = outer['table_id']
        
        # 计算嵌套层级
        self._calculate_nesting_levels(tables_info)
    
    def _is_contained(self, inner_bbox, outer_bbox, threshold=0.85):
        """检查一个边界框是否包含在另一个内部"""
        ix1, iy1, ix2, iy2 = inner_bbox
        ox1, oy1, ox2, oy2 = outer_bbox
        
        # 计算交集
        intersection_x1 = max(ix1, ox1)
        intersection_y1 = max(iy1, oy1)
        intersection_x2 = min(ix2, ox2)
        intersection_y2 = min(iy2, oy2)
        
        if intersection_x1 >= intersection_x2 or intersection_y1 >= intersection_y2:
            return False
        
        intersection_area = (intersection_x2 - intersection_x1) * (intersection_y2 - intersection_y1)
        inner_area = (ix2 - ix1) * (iy2 - iy1)
        
        # 如果交集占inner的面积比例超过阈值，认为是嵌套
        contained_ratio = intersection_area / inner_area
        
        # 面积比检查，防止误判
        area_ratio = inner_area / self._calculate_area(outer_bbox)
        
        return contained_ratio > threshold and area_ratio < 0.9
    
    def _calculate_area(self, bbox):
        """计算边界框面积"""
        x1, y1, x2, y2 = bbox
        return (x2 - x1) * (y2 - y1)
    
    def _calculate_nesting_levels(self, tables_info):
        """计算每个表格的嵌套层级"""
        # 创建表格ID到索引的映射
        table_id_to_index = {table['table_id']: i for i, table in enumerate(tables_info)}
        
        # 初始化所有表格的嵌套层级为0
        for table in tables_info:
            table['nesting_level'] = 0
        
        # 迭代计算嵌套层级
        changed = True
        while changed:
            changed = False
            for table in tables_info:
                if table['parent_id'] is not None:
                    parent_idx = table_id_to_index[table['parent_id']]
                    parent = tables_info[parent_idx]
                    if table['nesting_level'] <= parent['nesting_level']:
                        table['nesting_level'] = parent['nesting_level'] + 1
                        changed = True
