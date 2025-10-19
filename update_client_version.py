#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
客户端版本更新模块

用于获取最新的游戏客户端版本号并更新配置文件：
1. 通过App Store获取最新的客户端版本号
2. 更新account.json文件中的client_version
"""

import re
import os
import json
from utils import get_client_version, log_progress

def update_account_client_version(new_version: str) -> None:
    """
    更新account.json文件中的client_version值
    
    Args:
        new_version: 新的客户端版本号
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    account_path = os.path.join(current_dir, 'account.json')
    
    # 读取account.json文件
    try:
        with open(account_path, 'r', encoding='utf-8') as file:
            account_data = json.load(file)
        
        # 更新client_version
        account_data["auth"]["client_version"] = new_version
        
        # 保存更新后的数据
        with open(account_path, 'w', encoding='utf-8') as file:
            json.dump(account_data, file, indent=4)
        
        log_progress(f"已成功更新account.json中的客户端版本号至: {new_version}")
    except Exception as e:
        log_progress(f"更新account.json失败: {str(e)}")

def update_config_client_version(new_version: str) -> None:
    """
    更新config.py文件中的x-client-version值（兼容性保留）
    
    Args:
        new_version: 新的客户端版本号
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.py')
    
    # 确保config.py存在
    if not os.path.exists(config_path):
        log_progress(f"config.py不存在，跳过更新")
        return
    
    try:
        # 更新配置文件
        with open(config_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 使用正则表达式替换x-client-version值
        pattern = r'("x-client-version":\s*)"[^"]*"'
        new_content = re.sub(pattern, f'\\1"{new_version}"', content)
        
        # 同时更新DEFAULT_CLIENT_VERSION
        pattern_default = r'(DEFAULT_CLIENT_VERSION\s*=\s*)"[^"]*"'
        new_content = re.sub(pattern_default, f'\\1"{new_version}"', new_content)
        
        with open(config_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        
        log_progress(f"已成功更新config.py中的客户端版本号至: {new_version}")
    except Exception as e:
        log_progress(f"更新config.py失败: {str(e)}")

def main():
    """主函数"""
    log_progress("开始获取最新客户端版本号...")
    try:
        # 获取最新的客户端版本号
        new_version = get_client_version()
        log_progress(f"获取到最新版本号: {new_version}")
        
        # 更新account.json文件
        update_account_client_version(new_version)
        
        # 兼容性考虑：同时更新config.py
        try:
            update_config_client_version(new_version)
        except Exception as e:
            log_progress(f"更新config.py时发生错误: {str(e)}")
        
        log_progress("客户端版本号更新完成！")
    except Exception as e:
        log_progress(f"更新失败: {str(e)}")

if __name__ == "__main__":
    main()
