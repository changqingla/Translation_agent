"""
翻译Agent配置文件
"""
import os
from typing import Dict, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置管理类"""
    
    # OpenAI API配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")  # 统一使用OPENAI_BASE_URL
    OPENAI_API_BASE = OPENAI_BASE_URL  # 保持向后兼容
    
    # 模型配置
    DEFAULT_MODEL = "Qwen3-30B-A3B"
    LLM_MODEL = DEFAULT_MODEL  # 添加LLM_MODEL别名
    MAX_TOKENS = 48000  # GPT-4 Turbo的最大token数
    
    # 分块策略配置
    # CHUNK_TOKEN_LIMIT = 500  # 固定的chunk token限制
    # TOKEN_THRESHOLD = CHUNK_TOKEN_LIMIT  # 添加TOKEN_THRESHOLD别名
    GROUP_TOKEN_RATIO = 0.35  # 分组token占模型最大上下文的比例
    CHUNK_SEPARATORS = [
        "\n# ",      # 一级标题
        "\n## ",     # 二级标题
        "\n### ",    # 三级标题
        "\n#### ",   # 四级标题
        "\n##### ",  # 五级标题
        "\n###### ", # 六级标题
        "\n\n",      # 段落分隔
        "\n",        # 行分隔
        "。",        # 中文句号
        ".",         # 英文句号
        "？",        # 中文问号
        "?",         # 英文问号
        "！",        # 中文感叹号
        "!",         # 英文感叹号
    ]
    
    # 并行翻译配置
    DEFAULT_GROUP_SIZE = 4  # 默认每组chunk数量
    PARALLEL_GROUP_SIZE = DEFAULT_GROUP_SIZE  # 添加PARALLEL_GROUP_SIZE别名
    MIN_GROUP_SIZE = 1  # 最小组大小
    MAX_PARALLEL_GROUPS = int(os.getenv("MAX_PARALLEL_GROUPS", "10"))  # 最大并行组数
    
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    
    # 文件支持格式
    SUPPORTED_FORMATS = [".md", ".txt", ".pdf", ".docx", ".html"]
    
    # 系统提示词
    SYSTEM_PROMPTS = {   
"group_translation": """You are a professional translator specializing in document translation. Your task is to translate the following content into {target_language} while maintaining the highest quality and accuracy.

## Translation Guidelines:

### 1. Names and Places
- Keep original names and places in their source language
- Add the translated version in parentheses every time they appear
- Example: "Beijing (北京)" or "Einstein (爱因斯坦)"

### 2. Mathematical Content
- All mathematical expressions and formulas MUST use English terminology
- Format all mathematical content in LaTeX syntax
- Convert mathematical operators: "和" → "and", "或" → "or", etc.
- Example: $f(x) = x^2 + 2x + 1$ (not $f(x) = x^2 + 2x + 1$)

### 3. Language Quality
- Produce natural, idiomatic {target_language} that reads fluently
- Adapt sentence structure to match {target_language} conventions
- Maintain the original tone and style
- Ensure technical accuracy while prioritizing readability

### 4. Format Preservation
- Input format: Markdown
- Output format: Maintain identical markdown structure
- Preserve all formatting elements: headers, lists, tables, code blocks, etc.
- Keep line breaks and spacing consistent

### 5. Table of Contents Handling
- Format each section heading on a separate line
- Maintain hierarchical structure regardless of heading level
- Preserve numbering systems if present

### 6. Terminology Consistency
{terminology_info}

## Important Notes:
- Focus on conveying meaning accurately rather than word-for-word translation
- Consider cultural context when appropriate
- Maintain professional tone throughout
- Double-check technical terms and concepts

Please translate the following content into {target_language}:

"""
    }

# 全局配置实例
config = Config() 