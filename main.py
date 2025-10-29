"""
リンクラ工具箱应用程序入口
使用模块化重构后的GUI组件
"""

import sys
import atexit
from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow
import config


def main():
    """应用程序主函数"""
    # 启动时自动检查并更新客户端版本
    print("正在检查客户端版本...")
    try:
        config.update_client_version_auto()
    except Exception as e:
        print(f"客户端版本检查失败，继续启动应用: {e}")

    # 检查账号配置，必要时触发自动注册
    print("正在检查账号配置...")
    try:
        from login import check_and_run_register

        if not check_and_run_register():
            print("自动注册流程失败，请检查网络或手动运行 register.py")
    except Exception as e:
        print(f"账号配置检查异常，继续启动应用: {e}")

    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = MainWindow()
    
    # 设置退出清理
    window.setup_cleanup()
    
    # 显示窗口
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 
