"""
统一日志配置模块
配置项目中所有模块的日志输出，并将日志保存到本地文件
"""

import logging
import os
from datetime import datetime

def setup_logger(name=None, log_level=logging.INFO):
    """
    设置统一的日志配置
    
    Args:
        name: 日志记录器名称，如果为None则使用根日志记录器
        log_level: 日志级别
    
    Returns:
        logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名（每次运行创建新文件，包含详细时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"dhr_scheduler_{timestamp}.log")
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # 创建控制台处理器（同时输出到控制台）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置格式化器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 创建默认的全局日志记录器
default_logger = setup_logger("DHR_Scheduler")
