"""
工具函数模块

提供项目中使用的通用工具函数：
1. 请求重试装饰器
2. 玩家信息获取
3. 花瓣兑换信息获取
4. 日志记录
5. 资源版本获取
"""

import requests
from datetime import datetime
from typing import Dict, Any, Optional
import time
import uuid
from config import HEADERS, PROFILE_URL, CHARACTER_NAMES, BASE_URL, LOGIN_CONFIG, DEVICE_ID



def retry_request(func, max_retries=3, initial_delay=1):
    """
    重试装饰器，使用指数退避机制
    :param func: 要重试的函数
    :param max_retries: 最大重试次数
    :param initial_delay: 初始重试间隔（秒）
    """
    def wrapper(*args, **kwargs):
        last_error = None
        last_response = None
        retries = 0
        while retries < max_retries:
            try:
                response = func(*args, **kwargs)
                # 如果返回的是 Response 对象
                if isinstance(response, requests.Response):
                    # 无论状态码如何，先尝试解析响应内容
                    try:
                        response_json = response.json()
                        # 检查是否返回了错误代码21001_210102（非比赛期间），无论状态码是什么
                        if isinstance(response_json, dict) and response_json.get("error_code") == "21001_210102":
                            error_msg = response_json.get("message", "未知错误")
                            print(f"检测到关键错误: {error_msg}")
                            print("检测到非比赛期间，停止脚本执行")
                            import sys
                            sys.exit(1)  # 直接终止程序
                    except Exception as e:
                        # 如果不能解析JSON，继续处理
                        pass
                        
                    if response.status_code == 200:
                        response_json = response.json()
                        # 检查是否返回了其他错误代码，如果是，直接返回该错误信息
                        if isinstance(response_json, dict) and "error_code" in response_json:
                            print(f"API返回错误: {response_json.get('message', '未知错误')}")
                            # 直接返回错误信息，让调用方处理
                            return response_json
                        return response_json
                    print(f"请求失败，状态码：{response.status_code}")
                    print(f"响应内容：{response.text}")
                    
                    # 检查失败响应中是否包含非比赛期间错误
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict) and error_data.get("error_code") == "21001_210102":
                            error_msg = error_data.get("message", "未知错误")
                            print(f"检测到关键错误: {error_msg}")
                            print("检测到非比赛期间，停止脚本执行")
                            import sys
                            sys.exit(1)  # 直接终止程序
                    except:
                        # 忽略解析错误
                        pass
                        
                    last_response = response.text
                    raise requests.exceptions.RequestException(f"状态码: {response.status_code}")
                # 如果返回的是其他内容
                if response is not None:
                    return response
                raise Exception("Empty response")
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                # 如果之前没有保存过响应内容，尝试从异常中获取
                if not last_response and hasattr(e, 'response'):
                    last_response = e.response.text if hasattr(e.response, 'text') else None
                    
                    # 检查错误响应是否包含非比赛期间错误
                    if last_response:
                        try:
                            import json
                            error_data = json.loads(last_response)
                            if isinstance(error_data, dict) and error_data.get("error_code") == "21001_210102":
                                error_msg = error_data.get("message", "未知错误")
                                print(f"检测到关键错误: {error_msg}")
                                print("检测到非比赛期间，停止脚本执行")
                                import sys
                                sys.exit(1)  # 直接终止程序
                        except:
                            # 忽略解析错误
                            pass
                
                retries += 1
                if retries == max_retries:
                    print(f"最终失败: {last_error}")
                    if last_response:
                        print(f"最后的响应内容: {last_response}")
                        
                        # 最后一次检查错误响应是否包含非比赛期间错误
                        try:
                            import json
                            error_data = json.loads(last_response)
                            if isinstance(error_data, dict) and error_data.get("error_code") == "21001_210102":
                                error_msg = error_data.get("message", "未知错误")
                                print(f"检测到关键错误: {error_msg}")
                                print("检测到非比赛期间，停止脚本执行")
                                import sys
                                sys.exit(1)  # 直接终止程序
                        except:
                            # 忽略解析错误
                            pass
                            
                    return None
                # 使用指数退避计算等待时间：2^重试次数 * 初始延迟
                wait_time = initial_delay * (2 ** (retries - 1))
                print(f"第 {retries} 次尝试失败: {last_error}, {wait_time} 秒后重试...")
                time.sleep(wait_time)
            except Exception as e:
                last_error = str(e)
                retries += 1
                if retries == max_retries:
                    print(f"最终失败: {last_error}")
                    return None
                wait_time = initial_delay * (2 ** (retries - 1))
                print(f"第 {retries} 次尝试失败: {last_error}, {wait_time} 秒后重试...")
                time.sleep(wait_time)
        return None
    return wrapper

@retry_request
def get_player_profile(player_id: str, headers: Dict[str, str], profile_url: str) -> Optional[Dict[str, Any]]:
    """获取玩家档案信息"""
    response = requests.post(
        profile_url, 
        headers=headers, 
        json={"player_id": player_id}
    )
    if response.status_code == 200:
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况

@retry_request
def get_petal_exchange_info(headers: Dict[str, str], petal_exchange_url: str) -> Optional[Dict[str, Any]]:
    """获取花瓣兑换信息"""
    response = requests.post(
        petal_exchange_url, 
        headers=headers, 
    )
    if response.status_code == 200: 
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况

@retry_request
def get_fanlv(headers: Dict[str, str], fanlv_url: str, player_id: str) -> Optional[Dict[str, Any]]:
    """获取粉丝等级信息"""
    response = requests.post(
        fanlv_url, 
        headers=headers, 
        json={"player_id": player_id}
        
    )
    if response.status_code == 200: 
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况

def get_ranking(headers: Dict[str, str], ranking_url: str) -> Optional[Dict[str, Any]]:
    """获取排行榜数据,测试用,实际使用需要的函数硬编码到了multicatch.py中"""
    response = requests.post(
        ranking_url, 
        headers=headers, 
        json = {
            "grand_prix_id": 704109,
            "ranking_type": 1,#1公会榜,2个人榜,3会内榜
            "get_rank_type": 2,
            "target_rank": 1,
        }
    )
    if response.status_code == 200: 
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况 

def get_grade_ranking(headers: Dict[str, str], grade_ranking_url: str) -> Optional[Dict[str, Any]]:
    """获取赛季等级排名数据"""
    response = requests.post(
        grade_ranking_url,
        headers=headers,
        json = {
            "season_grade_id": 1005004,
            "get_rank_type": 0,
            "target_rank": 1,
        }
    )
    if response.status_code == 200:
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况

@retry_request
def get_circle_history(headers: Dict[str, str], circle_history_url: str, grand_prix_id: int) -> Optional[Dict[str, Any]]:
    """获取出刀历史"""
    response = requests.post(
        circle_history_url, 
        headers=headers, 
        json={"grand_prix_id": grand_prix_id,
             }
    )
    if response.status_code == 200: 
        return response.json()
    return response  # 直接返回 response 对象，让装饰器处理错误情况 

def log_progress(message: str):
    """记录进度信息"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{message} - 时间: {current_time}") 

def fetch_player_profile(player_info: dict, include_last_login: bool = False, headers: Dict[str, str] = None) -> dict:
    """
    统一的玩家信息获取函数
    
    Args:
        player_info: 包含player_id的字典，或直接的player_id字符串
        include_last_login: 是否包含最后登录时间
        headers: 自定义请求头，默认使用全局HEADERS
    
    Returns:
        dict: 处理后的玩家数据
    """
    player_id = player_info["player_id"] if isinstance(player_info, dict) else player_info
    # 使用传入的headers或全局HEADERS
    headers_to_use = headers if headers is not None else HEADERS
    result = get_player_profile(player_id, headers_to_use, PROFILE_URL)
    
    # 检查是否有错误信息
    if isinstance(result, dict) and "error_code" in result:
        # 直接返回错误信息，让调用方处理
        return result
    
    if result:
        profile_data = result.get('profile_info', {})
        fan_level_list = profile_data.get('fan_level_list', [])
        
        # 创建基础数据字典
        player_data = {
            "player_id": player_id,
            "player_name": profile_data.get("player_name", ""),
            "search_guild_key": profile_data.get("search_guild_key", ""),
            "guild_name": profile_data.get("guild_name", ""),
            "DR数量": profile_data.get("dream_style_num", 0)
        }
        
        # 如果是从排行榜获取的数据，添加排名和分数
        if isinstance(player_info, dict):
            player_data.update({
                "rank": player_info.get("rank", ""),
                "point": player_info.get("point", 0)
            })
            
        # 根据参数决定是否包含最后登录时间
        if include_last_login:
            player_data["最后登录时间"] = profile_data.get("last_login_date", "")
        
        # 创建一个字典存储每个角色的粉丝等级
        character_levels = {character_id: 0 for character_id in CHARACTER_NAMES}
        
        # 更新角色的粉丝等级
        for fan_info in fan_level_list:
            character_id = fan_info.get('character_id')
            d_season_level = fan_info.get('d_season_fan_level', 0)
            if character_id in character_levels:
                character_levels[character_id] = d_season_level
        
        # 计算季度等级总和
        total_level = sum(character_levels.values())
        
        # 计算104季度等级总和（排除泉和塞拉斯）
        total_104_level = sum(level for char_id, level in character_levels.items() if char_id not in [1051, 1052])
        
        # 按照CHARACTER_NAMES的顺序添加角色信息
        for character_id, character_name in CHARACTER_NAMES.items():
            player_data[f"{character_name}"] = character_levels[character_id]
            
        # 添加总和列
        player_data["季度等级"] = total_level
        player_data["104季度等级"] = total_104_level
        
        return player_data
    return None

@retry_request
def get_resource_version(prev_res_version=None, client_version=None):
    """
    通过登录API获取最新的资源版本号
    
    Args:
        prev_res_version: 上一个已知的资源版本号，默认使用config中的HEADERS值
        client_version: 客户端版本号，默认使用config中的HEADERS值
    
    Returns:
        str: 提取出的纯版本号
    """
    url = f"{BASE_URL}/user/login"
    
    # 使用传入的版本号或从HEADERS获取默认值
    if prev_res_version is None:
        prev_res_version = HEADERS.get("x-res-version", "").split("@")[0]
    
    if client_version is None:
        client_version = HEADERS.get("x-client-version", "")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Host": "api.link-like-lovelive.app",
        "Accept-Encoding": "gzip, deflate",
        "x-res-version": prev_res_version,
        "x-client-version": client_version,
        "x-device-type": "android",
        "x-idempotency-key": str(uuid.uuid4()),
        "inspix-user-api-version": "1.0.0",
        "x-api-key": HEADERS.get("x-api-key", ""),
        "User-Agent": f"inspix-android/{client_version}",
    }
    
    payload = {
        "player_id": LOGIN_CONFIG.get('player_id', ""),
        "device_specific_id": DEVICE_ID,
        "version": 1
    }

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise RuntimeError(f"登录失败: {response.status_code}, 响应内容: {response.text}")
    
    raw_version = response.headers.get("x-res-version", "")
    if not raw_version:
        raise RuntimeError("响应头中未找到 x-res-version")
    
    # 拆掉签名部分，只取 @ 前的纯版本号
    version = raw_version.split("@", 1)[0]
    
    return version