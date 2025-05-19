"""
登录模块

处理游戏登录相关功能：
1. 执行登录请求
2. 获取session token
3. 更新Authorization信息
4. 更新资源版本号
5. 获取当前token
"""
from config import BASE_URL, HEADERS, LOGIN_CONFIG, ACCOUNT_CONFIG, CURRENT_ACCOUNT, load_account_config, save_account_config
from utils import retry_request, get_resource_version, log_progress
import requests
import re
import os
import importlib.util
import subprocess
import sys

@retry_request
def login(player_id: str, device_id: str) -> dict:
    """登录请求"""
    url = f"{BASE_URL}/user/login"
    payload = {
        "player_id": player_id,
        "device_specific_id": device_id,
        "version": 1
    }
    
    # 创建不带 Authorization 的请求头
    headers = HEADERS.copy()
    headers.pop('Authorization', None)
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        # 从响应头中获取资源版本号
        raw_version = response.headers.get("x-res-version", "")
        if raw_version:
            # 提取纯版本号
            res_version = raw_version.split("@", 1)[0]
            # 更新HEADERS中的版本号
            HEADERS["x-res-version"] = res_version
            # 更新account.json中的版本号
            update_res_version(res_version)
            log_progress(f"资源版本号已更新至: {res_version}")
            
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况

def update_auth_token(session_token: str) -> None:
    """更新account.json文件中的Authorization token"""
    # 加载当前配置
    account_config = load_account_config()
    
    # 更新授权token
    account_config["auth"]["token"] = session_token
    
    # 保存更新后的配置
    save_account_config(account_config)
    
    # 更新内存中的HEADERS
    HEADERS['Authorization'] = f"Bearer {session_token}"
    
    log_progress("Authorization token已更新到account.json")

def update_res_version(res_version: str) -> None:
    """更新account.json文件中的资源版本号"""
    # 加载当前配置
    account_config = load_account_config()
    
    # 更新资源版本号
    account_config["auth"]["resource_version"] = res_version
    
    # 保存更新后的配置
    save_account_config(account_config)
    
    log_progress("资源版本号已更新到account.json")

def update_latest_resource_version():
    """获取并更新最新的资源版本号"""
    try:
        # 使用utils中的函数获取最新版本号
        new_version = get_resource_version()
        # 更新配置文件
        update_res_version(new_version)
        log_progress(f"资源版本号已单独更新至: {new_version}")
        return True
    except Exception as e:
        log_progress(f"资源版本号更新失败: {str(e)}")
        return False

def check_and_run_register():
    """检查是否需要运行register.py"""
    # 加载当前账号配置
    account_config = load_account_config()
    current_account = account_config["current_account"]
    accounts = account_config["accounts"]
    
    # 检查当前账号是否为"新注册"并且存在于accounts中
    # 且player_id不为空
    if (current_account == "新注册" and "新注册" in accounts and 
        accounts["新注册"].get("player_id")):
        return True  # 已存在"新注册"账号，不需要注册
    
    log_progress("未找到有效的'新注册'账号配置，将执行注册程序...")
    
    try:
        from register import register_account
        register_account()
        log_progress("注册程序执行完成")
        # 重新加载config模块以获取更新后的配置
        import importlib
        import config
        importlib.reload(config)
        return True
    except Exception as e:
        log_progress(f"注册程序执行失败: {e}")
        return False

def get_current_token() -> str:
    """获取当前的Authorization token
    
    Returns:
        str: 当前的Authorization token，格式为'Bearer xxx'
        如果token不存在，返回None
    """
    try:
        # 加载当前配置
        account_config = load_account_config()
        
        # 获取token
        token = account_config.get("auth", {}).get("token")
        
        if token:
            return f"Bearer {token}"
        else:
            log_progress("警告：未找到有效的Authorization token")
            return None
    except Exception as e:
        log_progress(f"获取token时发生错误: {e}")
        return None

def main():
    """登录并更新认证Token和资源版本号"""
    # 检查并在必要时运行register.py
    if not check_and_run_register():
        log_progress("由于注册失败，登录过程终止")
        return
    
    # 重新加载最新的配置
    account_config = load_account_config()
    current_account = account_config["current_account"]
    accounts = account_config["accounts"]
    
    if current_account not in accounts:
        log_progress(f"错误：当前指定的账号 '{current_account}' 不存在于配置中")
        return
    
    account_info = accounts[current_account]
    player_id = account_info.get("player_id", "")
    device_id = account_info.get("device_id", "")
    
    if not player_id or not device_id:
        log_progress("错误：玩家ID或设备ID为空")
        return
    
    result = login(player_id, device_id)
    if isinstance(result, dict) and "session_token" in result:
        session_token = result.get("session_token")
        log_progress("登录成功！")
        log_progress(f"Session Token: {session_token}")
        # 更新 Authorization
        update_auth_token(session_token)
        log_progress("Authorization token 已更新")
    else:
        log_progress("登录失败")
        # 尝试单独更新资源版本号
        update_latest_resource_version()

if __name__ == "__main__":
    main()
