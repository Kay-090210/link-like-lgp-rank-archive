#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件资源版本更新模块（兼容性保留）

用于更新config.py文件中的资源版本号，
此模块是为了保持与旧版代码的兼容性而保留
"""

import re
import os
from utils import log_progress

def update_config_res_version(new_version: str) -> None:
    """
    更新config.py文件中的x-res-version值
    
    Args:
        new_version: 新的资源版本号
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.py')
    
    # 确保config.py存在
    if not os.path.exists(config_path):
        log_progress(f"config.py不存在，跳过更新")
        return
    
    # 更新配置文件
    with open(config_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 使用正则表达式替换x-res-version值
    pattern = r'("x-res-version":\s*)"[^"]*"'
    new_content = re.sub(pattern, f'\\1"{new_version}"', content)
    
    with open(config_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    log_progress(f"已成功更新config.py中的资源版本号至: {new_version}")

if __name__ == "__main__":
    # 单独运行此模块时给出警告
    print("警告：此模块仅用于兼容性目的，请直接运行update_res_version.py来更新资源版本号") 