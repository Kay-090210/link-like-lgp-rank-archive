"""
日志线程模块
用于异步执行数据获取任务并输出日志
"""

import sys
import re
import logging
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

from ui.utils.gui_log_handler import GuiLogHandler


class LoggerThread(QThread):
    """
    日志线程，用于异步执行数据获取任务并输出日志
    """
    log_signal = pyqtSignal(str, str)  # 信号: (消息, 类型)
    reset_button_signal = pyqtSignal()  # 重置按钮状态的信号
    task_status_signal = pyqtSignal(bool)  # 任务状态信号: True=成功, False=失败
    
    def __init__(self, battle_type, ranking_type, current_month, lgp_start_day=None, parent=None):
        super().__init__(parent)
        self.battle_type = battle_type    # LGP类型: 'personal', 'guild', 'grade'
        self.ranking_type = ranking_type  # LGP类型: 'current', 'previous'
        self.lgp_start_day = lgp_start_day  # LGP开始日期（可选，已通过config设置）
        self.current_month = current_month  # 当前月份
        self.is_running = False  # 线程运行状态标志
        # 保存原始流以便恢复
        self.old_stdout = None
        self.old_stderr = None
        # 保存原始logging配置
        self.original_handlers = None
        self.gui_log_handler = None
        
    # 自定义输出重定向类
    class StreamRedirector:
        def __init__(self, signal_func, reset_signal):
            self.signal_func = signal_func
            self.reset_signal = reset_signal
            self.buffer = ""
            self.error_occurred = False
            # 新增：高频日志计数器
            self.progress_counters = {
                'fetch_ranking': 0,  # "获取...数据成功"
                'fetch_profile': 0   # "请求 player_id...信息成功"
            }
            
        def write(self, text):
            self.buffer += text
            if '\n' in text:
                line = self.buffer.strip()
                # 只处理高频进度日志，每500条和完成时emit一次
                # 匹配两种可能的日志格式：标准logging格式和直接print格式
                m1 = re.search(r"获取 .+ 排行榜 target_rank \d+ 的数据成功 \((\d+)/(\d+)\)", line)
                if m1:
                    self.progress_counters['fetch_ranking'] += 1
                    count = self.progress_counters['fetch_ranking']
                    total = int(m1.group(2))
                    # 每500条或完成时输出进度
                    if count % 500 == 0 or count == total:
                        self.signal_func(f"已采集({count}/{total})条排行榜数据", 'info')
                    self.buffer = ""
                    return  # 其余高频进度日志不emit
                m2 = re.search(r"请求 player_id .+ 的信息成功 \((\d+)/(\d+)\)", line)
                if m2:
                    self.progress_counters['fetch_profile'] += 1
                    count = self.progress_counters['fetch_profile']
                    total = int(m2.group(2))
                    # 每500条或完成时输出进度
                    if count % 500 == 0 or count == total:
                        self.signal_func(f"已采集({count}/{total})条玩家详细信息", 'info')
                    self.buffer = ""
                    return  # 其余高频进度日志不emit
                # 检测特定错误信息，设置错误标志
                error_keywords = [
                    "停止脚本执行", 
                    "非比赛期间", 
                    "测试请求未返回数据", 
                    "可能不在赛季期间"
                ]
                for keyword in error_keywords:
                    if keyword in line:
                        self.error_occurred = True
                        self.signal_func(line, 'error')
                        self.reset_signal.emit()
                        break
                else:
                    self.signal_func(line, 'info')
                self.buffer = ""
            
        def flush(self):
            if self.buffer:
                self.signal_func(self.buffer.strip(), 'info')
                self.buffer = ""
    
    def setup_logging_handler(self):
        """设置logging处理器来捕获logging输出"""
        try:
            # 获取根logger
            root_logger = logging.getLogger()
            
            # 保存原始处理器
            self.original_handlers = root_logger.handlers.copy()
            
            # 创建GUI处理器
            self.gui_log_handler = GuiLogHandler(self.log_signal.emit)
            self.gui_log_handler.setLevel(logging.INFO)  # 只捕获INFO级别及以上的日志
            
            # 清除现有处理器并添加我们的处理器
            root_logger.handlers.clear()
            root_logger.addHandler(self.gui_log_handler)
            root_logger.setLevel(logging.INFO)  # 设置为INFO级别，避免DEBUG日志泛滥
            
            # 禁用第三方库的调试日志
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('requests').setLevel(logging.WARNING)
            logging.getLogger('http').setLevel(logging.WARNING)
            logging.getLogger('httpx').setLevel(logging.WARNING)
            
        except Exception as e:
            # 如果设置失败，发送错误信号
            self.log_signal.emit(f"设置logging处理器失败: {str(e)}", "error")
    
    def cleanup_logging_handler(self):
        """清理logging处理器并恢复原始配置"""
        try:
            if self.gui_log_handler:
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.gui_log_handler)
                self.gui_log_handler = None
                
                # 恢复原始处理器
                if self.original_handlers:
                    for handler in self.original_handlers:
                        root_logger.addHandler(handler)
                    self.original_handlers = None
        except Exception:
            # 忽略清理过程中的错误
            pass
    
    def terminate(self):
        """安全终止线程"""
        self.is_running = False
        
        # 清理logging处理器
        self.cleanup_logging_handler()
        
        # 恢复标准输出和标准错误流（如果已被重定向）
        if self.old_stdout is not None:
            sys.stdout = self.old_stdout
            self.old_stdout = None
        if self.old_stderr is not None:
            sys.stderr = self.old_stderr
            self.old_stderr = None
        
        super().terminate()  # 调用基类的terminate方法
        self.wait(2000)  # 等待2秒确保线程终止
    
    def run(self):
        # 设置运行状态
        self.is_running = True
        
        # 保存原始的标准输出和标准错误流
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        
        # 创建自定义流并重定向标准输出和标准错误
        stdout_redirector = self.StreamRedirector(self.log_signal.emit, self.reset_button_signal)
        stderr_redirector = self.StreamRedirector(lambda msg, _: self.log_signal.emit(msg, 'error'), self.reset_button_signal)
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector
        
        # 设置logging处理器
        self.setup_logging_handler()
        
        data_collected = False  # 标记是否成功收集了数据
        error_occurred = False  # 标记是否发生了错误
        
        try:
            if not self.is_running:  # 检查是否已被请求终止
                return
                
            if self.battle_type == 'grade':
                # 调用grade榜获取功能
                # 根据当前月份计算最新的赛季等级ID
                import config
                from catchgraderank import GradeRankingDataCollector
                from config import SEASON_GRADE_ID, calculate_grade_id
                # 重新计算，确保使用最新的月份
                current_grade_id = calculate_grade_id(self.current_month)
                
                collector = GradeRankingDataCollector()
                collector.collect_data()
                data_collected = True
            else:
                # 调用普通排行榜获取功能
                from multicatch import RankingDataCollector
                # 确保config中的LGP类型与当前选择一致
                if self.battle_type in ['personal', 'guild']:
                    # 这里不需要再次更新LGP类型，因为在按钮点击事件中已经更新
                    pass
                
                # 根据battle_type确定使用的排行榜类型
                ranking_type_value = 2 if self.battle_type == 'personal' else 1
                
                # 确定是当前榜还是前日榜
                if self.ranking_type == 'previous':
                    ranking_type_value = 20 
                elif self.ranking_type == 'current':
                    ranking_type_value = 21 
                
                # 传递正确的榜单类型参数
                collector = RankingDataCollector(ranking_type_value)
                collector.collect_data()
                data_collected = True
            
            # 检查重定向器中是否标记了错误
            if stdout_redirector.error_occurred or stderr_redirector.error_occurred:
                error_occurred = True
                
            if data_collected and self.is_running and not error_occurred:
                self.log_signal.emit(f"数据获取成功！", "success")
        except Exception as e:
            error_occurred = True
            if self.is_running:  # 只在线程仍在运行时发送信号
                self.log_signal.emit(f"数据获取失败: {str(e)}", "error")
                # 确保发送重置按钮的信号
                self.reset_button_signal.emit()
        finally:
            # 检查数据获取完成后的BATTLE_TYPE状态
            import config
            battle_type = "个人战" if config.BATTLE_TYPE['personal'] else "公会战"
            
            # 清理logging处理器
            self.cleanup_logging_handler()
            
            # 仅当标准输出和错误流仍被重定向时才恢复它们
            if sys.stdout != self.old_stdout and self.old_stdout is not None:
                sys.stdout = self.old_stdout
            if sys.stderr != self.old_stderr and self.old_stderr is not None:
                sys.stderr = self.old_stderr
            
            # 清除引用以帮助垃圾收集
            self.old_stdout = None
            self.old_stderr = None
            
            # 如果程序因异常或检测到错误而终止，确保发出错误信号
            if not data_collected or error_occurred:
                self.log_signal.emit("数据获取已停止，未能成功获取数据", "error")
                # 发送任务状态信号：失败
                self.task_status_signal.emit(False)
            else:
                # 发送任务状态信号：成功
                self.task_status_signal.emit(True)
                
            # 确保发送重置按钮的信号
            self.reset_button_signal.emit()
                
            # 重置运行状态
            self.is_running = False 