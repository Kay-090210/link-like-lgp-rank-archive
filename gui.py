"""
リンクラ工具箱 GUI 应用
将HTML界面构想转换为PyQt5实现的GUI应用
提供公会战和个人战数据获取功能界面
"""

import sys
import os
from datetime import datetime
import atexit
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QRadioButton, QButtonGroup, QComboBox, QPushButton, 
    QTextEdit, QGroupBox, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# 导入项目中的功能模块
try:
    from multicatch import RankingDataCollector
    from catchgraderank import GradeRankingDataCollector
    import login
    from config import (GRAND_PRIX_CONFIG, SAVE_PATH, update_battle_type, 
                      calculate_event_id, calculate_grade_id, SEASON_GRADE_ID,
                      update_lgp_start_date, LGP_START_DATE)
    from getnews import get_latest_lgp_info
except ImportError as e:
    print(f"导入模块失败: {e}")

class ImageLoader(QObject):
    """
    图片加载器，用于从网络加载图片
    """
    image_loaded = pyqtSignal(QPixmap)
    load_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)
    
    def load_from_url(self, url):
        """从URL加载图片"""
        if not url or url == "未找到图片":
            self.load_error.emit("无效的图片URL")
            return
            
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.handle_reply(reply))
    
    def handle_reply(self, reply):
        """处理网络请求响应"""
        if reply.error() == QNetworkReply.NoError:
            # 读取图片数据并转换为QPixmap
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            # 如果加载成功，发出信号
            if not pixmap.isNull():
                self.image_loaded.emit(pixmap)
            else:
                self.load_error.emit("图片数据无效")
        else:
            self.load_error.emit(f"加载图片失败: {reply.errorString()}")
        
        # 清理资源
        reply.deleteLater()

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
        
    # 自定义输出重定向类
    class StreamRedirector:
        def __init__(self, signal_func, reset_signal):
            self.signal_func = signal_func
            self.reset_signal = reset_signal
            self.buffer = ""
            # 添加标志位，标记是否因错误而停止
            self.error_occurred = False
            
        def write(self, text):
            self.buffer += text
            if '\n' in text:
                line = self.buffer.strip()
                
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
                        # 将消息标记为错误，而不是普通信息
                        self.signal_func(line, 'error')
                        # 发送重置按钮信号
                        self.reset_signal.emit()
                        break
                else:
                    # 如果没有匹配到错误关键字，正常输出
                    self.signal_func(line, 'info')
                
                self.buffer = ""
                
        def flush(self):
            if self.buffer:
                self.signal_func(self.buffer.strip(), 'info')
                self.buffer = ""
    
    def terminate(self):
        """安全终止线程"""
        self.is_running = False
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
        
        data_collected = False  # 标记是否成功收集了数据
        error_occurred = False  # 标记是否发生了错误
        
        try:
            if not self.is_running:  # 检查是否已被请求终止
                return
                
            if self.battle_type == 'grade':
                # 调用grade榜获取功能
                # 根据当前月份计算最新的赛季等级ID
                from config import SEASON_GRADE_ID, calculate_grade_id
                # 重新计算，确保使用最新的月份
                current_grade_id = calculate_grade_id(self.current_month)
                
                collector = GradeRankingDataCollector()
                collector.collect_data()
                data_collected = True
            else:
                # 调用普通排行榜获取功能
                # 确保config中的LGP类型与当前选择一致
                if self.battle_type in ['personal', 'guild']:
                    # 这里不需要再次更新LGP类型，因为在按钮点击事件中已经更新
                    pass
                
                # 根据battle_type确定使用的排行榜类型
                ranking_type_value = 2 if self.battle_type == 'personal' else 1
                
                # 确定是当前榜还是前日榜
                if self.ranking_type == 'previous':
                    ranking_type_value = 20 if self.battle_type == 'personal' else 30
                elif self.ranking_type == 'current':
                    ranking_type_value = 21 if self.battle_type == 'personal' else 31
                
                collector = RankingDataCollector()
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # 设置窗口基本属性
        self.setWindowTitle("リンクラ工具箱")
        self.setMinimumSize(800, 600)
        
        # 设置应用样式
        self.set_application_style()
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 添加标题
        self.add_header(main_layout)
        
        # 添加主界面卡片
        self.add_main_card(main_layout)
        
        # 添加按钮区域
        self.add_button_group(main_layout)
        
        # 添加日志卡片
        self.add_log_card(main_layout)
        
        # 初始化当前月份
        self.current_month = datetime.now().month
        self.current_month_display.setText(f"{self.current_month}月")
        
        # 自动加载LGP信息（替代手动选择日期）
        # 这将自动获取最新的LGP信息并更新UI
        lgp_day = self.load_lgp_info()
        
        # 检查初始状态
        self.check_battle_type_selection()
        
        # 根据默认选中的单选按钮设置LGP类型和对应ID
        if self.personal_radio.isChecked():
            battle_type = 'personal'
            update_battle_type(battle_type)
            calculate_event_id(self.current_month)
        elif self.guild_radio.isChecked():
            battle_type = 'guild'
            update_battle_type(battle_type)
            calculate_event_id(self.current_month)
        elif self.grade_radio.isChecked():
            calculate_grade_id(self.current_month)
    
    def set_application_style(self):
        """设置全局应用样式"""
        # 设置颜色变量
        self.primary_color = "#6a4dbc"
        self.primary_light = "#8b71d2"
        self.bg_color = "#f5f7fa"
        self.card_bg = "#ffffff"
        self.text_color = "#333333"
        
        # 设置应用背景色
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(self.bg_color))
        palette.setColor(QPalette.WindowText, QColor(self.text_color))
        self.setPalette(palette)
        
    def add_header(self, layout):
        """添加标题部分"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        # 创建标题标签
        title_label = QLabel("リンクラ工具箱")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {self.primary_color};")
        
        # 创建副标题标签
        subtitle_label = QLabel("公会战 & 个人战数据获取工具")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        # 创建LGP图片显示区域
        self.lgp_image_label = QLabel()
        self.lgp_image_label.setAlignment(Qt.AlignCenter)
        self.lgp_image_label.setMinimumHeight(150)
        self.lgp_image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.card_bg};
                border-radius: 8px;
                padding: 5px;
                margin-top: 5px;
                margin-bottom: 5px;
            }}
        """)
        self.lgp_image_label.setText("正在加载LGP图片...")
        
        # 创建月份文本显示
        self.current_month_display = QLabel()
        month_font = QFont()
        month_font.setPointSize(16)
        month_font.setBold(True)
        self.current_month_display.setFont(month_font)
        self.current_month_display.setAlignment(Qt.AlignCenter)
        self.current_month_display.setStyleSheet(f"color: {self.primary_color}; margin-top: 5px;")
        
        # 创建LGP举行时间标签
        self.lgp_period_label = QLabel("正在获取LGP举行时间...")
        period_font = QFont()
        period_font.setPointSize(13)
        self.lgp_period_label.setFont(period_font)
        self.lgp_period_label.setStyleSheet(f"""
            color: #444;
            margin-top: 2px;
            padding: 0px;
        """)
        self.lgp_period_label.setAlignment(Qt.AlignCenter)
        self.lgp_period_label.setWordWrap(True)
        
        # 添加到布局
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(self.lgp_image_label)
        header_layout.addWidget(self.current_month_display)
        header_layout.addWidget(self.lgp_period_label)
        layout.addLayout(header_layout)
    
    def add_main_card(self, layout):
        """添加主界面卡片"""
        # 创建卡片
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        # 卡片内部布局
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        
        # 添加LGP类型选择
        self.add_battle_type_selection(card_layout)
        
        # 添加LGP类型选择
        self.add_ranking_type_selection(card_layout)
        
        # 添加卡片到主布局
        layout.addWidget(card)
    
    def add_battle_type_selection(self, layout):
        """添加LGP类型选择部分"""
        # 创建分组框
        group_box = QGroupBox("LGP类型")
        group_box.setStyleSheet(f"QGroupBox {{ color: {self.primary_color}; font-weight: bold; }}")
        
        # 创建单选按钮
        self.personal_radio = QRadioButton("个人战")
        self.guild_radio = QRadioButton("公会战")
        self.grade_radio = QRadioButton("grade榜")
        
        # 设置默认选中
        self.personal_radio.setChecked(True)
        
        # 创建按钮组
        self.battle_type_group = QButtonGroup()
        self.battle_type_group.addButton(self.personal_radio)
        self.battle_type_group.addButton(self.guild_radio)
        self.battle_type_group.addButton(self.grade_radio)
        
        # 添加变更事件
        self.battle_type_group.buttonClicked.connect(self.on_battle_type_changed)
        
        # 创建布局
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.personal_radio)
        radio_layout.addWidget(self.guild_radio)
        radio_layout.addWidget(self.grade_radio)
        radio_layout.addStretch()
        
        # 设置分组框布局
        group_box.setLayout(radio_layout)
        
        # 添加到卡片布局
        layout.addWidget(group_box)
    
    def add_ranking_type_selection(self, layout):
        """添加榜单类型选择部分"""
        # 创建分组框
        self.ranking_type_group_box = QGroupBox("榜单类型")
        self.ranking_type_group_box.setStyleSheet(f"QGroupBox {{ color: {self.primary_color}; font-weight: bold; }}")
        
        # 创建单选按钮
        self.current_radio = QRadioButton("当前榜")
        self.previous_radio = QRadioButton("前日榜")
        
        # 设置默认选中
        self.current_radio.setChecked(True)
        
        # 创建按钮组
        self.ranking_type_group = QButtonGroup()
        self.ranking_type_group.addButton(self.current_radio)
        self.ranking_type_group.addButton(self.previous_radio)
        
        # 创建布局
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.current_radio)
        radio_layout.addWidget(self.previous_radio)
        radio_layout.addStretch()
        
        # 设置分组框布局
        self.ranking_type_group_box.setLayout(radio_layout)
        
        # 添加到卡片布局
        layout.addWidget(self.ranking_type_group_box)
    
    def add_button_group(self, layout):
        """添加按钮组部分"""
        button_layout = QHBoxLayout()
        
        # 创建开始按钮
        self.start_button = QPushButton("开始获取")
        self.start_button.setMinimumSize(120, 40)
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.primary_color};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: {self.primary_light};
            }}
            QPushButton:pressed {{
                margin-top: 1px;
            }}
        """)
        
        # 连接点击事件
        self.start_button.clicked.connect(self.on_start_button_clicked)
        
        # 添加到布局
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def add_log_card(self, layout):
        """添加日志卡片部分"""
        # 创建卡片
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        # 卡片内部布局
        card_layout = QVBoxLayout(card)
        
        # 创建标题
        title_label = QLabel("任务日志")
        title_label.setStyleSheet(f"color: {self.primary_color}; font-weight: bold;")
        
        # 创建日志文本框
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(300)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #2f2f2f;
                color: #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, "Source Code Pro", monospace;
                font-size: 14px;
            }
        """)
        
        # 添加初始日志消息
        self.add_log("准备就绪，请点击\"开始获取\"按钮运行脚本...")
        
        # 添加到布局
        card_layout.addWidget(title_label)
        card_layout.addWidget(self.log_output)
        
        # 添加卡片到主布局
        layout.addWidget(card)
    
    def add_log(self, message, log_type=''):
        """添加日志消息到日志窗口"""
        # 根据日志类型设置颜色
        color_map = {
            'info': '#8bc34a',    # 绿色
            'error': '#f44336',   # 红色
            'warning': '#ffc107', # 黄色
            'success': '#4caf50'  # 深绿色
        }
        
        color = color_map.get(log_type, '#42a5f5')  # 默认使用 Material Design 蓝色
        
        # 添加时间戳
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 格式化为HTML并添加
        html = f'<span style="color: {color};">[{timestamp}] {message}</span><br>'
        self.log_output.insertHtml(html)
        
        # 滚动到底部
        self.log_output.moveCursor(self.log_output.textCursor().End)
    
    def check_battle_type_selection(self):
        """检查LGP类型并切换相关组件的可见性"""
        if self.grade_radio.isChecked():
            self.ranking_type_group_box.setVisible(False)
        else:
            self.ranking_type_group_box.setVisible(True)
    
    def on_battle_type_changed(self, button):
        """LGP类型改变事件处理"""
        self.check_battle_type_selection()
        
        # 更新config中的LGP类型配置
        if button == self.personal_radio:
            update_battle_type('personal')
            
            # 更新活动ID
            current_month = self.current_month
            calculate_event_id(current_month)
            
        elif button == self.guild_radio:
            update_battle_type('guild')
            
            # 更新活动ID
            current_month = self.current_month
            calculate_event_id(current_month)
            
        elif button == self.grade_radio:
            # 更新赛季等级ID
            current_month = self.current_month
            calculate_grade_id(current_month)
    
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
            self.add_log("正在终止先前的任务...", "warning")
            try:
                self.logger_thread.terminate()  # 使用我们的安全终止方法
                self.logger_thread.wait(3000)  # 等待线程完全终止，最多3秒
                
                # 如果线程仍在运行，发出警告并返回
                if self.logger_thread and self.logger_thread.isRunning():
                    self.add_log("无法终止先前的任务，请稍后再试", "error")
                    self.start_button.setEnabled(True)
                    self.start_button.setText("开始获取")
                    return
            except RuntimeError:
                # 如果在操作过程中C++对象被删除
                pass
            finally:
                # 不再使用deleteLater，而是直接设置为None
                self.logger_thread = None
        
        # 检查LGP开始日期是否已设置
        if LGP_START_DATE is None:
            self.add_log("错误: LGP开始日期未设置，正在重新获取...", "warning")
            if not self.load_lgp_info():
                self.add_log("错误: 无法获取LGP信息，请稍后重试", "error")
                return
        
        # 获取当前选择的值
        battle_type = 'personal'
        if self.guild_radio.isChecked():
            battle_type = 'guild'
        elif self.grade_radio.isChecked():
            battle_type = 'grade'
        
        ranking_type = 'current'
        if self.previous_radio.isChecked():
            ranking_type = 'previous'
        
        # 更新config中的LGP类型配置和活动ID
        if battle_type in ['personal', 'guild']:
            update_battle_type(battle_type)
            # 使用当前月份重新计算活动ID
            new_event_id = calculate_event_id(self.current_month)
        elif battle_type == 'grade':
            # 更新赛季等级ID
            new_grade_id = calculate_grade_id(self.current_month)
        
        # 创建日志线程并启动
        self.logger_thread = LoggerThread(
            battle_type=battle_type,
            ranking_type=ranking_type,
            current_month=self.current_month,
            lgp_start_day=None  # 不再使用从界面获取的开始日期
        )
        
        # 连接日志信号
        self.logger_thread.log_signal.connect(self.add_log)
        
        # 禁用开始按钮
        self.start_button.setEnabled(False)
        self.start_button.setText("获取中...")
        
        # 线程完成时启用按钮
        def on_thread_finished():
            self.start_button.setEnabled(True)
            self.start_button.setText("开始获取")
        
        # 连接重置按钮信号
        self.logger_thread.reset_button_signal.connect(on_thread_finished)
        
        # 连接任务状态信号
        def on_task_status(success):
            if success:
                self.add_log("数据获取任务已成功完成", "success")
            # 失败信息已在线程中直接通过log_signal发送，这里不需要额外处理
        
        self.logger_thread.task_status_signal.connect(on_task_status)
        
        # 连接线程完成信号
        self.logger_thread.finished.connect(on_thread_finished)
        
        # 启动线程
        self.logger_thread.start()

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
            self.add_log("正在安全终止运行中的任务...", "warning")
            # 恢复按钮状态
            self.start_button.setEnabled(True)
            self.start_button.setText("开始获取")
            
            try:
                # 安全终止线程
                self.logger_thread.terminate()
                # 等待线程终止（最多3秒）
                if not self.logger_thread.wait(3000):
                    self.add_log("无法正常终止线程，强制关闭", "error")
                
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

    def load_lgp_info(self):
        """加载LGP信息并更新UI"""
        self.add_log("正在获取最新LGP信息...", "info")
        
        try:
            # 获取最新的LGP信息
            latest_lgp = get_latest_lgp_info()
            
            if latest_lgp:
                self.add_log(f"获取到LGP信息: {latest_lgp['title']}", "info")
                
                # 验证日期信息
                if not latest_lgp.get('start_month') or not latest_lgp.get('start_day'):
                    self.add_log("错误: LGP信息中缺少开始日期", "error")
                    return None
                    
                # 验证日期值的合理性
                if not (1 <= latest_lgp['start_month'] <= 12):
                    self.add_log(f"错误: 无效的月份值 {latest_lgp['start_month']}", "error")
                    return None
                    
                if not (1 <= latest_lgp['start_day'] <= 31):
                    self.add_log(f"错误: 无效的日期值 {latest_lgp['start_day']}", "error")
                    return None
                
                # 更新月份
                self.current_month = latest_lgp['start_month']
                self.current_month_display.setText(f"{self.current_month}月")
                
                # 更新LGP开始日期
                current_year = datetime.now().year
                update_lgp_start_date(current_year, self.current_month, latest_lgp['start_day'])
                self.add_log(f"已设置LGP开始日期为: {current_year}年{self.current_month}月{latest_lgp['start_day']}日", "info")
                
                # 更新config.py文件中的LGP_START_DATE
                try:
                    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_content = f.read()
                    
                    # 使用正则表达式查找并替换LGP_START_DATE的定义
                    import re
                    # 尝试查找现有的LGP_START_DATE定义
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
                    
                    self.add_log("已更新config.py文件中的LGP开始日期", "success")
                    
                    # 重新加载config模块以更新全局变量
                    import config
                    import importlib
                    importlib.reload(config)
                    
                except Exception as e:
                    self.add_log(f"更新config.py文件失败: {str(e)}", "error")
                
                # 更新LGP举行时间标签
                if 'period' in latest_lgp and latest_lgp['period']:
                    # 简化时间显示格式
                    period = latest_lgp['period']
                    
                    # 尝试提取更简洁的时间格式：优先获取日期和时间范围
                    # 格式如：5月11日(日) 12:00 ～ 5月17日(土) 3:59
                    simple_period = re.search(r'(\d+月\d+日\([^)]+\).*?～.*?\d+月\d+日\([^)]+\))', period)
                    if simple_period:
                        period_text = simple_period.group(1)
                    else:
                        # 尝试获取更简单的格式，只显示日期范围
                        date_range = re.search(r'(\d+月\d+日.*?～.*?\d+月\d+日)', period)
                        if date_range:
                            period_text = date_range.group(1)
                        else:
                            period_text = period.split('\n')[0] if '\n' in period else period
                    
                    self.lgp_period_label.setText(period_text)
                else:
                    # 如果没有详细的时间信息，则使用提取的月日信息
                    self.lgp_period_label.setText(f"{self.current_month}月{latest_lgp['start_day']}日开始")
                
                # 更新UI显示
                self.add_log(f"获取到最新LGP信息: {latest_lgp['title']}", "success")
                self.add_log(f"LGP开始时间: {self.current_month}月{latest_lgp['start_day']}日", "info")
                
                # 加载LGP图片
                self.load_lgp_image(latest_lgp['first_img'])
                
                # 根据当前battle_type更新活动ID
                if self.personal_radio.isChecked():
                    battle_type = 'personal'
                    update_battle_type(battle_type)
                    calculate_event_id(self.current_month)
                elif self.guild_radio.isChecked():
                    battle_type = 'guild'
                    update_battle_type(battle_type)
                    calculate_event_id(self.current_month)
                elif self.grade_radio.isChecked():
                    calculate_grade_id(self.current_month)
                
                return latest_lgp['start_day']
            else:
                self.add_log("未能获取到有效的LGP信息", "warning")
                self.lgp_period_label.setText("未能获取LGP时间信息")
                return None
                
        except Exception as e:
            self.add_log(f"获取LGP信息失败: {str(e)}", "error")
            self.lgp_period_label.setText("获取LGP时间信息失败")
            return None
    
    def load_lgp_image(self, image_url):
        """加载LGP图片"""
        if not hasattr(self, 'image_loader'):
            # 创建图片加载器
            self.image_loader = ImageLoader(self)
            self.image_loader.image_loaded.connect(self.on_image_loaded)
            self.image_loader.load_error.connect(lambda err: self.add_log(f"图片加载失败: {err}", "error"))
        
        # 加载图片
        self.image_loader.load_from_url(image_url)
    
    def on_image_loaded(self, pixmap):
        """图片加载完成的回调"""
        # 调整图片大小，保持宽高比
        scaled_pixmap = pixmap.scaled(650, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 设置图片
        self.lgp_image_label.setPixmap(scaled_pixmap)
        self.add_log("LGP图片加载成功", "success")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    # 添加退出处理
    def cleanup():
        try:
            has_running_thread = hasattr(window, 'logger_thread') and window.logger_thread and window.logger_thread.isRunning()
        except (RuntimeError, AttributeError):
            # 窗口或线程对象可能已被删除
            has_running_thread = False
        
        if has_running_thread:
            print("程序退出，正在清理资源...")
            try:
                # 安全终止线程
                window.logger_thread.terminate()
                # 等待线程终止，但不超过2秒
                window.logger_thread.wait(2000)
                
                # 恢复标准输出和标准错误流
                if hasattr(window.logger_thread, 'old_stdout') and window.logger_thread.old_stdout is not None:
                    sys.stdout = window.logger_thread.old_stdout
                if hasattr(window.logger_thread, 'old_stderr') and window.logger_thread.old_stderr is not None:
                    sys.stderr = window.logger_thread.old_stderr
            except (RuntimeError, AttributeError):
                # 对象可能在操作过程中被删除
                # 确保标准流被恢复到默认状态
                if sys.stdout != sys.__stdout__:
                    sys.stdout = sys.__stdout__
                if sys.stderr != sys.__stderr__:
                    sys.stderr = sys.__stderr__
    
    atexit.register(cleanup)
    
    sys.exit(app.exec_()) 