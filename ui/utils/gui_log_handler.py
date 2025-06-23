"""
GUI日志处理器模块
用于将logging输出重定向到GUI界面
"""

import logging


class GuiLogHandler(logging.Handler):
    """
    自定义的logging处理器，将logging的输出重定向到GUI的日志信号
    """
    def __init__(self, signal_func):
        super().__init__()
        self.signal_func = signal_func
        
    def emit(self, record):
        try:
            msg = self.format(record)
            # 根据日志级别设置类型
            log_type = 'error' if record.levelno >= logging.ERROR else 'warning' if record.levelno >= logging.WARNING else 'info'
            self.signal_func(msg, log_type)
        except Exception:
            # 忽略处理过程中的错误，避免递归
            pass 