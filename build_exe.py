#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建exe文件的脚本
使用PyInstaller将项目打包成可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_exe():
    """构建exe文件"""
    print("开始构建exe文件...")
    
    # 确保当前目录是项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 检查必要文件是否存在
    required_files = ['gui.py', 'icon.ico', 'account.json']
    for file in required_files:
        if not Path(file).exists():
            print(f"错误: 找不到必要文件 {file}")
            return False
    
    # 清理之前的构建文件
    build_dirs = ['build', 'dist/__pycache__']
    for dir_path in build_dirs:
        if Path(dir_path).exists():
            print(f"清理目录: {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)
    
    # PyInstaller命令参数
    pyinstaller_args = [
        'pyinstaller',
        '--onefile',                    # 打包成单个exe文件
        '--windowed',                   # 不显示控制台窗口
        '--icon=icon.ico',              # 设置图标
        '--name=LinkLike-LGP-Rank',     # 设置exe文件名
        '--add-data=account.json;.',    # 添加account.json到根目录
        '--add-data=icon.ico;.',        # 添加icon.ico到根目录
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=PyQt5.QtNetwork',
        '--hidden-import=requests',
        '--hidden-import=urllib3',
        '--clean',                      # 清理临时文件
        'gui.py'                        # 入口文件
    ]
    
    try:
        print("执行PyInstaller命令...")
        print(" ".join(pyinstaller_args))
        
        # 执行PyInstaller命令
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        
        print("PyInstaller执行成功!")
        print("标准输出:", result.stdout)
        
        # 检查生成的exe文件
        exe_path = Path('dist/LinkLike-LGP-Rank.exe')
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # 转换为MB
            print(f"✅ exe文件构建成功!")
            print(f"📁 文件位置: {exe_path.absolute()}")
            print(f"📊 文件大小: {file_size:.2f} MB")
            return True
        else:
            print("❌ exe文件未找到")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller执行失败: {e}")
        print("标准错误:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ 构建过程中发生错误: {e}")
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        print("PyInstaller已安装")
        return True
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
            print("PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"PyInstaller安装失败: {e}")
            return False

if __name__ == "__main__":
    print("=== LinkLike LGP Rank 项目打包工具 ===")
    
    # 检查并安装PyInstaller
    if not install_pyinstaller():
        sys.exit(1)
    
    # 构建exe
    if build_exe():
        print("\n🎉 构建完成! 可以在dist目录中找到exe文件")
    else:
        print("\n❌ 构建失败")
        sys.exit(1) 