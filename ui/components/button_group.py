"""
按钮组组件模块
包含应用的主要操作按钮
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal

from ui.utils.style_manager import StyleManager


class ButtonGroup(QWidget):
    """按钮组组件"""
    
    # 信号
    start_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        button_layout = QHBoxLayout(self)
        
        # 创建开始按钮
        self.start_button = QPushButton("开始获取")
        self.start_button.setMinimumSize(120, 40)
        self.start_button.setStyleSheet(StyleManager.get_button_style())
        
        # 连接点击事件
        self.start_button.clicked.connect(self.on_start_clicked)
        
        # 添加到布局
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addStretch()
        
    def on_start_clicked(self):
        """开始按钮点击事件"""
        self.start_clicked.emit()
        
    def set_button_state(self, enabled, text="开始获取"):
        """设置按钮状态"""
        self.start_button.setEnabled(enabled)
        self.start_button.setText(text) 