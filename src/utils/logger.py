import logging
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import threading
from contextlib import contextmanager

class TranslationLogger:
    """翻译过程的详细日志记录器"""
    
    def __init__(self, log_dir: str = "logs", debug_mode: bool = False):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.debug_mode = debug_mode
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建不同级别的日志文件
        self.setup_loggers()
        
        # 进程跟踪
        self.process_steps = []
        self._lock = threading.Lock() # 用于保护 process_steps
        
        # 使用线程本地存储来管理每个线程的步骤信息
        self.thread_local = threading.local()
        
    def setup_loggers(self):
        """设置不同级别的日志记录器"""
        # 主日志记录器
        self.main_logger = logging.getLogger('translation_main')
        self.main_logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        
        # 处理过程日志记录器
        self.process_logger = logging.getLogger('translation_process')
        self.process_logger.setLevel(logging.DEBUG)
        
        # 错误日志记录器
        self.error_logger = logging.getLogger('translation_error')
        self.error_logger.setLevel(logging.ERROR)
        
        # 清除现有的处理器
        for logger in [self.main_logger, self.process_logger, self.error_logger]:
            logger.handlers.clear()
            
        # 创建格式化器
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 文件处理器
        main_handler = logging.FileHandler(
            self.log_dir / f"translation_{self.session_id}.log",
            encoding='utf-8'
        )
        main_handler.setFormatter(detailed_formatter)
        self.main_logger.addHandler(main_handler)
        
        process_handler = logging.FileHandler(
            self.log_dir / f"process_{self.session_id}.log",
            encoding='utf-8'
        )
        process_handler.setFormatter(detailed_formatter)
        self.process_logger.addHandler(process_handler)
        
        error_handler = logging.FileHandler(
            self.log_dir / f"error_{self.session_id}.log",
            encoding='utf-8'
        )
        error_handler.setFormatter(detailed_formatter)
        self.error_logger.addHandler(error_handler)
        
        # 控制台处理器（仅在调试模式下）
        if self.debug_mode:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(simple_formatter)
            self.main_logger.addHandler(console_handler)
            
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录信息级别日志"""
        log_entry = self._create_log_entry("INFO", message, extra_data)
        self.main_logger.info(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """记录调试级别日志"""
        log_entry = self._create_log_entry("DEBUG", message, extra_data)
        self.main_logger.debug(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
    def error(self, message: str, error: Optional[Exception] = None, extra_data: Optional[Dict[str, Any]] = None):
        """记录错误级别日志"""
        log_entry = self._create_log_entry("ERROR", message, extra_data)
        if error:
            log_entry["error_type"] = type(error).__name__
            log_entry["error_message"] = str(error)
            log_entry["error_traceback"] = str(error.__traceback__)
        
        self.error_logger.error(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
    def _create_log_entry(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建日志条目"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "level": level,
            "message": message,
            "current_step": getattr(self.thread_local, 'current_step', None),
            "thread_id": threading.get_ident()
        }
        
        if extra_data:
            entry.update(extra_data)
            
        return entry
        
    @contextmanager
    def step(self, step_name: str, description: str = ""):
        """上下文管理器，用于跟踪处理步骤"""
        self.start_step(step_name, description)
        try:
            yield self
        except Exception as e:
            self.error(f"步骤 {step_name} 执行失败", error=e)
            # 在finally中处理end_step，确保无论如何都调用
            # raise e # 根据上下文决定是否要重新抛出异常
        finally:
            self.end_step()
            
    def start_step(self, step_name: str, description: str = ""):
        """开始一个处理步骤"""
        # 步骤信息存储在线程本地变量中
        self.thread_local.current_step = step_name
        self.thread_local.step_start_time = time.time()
        
        step_info = {
            "step_name": step_name,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "status": "started",
            "thread_id": threading.get_ident()
        }
        
        with self._lock:
            self.process_steps.append(step_info)
        
        self.process_logger.info(f"开始步骤: {step_name} - {description} (线程: {threading.get_ident()})")
        
        if self.debug_mode:
            print(f"🔄 开始步骤: {step_name} (线程: {threading.get_ident()})")
                
    def end_step(self, result: Optional[Dict[str, Any]] = None):
        """结束当前处理步骤"""
        # 从线程本地变量中获取步骤信息
        current_step = getattr(self.thread_local, 'current_step', None)
        step_start_time = getattr(self.thread_local, 'step_start_time', None)

        if not current_step:
            return
            
        duration = time.time() - step_start_time if step_start_time else 0
        thread_id = threading.get_ident()

        with self._lock:
            # 更新对应的步骤信息
            # 注意：这里需要一种更可靠的方式来找到并更新正确的步骤
            # 简单起见，我们先按名称和线程ID查找
            step_to_update = None
            for step in reversed(self.process_steps):
                if step.get("step_name") == current_step and step.get("thread_id") == thread_id and step.get("status") == "started":
                    step_to_update = step
                    break
            
            if step_to_update:
                step_to_update.update({
                    "end_time": datetime.now().isoformat(),
                    "duration": duration,
                    "status": "completed",
                    "result": result
                })
        
        self.process_logger.info(f"完成步骤: {current_step} (耗时: {duration:.2f}秒, 线程: {thread_id})")
        
        if self.debug_mode:
            print(f"✅ 完成步骤: {current_step} (耗时: {duration:.2f}秒, 线程: {thread_id})")
            
        # 清理线程本地变量
        self.thread_local.current_step = None
        self.thread_local.step_start_time = None
            
    def log_translation_chunk(self, chunk_info: Dict[str, Any]):
        """记录翻译块的详细信息"""
        self.process_logger.info(f"翻译块信息: {json.dumps(chunk_info, ensure_ascii=False, indent=2)}")
        
    def log_context_update(self, context_info: Dict[str, Any]):
        """记录上下文更新信息"""
        self.process_logger.info(f"上下文更新: {json.dumps(context_info, ensure_ascii=False, indent=2)}")
        
    def log_token_usage(self, token_info: Dict[str, Any]):
        """记录Token使用情况"""
        self.process_logger.info(f"Token使用: {json.dumps(token_info, ensure_ascii=False, indent=2)}")
        
    def get_process_summary(self) -> Dict[str, Any]:
        """获取处理过程摘要"""
        total_duration = sum(step.get("duration", 0) for step in self.process_steps)
        
        return {
            "session_id": self.session_id,
            "total_steps": len(self.process_steps),
            "total_duration": total_duration,
            "steps": self.process_steps,
            "summary": {
                "completed_steps": len([s for s in self.process_steps if s.get("status") == "completed"]),
                "failed_steps": len([s for s in self.process_steps if s.get("status") == "failed"]),
                "average_step_duration": total_duration / len(self.process_steps) if self.process_steps else 0
            }
        }
        
    def save_process_summary(self):
        """保存处理过程摘要到文件"""
        summary = self.get_process_summary()
        summary_file = self.log_dir / f"summary_{self.session_id}.json"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
        return summary_file
        
    def get_recent_logs(self, lines: int = 50) -> List[str]:
        """获取最近的日志条目"""
        main_log_file = self.log_dir / f"translation_{self.session_id}.log"
        
        if not main_log_file.exists():
            return []
            
        with open(main_log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines

# 全局日志实例
_logger_instance = None

def get_logger(debug_mode: bool = False) -> TranslationLogger:
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TranslationLogger(debug_mode=debug_mode)
    return _logger_instance

def init_logger(log_dir: str = "logs", debug_mode: bool = False) -> TranslationLogger:
    """初始化日志系统"""
    global _logger_instance
    _logger_instance = TranslationLogger(log_dir=log_dir, debug_mode=debug_mode)
    return _logger_instance 