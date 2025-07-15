"""
API数据模型定义
使用Pydantic进行数据验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, List

class TranslationRequest(BaseModel):
    """翻译请求的数据模型"""
    content: str = Field(..., description="需要翻译的文本内容")
    target_language: str = Field("中文", description="目标翻译语言")
    terminology: Optional[Dict[str, str]] = Field(None, description="可选的术语词典")

class TaskCreationResponse(BaseModel):
    """任务创建响应模型"""
    task_id: str = Field(..., description="后台翻译任务的唯一ID")
    status_url: str = Field(..., description="用于查询任务状态的URL")
    result_url: str = Field(..., description="任务完成后用于获取结果的URL")

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="当前任务状态 (pending, running, completed, failed)")
    error: Optional[str] = Field(None, description="如果任务失败，此字段包含错误信息")

class TranslationResponse(BaseModel):
    """翻译响应的数据模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    translated_content: Optional[str] = Field(None, description="翻译后的文本内容")
    original_content: str = Field(..., description="原始文本内容")
    target_language: str = Field(..., description="目标语言")
    usage: Dict[str, int] = Field(..., description="Token使用情况统计")

class ErrorResponse(BaseModel):
    """错误响应的数据模型"""
    detail: str = Field(..., description="错误的详细信息") 