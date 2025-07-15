"""
翻译引擎核心模块
"""
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import config
from utils.tokenizer import token_calculator
from utils.logger import get_logger
import time
import asyncio
import concurrent.futures
from threading import Semaphore

class TranslationEngine:
    """
    翻译引擎类，负责所有与翻译相关的操作。
    它封装了与大语言模型（LLM）的交互，实现了并行翻译逻辑，并处理术语。
    """
    
    def __init__(self):
        """
        初始化翻译引擎。
        - 设置LLM客户端，包括模型、API密钥和超时。
        - 初始化token计算器和日志记录器。
        - 创建一个信号量来限制并行翻译的组数，防止API过载。
        """
        self.llm = ChatOpenAI(
            model=config.DEFAULT_MODEL,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            temperature=0.3,
            request_timeout=120,  # 为LLM请求设置120秒超时，防止线程挂起
            extra_body=dict(chat_template_kwargs=dict(enable_thinking=False))  # 禁用思考模式
        )
        self.token_calculator = token_calculator  # 用于计算token数量
        self.logger = get_logger()  # 获取全局日志实例
        # 创建信号量，其计数由配置文件中的MAX_PARALLEL_GROUPS决定，用于控制并发线程数
        self.parallel_semaphore = Semaphore(config.MAX_PARALLEL_GROUPS)
    
    def translate_group(
        self, 
        chunk_group: List[Dict[str, Any]],
        target_language: str,
        terminology: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        翻译一组文档块。
        此方法在组内是“串行”的，即按顺序逐个翻译块，以确保翻译的连贯性。
        
        Args:
            chunk_group (List[Dict[str, Any]]): 一个包含多个文档块（chunk）的列表。
            target_language (str): 目标翻译语言。
            terminology (Dict[str, str], optional): 一个术语词典，用于保证特定术语的翻译准确性。
            
        Returns:
            List[Dict[str, Any]]: 一个包含每个块翻译结果的列表。
        """
        # 使用日志记录器的step上下文管理器来跟踪此操作
        with self.logger.step("translate_group", f"翻译组内{len(chunk_group)}个块"):
            group_start_time = time.time()  # 记录组翻译开始时间
            
            # 准备并记录关于此翻译组的元数据信息
            group_info = {
                "group_size": len(chunk_group),
                "group_tokens": sum(chunk.get('tokens', 0) for chunk in chunk_group),
                "target_language": target_language,
                "has_terminology": bool(terminology)
            }
            
            self.logger.info("开始组翻译", group_info)
            
            # 将术语词典格式化为字符串，以便注入到系统提示中
            terminology_info = self._build_terminology_info(terminology)
            
            # 从配置中获取系统提示模板，并填入目标语言和术语信息
            system_prompt = config.SYSTEM_PROMPTS["translation"].format(
                target_language=target_language,
                terminology_info=terminology_info
            )
            
            results = []  # 用于存储此组内每个块的翻译结果
            
            try:
                # 遍历组内的每一个文档块，进行独立的翻译
                for i, chunk in enumerate(chunk_group):
                    # 为每个块构建独立的LLM消息，包括系统提示和用户内容（即要翻译的文本）
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=chunk['content'])
                    ]
                    # 调用LLM进行翻译，这是一个阻塞操作
                    response = self.llm.invoke(messages)
                    translated_content = response.content.strip()  # 清理翻译结果中的多余空白
                    # 构建包含详细信息的翻译结果字典
                    result = {
                        "original_content": chunk['content'],
                        "translated_content": translated_content,
                        "target_language": target_language,
                        "chunk_id": chunk['chunk_id'], # 保留原始的块ID，用于后续排序
                        "input_tokens": chunk.get('tokens', 0),
                        "output_tokens": self.token_calculator.count_tokens(translated_content),
                        "processing_time": time.time() - group_start_time,
                        "success": True,
                        "error": None
                    }
                    results.append(result)
                    # 记录调试信息，说明组内单个块的翻译已完成
                    self.logger.debug(f"组内第{i+1}个chunk翻译完成", {
                        "chunk_id": chunk['chunk_id'],
                        "output_length": len(translated_content),
                        "output_tokens": result["output_tokens"]
                    })
                
                # 记录整个组翻译完成的信息
                processing_time = time.time() - group_start_time
                self.logger.info("组翻译完成", {
                    "group_size": len(chunk_group),
                    "processing_time": processing_time,
                    "success": True
                })
                
                return results
                
            except Exception as e:
                # 如果在翻译过程中发生任何异常
                processing_time = time.time() - group_start_time
                self.logger.error("组翻译失败", e, {
                    "group_size": len(chunk_group),
                    "processing_time": processing_time,
                    "processed_chunks": len(results)
                })
                
                # 为组内所有未成功处理的块创建失败结果
                for i in range(len(results), len(chunk_group)):
                    chunk = chunk_group[i]
                    result = {
                        "original_content": chunk['content'],
                        "translated_content": "",
                        "target_language": target_language,
                        "chunk_id": chunk['chunk_id'],
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "processing_time": processing_time,
                        "success": False,
                        "error": str(e)
                    }
                    results.append(result)
                
                return results
    
    def parallel_group_translate(
        self,
        chunk_groups: List[List[Dict[str, Any]]],
        target_language: str,
        terminology: Dict[str, str] = None,
        progress_callback: callable = None
    ) -> List[Dict[str, Any]]:
        """
        并行翻译多个文档块组。
        这是翻译引擎的核心性能所在，它使用线程池来同时处理多个翻译组。
        
        Args:
            chunk_groups (List[List[Dict[str, Any]]]): 一个包含多个组的列表，每个组又包含多个块。
            target_language (str): 目标翻译语言。
            terminology (Dict[str, str], optional): 术语词典。
            progress_callback (callable, optional): 一个回调函数，用于在翻译过程中报告进度。
            
        Returns:
            List[Dict[str, Any]]: 一个包含所有块翻译结果的扁平化列表。
        """
        with self.logger.step("parallel_group_translate", f"并行翻译{len(chunk_groups)}个组"):
            batch_start_time = time.time()
            
            # 记录整个并行翻译任务的启动信息
            batch_info = {
                "total_groups": len(chunk_groups),
                "total_chunks": sum(len(group) for group in chunk_groups),
                "target_language": target_language,
                "max_parallel_groups": config.MAX_PARALLEL_GROUPS,
                "has_terminology": bool(terminology),
                "terminology_count": len(terminology) if terminology else 0
            }
            
            self.logger.info("开始并行组翻译", batch_info)
            
            all_results = []
            completed_groups = 0
            
            def translate_single_group(group_index, group):
                """这是一个包装函数，用于在单独的线程中翻译单个组。"""
                # 在进入翻译逻辑前，首先获取信号量。如果达到最大并发数，线程将在此处阻塞。
                with self.parallel_semaphore:
                    try:
                        # 调用组翻译方法
                        group_results = self.translate_group(group, target_language, terminology)
                        return group_index, group_results
                    except Exception as e:
                        # 如果在组翻译过程中发生未捕获的异常，记录错误并返回失败结果
                        self.logger.error(f"组{group_index}翻译失败", e)
                        failed_results = []
                        for chunk in group:
                            failed_results.append({
                                "original_content": chunk['content'],
                                "translated_content": "",
                                "target_language": target_language,
                                "chunk_id": chunk['chunk_id'],
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "processing_time": 0,
                                "success": False,
                                "error": str(e)
                            })
                        return group_index, failed_results
            
            # 使用ThreadPoolExecutor来管理并发执行的线程
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_GROUPS) as executor:
                # 提交所有组的翻译任务
                future_to_group = {
                    executor.submit(translate_single_group, i, group): i 
                    for i, group in enumerate(chunk_groups)
                }
                
                # 创建一个列表来按原始顺序存储每个组的结果
                group_results = [None] * len(chunk_groups)
                
                # 使用as_completed来处理完成的任务，哪个任务先完成就先处理哪个
                for future in concurrent.futures.as_completed(future_to_group):
                    group_index = future_to_group[future]
                    try:
                        # 获取任务的返回结果
                        result_group_index, results = future.result()
                        # 将结果存放到对应索引的位置，确保最终顺序正确
                        group_results[result_group_index] = results
                        completed_groups += 1
                        
                        # 添加调试日志，记录每个组的详细翻译结果
                        self.logger.debug(f"组 {result_group_index} 的翻译结果", {"result_data": results})
                        
                        # 如果提供了进度回调函数，则调用它来更新UI或外部状态
                        if progress_callback:
                            progress_callback(completed_groups, len(chunk_groups), results)
                        
                        # 记录单个组完成的日志
                        self.logger.info(f"组{result_group_index}翻译完成", {
                            "group_index": result_group_index,
                            "group_size": len(results),
                            "completed_groups": completed_groups,
                            "total_groups": len(chunk_groups)
                        })
                        
                    except Exception as e:
                        self.logger.error(f"处理组{group_index}结果时出错", e)
            
            # 按顺序合并所有组的结果到一个扁平列表中
            for group_result in group_results:
                if group_result:
                    all_results.extend(group_result)
            
            # 记录整个并行翻译任务完成后的最终统计数据
            processing_time = time.time() - batch_start_time
            successful_translations = sum(1 for result in all_results if result.get('success', False))
            
            final_stats = {
                "total_groups": len(chunk_groups),
                "total_chunks": len(all_results),
                "successful_translations": successful_translations,
                "failed_translations": len(all_results) - successful_translations,
                "total_processing_time": processing_time,
                "average_time_per_group": processing_time / len(chunk_groups) if chunk_groups else 0
            }
            
            self.logger.info("并行组翻译完成", final_stats)
            
            return all_results
    
    def _build_terminology_info(self, terminology: Dict[str, str] = None) -> str:
        """
        将术语词典构造成一个格式化的字符串，以便嵌入到系统提示中。
        
        Args:
            terminology (Dict[str, str], optional): 术语词典。
            
        Returns:
            str: 格式化后的术语字符串，如果词典为空则返回空字符串。
        """
        if not terminology:
            return ""
        
        terminology_lines = []
        for term, translation in terminology.items():
            terminology_lines.append(f"- {term}: {translation}")
        
        return f"\n术语词典：\n" + "\n".join(terminology_lines) + "\n"
    