#!/usr/bin/env python3
"""
Linkura版本号获取工具
从App Store和API获取最新版本信息
"""

import re
import json
import random
import string
import requests
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class VersionInfo:
    """版本信息数据类"""
    client_version: Optional[str] = None  # 客户端版本 (从App Store获取)
    res_version: Optional[str] = None     # 资源版本 (从API获取)


class LinkuraVersionChecker:
    """Linkura版本检查器"""
    
    # 常量定义
    API_BASE = "https://api.link-like-lovelive.app/v1"
    LINKURA_APP_STORE_URL = "https://apps.apple.com/jp/app/link-like-%E3%83%A9%E3%83%96%E3%83%A9%E3%82%A4%E3%83%96-%E8%93%AE%E3%83%8E%E7%A9%BA%E3%82%B9%E3%82%AF%E3%83%BC%E3%83%AB%E3%82%A2%E3%82%A4%E3%83%89%E3%83%AB%E3%82%AF%E3%83%A9%E3%83%96/id1665027261"
    WEB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    UA_PREFIX = "inspix-android"
    BASE_RES_VERSION = "R2504300"
    BASE_CLIENT_VERSION = "3.1.0"
    
    # API Header常量
    DEVICE_TYPE = "android"
    API_VERSION = "1.0.0"
    ACCEPT = "application/json"
    X_API_KEY = "4e769efa67d8f54be0b67e8f70ccb23d513a3c841191b6b2ba45ffc6fb498068"
    HOST = "api.link-like-lovelive.app"
    ACCEPT_ENCODING = "gzip, deflate"
    
    def __init__(self, timeout: int = 30):
        """
        初始化版本检查器
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.session = requests.Session()
        
    def generate_random_idempotency_key(self, length: int = 32) -> str:
        """
        生成随机的幂等性密钥
        
        Args:
            length: 密钥长度，默认32
            
        Returns:
            随机字符串
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def get_client_version_from_app_store(self) -> Optional[str]:
        """
        从App Store获取客户端版本号
        
        Returns:
            客户端版本号，如果获取失败返回None
        """
        try:
            print("正在从App Store获取版本信息...")
            
            headers = {
                "User-Agent": self.WEB_UA
            }
            
            response = self.session.get(
                self.LINKURA_APP_STORE_URL,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                print(f"App Store请求失败: HTTP {response.status_code}")
                return None
                
            html = response.text
            
            # 使用正则表达式提取版本号
            # 对应Rust中的: r#"\\"versionDisplay\\":\\"(\d+\.\d+\.\d+)\\""#
            pattern = r'\\"versionDisplay\\":\\"(\d+\.\d+\.\d+)\\"'
            match = re.search(pattern, html)
            
            if match:
                version = match.group(1)
                print(f"从App Store获取到客户端版本: {version}")
                return version
            else:
                print("未能从App Store页面解析出版本号")
                return None
                
        except requests.RequestException as e:
            print(f"访问App Store时发生网络错误: {e}")
            return None
        except Exception as e:
            print(f"获取App Store版本时发生错误: {e}")
            return None
    
    def get_res_version_from_api(self, client_version: Optional[str] = None) -> Optional[str]:
        """
        从API获取资源版本号
        
        Args:
            client_version: 客户端版本号，如果不提供则使用默认值
            
        Returns:
            资源版本号，如果获取失败返回None
        """
        try:
            print("正在从API获取资源版本信息...")
            
            # 使用提供的版本或默认版本
            version_to_use = client_version or self.BASE_CLIENT_VERSION
            
            # 构建请求URL
            url = f"{self.API_BASE}/user/login"
            
            # 构建请求头
            headers = {
                "x-res-version": self.BASE_RES_VERSION,
                "x-client-version": version_to_use,
                "x-device-type": self.DEVICE_TYPE,
                "inspix-user-api-version": self.API_VERSION,
                "Accept": self.ACCEPT,
                "x-api-key": self.X_API_KEY,
                "User-Agent": f"{self.UA_PREFIX}/{version_to_use}",
                "Host": self.HOST,
                "Accept-Encoding": self.ACCEPT_ENCODING,
                "Content-Type": "application/json",
                "x-idempotency-key": self.generate_random_idempotency_key()
            }
            
            # 构建请求体
            payload = {
                "player_id": "",
                "device_specific_id": "",
                "version": 1
            }
            
            # 发送POST请求
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                print(f"API请求失败: HTTP {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
            
            # 从响应头获取资源版本
            res_version_header = response.headers.get("x-res-version")
            if res_version_header:
                # 处理版本格式，去掉@后面的部分
                res_version = res_version_header.split('@')[0]
                print(f"从API获取到资源版本: {res_version}")
                return res_version
            else:
                print("API响应中未找到x-res-version头")
                return None
                
        except requests.RequestException as e:
            print(f"API请求时发生网络错误: {e}")
            return None
        except Exception as e:
            print(f"获取API资源版本时发生错误: {e}")
            return None
    
    def get_app_version(self) -> VersionInfo:
        """
        获取完整的应用版本信息
        
        Returns:
            包含客户端版本和资源版本的VersionInfo对象
        """
        print("开始获取Linkura应用版本信息...")
        print("=" * 50)
        
        # 获取客户端版本
        client_version = self.get_client_version_from_app_store()
        
        # 获取资源版本
        res_version = self.get_res_version_from_api(client_version)
        
        version_info = VersionInfo(
            client_version=client_version,
            res_version=res_version
        )
        
        print("=" * 50)
        print("版本信息获取完成:")
        print(f"  客户端版本: {version_info.client_version or '获取失败'}")
        print(f"  资源版本: {version_info.res_version or '获取失败'}")
        
        return version_info
    
    def save_version_to_file(self, version_info: VersionInfo, filename: str = "linkura_versions.json"):
        """
        将版本信息保存到JSON文件
        
        Args:
            version_info: 版本信息对象
            filename: 保存的文件名
        """
        try:
            data = {
                "client_version": version_info.client_version,
                "res_version": version_info.res_version,
                "base_client_version": self.BASE_CLIENT_VERSION,
                "base_res_version": self.BASE_RES_VERSION,
                "timestamp": requests.utils.default_headers()["User-Agent"]  # 简单的时间戳替代
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"版本信息已保存到: {filename}")
            
        except Exception as e:
            print(f"保存版本信息时发生错误: {e}")


def main():
    """主函数 - 命令行使用示例"""
    print("Linkura版本号检查工具")
    print("=" * 50)
    
    # 创建版本检查器
    checker = LinkuraVersionChecker()
    
    # 获取版本信息
    version_info = checker.get_app_version()
    
    # 保存到文件
    checker.save_version_to_file(version_info)
    
    # 显示使用建议
    if version_info.client_version and version_info.res_version:
        print("\n建议更新的配置:")
        print(f'BASE_CLIENT_VERSION = "{version_info.client_version}"')
        print(f'BASE_RES_VERSION = "{version_info.res_version}"')


if __name__ == "__main__":
    main()

