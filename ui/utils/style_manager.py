"""
样式管理器模块
统一管理应用程序的样式配置
"""

from PyQt5.QtGui import QColor, QPalette


class StyleManager:
    """样式管理器类，提供统一的样式配置"""
    
    # 颜色配置
    PRIMARY_COLOR = "#6a4dbc"
    PRIMARY_LIGHT = "#8b71d2"
    BG_COLOR = "#f5f7fa"
    CARD_BG = "#ffffff"
    TEXT_COLOR = "#333333"
    
    @classmethod
    def get_button_style(cls):
        """获取按钮样式"""
        return f"""
            QPushButton {{
                background-color: {cls.PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: {cls.PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                margin-top: 1px;
            }}
        """
    
    @classmethod
    def get_card_style(cls):
        """获取卡片样式"""
        return f"""
            QFrame {{
                background-color: {cls.CARD_BG};
                border-radius: 8px;
                padding: 15px;
            }}
        """
    
    @classmethod
    def get_group_box_style(cls):
        """获取分组框样式"""
        return f"QGroupBox {{ color: {cls.PRIMARY_COLOR}; font-weight: bold; }}"
    
    @classmethod
    def get_log_output_style(cls):
        """获取日志输出框样式"""
        return """
            QTextEdit {
                background-color: #2f2f2f;
                color: #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, "Source Code Pro", monospace;
                font-size: 14px;
            }
        """
    
    @classmethod
    def get_input_style(cls):
        """获取输入框样式"""
        return f"""
            QLineEdit {{
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
            }}
            QLineEdit:focus {{
                border-color: {cls.PRIMARY_COLOR};
            }}
        """
    
    @classmethod
    def setup_application_palette(cls, app):
        """设置应用程序调色板"""
        palette = app.palette()
        palette.setColor(QPalette.Window, QColor(cls.BG_COLOR))
        palette.setColor(QPalette.WindowText, QColor(cls.TEXT_COLOR))
        app.setPalette(palette) 