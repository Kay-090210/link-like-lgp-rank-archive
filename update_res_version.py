#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源版本更新模块

用于获取最新的游戏资源版本号并更新配置文件：
1. 通过登录API获取最新的资源版本号
2. 更新account.json文件中的resource_version
"""

import re
import os
import json
from utils import get_resource_version, log_progress

def update_account_res_version(new_version: str) -> None:
    """
    更新account.json文件中的resource_version值
    
    Args:
        new_version: 新的资源版本号
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    account_path = os.path.join(current_dir, 'account.json')
    
    # 读取account.json文件
    try:
        with open(account_path, 'r', encoding='utf-8') as file:
            account_data = json.load(file)
        
        # 更新resource_version
        account_data["auth"]["resource_version"] = new_version
        
        # 保存更新后的数据
        with open(account_path, 'w', encoding='utf-8') as file:
            json.dump(account_data, file, indent=4)
        
        log_progress(f"已成功更新account.json中的资源版本号至: {new_version}")
    except Exception as e:
        log_progress(f"更新account.json失败: {str(e)}")

def main():
    """主函数"""
    log_progress("开始获取最新资源版本号...")
    try:
        # 获取最新的资源版本号
        new_version = get_resource_version()
        log_progress(f"获取到最新版本号: {new_version}")
        
        # 更新account.json文件
        update_account_res_version(new_version)
        
        # 兼容性考虑：仍然更新config.py
        try:
            from update_config_res_version import update_config_res_version
            update_config_res_version(new_version)
        except ImportError:
            log_progress("未找到config.py更新函数，只更新了account.json")
        
        log_progress("版本号更新完成！")
    except Exception as e:
        log_progress(f"更新失败: {str(e)}")

if __name__ == "__main__":
    main() 