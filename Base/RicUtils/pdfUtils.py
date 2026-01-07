import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# 尝试导入不同的 PDF 处理库
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """PDF 文本提取器，支持多种 PDF 处理库"""
    
    def __init__(self, preferred_library: str = "auto"):
        """
        初始化 PDF 文本提取器
        
        Args:
            preferred_library: 首选库，可选值: "auto", "pypdf2", "pdfplumber", "pymupdf"
        """
        self.preferred_library = preferred_library
        self.available_libraries = self._check_available_libraries()
        
        if not self.available_libraries:
            raise ImportError("没有可用的 PDF 处理库。请安装以下之一: PyPDF2, pdfplumber, PyMuPDF")
    
    def _check_available_libraries(self) -> List[str]:
        """检查可用的 PDF 处理库"""
        available = []
        if PYPDF2_AVAILABLE:
            available.append("pypdf2")
        if PDFPLUMBER_AVAILABLE:
            available.append("pdfplumber")
        if PYMUPDF_AVAILABLE:
            available.append("pymupdf")
        return available
    
    def _choose_library(self) -> str:
        """选择最适合的库"""
        if self.preferred_library != "auto" and self.preferred_library in self.available_libraries:
            return self.preferred_library
        
        # 优先级: PyMuPDF > pdfplumber > PyPDF2
        priority_order = ["pymupdf", "pdfplumber", "pypdf2"]
        for lib in priority_order:
            if lib in self.available_libraries:
                return lib
        
        return self.available_libraries[0]
    
    def extract_text(self, pdf_path: str, **kwargs) -> Optional[str]:
        """
        从 PDF 文件提取文本内容
        
        Args:
            pdf_path: PDF 文件路径
            **kwargs: 额外参数
                - pages: 指定页面范围，如 [1, 3, 5] 或 (1, 5)
                - preserve_layout: 是否保持布局（仅 pdfplumber 支持）
                - extract_images: 是否提取图片中的文字（仅 PyMuPDF 支持）
        
        Returns:
            提取的文本内容，失败返回 None
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF 文件不存在: {pdf_path}")
            return None
        
        library = self._choose_library()
        logger.info(f"使用 {library} 库处理 PDF: {pdf_path}")
        
        try:
            if library == "pymupdf":
                return self._extract_with_pymupdf(pdf_path, **kwargs)
            elif library == "pdfplumber":
                return self._extract_with_pdfplumber(pdf_path, **kwargs)
            elif library == "pypdf2":
                return self._extract_with_pypdf2(pdf_path, **kwargs)
        except Exception as e:
            logger.error(f"使用 {library} 提取文本失败: {e}")
            # 尝试使用其他库
            for fallback_lib in self.available_libraries:
                if fallback_lib != library:
                    try:
                        logger.info(f"尝试使用备用库 {fallback_lib}")
                        if fallback_lib == "pymupdf":
                            return self._extract_with_pymupdf(pdf_path, **kwargs)
                        elif fallback_lib == "pdfplumber":
                            return self._extract_with_pdfplumber(pdf_path, **kwargs)
                        elif fallback_lib == "pypdf2":
                            return self._extract_with_pypdf2(pdf_path, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"备用库 {fallback_lib} 也失败: {fallback_error}")
            
            return None
    
    def _extract_with_pymupdf(self, pdf_path: str, **kwargs) -> str:
        """使用 PyMuPDF 提取文本"""
        import fitz
        
        doc = fitz.open(pdf_path)
        text_parts = []
        
        pages = kwargs.get('pages')
        extract_images = kwargs.get('extract_images', False)
        
        page_range = range(len(doc))
        if pages:
            if isinstance(pages, (list, tuple)):
                page_range = [p - 1 for p in pages if 0 < p <= len(doc)]
            elif isinstance(pages, int):
                page_range = [pages - 1] if 0 < pages <= len(doc) else []
        
        for page_num in page_range:
            page = doc[page_num]
            
            # 提取文本
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- 第 {page_num + 1} 页 ---\n{text}")
            
            # 如果需要提取图片中的文字
            if extract_images:
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n - pix.alpha < 4:  # 确保不是 CMYK
                            img_text = page.get_text("words", clip=page.get_image_bbox(img))
                            if img_text:
                                text_parts.append(f"--- 图片 {img_index + 1} 文字 ---\n{img_text}")
                        pix = None
                    except Exception as e:
                        logger.warning(f"提取图片文字失败: {e}")
        
        doc.close()
        return "\n\n".join(text_parts)
    
    def _extract_with_pdfplumber(self, pdf_path: str, **kwargs) -> str:
        """使用 pdfplumber 提取文本"""
        import pdfplumber
        
        text_parts = []
        pages = kwargs.get('pages')
        preserve_layout = kwargs.get('preserve_layout', True)
        
        with pdfplumber.open(pdf_path) as pdf:
            page_range = range(len(pdf.pages))
            if pages:
                if isinstance(pages, (list, tuple)):
                    page_range = [p - 1 for p in pages if 0 < p <= len(pdf.pages)]
                elif isinstance(pages, int):
                    page_range = [pages - 1] if 0 < pages <= len(pdf.pages) else []
            
            for page_num in page_range:
                page = pdf.pages[page_num]
                
                if preserve_layout:
                    text = page.extract_text(x_tolerance=1, y_tolerance=1)
                else:
                    text = page.extract_text()
                
                if text and text.strip():
                    text_parts.append(f"--- 第 {page_num + 1} 页 ---\n{text}")
        
        return "\n\n".join(text_parts)
    
    def _extract_with_pypdf2(self, pdf_path: str, **kwargs) -> str:
        """使用 PyPDF2 提取文本"""
        import PyPDF2
        
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
        
        library = self._choose_library()
        
        try:
            if library == "pymupdf":
                return self._get_info_with_pymupdf(pdf_path)
            elif library == "pdfplumber":
                return self._get_info_with_pdfplumber(pdf_path)
            elif library == "pypdf2":
                return self._get_info_with_pypdf2(pdf_path)
        except Exception as e:
            logger.error(f"获取 PDF 信息失败: {e}")
            return None
    
    def _get_info_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """使用 PyMuPDF 获取 PDF 信息"""
        import fitz
        
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        
        info = {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(doc),
            "is_encrypted": doc.is_encrypted,
            "file_size": os.path.getsize(pdf_path)
        }
        
        doc.close()
        return info
    
    def _get_info_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """使用 pdfplumber 获取 PDF 信息"""
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata or {}
            
            info = {
                "title": metadata.get("Title", ""),
                "author": metadata.get("Author", ""),
                "subject": metadata.get("Subject", ""),
                "creator": metadata.get("Creator", ""),
                "producer": metadata.get("Producer", ""),
                "creation_date": metadata.get("CreationDate", ""),
                "modification_date": metadata.get("ModDate", ""),
                "page_count": len(pdf.pages),
                "file_size": os.path.getsize(pdf_path)
            }
            
            return info
    
    def _get_info_with_pypdf2(self, pdf_path: str) -> Dict[str, Any]:
        """使用 PyPDF2 获取 PDF 信息"""
        import PyPDF2
        
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
            - library: 指定使用的库 ("auto", "pypdf2", "pdfplumber", "pymupdf")
            - pages: 指定页面范围
            - preserve_layout: 是否保持布局
            - extract_images: 是否提取图片中的文字
    
    Returns:
        提取的文本内容，失败返回 None
    """
    try:
        library = kwargs.pop('library', 'auto')
        extractor = PDFTextExtractor(preferred_library=library)
        return extractor.extract_text(pdf_path, **kwargs)
    except Exception as e:
        logger.error(f"提取 PDF 文本失败: {e}")
        return None


def get_pdf_info(pdf_path: str, library: str = "auto") -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取 PDF 文件信息
    
    Args:
        pdf_path: PDF 文件路径
        library: 指定使用的库
    
    Returns:
        PDF 信息字典，失败返回 None
    """
    try:
        extractor = PDFTextExtractor(preferred_library=library)
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