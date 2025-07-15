"""
自然语言处理模块
使用大模型进行智能意图识别和交互
"""
import re
import json
from typing import Dict, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import Config

class NLPProcessor:
    """自然语言处理器，使用大模型进行智能意图识别"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.DEFAULT_MODEL,
            temperature=0.1,
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
            timeout=120,
            extra_body=dict(chat_template_kwargs=dict(enable_thinking=False))
        )
        
        # 支持的语言列表
        self.supported_languages = [
            'English', '中文', '日文', '韩文', '法文', '德文', 
            '西班牙文', '俄文', '意大利文', '葡萄牙文', 
            '阿拉伯文', '泰文', '越南文'
        ]
    
    def analyze_user_intent(self, user_input: str, has_document: bool = False) -> Dict[str, any]:
        """
        使用大模型分析用户意图
        返回格式：
        {
            'request_type': 'translation'|'other',
            'has_document': bool,
            'target_language': str|None,
            'content': str,
            'needs_clarification': bool,
            'question': str|None
        }
        """
        prompt_template = """# 文档翻译Agent Prompt 

你是一个文档翻译助手。分析用户输入和上传的文档，判断是否为翻译任务。

## 用户输入
<user_input>
{user_input}
</user_input>

## 文档状态
has_document: {has_document}

## 判断逻辑
1. **有文档上传且文本包含翻译指令** → 翻译任务
2. **文本包含翻译指令** → 翻译任务  
3. **其他情况** → 非翻译任务

## 语言识别规则
- "中文/中国话/汉语/Chinese" → "中文"
- "英文/英语/English" → "English"  
- "日文/日语/Japanese" → "日文"
- "韩文/韩语/Korean" → "韩文"
- 其他语言按标准名称识别

## 输出格式
```json
{{
  "request_type": "translation" | "other",
  "has_document": true | false,
  "target_language": "具体语言名称" | "需要确认" | null,
  "content": "回应内容",
  "needs_clarification": true | false,
  "question": "需要询问的问题" | null
}}
```

## 处理规则
- 只上传文档无说明 → 询问目标语言
- 文档+翻译指令 → 直接翻译，明确识别目标语言
- 纯文本翻译 → 按原逻辑处理
- 非翻译任务 → 正常回应

## 重要提醒
- 必须准确识别目标语言，如"帮我把这篇文章翻译成中文"中的"中文"
- 如果用户明确说了目标语言，不要再追问
- 支持的目标语言：English、中文、日文、韩文、法文、德文、西班牙文、俄文、意大利文、葡萄牙文、阿拉伯文、泰文、越南文

现在分析用户输入并输出JSON格式结果。"""

        try:
            prompt = ChatPromptTemplate.from_template(prompt_template)
            response = self.llm.invoke(prompt.format_messages(
                user_input=user_input,
                has_document=has_document
            ))
            content = response.content.strip()
            
            # 解析LLM回复中的JSON
            return self._parse_llm_json_response(content, user_input, has_document)
            
        except Exception as e:
            print(f"LLM意图识别失败: {e}")
            return {
                'request_type': 'other',
                'has_document': has_document,
                'target_language': None,
                'content': '抱歉，我暂时无法理解您的需求，请重新描述。',
                'needs_clarification': False,
                'question': None
            }
    
    def _parse_llm_json_response(self, llm_content: str, user_input: str, has_document: bool) -> Dict[str, any]:
        """解析LLM的JSON回复内容"""
        try:
            # 尝试从回复中提取JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有找到```json```标记，尝试直接解析整个内容
                json_str = llm_content
            
            # 解析JSON
            result = json.loads(json_str)
            
            # 验证和补充字段
            result['has_document'] = has_document
            
            # 验证target_language是否在支持列表中
            if result.get('target_language') and result['target_language'] not in ['需要确认'] + self.supported_languages:
                # 尝试映射到支持的语言
                mapped_lang = self._map_to_supported_language(result['target_language'])
                if mapped_lang:
                    result['target_language'] = mapped_lang
                else:
                    result['target_language'] = '需要确认'
                    result['needs_clarification'] = True
                    result['question'] = f"请明确指定目标语言，支持的语言有：{', '.join(self.supported_languages)}"
            
            return result
            
        except json.JSONDecodeError:
            # JSON解析失败，使用备用逻辑
            return self._fallback_analysis(user_input, has_document, llm_content)
    
    def _map_to_supported_language(self, language: str) -> Optional[str]:
        """映射到支持的语言"""
        language_mapping = {
            '英语': 'English', '英文': 'English', 'english': 'English',
            '中国话': '中文', '汉语': '中文', 'chinese': '中文',
            '日语': '日文', 'japanese': '日文',
            '韩语': '韩文', 'korean': '韩文',
            '法语': '法文', 'french': '法文',
            '德语': '德文', 'german': '德文',
            '西班牙语': '西班牙文', 'spanish': '西班牙文',
            '俄语': '俄文', 'russian': '俄文',
            '意大利语': '意大利文', 'italian': '意大利文',
            '葡萄牙语': '葡萄牙文', 'portuguese': '葡萄牙文',
            '阿拉伯文': '阿拉伯文', 'arabic': '阿拉伯文',
            '泰文': '泰文', 'thai': '泰文',
            '越南文': '越南文', 'vietnamese': '越南文'
        }
        
        return language_mapping.get(language.lower())
    
    def _fallback_analysis(self, user_input: str, has_document: bool, llm_content: str) -> Dict[str, any]:
        """备用分析逻辑"""
        # 简单的关键词匹配
        translation_keywords = ['翻译', 'translate', '译成', '转换', '变成', '改成']
        is_translation = has_document or any(keyword in user_input.lower() for keyword in translation_keywords)
        
        if is_translation:
            # 尝试提取目标语言
            target_language = self._extract_language_from_input(user_input)
            
            if target_language:
                return {
                    'request_type': 'translation',
                    'has_document': has_document,
                    'target_language': target_language,
                    'content': f'已识别目标语言为【{target_language}】，准备开始翻译。',
                    'needs_clarification': False,
                    'question': None
                }
            else:
                return {
                    'request_type': 'translation',
                    'has_document': has_document,
                    'target_language': '需要确认',
                    'content': '我理解您需要翻译，请告诉我您想翻译成什么语言？',
                    'needs_clarification': True,
                    'question': f'请选择目标语言：{", ".join(self.supported_languages)}'
                }
        else:
            return {
                'request_type': 'other',
                'has_document': has_document,
                'target_language': None,
                'content': llm_content or '您好！我是智能翻译助手，可以帮您翻译文档。请告诉我您的需求。',
                'needs_clarification': False,
                'question': None
            }
    
    def _extract_language_from_input(self, user_input: str) -> Optional[str]:
        """从用户输入中提取目标语言"""
        language_patterns = {
            r'(?:英语|英文|English|english)': 'English',
            r'(?:中文|中国话|Chinese|chinese|汉语|简体中文|繁体中文)': '中文',
            r'(?:日语|日文|Japanese|japanese|日本语)': '日文',
            r'(?:韩语|韩文|Korean|korean|朝鲜语)': '韩文',
            r'(?:法语|法文|French|french)': '法文',
            r'(?:德语|德文|German|german)': '德文',
            r'(?:西班牙语|西班牙文|Spanish|spanish)': '西班牙文',
            r'(?:俄语|俄文|Russian|russian)': '俄文',
            r'(?:意大利语|意大利文|Italian|italian)': '意大利文',
            r'(?:葡萄牙语|葡萄牙文|Portuguese|portuguese)': '葡萄牙文',
            r'(?:阿拉伯语|阿拉伯文|Arabic|arabic)': '阿拉伯文',
            r'(?:泰语|泰文|Thai|thai)': '泰文',
            r'(?:越南语|越南文|Vietnamese|vietnamese)': '越南文'
        }
        
        for pattern, language in language_patterns.items():
            if re.search(pattern, user_input, re.IGNORECASE):
                return language
        
        return None
    
    # def extract_translation_intent(self, user_input: str, has_document: bool = False) -> Dict[str, str]:
    #     """
    #     提取翻译意图，兼容原有接口
    #     返回格式保持与原来一致，以便与Gradio应用兼容
    #     """
    #     intent_result = self.analyze_user_intent(user_input, has_document)
        
    #     # 转换为原有格式
    #     return {
    #         'action': 'translate' if intent_result['request_type'] == 'translation' else 'chat',
    #         'target_language': intent_result.get('target_language') or '中文',
    #         'confidence': 'high' if intent_result['request_type'] == 'translation' else 'low',
    #         'response': intent_result['content'],
    #         'needs_clarification': intent_result.get('needs_clarification', False),
    #         'question': intent_result.get('question')
    #     }
    
    # # 保持向后兼容的方法
    # def is_translation_request(self, user_input: str, has_document: bool = False) -> bool:
    #     """判断用户输入是否为翻译请求"""
    #     intent = self.analyze_user_intent(user_input, has_document)
    #     return intent['request_type'] == 'translation'
    
    # def extract_target_language(self, user_input: str, has_document: bool = False) -> str:
    #     """从用户输入中提取目标语言"""
    #     intent = self.analyze_user_intent(user_input, has_document)
    #     return intent.get('target_language') or '中文' 