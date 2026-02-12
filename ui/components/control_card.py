"""
控制卡片组件模块
包含客户端版本输入、战斗类型选择等控件
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLineEdit, QRadioButton, QButtonGroup, QFrame
)
from PyQt5.QtCore import pyqtSignal

from ui.utils.style_manager import StyleManager
import config


class ControlCard(QWidget):
    """控制卡片组件"""
    
    # 信号
    client_version_changed = pyqtSignal(str)
    battle_type_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置UI布局"""
        # 创建主卡片
        self.card = QFrame()
        self.card.setFrameShape(QFrame.StyledPanel)
        self.card.setStyleSheet(StyleManager.get_card_style())
        
        # 卡片内部布局
        card_layout = QVBoxLayout(self.card)
        card_layout.setSpacing(20)
        
        # 添加Client Version输入框
        self.add_client_version_input(card_layout)
        
        # 添加战斗类型选择
        self.add_battle_type_selection(card_layout)
        
        # 添加榜单类型选择
        self.add_ranking_type_selection(card_layout)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.card)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
    def add_client_version_input(self, layout):
        """添加Client Version输入框"""
        # 创建分组框
        group_box = QGroupBox("Client Version")
        group_box.setStyleSheet(StyleManager.get_group_box_style())
        
        # 创建水平布局
        input_layout = QHBoxLayout()
        
        # 创建输入框
        self.client_version_input = QLineEdit()
        self.client_version_input.setPlaceholderText("输入客户端版本")
        self.client_version_input.setText(config.DEFAULT_CLIENT_VERSION)  # 设置默认值
        self.client_version_input.setStyleSheet(StyleManager.get_input_style())
        
        # 添加输入框到布局
        input_layout.addWidget(self.client_version_input)
        
        # 设置分组框布局
        group_box.setLayout(input_layout)
        
        # 添加到卡片布局
        layout.addWidget(group_box)
        
    def add_battle_type_selection(self, layout):
        """添加战斗类型选择部分"""
        # 创建分组框
        group_box = QGroupBox("LGP类型")
        group_box.setStyleSheet(StyleManager.get_group_box_style())
        
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
        self.ranking_type_group_box.setStyleSheet(StyleManager.get_group_box_style())
        
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
        
    def setup_connections(self):
        """设置信号连接"""
        # 客户端版本变化
        self.client_version_input.textChanged.connect(self.on_client_version_changed)
        
        # 战斗类型变化
        self.battle_type_group.buttonClicked.connect(self.on_battle_type_changed)
        
        # 初始化时检查战斗类型
        self.check_battle_type_selection()
        
    def on_client_version_changed(self, new_version):
        """处理客户端版本变化"""
        self.client_version_changed.emit(new_version)
        
    def on_battle_type_changed(self, button):
        """战斗类型单选按钮变化事件处理"""
        self.check_battle_type_selection()
        
        # 确定战斗类型
        if button == self.personal_radio:
            battle_type = 'personal'
        elif button == self.guild_radio:
            battle_type = 'guild'
        elif button == self.grade_radio:
            battle_type = 'grade'
        else:
            battle_type = 'personal'
            
        self.battle_type_changed.emit(battle_type)
        
    def check_battle_type_selection(self):
        """检查战斗类型并切换相关组件的可见性"""
        if self.grade_radio.isChecked():
            self.ranking_type_group_box.setVisible(False)
        else:
            self.ranking_type_group_box.setVisible(True)
            
    def get_current_selections(self):
        """获取当前选择的设置"""
        # 战斗类型
        battle_type = 'personal'
        if self.guild_radio.isChecked():
            battle_type = 'guild'
        elif self.grade_radio.isChecked():
            battle_type = 'grade'
            
        # 榜单类型
        ranking_type = 'current'
        if self.previous_radio.isChecked():
            ranking_type = 'previous'
            
        return {
            'client_version': self.client_version_input.text(),
            'battle_type': battle_type,
            'ranking_type': ranking_type
        }
        
    def refresh_client_version(self):
        """刷新客户端版本显示"""
        # 获取最新的client version
        current_version = config.get_current_client_version()
        
        # 暂时断开信号连接，避免触发change事件
        self.client_version_input.textChanged.disconnect()
        
        # 更新输入框文本
        self.client_version_input.setText(current_version)
        
        # 重新连接信号
        self.client_version_input.textChanged.connect(self.on_client_version_changed) 