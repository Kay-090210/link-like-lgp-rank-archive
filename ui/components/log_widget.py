"""
日志组件模块
用于显示应用程序的运行日志
"""

from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame

from ui.utils.style_manager import StyleManager


class LogWidget(QWidget):
    """日志显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_lines = []  # 日志队列
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        # 创建卡片
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(StyleManager.get_card_style())
        
        # 卡片内部布局
        card_layout = QVBoxLayout(card)
        
        # 创建标题
        title_label = QLabel("任务日志")
        title_label.setStyleSheet(f"color: {StyleManager.PRIMARY_COLOR}; font-weight: bold;")
        
        # 创建日志文本框
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(300)
        self.log_output.setStyleSheet(StyleManager.get_log_output_style())
        
        # 添加初始日志消息
        self.add_log("准备就绪，请点击\"开始获取\"按钮运行脚本...")
        
        # 添加到布局
        card_layout.addWidget(title_label)
        card_layout.addWidget(self.log_output)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(card)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        # 格式化为HTML
        html = f'<span style="color: {color};">[{timestamp}] {message}</span><br>'
        
        # 维护日志队列
        self.log_lines.append(html)
        if len(self.log_lines) > 500:
            self.log_lines.pop(0)
            
        # 刷新QTextEdit内容
        self.log_output.setHtml(''.join(self.log_lines))
        
        # 滚动到底部
        self.log_output.moveCursor(self.log_output.textCursor().End)
        
    def clear_logs(self):
        """清空日志"""
        self.log_lines.clear()
        self.log_output.clear() 