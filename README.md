# nested-table-pdf-processor

# 嵌套表格PDF处理器

这个项目提供了一个完整的解决方案，用于处理包含复杂嵌套表格的PDF文档，支持表格检测、结构分析、语义增强和基于检索的问答。

## 功能特点

- **多层嵌套表格检测**：能够识别PDF中的嵌套表格及其层级关系
- **表格结构分析**：提取表格的行列结构、表头和数据单元格
- **语义增强**：为表格添加语义描述和关键指标提取
- **多粒度分块**：生成多种粒度的表格表示（整表、行、列、指标）
- **向量索引**：构建高效的检索索引，支持语义搜索
- **意图感知查询**：分析查询意图，智能提供针对性响应
- **上下文响应**：考虑表格间关系和文档上下文生成响应

## 安装与依赖

```bash
# 克隆仓库
git clone https://github.com/yourusername/nested-table-pdf-processor.git
cd nested-table-pdf-processor

# 安装依赖
pip install -r requirements.txt


python examples/process_pdf.py path/to/your/document.pdf output/results.json

python examples/query_examples.py output/results.json


nested-table-pdf-processor/
├── src/                # 源代码
│   ├── table_extraction/  # 表格提取相关代码
│   ├── table_processing/  # 表格处理相关代码
│   ├── vector_indexing/   # 向量索引相关代码
│   ├── querying/          # 查询处理相关代码
│   └── utils/             # 工具函数
├── examples/          # 示例脚本
├── data/              # 数据文件夹
│   └── samples/       # 示例PDF文件
└── output/            # 输出文件夹


# 导入必要模块
from src.table_extraction.detector import TableDetector
from src.table_extraction.structure import TableStructureAnalyzer
from src.table_processing.semantic_enhancer import TableSemanticEnhancer

# 检测表格
detector = TableDetector()
tables_info = detector.detect_tables("document.pdf")

# 分析表格结构
analyzer = TableStructureAnalyzer()
structured_tables = []
for table_info in tables_info:
    table_structure = analyzer.extract_table_structure("document.pdf", table_info)
    structured_tables.append(table_structure)

# 语义增强
enhancer = TableSemanticEnhancer()
enhanced_tables = []
for table in structured_tables:
    enhanced_table = enhancer.enhance_table(table)
    enhanced_tables.append(enhanced_table)


### 推荐的测试PDF文件

这里是一些可以用于测试的公开可用PDF文件链接：

1. 财务报告类：
   - [工商银行2022年年度报告](http://www.icbc-ltd.com/icbc/html/download/nianbao/2022/index.html)
   - [中国平安2022年年度报告](https://www.pingan.cn/en/investor_relations/info_dis/annual_report.shtml)

2. 统计报告类：
   - [中国统计年鉴2022](http://www.stats.gov.cn/sj/ndsj/2022/indexch.htm)

3. 科学论文类：
   - 任何包含复杂表格的生物医学、经济学或工程学领域论文

这些文档都包含复杂表格和嵌套表格，是测试系统的良好素材。

---

现在您已经有了完整的项目代码。您可以按照以下步骤在本地创建项目：

1. 创建项目目录结构
2. 复制各个文件到相应位置
3. 安装所需的依赖项
4. 下载推荐的测试PDF文件
5. 运行处理和查询脚本测试系统

完成这些步骤后，您就有了一个可以处理复杂嵌套表格PDF的完整系统，然后可以根据需要上传到您的GitHub仓库。
