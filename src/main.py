"""
FastAPI 应用主入口
提供HTTP API接口用于翻译服务
"""
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request as FastAPIRequest
from api.models import (
    TranslationRequest, 
    TranslationResponse, 
    ErrorResponse, 
    TaskCreationResponse, 
    TaskStatusResponse
)
from api.services import TranslationService
from api.task_manager import TaskManager
from utils.logger import init_logger

# 初始化
init_logger(debug_mode=True)
app = FastAPI(
    title="文档翻译 Agent API",
    description="提供异步翻译任务处理的API服务。",
    version="1.0.0"
)
translation_service = TranslationService()
task_manager = TaskManager()

def run_translation_task(task_id: str, request_data: TranslationRequest):
    """
    后台执行的翻译任务函数。
    """
    try:
        task_manager.set_status(task_id, "running")
        result = translation_service.translate_document(
            content=request_data.content,
            target_language=request_data.target_language,
            terminology=request_data.terminology
        )
        task_manager.set_result(task_id, result)
    except Exception as e:
        app.logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
        task_manager.set_error(task_id, str(e))

@app.post("/translation/start", 
            response_model=TaskCreationResponse,
            status_code=202,
            summary="启动一个异步翻译任务",
            description="提交翻译请求，服务将在后台处理，并立即返回一个任务ID。")
async def start_translation(request: TranslationRequest, background_tasks: BackgroundTasks, http_request: FastAPIRequest):
    """
    接收翻译请求，创建后台任务，并立即返回任务ID。
    """
    # 存储请求数据以便后续获取结果时使用
    request_data = {
        "content": request.content,
        "target_language": request.target_language,
        "terminology": request.terminology
    }
    task_id = task_manager.create_task(request_data)
    
    # 将耗时的翻译任务添加到后台执行
    background_tasks.add_task(run_translation_task, task_id, request)
    
    # 构建状态和结果查询的URL
    status_url = http_request.url_for('get_task_status', task_id=task_id)
    result_url = http_request.url_for('get_task_result', task_id=task_id)
    
    return TaskCreationResponse(
        task_id=task_id,
        status_url=str(status_url),
        result_url=str(result_url)
    )

@app.get("/translation/status/{task_id}", 
           response_model=TaskStatusResponse,
           summary="查询翻译任务的状态",
           description="根据任务ID查询翻译任务的当前状态。")
async def get_task_status(task_id: str):
    """
    根据任务ID返回任务的当前状态。
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        error=task.get("error")
    )

@app.get("/translation/result/{task_id}",
           response_model=TranslationResponse,
           summary="获取翻译任务的结果",
           description="根据任务ID获取翻译结果。只有在任务完成后才能获取。",
           responses={202: {"description": "任务仍在处理中"}, 404: {"model": ErrorResponse}})
async def get_task_result(task_id: str):
    """
    根据任务ID返回翻译结果。
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    if task["status"] != "completed":
        # 如果任务未完成，可以返回一个202 Accepted响应或重定向到状态URL
        raise HTTPException(status_code=202, detail=f"任务仍在处理中，当前状态: {task['status']}")

    result_data = task["result"]
    request_data = task.get("request_data", {})
    
    return TranslationResponse(
        task_id=task_id,
        status=task["status"],
        translated_content=result_data["translated_content"],
        original_content=request_data.get("content", ""), # 从存储的请求数据中获取
        target_language=request_data.get("target_language", "中文"), # 从存储的请求数据中获取
        usage=result_data["usage"]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8099) 

#uvicorn main:app --host 0.0.0.0 --port 8099 --reload