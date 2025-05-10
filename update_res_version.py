#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源版本更新模块

用于获取最新的游戏资源版本号并更新配置文件：
1. 通过登录API获取最新的资源版本号
2. 更新config.py文件中的x-res-version
"""

import re
import os
from utils import get_resource_version, log_progress

def update_config_res_version(new_version: str) -> None:
    """
    更新config.py文件中的x-res-version值
    
    Args:
        new_version: 新的资源版本号
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.py')
    
    # 更新配置文件
    with open(config_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 使用正则表达式替换x-res-version值
    pattern = r'("x-res-version":\s*)"[^"]*"'
    new_content = re.sub(pattern, f'\\1"{new_version}"', content)
    
    with open(config_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    log_progress(f"已成功更新资源版本号至: {new_version}")

def main():
    """主函数"""
    log_progress("开始获取最新资源版本号...")
    try:
        # 获取最新的资源版本号
        new_version = get_resource_version()
        log_progress(f"获取到最新版本号: {new_version}")
        
        # 更新配置文件
        update_config_res_version(new_version)
        log_progress("版本号更新完成！")
    except Exception as e:
        log_progress(f"更新失败: {str(e)}")

if __name__ == "__main__":
    main() 