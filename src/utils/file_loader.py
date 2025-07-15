"""
文件加载工具
"""
import os
from typing import Optional
from pathlib import Path
import PyPDF2
import docx2txt
from markdownify import markdownify as md
from config import config

class FileLoader:
    """文件加载器"""
    
    @staticmethod
    def load_file(file_path: str) -> str:
        """加载文件内容"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix not in config.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        if suffix == ".md":
            return FileLoader._load_markdown(file_path)
        elif suffix == ".txt":
            return FileLoader._load_text(file_path)
        elif suffix == ".pdf":
            return FileLoader._load_pdf(file_path)
        elif suffix == ".docx":
            return FileLoader._load_docx(file_path)
        elif suffix == ".html":
            return FileLoader._load_html(file_path)
        else:
            raise ValueError(f"未实现的文件格式处理: {suffix}")
    
    @staticmethod
    def _load_markdown(file_path: str) -> str:
        """加载Markdown文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def _load_text(file_path: str) -> str:
        """加载文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def _load_pdf(file_path: str) -> str:
        """加载PDF文件"""
        content = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        return content
    
    @staticmethod
    def _load_docx(file_path: str) -> str:
        """加载Word文档"""
        return docx2txt.process(file_path)
    
    @staticmethod
    def _load_html(file_path: str) -> str:
        """加载HTML文件并转换为Markdown"""
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return md(html_content)
    
    @staticmethod
    def save_file(content: str, file_path: str) -> None:
        """保存文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """获取文件信息"""
        path = Path(file_path)
        return {
            "name": path.name,
            "size": path.stat().st_size,
            "suffix": path.suffix,
            "is_supported": path.suffix.lower() in config.SUPPORTED_FORMATS
        } 