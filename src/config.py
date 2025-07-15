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
    CHUNK_TOKEN_LIMIT = 500  # 固定的chunk token限制
    TOKEN_THRESHOLD = CHUNK_TOKEN_LIMIT  # 添加TOKEN_THRESHOLD别名
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
        "translation": """
You are an expert translator, you need to translate the following paragraph into {target_language}.
 Please pay attention to the
following rules:
1. Maintain the original writing of names and places in the original article, and add the translated name and place in
parentheses;
2. The language in mathematical formulas **must** be english, e.g., "和" is translated to "and", mathematical formulas
should be written in **LaTex**;
3. Ensure that the translation is "as natural as possible" in {target_language};
4. The input format is **markdown**, and the output format is not changed;
5. For section headings in the table of contents, write each section in a line, regardless the level of headings.

{terminology_info}

please translate the following paragraph into {target_language}:
""",
        
        "group_translation": """
You are an expert translator, you need to translate the following paragraph into {target_language}.
 Please pay attention to the
following rules:
1. Maintain the original writing of names and places in the original article, and add the translated name and place in
parentheses;
2. The language in mathematical formulas **must** be english, e.g., "和" is translated to "and", mathematical formulas
should be written in **LaTex**;
3. Ensure that the translation is "as natural as possible" in {target_language};
4. The input format is **markdown**, and the output format is not changed;
5. For section headings in the table of contents, write each section in a line, regardless the level of headings.


{terminology_info}

please translate the following paragraph into {target_language}:
"""
    }

# 全局配置实例
config = Config() 