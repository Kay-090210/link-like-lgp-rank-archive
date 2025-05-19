import requests
import json
import re
import uuid
import os

# 使用临时配置进行注册
TEMP_DEVICE_ID = str(uuid.uuid4())

URL = "https://api.link-like-lovelive.app/v1/register/approve_terms"

# 基于固定请求头构建注册专用请求头
HEADERS = {
    "x-res-version": "R2504400",
    "x-client-version": "3.1.0",
    "x-device-specific-id": TEMP_DEVICE_ID,
    "x-device-type": "android",
    "x-idempotency-key": "c98f77c1cc4a47f4b88720283ca3392b",
    "inspix-user-api-version": "1.0.0",
    "x-api-key": "4e769efa67d8f54be0b67e8f70ccb23d513a3c841191b6b2ba45ffc6fb498068",
    "User-Agent": "inspix-android/3.0.10",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/json",
}

DATA = {"platform_type": 1}  # 1 = Android

def load_account_config():
    """从account.json加载账号配置"""
    try:
        account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'account.json')
        with open(account_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载account.json失败: {e}")
        # 返回默认配置
        return {
            "current_account": "新注册",
            "accounts": {
                "新注册": {
                    "device_id": TEMP_DEVICE_ID,
                    "player_id": ""
                }
            },
            "auth": {
                "token": "",
                "resource_version": "R2505100",
                "client_version": "3.1.0"
            }
        }

def save_account_config(account_config):
    """保存账号配置到account.json"""
    account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'account.json')
    with open(account_path, 'w', encoding='utf-8') as f:
        json.dump(account_config, f, indent=4)

def update_account_json(player_id, device_id, session_token):
    """更新account.json文件中的账号信息和Authorization"""
    # 加载当前配置
    account_config = load_account_config()
    
    # 更新"新注册"账号信息
    account_config["accounts"]["新注册"] = {
        "device_id": device_id,
        "player_id": player_id
    }
    
    # 设置当前账号为"新注册"
    account_config["current_account"] = "新注册"
    
    # 更新授权token
    account_config["auth"]["token"] = session_token
    
    # 保存更新后的配置
    save_account_config(account_config)
    
    print("已更新account.json中的账号信息和认证信息")
    return True

def register_account():
    resp = requests.post(URL, headers=HEADERS, json=DATA, timeout=15)
    print("\n=== Response Body ===")
    print(resp.text)
    
    # 解析响应
    try:
        data = json.loads(resp.text)
        if "player_id" in data and "device_specific_id" in data and "session_token" in data:
            player_id = data["player_id"]
            device_id = data["device_specific_id"]
            session_token = data["session_token"]
            
            # 更新account.json
            update_account_json(player_id, device_id, session_token)
        else:
            print("响应中缺少必要字段，无法更新account.json")
    except json.JSONDecodeError:
        print("响应不是有效的JSON格式，无法解析")
    except Exception as e:
        print(f"处理出错: {e}")

if __name__ == "__main__":
    register_account()
