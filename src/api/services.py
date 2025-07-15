"""
翻译服务模块
封装了翻译的核心业务逻辑，取代了旧的工作流。
"""
from core.document_chunker import DocumentChunker
from core.translation_engine import TranslationEngine
from utils.logger import get_logger

class TranslationService:
    """
    封装核心翻译逻辑的服务类。
    """
    def __init__(self):
        """
        初始化翻译服务，加载所需的核心组件。
        """
        self.document_chunker = DocumentChunker()
        self.translation_engine = TranslationEngine()
        self.logger = get_logger()

    def translate_document(self, content: str, target_language: str, terminology: dict = None) -> dict:
        """
        执行完整的文档翻译流程。
        1. 分块 (Chunking)
        2. 分组 (Grouping)
        3. 并行翻译 (Parallel Translation)
        4. 结果组装 (Assembling)
        
        Args:
            content (str): 需要翻译的文档内容。
            target_language (str): 目标语言。
            terminology (dict, optional): 术语词典。
            
        Returns:
            dict: 包含翻译结果和统计信息的字典。
        """
        with self.logger.step("translate_document_service", "执行完整的文档翻译"):
            # 1. 文档分块
            chunks = self.document_chunker.chunk_document(content)
            self.logger.info(f"文档被分为 {len(chunks)} 个块")

            # 2. 创建翻译组
            chunk_groups = self.document_chunker.create_chunk_groups(chunks)
            self.logger.info(f"创建了 {len(chunk_groups)} 个翻译组")

            # 3. 并行翻译
            translation_results = self.translation_engine.parallel_group_translate(
                chunk_groups=chunk_groups,
                target_language=target_language,
                terminology=terminology
            )
            self.logger.info(f"完成了 {len(translation_results)} 个块的翻译")

            # 4. 组装最终输出
            translated_parts = []
            total_input_tokens = 0
            total_output_tokens = 0

            for result in translation_results:
                if result.get('success'):
                    translated_parts.append(result['translated_content'])
                    total_input_tokens += result.get('input_tokens', 0)
                    total_output_tokens += result.get('output_tokens', 0)
                else:
                    # 如果翻译失败，保留原文并添加错误提示
                    error_info = result.get('error', '未知错误')
                    translated_parts.append(f"【翻译失败: {error_info}】\n{result['original_content']}")
            
            final_output = "\n\n".join(translated_parts)
            
            return {
                "translated_content": final_output,
                "usage": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                }
            } 