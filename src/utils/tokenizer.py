"""
Token计算工具
"""
import tiktoken
from typing import List, Dict, Any
from config import config

class TokenCalculator:
    """Token计算器"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.DEFAULT_MODEL
        try:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            # 如果模型不支持，使用默认编码
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        return len(self.encoding.encode(text))
    
    def count_tokens_for_messages(self, messages: List[Any]) -> int:
        """计算消息列表的token数量"""
        total_tokens = 0
        for message in messages:
            # 每个消息有固定的开销
            total_tokens += 4  # 每个消息的固定开销
            
            # 处理LangChain消息对象
            if hasattr(message, 'content'):
                # LangChain消息对象
                total_tokens += self.count_tokens(message.content)
                if hasattr(message, 'name') and message.name:
                    total_tokens += 1
            elif isinstance(message, dict):
                # 字典格式的消息
                for key, value in message.items():
                    if isinstance(value, str):
                        total_tokens += self.count_tokens(value)
                        if key == "name":  # 如果有name字段，额外增加token
                            total_tokens += 1
            else:
                # 其他格式，尝试转换为字符串
                total_tokens += self.count_tokens(str(message))
                
        total_tokens += 2  # 对话的固定开销
        return total_tokens
    
    def is_within_limit(self, text: str, ratio: float = None) -> bool:
        """检查文本是否在token限制内"""
        ratio = ratio or config.SAFE_TOKEN_RATIO
        max_tokens = int(config.MAX_TOKENS * ratio)
        return self.count_tokens(text) <= max_tokens
    
    def get_max_tokens(self, ratio: float = None) -> int:
        """获取最大token数量"""
        ratio = ratio or config.SAFE_TOKEN_RATIO
        return int(config.MAX_TOKENS * ratio)
    
    def truncate_text(self, text: str, max_tokens: int) -> str:
        """截断文本到指定的token数量"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)

# 全局token计算器实例
token_calculator = TokenCalculator() 