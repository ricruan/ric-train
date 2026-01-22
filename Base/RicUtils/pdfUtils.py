import os
import logging
from typing import Optional, Dict, Any

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    PyPDF2 = None

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """PDF 文本提取器，使用 PyPDF2 库"""
    
    def __init__(self):
        """初始化 PDF 文本提取器"""
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 库不可用。请安装: pip install PyPDF2")
    
    def extract_text(self, pdf_path: str, **kwargs) -> Optional[str]:
        """
        从 PDF 文件提取文本内容
        
        Args:
            pdf_path: PDF 文件路径
            **kwargs: 额外参数
                - pages: 指定页面范围，如 [1, 3, 5] 或 (1, 5)
        
        Returns:
            提取的文本内容，失败返回 None
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF 文件不存在: {pdf_path}")
            return None
        
        logger.info(f"使用 PyPDF2 库处理 PDF: {pdf_path}")
        
        try:
            return self._extract_with_pypdf2(pdf_path, **kwargs)
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            return None
    
    def _extract_with_pypdf2(self, pdf_path: str, **kwargs) -> str:
        """使用 PyPDF2 提取文本"""
        text_parts = []
        pages = kwargs.get('pages')
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            page_range = range(len(pdf_reader.pages))
            if pages:
                if isinstance(pages, (list, tuple)):
                    page_range = [p - 1 for p in pages if 0 < p <= len(pdf_reader.pages)]
                elif isinstance(pages, int):
                    page_range = [pages - 1] if 0 < pages <= len(pdf_reader.pages) else []
            
            for page_num in page_range:
                page = pdf_reader.pages[page_num]
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(f"--- 第 {page_num + 1} 页 ---\n{text}")
                except Exception as e:
                    logger.warning(f"提取第 {page_num + 1} 页失败: {e}")
        
        return "\n\n".join(text_parts)
    
    def get_pdf_info(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """获取 PDF 文件信息"""
        if not os.path.exists(pdf_path):
            return None
        
        try:
            return self._get_info_with_pypdf2(pdf_path)
        except Exception as e:
            logger.error(f"获取 PDF 信息失败: {e}")
            return None
    
    def _get_info_with_pypdf2(self, pdf_path: str) -> Dict[str, Any]:
        """使用 PyPDF2 获取 PDF 信息"""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata or {}
            
            info = {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": metadata.get("/CreationDate", ""),
                "modification_date": metadata.get("/ModDate", ""),
                "page_count": len(pdf_reader.pages),
                "is_encrypted": pdf_reader.is_encrypted,
                "file_size": os.path.getsize(pdf_path)
            }
            
            return info


# 便捷函数
def extract_pdf_text(pdf_path: str, **kwargs) -> Optional[str]:
    """
    便捷函数：从 PDF 文件提取文本内容
    
    Args:
        pdf_path: PDF 文件路径
        **kwargs: 额外参数
            - pages: 指定页面范围
    
    Returns:
        提取的文本内容，失败返回 None
    """
    try:
        extractor = PDFTextExtractor()
        return extractor.extract_text(pdf_path, **kwargs)
    except Exception as e:
        logger.error(f"提取 PDF 文本失败: {e}")
        return None


def get_pdf_info(pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取 PDF 文件信息
    
    Args:
        pdf_path: PDF 文件路径
    
    Returns:
        PDF 信息字典，失败返回 None
    """
    try:
        extractor = PDFTextExtractor()
        return extractor.get_pdf_info(pdf_path)
    except Exception as e:
        logger.error(f"获取 PDF 信息失败: {e}")
        return None


# =============================
# 使用示例
# =============================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 示例 PDF 文件路径（请替换为实际路径）
    pdf_file = r"C:\Users\11243\Desktop\黄简历.pdf"
    
    if os.path.exists(pdf_file):
        # 提取全部文本
        print("=== 提取全部文本 ===")
        text = extract_pdf_text(pdf_file)
        if text:
            print(text[:500] + "..." if len(text) > 500 else text)
        
        # 提取指定页面
        print("\n=== 提取第1-3页 ===")
        text_pages = extract_pdf_text(pdf_file, pages=[1, 2, 3])
        if text_pages:
            print(text_pages[:300] + "..." if len(text_pages) > 300 else text_pages)
        
        # 获取 PDF 信息
        print("\n=== PDF 信息 ===")
        info = get_pdf_info(pdf_file)
        if info:
            for key, value in info.items():
                print(f"{key}: {value}")
    else:
        print(f"PDF 文件不存在: {pdf_file}")
        print("请将示例 PDF 文件放在当前目录，或修改 pdf_file 路径")
