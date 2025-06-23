"""
主窗口模块
应用程序的主窗口实现
"""

import sys
import os
import atexit
import logging
from datetime import datetime

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

# 导入自定义组件
from ui.components.header_widget import HeaderWidget
from ui.components.control_card import ControlCard
from ui.components.button_group import ButtonGroup
from ui.components.log_widget import LogWidget
from ui.workers.logger_thread import LoggerThread
from ui.utils.style_manager import StyleManager

# 导入项目模块
try:
    import config
    from config import (
        update_battle_type, calculate_event_id, calculate_grade_id, 
        update_lgp_start_date, LGP_START_DATE
    )
    from getnews import get_latest_lgp_info
except ImportError as e:
    print(f"导入模块失败: {e}")


class MainWindow(QMainWindow):
    """应用程序主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_month = datetime.now().month
        self.logger_thread = None
        self.setup_ui()
        self.setup_connections()
        
        # 初始化时加载LGP信息
        self.load_lgp_info()
        
    def setup_ui(self):
        """设置UI布局"""
        # 设置窗口基本属性
        self.setWindowTitle("リンクラ工具箱")
        self.setMinimumSize(800, 600)
        
        # 设置应用样式
        StyleManager.setup_application_palette(self)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 添加组件
        self.header = HeaderWidget()
        self.control_card = ControlCard()
        self.button_group = ButtonGroup()
        self.log_widget = LogWidget()
        
        main_layout.addWidget(self.header)
        main_layout.addWidget(self.control_card)
        main_layout.addWidget(self.button_group)
        main_layout.addWidget(self.log_widget)
        
        # 初始化月份显示
        self.header.update_month_display(self.current_month)
        
    def setup_connections(self):
        """设置信号连接"""
        # 控制卡片信号
        self.control_card.client_version_changed.connect(self.on_client_version_changed)
        self.control_card.battle_type_changed.connect(self.on_battle_type_changed)
        
        # 按钮组信号
        self.button_group.start_clicked.connect(self.on_start_button_clicked)
        
        # 根据默认选中的单选按钮设置LGP类型
        selections = self.control_card.get_current_selections()
        self.on_battle_type_changed(selections['battle_type'])
        
    def on_client_version_changed(self, new_version):
        """处理客户端版本变化"""
        try:
            # 使用config中的函数更新client version
            config.update_client_version(new_version)
            
            # 保存到account.json
            config.save_account_config(config.ACCOUNT_DATA)
            
            self.log_widget.add_log(f"已更新客户端版本为: {new_version}", "info")
        except Exception as e:
            self.log_widget.add_log(f"更新客户端版本失败: {str(e)}", "error")
            
    def on_battle_type_changed(self, battle_type):
        """处理战斗类型变化"""
        # 更新config中的LGP类型配置
        if battle_type in ['personal', 'guild']:
            config.update_battle_type(battle_type)
        elif battle_type == 'grade':
            # 更新赛季等级ID
            config.calculate_grade_id(self.current_month)
            
    def on_start_button_clicked(self):
        """开始按钮点击事件处理"""
        # 检查是否有正在运行的线程
        try:
            has_running_thread = hasattr(self, 'logger_thread') and self.logger_thread and self.logger_thread.isRunning()
        except RuntimeError:
            # C++对象已被删除，但Python对象仍然存在
            has_running_thread = False
            # 清除无效引用
            if hasattr(self, 'logger_thread'):
                self.logger_thread = None
        
        if has_running_thread:
            self.log_widget.add_log("正在终止先前的任务...", "warning")
            try:
                self.logger_thread.terminate()  # 使用我们的安全终止方法
                self.logger_thread.wait(3000)  # 等待线程完全终止，最多3秒
                
                # 如果线程仍在运行，发出警告并返回
                if self.logger_thread and self.logger_thread.isRunning():
                    self.log_widget.add_log("无法终止先前的任务，请稍后再试", "error")
                    self.button_group.set_button_state(True, "开始获取")
                    return
            except RuntimeError:
                # 如果在操作过程中C++对象被删除
                pass
            finally:
                # 不再使用deleteLater，而是直接设置为None
                self.logger_thread = None
        
        # 检查LGP开始日期是否已设置
        if LGP_START_DATE is None:
            self.log_widget.add_log("错误: LGP开始日期未设置，正在重新获取...", "warning")
            if not self.load_lgp_info():
                self.log_widget.add_log("错误: 无法获取LGP信息，请稍后重试", "error")
                return
        
        # 获取当前选择的值
        selections = self.control_card.get_current_selections()
        battle_type = selections['battle_type']
        ranking_type = selections['ranking_type']
        
        # 更新config中的LGP类型配置和活动ID
        if battle_type in ['personal', 'guild']:
            config.update_battle_type(battle_type)
            # 使用当前月份重新计算活动ID
            new_event_id = config.calculate_event_id(self.current_month)
            # 保存GUI设置的活动ID
            config.set_gui_event_id(new_event_id)
            self.log_widget.add_log(f"已设置活动ID: {new_event_id}", "info")
        elif battle_type == 'grade':
            # 更新赛季等级ID
            new_grade_id = config.calculate_grade_id(self.current_month)
            self.log_widget.add_log(f"已设置赛季等级ID: {new_grade_id}", "info")
        
        # 创建日志线程并启动
        self.logger_thread = LoggerThread(
            battle_type=battle_type,
            ranking_type=ranking_type,
            current_month=self.current_month,
            lgp_start_day=None  # 不再使用从界面获取的开始日期
        )
        
        # 连接日志信号
        self.logger_thread.log_signal.connect(self.log_widget.add_log)
        
        # 禁用开始按钮
        self.button_group.set_button_state(False, "获取中...")
        
        # 线程完成时启用按钮
        def on_thread_finished():
            self.button_group.set_button_state(True, "开始获取")
        
        # 连接重置按钮信号
        self.logger_thread.reset_button_signal.connect(on_thread_finished)
        
        # 连接任务状态信号
        def on_task_status(success):
            if success:
                self.log_widget.add_log("数据获取任务已成功完成", "success")
            # 失败信息已在线程中直接通过log_signal发送，这里不需要额外处理
        
        self.logger_thread.task_status_signal.connect(on_task_status)
        
        # 连接线程完成信号
        self.logger_thread.finished.connect(on_thread_finished)
        
        # 启动线程
        self.logger_thread.start()
        
    def load_lgp_info(self):
        """加载LGP信息并更新UI"""
        self.log_widget.add_log("正在获取最新LGP信息...", "info")
        
        try:
            # 获取最新的LGP信息
            latest_lgp = get_latest_lgp_info()
            
            if latest_lgp:
                self.log_widget.add_log(f"获取到LGP信息: {latest_lgp['title']}", "info")
                
                # 验证日期信息
                if not latest_lgp.get('start_month') or not latest_lgp.get('start_day'):
                    self.log_widget.add_log("错误: LGP信息中缺少开始日期", "error")
                    return None
                    
                # 验证日期值的合理性
                if not (1 <= latest_lgp['start_month'] <= 12):
                    self.log_widget.add_log(f"错误: 无效的月份值 {latest_lgp['start_month']}", "error")
                    return None
                    
                if not (1 <= latest_lgp['start_day'] <= 31):
                    self.log_widget.add_log(f"错误: 无效的日期值 {latest_lgp['start_day']}", "error")
                    return None
                
                # 更新月份
                self.current_month = latest_lgp['start_month']
                self.header.update_month_display(self.current_month)
                
                # 更新LGP开始日期
                current_year = datetime.now().year
                update_lgp_start_date(current_year, self.current_month, latest_lgp['start_day'])
                self.log_widget.add_log(f"已设置LGP开始日期为: {current_year}年{self.current_month}月{latest_lgp['start_day']}日", "info")
                
                # 更新config.py文件中的LGP_START_DATE
                self.update_config_file(current_year, latest_lgp)
                
                # 更新LGP举行时间标签
                self.header.update_period_display(latest_lgp)
                
                # 更新UI显示
                self.log_widget.add_log(f"获取到最新LGP信息: {latest_lgp['title']}", "success")
                self.log_widget.add_log(f"LGP开始时间: {self.current_month}月{latest_lgp['start_day']}日", "info")
                
                # 加载LGP图片
                self.header.load_lgp_image(latest_lgp['first_img'], self.log_widget.add_log)
                
                return latest_lgp['start_day']
            else:
                self.log_widget.add_log("未能获取到有效的LGP信息", "warning")
                return None
                
        except Exception as e:
            self.log_widget.add_log(f"获取LGP信息失败: {str(e)}", "error")
            return None
            
    def update_config_file(self, current_year, latest_lgp):
        """更新config.py文件中的LGP开始日期"""
        try:
            # 处理PyInstaller打包后的路径问题
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe，不尝试修改config.py
                self.log_widget.add_log("exe环境下跳过config.py文件更新", "info")
            else:
                # 如果是开发环境，正常更新config.py
                import re
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.py')
                config_path = os.path.normpath(config_path)
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                
                # 使用正则表达式查找并替换LGP_START_DATE的定义
                lgp_date_pattern = r'(LGP_START_DATE\s*=\s*)(None|datetime\([^)]+\))'
                new_date_str = f"datetime({current_year}, {self.current_month}, {latest_lgp['start_day']})"
                
                if re.search(lgp_date_pattern, config_content):
                    # 如果找到了现有定义，就替换它
                    new_config_content = re.sub(lgp_date_pattern, f"\\1{new_date_str}", config_content)
                else:
                    # 如果没找到，就在文件开头的import部分后面添加定义
                    import_section_end = re.search(r'(from datetime import datetime\n)', config_content)
                    if import_section_end:
                        pos = import_section_end.end()
                        new_config_content = (
                            config_content[:pos] + 
                            f"\n# LGP开始日期配置（由GUI自动更新）\nLGP_START_DATE = {new_date_str}\n\n" +
                            config_content[pos:]
                        )
                    else:
                        # 如果找不到import部分，就在文件开头添加
                        new_config_content = (
                            "from datetime import datetime\n\n"
                            f"# LGP开始日期配置（由GUI自动更新）\nLGP_START_DATE = {new_date_str}\n\n" +
                            config_content
                        )
                
                # 写入更新后的内容
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(new_config_content)
                
                self.log_widget.add_log("已更新config.py文件中的LGP开始日期", "success")
                
                # 重新加载config模块以更新全局变量
                import importlib
                
                # 保存GUI设置的活动ID（如果存在）
                gui_event_id_set = getattr(config, '_gui_event_id_set', False)
                gui_event_id = getattr(config, '_gui_event_id', None)
                
                importlib.reload(config)
                
                # 恢复GUI设置的活动ID
                if gui_event_id_set and gui_event_id is not None:
                    config._gui_event_id_set = gui_event_id_set
                    config._gui_event_id = gui_event_id
            
        except Exception as e:
            self.log_widget.add_log(f"更新config.py文件失败: {str(e)}", "error")
            
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 检查是否有活动的日志线程
        try:
            has_running_thread = hasattr(self, 'logger_thread') and self.logger_thread and self.logger_thread.isRunning()
        except RuntimeError:
            # C++对象已被删除
            has_running_thread = False
            if hasattr(self, 'logger_thread'):
                self.logger_thread = None
        
        if has_running_thread:
            self.log_widget.add_log("正在安全终止运行中的任务...", "warning")
            # 恢复按钮状态
            self.button_group.set_button_state(True, "开始获取")
            
            try:
                # 安全终止线程
                self.logger_thread.terminate()
                # 等待线程终止（最多3秒）
                if not self.logger_thread.wait(3000):
                    self.log_widget.add_log("无法正常终止线程，强制关闭", "error")
                
                # 确保logging处理器被清理
                if hasattr(self.logger_thread, 'cleanup_logging_handler'):
                    self.logger_thread.cleanup_logging_handler()
                
                # 确保所有标准流都恢复到原始状态
                if hasattr(self.logger_thread, 'old_stdout') and self.logger_thread.old_stdout is not None:
                    sys.stdout = self.logger_thread.old_stdout
                    self.logger_thread.old_stdout = None
                    
                if hasattr(self.logger_thread, 'old_stderr') and self.logger_thread.old_stderr is not None:
                    sys.stderr = self.logger_thread.old_stderr
                    self.logger_thread.old_stderr = None
            except RuntimeError:
                # 对象可能在操作过程中被删除
                # 确保标准流被恢复到默认状态
                if sys.stdout != sys.__stdout__:
                    sys.stdout = sys.__stdout__
                if sys.stderr != sys.__stderr__:
                    sys.stderr = sys.__stderr__
        
        # 接受关闭事件
        event.accept()
        
    def setup_cleanup(self):
        """设置退出清理函数"""
        def cleanup():
            try:
                has_running_thread = hasattr(self, 'logger_thread') and self.logger_thread and self.logger_thread.isRunning()
            except (RuntimeError, AttributeError):
                # 窗口或线程对象可能已被删除
                has_running_thread = False
            
            if has_running_thread:
                print("程序退出，正在清理资源...")
                try:
                    # 安全终止线程
                    self.logger_thread.terminate()
                    # 等待线程终止，但不超过2秒
                    self.logger_thread.wait(2000)
                    
                    # 清理logging处理器
                    if hasattr(self.logger_thread, 'cleanup_logging_handler'):
                        self.logger_thread.cleanup_logging_handler()
                    
                    # 恢复标准输出和标准错误流
                    if hasattr(self.logger_thread, 'old_stdout') and self.logger_thread.old_stdout is not None:
                        sys.stdout = self.logger_thread.old_stdout
                    if hasattr(self.logger_thread, 'old_stderr') and self.logger_thread.old_stderr is not None:
                        sys.stderr = self.logger_thread.old_stderr
                except (RuntimeError, AttributeError):
                    # 对象可能在操作过程中被删除
                    # 确保logging处理器被清理
                    try:
                        root_logger = logging.getLogger()
                        # 移除所有处理器并恢复基本配置
                        for handler in root_logger.handlers[:]:
                            root_logger.removeHandler(handler)
                        logging.basicConfig()
                    except Exception:
                        pass
                    
                    # 确保标准流被恢复到默认状态
                    if sys.stdout != sys.__stdout__:
                        sys.stdout = sys.__stdout__
                    if sys.stderr != sys.__stderr__:
                        sys.stderr = sys.__stderr__
        
        atexit.register(cleanup) 