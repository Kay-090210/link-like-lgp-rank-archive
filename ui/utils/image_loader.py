"""
图片加载器模块
用于从网络异步加载图片
"""

import requests
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPixmap


class ImageLoader(QObject):
    """
    图片加载器，用于从网络加载图片
    """
    image_loaded = pyqtSignal(QPixmap)
    load_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = requests.Session()
        # 禁用SSL验证警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # 重试相关配置
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def load_from_url(self, url, retry_count=0):
        """从URL加载图片"""
        if not url or url == "未找到图片":
            self.load_error.emit("无效的图片URL")
            return
            
        try:
            # 打印调试信息
            print(f"正在尝试加载图片: {url}")
            print(f"使用的请求头: {self.session.headers}")
            
            # 使用requests获取图片数据，禁用SSL验证，允许重定向
            response = self.session.get(url, verify=False, timeout=10, allow_redirects=True)
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get('content-type', '')
            print(f"响应内容类型: {content_type}")
            
            if not content_type.startswith('image/'):
                self.load_error.emit(f"响应不是图片类型: {content_type}")
                return
            
            # 将图片数据转换为QPixmap
            pixmap = QPixmap()
            success = pixmap.loadFromData(response.content)
            
            if success and not pixmap.isNull():
                print(f"图片加载成功，尺寸: {pixmap.width()}x{pixmap.height()}")
                self.image_loaded.emit(pixmap)
            else:
                error_msg = "无法将响应数据转换为图片" if not success else "加载的图片数据无效"
                print(f"图片加载失败: {error_msg}")
                print(f"响应内容长度: {len(response.content)} 字节")
                
                # 如果还有重试次数，则进行重试
                if retry_count < self.max_retries:
                    print(f"准备进行第{retry_count + 1}次重试...")
                    import time
                    time.sleep(self.retry_delay)
                    return self.load_from_url(url, retry_count + 1)
                else:
                    self.load_error.emit(error_msg)
                
        except requests.exceptions.SSLError as e:
            print(f"SSL验证错误: {str(e)}")
            if retry_count < self.max_retries:
                print(f"准备进行第{retry_count + 1}次重试...")
                import time
                time.sleep(self.retry_delay)
                return self.load_from_url(url, retry_count + 1)
            self.load_error.emit(f"SSL验证错误: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: {str(e)}")
            if retry_count < self.max_retries:
                print(f"准备进行第{retry_count + 1}次重试...")
                import time
                time.sleep(self.retry_delay)
                return self.load_from_url(url, retry_count + 1)
            self.load_error.emit(f"连接错误: {str(e)}")
        except requests.exceptions.Timeout as e:
            print(f"请求超时: {str(e)}")
            if retry_count < self.max_retries:
                print(f"准备进行第{retry_count + 1}次重试...")
                import time
                time.sleep(self.retry_delay)
                return self.load_from_url(url, retry_count + 1)
            self.load_error.emit(f"请求超时: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {str(e)}")
            if retry_count < self.max_retries:
                print(f"准备进行第{retry_count + 1}次重试...")
                import time
                time.sleep(self.retry_delay)
                return self.load_from_url(url, retry_count + 1)
            self.load_error.emit(f"请求错误: {str(e)}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"图片加载错误详情:\n{error_details}")
            if retry_count < self.max_retries:
                print(f"准备进行第{retry_count + 1}次重试...")
                import time
                time.sleep(self.retry_delay)
                return self.load_from_url(url, retry_count + 1)
            self.load_error.emit(f"处理图片时发生错误: {str(e)}") 