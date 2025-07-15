"""
简单的内存任务管理器
用于跟踪后台翻译任务的状态和结果。
"""
import uuid
from typing import Dict, Any, Literal

# 定义任务状态的类型
TaskStatus = Literal["pending", "running", "completed", "failed"]

class TaskManager:
    """
    一个简单的内存任务管理器。
    注意：这是一个基础实现，服务重启后任务状态会丢失。
    """
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, request_data: Dict[str, Any] = None) -> str:
        """
        创建一个新任务并返回其ID。
        """
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "request_data": request_data or {}
        }
        return task_id

    def set_status(self, task_id: str, status: TaskStatus):
        """
        设置任务的状态。
        """
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status
        else:
            raise KeyError(f"Task with ID '{task_id}' not found.")

    def set_result(self, task_id: str, result: Any):
        """
        为已完成的任务设置结果。
        """
        if task_id in self._tasks:
            self._tasks[task_id]["result"] = result
            self.set_status(task_id, "completed")
        else:
            raise KeyError(f"Task with ID '{task_id}' not found.")

    def set_error(self, task_id: str, error_message: str):
        """
        为失败的任务设置错误信息。
        """
        if task_id in self._tasks:
            self._tasks[task_id]["error"] = error_message
            self.set_status(task_id, "failed")
        else:
            raise KeyError(f"Task with ID '{task_id}' not found.")

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务的完整信息（状态、结果、错误）。
        """
        if task_id in self._tasks:
            return self._tasks[task_id]
        return None 