"""
文档分块模块
"""
from typing import List, Dict, Any
import re
from config import config
from utils.tokenizer import token_calculator
from utils.logger import get_logger

class DocumentChunker:
    """文档分块器"""
    
    def __init__(self):
        self.token_calculator = token_calculator
        self.max_chunk_tokens = config.CHUNK_TOKEN_LIMIT  # 使用固定的500 tokens
        self.logger = get_logger()
    
    def chunk_document(self, content: str) -> List[Dict[str, Any]]:
        """
        对文档进行分块
        
        Args:
            content: 文档内容
            
        Returns:
            分块列表，每个块包含 {'content': str, 'tokens': int, 'chunk_id': int}
        """
        with self.logger.step("document_chunking", "文档分块处理"):
            # 计算文档总token数
            total_tokens = self.token_calculator.count_tokens(content)
            
            self.logger.info("开始文档分块", {
                "content_length": len(content),
                "total_tokens": total_tokens,
                "max_chunk_tokens": self.max_chunk_tokens
            })
            
            # 如果文档总token数小于限制，直接返回
            if total_tokens <= self.max_chunk_tokens:
                self.logger.info("文档无需分块，直接处理", {
                    "decision": "complete_document",
                    "reason": f"总token数({total_tokens}) <= 最大限制({self.max_chunk_tokens})"
                })
                return [{
                    'content': content,
                    'tokens': total_tokens,
                    'chunk_id': 0,
                    'type': 'complete'
                }]
            
            # 需要分块处理
            self.logger.info("文档需要分块处理", {
                "decision": "chunking_required",
                "reason": f"总token数({total_tokens}) > 最大限制({self.max_chunk_tokens})"
            })
            
            chunks = []
            used_separator = None
            
            # 按照配置的分隔符层次分块
            for separator in config.CHUNK_SEPARATORS:
                if separator in content:
                    self.logger.debug("尝试使用分隔符分块", {
                        "separator": repr(separator),
                        "separator_count": content.count(separator)
                    })
                    chunks = self._split_by_separator(content, separator)
                    used_separator = separator
                    break
            
            # 如果没有找到合适的分隔符，按字符分块
            if not chunks:
                self.logger.info("未找到合适分隔符，使用长度分块", {
                    "method": "length_based_chunking"
                })
                chunks = self._split_by_length(content)
                used_separator = "length_based"
            
            self.logger.info("初步分块完成", {
                "separator_used": used_separator,
                "initial_chunks": len(chunks),
                "chunk_sizes": [len(chunk) for chunk in chunks[:5]]  # 只记录前5个的大小
            })
            
            # 为每个块添加元数据
            result_chunks = []
            for i, chunk_content in enumerate(chunks):
                chunk_tokens = self.token_calculator.count_tokens(chunk_content)
                result_chunks.append({
                    'content': chunk_content,
                    'tokens': chunk_tokens,
                    'chunk_id': i,
                    'type': 'chunk'
                })
            
            # 记录token分布
            token_distribution = [chunk['tokens'] for chunk in result_chunks]
            self.logger.info("分块token分布", {
                "chunk_count": len(result_chunks),
                "token_distribution": token_distribution,
                "max_tokens": max(token_distribution) if token_distribution else 0,
                "min_tokens": min(token_distribution) if token_distribution else 0,
                "avg_tokens": sum(token_distribution) / len(token_distribution) if token_distribution else 0
            })
            
            # 如果某个块仍然过大，继续分割
            final_chunks = []
            oversized_chunks = 0
            for chunk in result_chunks:
                if chunk['tokens'] > self.max_chunk_tokens:
                    oversized_chunks += 1
                    self.logger.debug("发现超大块，进行二次分割", {
                        "chunk_id": chunk['chunk_id'],
                        "chunk_tokens": chunk['tokens'],
                        "max_allowed": self.max_chunk_tokens
                    })
                    sub_chunks = self._split_large_chunk(chunk['content'])
                    for j, sub_chunk in enumerate(sub_chunks):
                        final_chunks.append({
                            'content': sub_chunk,
                            'tokens': self.token_calculator.count_tokens(sub_chunk),
                            'chunk_id': len(final_chunks),
                            'type': 'sub_chunk'
                        })
                else:
                    final_chunks.append(chunk)
            
            if oversized_chunks > 0:
                self.logger.info("完成二次分割", {
                    "oversized_chunks": oversized_chunks,
                    "final_chunk_count": len(final_chunks)
                })
            
            # 最终统计
            final_token_distribution = [chunk['tokens'] for chunk in final_chunks]
            self.logger.info("分块处理完成", {
                "final_chunk_count": len(final_chunks),
                "total_tokens": sum(final_token_distribution),
                "max_chunk_tokens": max(final_token_distribution) if final_token_distribution else 0,
                "processing_strategy": "chunked" if len(final_chunks) > 1 else "single"
            })
            
            return final_chunks
    
    def create_chunk_groups(self, chunks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        将chunks分组用于并行翻译
        每组最多包含4个连续chunk，但要确保不超过模型最大上下文的35%
        """
        with self.logger.step("chunk_grouping", "创建分组用于并行翻译"):
            groups = []
            current_group = []
            current_group_tokens = 0
            max_group_tokens = int(config.MAX_TOKENS * config.GROUP_TOKEN_RATIO)
            
            self.logger.info("开始分组", {
                "total_chunks": len(chunks),
                "max_group_tokens": max_group_tokens,
                "default_group_size": config.DEFAULT_GROUP_SIZE
            })
            
            for chunk in chunks:
                chunk_tokens = chunk['tokens']
                
                # 检查是否可以加入当前组
                if (len(current_group) < config.DEFAULT_GROUP_SIZE and 
                    current_group_tokens + chunk_tokens <= max_group_tokens):
                    current_group.append(chunk)
                    current_group_tokens += chunk_tokens
                else:
                    # 当前组已满或加入新chunk会超过token限制
                    if current_group:
                        groups.append(current_group)
                        self.logger.debug("完成一个分组", {
                            "group_id": len(groups) - 1,
                            "group_size": len(current_group),
                            "group_tokens": current_group_tokens
                        })
                    
                    # 开始新组
                    current_group = [chunk]
                    current_group_tokens = chunk_tokens
            
            # 添加最后一组
            if current_group:
                groups.append(current_group)
                self.logger.debug("完成最后一个分组", {
                    "group_id": len(groups) - 1,
                    "group_size": len(current_group),
                    "group_tokens": current_group_tokens
                })
            
            self.logger.info("分组完成", {
                "total_groups": len(groups),
                "group_sizes": [len(group) for group in groups],
                "group_tokens": [sum(chunk['tokens'] for chunk in group) for group in groups]
            })
            
            return groups
    
    def _split_by_separator(self, content: str, separator: str) -> List[str]:
        """按分隔符分割文档"""
        if separator.startswith('\n#'):
            # 处理标题分隔符
            parts = content.split(separator)
            chunks = []
            for i, part in enumerate(parts):
                if i == 0:
                    chunks.append(part)
                else:
                    chunks.append(separator + part)
            return [chunk.strip() for chunk in chunks if chunk.strip()]
        else:
            # 处理其他分隔符
            return [chunk.strip() for chunk in content.split(separator) if chunk.strip()]
    
    def _split_by_length(self, content: str, max_length: int = None) -> List[str]:
        """按长度分割文档"""
        if max_length is None:
            max_length = self.max_chunk_tokens * 3  # 估算字符数
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(content):
            end_pos = min(current_pos + max_length, len(content))
            chunk = content[current_pos:end_pos]
            chunks.append(chunk)
            current_pos = end_pos
        
        return chunks
    
    def _split_large_chunk(self, content: str) -> List[str]:
        """分割过大的块"""
        # 使用更细粒度的分隔符
        fine_separators = ["\n\n", "\n", "。", ".", "？", "?", "！", "!"]
        
        for separator in fine_separators:
            if separator in content:
                parts = self._split_by_separator(content, separator)
                # 检查分割后的结果
                valid_parts = []
                for part in parts:
                    if self.token_calculator.count_tokens(part) <= self.max_chunk_tokens:
                        valid_parts.append(part)
                    else:
                        # 如果还是太大，强制按token数分割
                        valid_parts.extend(self._force_split_by_tokens(part))
                
                if len(valid_parts) > 1:
                    return valid_parts
        
        # 如果都不行，强制按token数分割
        return self._force_split_by_tokens(content)
    
    def _force_split_by_tokens(self, content: str) -> List[str]:
        """强制按token数分割"""
        tokens = self.token_calculator.encoding.encode(content)
        chunks = []
        
        current_pos = 0
        while current_pos < len(tokens):
            end_pos = min(current_pos + self.max_chunk_tokens, len(tokens))
            chunk_tokens = tokens[current_pos:end_pos]
            chunk_content = self.token_calculator.encoding.decode(chunk_tokens)
            chunks.append(chunk_content)
            current_pos = end_pos
        
        return chunks
    
    def estimate_processing_time(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """估算处理时间"""
        total_tokens = sum(chunk['tokens'] for chunk in chunks)
        estimated_seconds = len(chunks) * 30  # 假设每个块需要30秒
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': total_tokens,
            'estimated_seconds': estimated_seconds,
            'estimated_minutes': estimated_seconds / 60
        } 