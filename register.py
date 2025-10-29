import json
import os
import re
import shutil
import sys
import uuid

import requests

try:
    from config import DEFAULT_CLIENT_VERSION
except Exception:
    # 独立运行时无法导入 config 的兜底处理
    DEFAULT_CLIENT_VERSION = "4.8.0"

# 默认资源版本号，用于首次启动构造注册请求
DEFAULT_RESOURCE_VERSION = "R2510300"

# 注册接口地址
URL = "https://api.link-like-lovelive.app/v1/register/approve_terms"

# 临时生成的设备ID（注册后会被正式值覆盖）
TEMP_DEVICE_ID = str(uuid.uuid4())

# 应用运行目录（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLED_DIR = getattr(sys, '_MEIPASS', APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLED_DIR = APP_DIR


def get_account_path(for_write: bool = False) -> str:
    """获取 account.json 的实际读写路径"""
    account_path = os.path.join(APP_DIR, 'account.json')

    if not for_write and not os.path.exists(account_path):
        bundled_account = os.path.join(BUNDLED_DIR, 'account.json')
        if os.path.exists(bundled_account):
            os.makedirs(APP_DIR, exist_ok=True)
            shutil.copyfile(bundled_account, account_path)

    if for_write:
        os.makedirs(APP_DIR, exist_ok=True)

    return account_path


def load_account_config() -> dict:
    """加载账号配置，失败时返回默认结构"""
    account_path = get_account_path()
    try:
        with open(account_path, 'r', encoding='utf-8') as fp:
            return json.load(fp)
    except Exception as exc:
        print(f"加载account.json失败: {exc}")
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
                "resource_version": DEFAULT_RESOURCE_VERSION,
                "client_version": DEFAULT_CLIENT_VERSION
            }
        }


def save_account_config(account_config: dict) -> None:
    """将账号配置写回 account.json"""
    account_path = get_account_path(for_write=True)
    with open(account_path, 'w', encoding='utf-8') as fp:
        json.dump(account_config, fp, indent=4, ensure_ascii=False)
    print(f"已写入账号配置: {account_path}")


def sanitize_version(raw_version: str, fallback: str) -> str:
    """提取版本号主体，不合法时使用默认值"""
    if not raw_version:
        return fallback
    match = re.match(r'([A-Za-z0-9._-]+)', raw_version)
    return match.group(1) if match else fallback


# 初始化配置并提取版本信息
account_config = load_account_config()
RESOURCE_VERSION = sanitize_version(
    account_config.get("auth", {}).get("resource_version"),
    DEFAULT_RESOURCE_VERSION
)
CLIENT_VERSION = sanitize_version(
    account_config.get("auth", {}).get("client_version"),
    DEFAULT_CLIENT_VERSION
)

# 注册请求固定请求头
HEADERS = {
    "x-res-version": RESOURCE_VERSION,
    "x-client-version": CLIENT_VERSION,
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

# Android 平台标识
DATA = {"platform_type": 1}


def update_account_json(player_id: str, device_id: str, session_token: str) -> bool:
    """更新 account.json 中的账号标识与认证信息"""
    account_config = load_account_config()

    account_config.setdefault("accounts", {})
    account_config["accounts"]["新注册"] = {
        "device_id": device_id,
        "player_id": player_id
    }
    account_config["current_account"] = "新注册"

    account_config.setdefault("auth", {})
    account_config["auth"]["token"] = session_token
    account_config["auth"]["resource_version"] = RESOURCE_VERSION
    account_config["auth"]["client_version"] = CLIENT_VERSION

    save_account_config(account_config)
    print("已更新account.json中的账号信息和认证信息")
    return True


def register_account() -> None:
    """调用官方注册接口获取新的账号凭据"""
    response = requests.post(URL, headers=HEADERS, json=DATA, timeout=15)
    print("\n=== Response Body ===")
    print(response.text)

    try:
        data = response.json()
    except ValueError:
        print("响应不是有效的JSON格式，无法解析")
        return

    player_id = data.get("player_id")
    device_id = data.get("device_specific_id")
    session_token = data.get("session_token")

    if player_id and device_id and session_token:
        update_account_json(player_id, device_id, session_token)
    else:
        print("响应中缺少必要字段，无法更新account.json")


if __name__ == "__main__":
    register_account()
