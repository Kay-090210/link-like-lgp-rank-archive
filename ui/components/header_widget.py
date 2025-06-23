"""
头部组件模块
包含应用标题、LGP图片和时间信息
"""

import re
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.utils.image_loader import ImageLoader
from ui.utils.style_manager import StyleManager


class HeaderWidget(QWidget):
    """应用程序头部组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_loader = None
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # 创建标题标签
        self.title_label = QLabel("リンクラ工具箱")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {StyleManager.PRIMARY_COLOR};")
        
        # 创建副标题标签
        self.subtitle_label = QLabel("公会战 & 个人战数据获取工具")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        
        # 创建LGP图片显示区域
        self.lgp_image_label = QLabel()
        self.lgp_image_label.setAlignment(Qt.AlignCenter)
        self.lgp_image_label.setMinimumHeight(150)
        self.lgp_image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {StyleManager.CARD_BG};
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
        self.current_month_display.setStyleSheet(f"color: {StyleManager.PRIMARY_COLOR}; margin-top: 5px;")
        
        # 创建LGP举行时间标签
        self.lgp_period_label = QLabel("正在获取LGP举行时间...")
        period_font = QFont()
        period_font.setPointSize(13)
        self.lgp_period_label.setFont(period_font)
        self.lgp_period_label.setStyleSheet("""
            color: #444;
            margin-top: 2px;
            padding: 0px;
        """)
        self.lgp_period_label.setAlignment(Qt.AlignCenter)
        self.lgp_period_label.setWordWrap(True)
        
        # 添加到布局
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.lgp_image_label)
        layout.addWidget(self.current_month_display)
        layout.addWidget(self.lgp_period_label)
    
    def update_month_display(self, month):
        """更新月份显示"""
        self.current_month_display.setText(f"{month}月")
    
    def update_period_display(self, period_info):
        """更新LGP举行时间显示"""
        if 'period' in period_info and period_info['period']:
            # 简化时间显示格式
            period = period_info['period']
            
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
            if 'start_month' in period_info and 'start_day' in period_info:
                self.lgp_period_label.setText(f"{period_info['start_month']}月{period_info['start_day']}日开始")
            else:
                self.lgp_period_label.setText("未能获取LGP时间信息")
    
    def load_lgp_image(self, image_url, log_callback=None):
        """加载LGP图片"""
        if not self.image_loader:
            # 创建图片加载器
            self.image_loader = ImageLoader(self)
            self.image_loader.image_loaded.connect(self.on_image_loaded)
            if log_callback:
                self.image_loader.load_error.connect(lambda err: log_callback(f"图片加载失败: {err}", "error"))
        
        # 验证和处理图片URL
        if not image_url or image_url == "未找到图片":
            if log_callback:
                log_callback("无效的图片URL", "error")
            return
            
        # 处理相对URL
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif not image_url.startswith(('http://', 'https://')):
            image_url = 'https://' + image_url
            
        # 加载图片
        self.image_loader.load_from_url(image_url)
    
    def on_image_loaded(self, pixmap):
        """图片加载完成的回调"""
        # 调整图片大小，保持宽高比
        scaled_pixmap = pixmap.scaled(650, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 设置图片
        self.lgp_image_label.setPixmap(scaled_pixmap) 