"""
智能翻译Agent

一个基于LangChain和LangGraph的智能文档翻译系统。
"""

__version__ = "1.0.0"
__author__ = "Translation Agent Team"
__email__ = "team@translation-agent.com"
__description__ = "智能文档翻译Agent"

# 导入主要组件
from workflow.translation_workflow import TranslationWorkflow
from workflow.user_interaction import UserInteractionManager
from core.document_chunker import DocumentChunker
from core.translation_engine import TranslationEngine
from core.context_manager import ContextManager
from output.formatter import OutputFormatter
from utils.file_loader import FileLoader

__all__ = [
    "TranslationWorkflow",
    "UserInteractionManager",
    "DocumentChunker",
    "TranslationEngine",
    "ContextManager",
    "OutputFormatter",
    "FileLoader"
] 