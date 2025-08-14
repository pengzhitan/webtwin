#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebTwin 日志记录和错误处理模块
提供统一的日志管理和异常处理功能
"""

import os
import sys
import logging
import logging.handlers
import traceback
import functools
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union
from enum import Enum

from config import Config


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class CustomFormatter(logging.Formatter):
    """自定义日志格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record):
        # 基础格式
        log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d] - %(message)s"
        )
        
        # 添加颜色（仅用于控制台输出）
        if self.use_colors and hasattr(record, 'levelname'):
            level_name = record.levelname
            if level_name in self.COLORS:
                colored_level = (
                    f"{self.COLORS[level_name]}{level_name}{self.COLORS['RESET']}"
                )
                record.levelname = colored_level
        
        formatter = logging.Formatter(log_format)
        return formatter.format(record)


class JsonFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
        
        return json.dumps(log_entry, ensure_ascii=False)


class LoggerManager:
    """日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, config: Config = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Config = None):
        if self._initialized:
            return
        
        self.config = config or Config()
        self.loggers = {}
        self._setup_logging()
        self._initialized = True
    
    def _setup_logging(self):
        """设置日志系统"""
        # 确保日志目录存在
        log_dir = Path(self.config.LOGS_FOLDER)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置根日志级别
        logging.root.setLevel(self.config.LOG_LEVEL)
        
        # 清除现有处理器
        logging.root.handlers.clear()
        
        # 创建处理器
        self._create_console_handler()
        self._create_file_handler()
        self._create_error_handler()
        
        if self.config.LOG_JSON_FORMAT:
            self._create_json_handler()
    
    def _create_console_handler(self):
        """创建控制台处理器"""
        if not self.config.LOG_TO_CONSOLE:
            return
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.config.LOG_LEVEL)
        
        # 使用彩色格式化器
        formatter = CustomFormatter(use_colors=True)
        console_handler.setFormatter(formatter)
        
        logging.root.addHandler(console_handler)
    
    def _create_file_handler(self):
        """创建文件处理器"""
        if not self.config.LOG_TO_FILE:
            return
        
        log_file = os.path.join(self.config.LOGS_FOLDER, 'webtwin.log')
        
        # 使用轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.LOG_MAX_SIZE,
            backupCount=self.config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        
        file_handler.setLevel(self.config.LOG_LEVEL)
        
        # 使用标准格式化器
        formatter = CustomFormatter(use_colors=False)
        file_handler.setFormatter(formatter)
        
        logging.root.addHandler(file_handler)
    
    def _create_error_handler(self):
        """创建错误日志处理器"""
        error_log_file = os.path.join(self.config.LOGS_FOLDER, 'error.log')
        
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.config.LOG_MAX_SIZE,
            backupCount=self.config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        
        error_handler.setLevel(logging.ERROR)
        
        # 详细的错误格式
        error_format = (
            "%(asctime)s - %(name)s - %(levelname)s\n"
            "File: %(pathname)s:%(lineno)d in %(funcName)s\n"
            "Message: %(message)s\n"
            "%(exc_text)s\n"
            "-" * 80 + "\n"
        )
        
        formatter = logging.Formatter(error_format)
        error_handler.setFormatter(formatter)
        
        logging.root.addHandler(error_handler)
    
    def _create_json_handler(self):
        """创建JSON格式处理器"""
        json_log_file = os.path.join(self.config.LOGS_FOLDER, 'webtwin.json')
        
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=self.config.LOG_MAX_SIZE,
            backupCount=self.config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        
        json_handler.setLevel(self.config.LOG_LEVEL)
        json_handler.setFormatter(JsonFormatter())
        
        logging.root.addHandler(json_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def log_with_extra(self, logger: logging.Logger, level: int, 
                      message: str, extra_data: Dict[str, Any] = None):
        """记录带有额外数据的日志"""
        if extra_data:
            # 创建LogRecord并添加额外数据
            record = logger.makeRecord(
                logger.name, level, '', 0, message, (), None
            )
            record.extra_data = extra_data
            logger.handle(record)
        else:
            logger.log(level, message)
    
    def cleanup_old_logs(self, max_age_days: int = 30):
        """清理旧日志文件"""
        try:
            log_dir = Path(self.config.LOGS_FOLDER)
            if not log_dir.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            cleaned_count = 0
            
            for log_file in log_dir.glob('*.log*'):
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    print(f"清理日志文件失败 {log_file}: {e}")
            
            if cleaned_count > 0:
                logger = self.get_logger(__name__)
                logger.info(f"已清理 {cleaned_count} 个旧日志文件")
                
        except Exception as e:
            print(f"清理日志目录失败: {e}")


class WebTwinException(Exception):
    """WebTwin基础异常类"""
    
    def __init__(self, message: str, error_code: str = None, 
                 details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'type': self.__class__.__name__
        }
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class ExtractionError(WebTwinException):
    """网站提取错误"""
    pass


class ValidationError(WebTwinException):
    """验证错误"""
    pass


class ConfigurationError(WebTwinException):
    """配置错误"""
    pass


class NetworkError(WebTwinException):
    """网络错误"""
    pass


class FileOperationError(WebTwinException):
    """文件操作错误"""
    pass


class SeleniumError(WebTwinException):
    """Selenium相关错误"""
    pass


def log_exceptions(logger: logging.Logger = None, 
                  reraise: bool = True,
                  default_return: Any = None):
    """异常日志装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录异常
                func_logger.error(
                    f"函数 {func.__name__} 执行失败: {str(e)}",
                    exc_info=True,
                    extra={'function': func.__name__, 'args': str(args)[:200]}
                )
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator


def log_performance(logger: logging.Logger = None, 
                   threshold_seconds: float = 1.0):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                if duration > threshold_seconds:
                    func_logger.warning(
                        f"函数 {func.__name__} 执行时间较长: {duration:.2f}秒",
                        extra={
                            'function': func.__name__,
                            'duration': duration,
                            'threshold': threshold_seconds
                        }
                    )
                else:
                    func_logger.debug(
                        f"函数 {func.__name__} 执行完成: {duration:.2f}秒"
                    )
        
        return wrapper
    return decorator


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = LoggerManager(config).get_logger(__name__)
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'recent_errors': []
        }
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理错误并返回错误信息"""
        error_info = self._create_error_info(error, context)
        
        # 记录错误
        self._log_error(error, error_info)
        
        # 更新统计
        self._update_error_stats(error_info)
        
        return error_info
    
    def _create_error_info(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建错误信息"""
        error_info = {
            'type': error.__class__.__name__,
            'message': str(error),
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        # 如果是自定义异常，添加额外信息
        if isinstance(error, WebTwinException):
            error_info.update(error.to_dict())
        
        return error_info
    
    def _log_error(self, error: Exception, error_info: Dict[str, Any]):
        """记录错误日志"""
        if isinstance(error, WebTwinException):
            self.logger.error(
                f"{error.error_code}: {error.message}",
                extra={'error_info': error_info}
            )
        else:
            self.logger.error(
                f"未处理的异常: {str(error)}",
                exc_info=True,
                extra={'error_info': error_info}
            )
    
    def _update_error_stats(self, error_info: Dict[str, Any]):
        """更新错误统计"""
        self.error_stats['total_errors'] += 1
        
        error_type = error_info['type']
        self.error_stats['errors_by_type'][error_type] = (
            self.error_stats['errors_by_type'].get(error_type, 0) + 1
        )
        
        # 保留最近的错误（最多100个）
        self.error_stats['recent_errors'].append(error_info)
        if len(self.error_stats['recent_errors']) > 100:
            self.error_stats['recent_errors'].pop(0)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return self.error_stats.copy()
    
    def clear_error_stats(self):
        """清除错误统计"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'recent_errors': []
        }
        self.logger.info("错误统计已清除")


# 全局实例
_logger_manager = None
_error_handler = None


def get_logger(name: str = None) -> logging.Logger:
    """获取日志器的便捷函数"""
    global _logger_manager
    
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    
    return _logger_manager.get_logger(name or __name__)


def get_error_handler() -> ErrorHandler:
    """获取错误处理器的便捷函数"""
    global _error_handler
    
    if _error_handler is None:
        _error_handler = ErrorHandler()
    
    return _error_handler


def setup_logging(config: Config = None):
    """设置日志系统的便捷函数"""
    global _logger_manager
    _logger_manager = LoggerManager(config)
    return _logger_manager