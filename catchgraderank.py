"""
赛季等级排名数据采集模块

用于批量获取赛季等级排名数据和玩家详细信息：
1. 获取指定范围的赛季等级排名数据
2. 获取每个玩家的详细信息
3. 保存数据到Excel文件
"""
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from config import (
    HEADERS, GRADE_RANKING_URL, PROFILE_URL, SAVE_PATH, 
    FILE_NAMES, target_ranks, CHARACTER_NAMES, SEASON_GRADE_ID
)
from utils import log_progress, retry_request, fetch_player_profile
import requests
import os
import importlib.util
import sys
import importlib

# 添加login模块导入
try:
    from login import main as login_main, get_current_token
except ImportError:
    # 如果直接导入失败，则尝试使用importlib动态导入
    pass

class GradeRankingDataCollector:
    def __init__(self, season_grade_id=SEASON_GRADE_ID):
        self.lock = Lock()
        self.completed_count_step1 = 0
        self.completed_count_step2 = 0
        self.target_ranks = target_ranks
        self.stop_rank = float('inf')  # 记录获取到空列表的排名
        self.season_grade_id = season_grade_id
        # 添加一个集合用于跟踪已处理的玩家ID
        self.processed_player_ids = set()
        # 保存headers的副本，用于请求
        self.headers = HEADERS.copy()
    
    def perform_login(self):
        """执行登录并获取新token"""
        login_successful = False
        token = None
        
        # 方法1: 直接导入login模块
        if 'login_main' in globals():
            try:
                print("正在执行登录...")
                login_main()
                login_successful = True
                # 登录成功后获取token
                try:
                    token = get_current_token()
                except Exception as e:
                    print(f"获取token失败: {e}")
            except Exception as e:
                print(f"直接导入登录执行失败: {e}")
        
        # 方法2: 尝试找到login.py的确切路径
        if not login_successful:
            possible_paths = [
                "login.py",
                "リンクラ工具箱/login.py",
                "../login.py",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.py"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "リンクラ工具箱", "login.py")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        print(f"尝试从路径 {path} 导入login模块...")
                        spec = importlib.util.spec_from_file_location("login", path)
                        if spec:
                            login_module = importlib.util.module_from_spec(spec)
                            sys.modules["login"] = login_module
                            spec.loader.exec_module(login_module)
                            if hasattr(login_module, 'main'):
                                login_module.main()
                                login_successful = True
                                # 尝试获取token
                                if hasattr(login_module, 'get_current_token'):
                                    token = login_module.get_current_token()
                                else:
                                    print("警告: login模块中没有get_current_token函数")
                                break
                            else:
                                print(f"警告: {path}中未找到main函数")
                    except Exception as e:
                        print(f"从{path}导入执行login失败: {e}")
        
        # 方法3: 使用subprocess执行
        if not login_successful:
            print("尝试使用subprocess执行login.py...")
            import subprocess
            try:
                # 尝试不同路径
                for path in possible_paths:
                    if os.path.exists(path):
                        print(f"尝试执行: {path}")
                        subprocess.run([sys.executable, path], check=True)
                        login_successful = True
                        # 登录成功后尝试重新导入config获取新token
                        break
            except subprocess.SubprocessError as e:
                print(f"执行login.py失败: {e}")
        
        # 登录成功后，刷新token
        if login_successful:
            # 重新导入config模块获取最新的HEADERS
            try:
                if 'config' in sys.modules:
                    importlib.reload(sys.modules['config'])
                    from config import HEADERS as NEW_HEADERS
                    # 更新实例的headers
                    self.headers = NEW_HEADERS.copy()
                    print("已从config模块更新headers")
                
                # 如果获取到token，直接更新headers
                if token:
                    self.headers["Authorization"] = token
                    print(f"已直接更新Authorization令牌: {token[:10]}...")
                
                # 也可以尝试再次获取token
                try:
                    token = get_current_token()
                    self.headers["Authorization"] = token
                    print(f"最终使用的Authorization令牌: {token[:10]}...")
                except Exception as e:
                    print(f"再次获取token时出错: {e}")
            except Exception as e:
                print(f"更新headers时出错: {e}")
        
        # 返回登录是否成功
        return login_successful
    
    @retry_request
    def fetch_grade_ranking(self, target_rank: int, idx: int, total: int) -> list:
        """获取赛季等级排名数据"""
        # 检查当前请求的排名是否超过停止排名
        if target_rank > self.stop_rank:
            return []
            
        ranking_payload = {
            "season_grade_id": self.season_grade_id.get('current'),
            "get_rank_type": 0,
            "target_rank": target_rank
        }
        # 使用实例的headers而不是全局HEADERS
        response = requests.post(GRADE_RANKING_URL, headers=self.headers, json=ranking_payload)
        if response.status_code == 200:
            ranking_data = response.json()
            
            # 检查是否返回错误代码21001_210102（非比赛期间）
            if isinstance(ranking_data, dict) and ranking_data.get("error_code") == "21001_210102":
                error_msg = ranking_data.get("message", "未知错误")
                print(f"错误: {error_msg}")
                print("检测到非比赛期间，停止脚本执行")
                sys.exit(1)
                
            player_list = ranking_data.get("point_rankings", [])
            
            # 如果获取到空列表，更新停止排名
            if not player_list:
                with self.lock:
                    if target_rank < self.stop_rank:  # 确保记录最小的空列表排名
                        self.stop_rank = target_rank
                        log_progress(f"在 rank {target_rank} 处获取到空列表，将停止获取更高排名")
            
            with self.lock:
                self.completed_count_step1 += 1
                log_progress(f"获取赛季等级 target_rank {target_rank} 的数据成功 ({self.completed_count_step1}/{total})")
            return player_list
        return response  # 返回response对象让装饰器处理

    def fetch_profile(self, player_info: dict, idx: int, total: int) -> dict:
        """获取玩家详细信息"""
        # 传递实例的headers给fetch_player_profile函数
        result = fetch_player_profile(player_info, headers=self.headers)
        
        # 检查返回值是否包含错误代码
        if isinstance(result, dict) and result.get("error_code") == "21001_210102":
            error_msg = result.get("message", "未知错误")
            print(f"错误: {error_msg}")
            print("检测到非比赛期间，停止脚本执行")
            sys.exit(1)
            
        if result:
            with self.lock:
                self.completed_count_step2 += 1
                log_progress(f"请求 player_id {player_info['player_id']} 的信息成功 ({self.completed_count_step2}/{total})")
            return result
        return None

    def collect_data(self):
        # 先执行登录
        login_success = self.perform_login()
        if not login_success:
            print("警告：登录过程可能未完成，请先运行login.py再执行此脚本")
            if input("是否继续执行(y/n)? ").lower() != 'y':
                print("退出脚本")
                return
        
        # 登录后，先发送一个测试请求检查是否在赛季期间
        print("检查当前是否在赛季期间...")
        try:
            test_result = self.fetch_grade_ranking(1, 0, 1)  # 尝试获取赛季等级排名第一名数据
            if not test_result:
                print("警告: 测试请求未返回数据，可能不在赛季期间，停止脚本执行")
                print("退出脚本")
                return
            else:
                print("检查通过，当前在赛季期间，继续执行...")
        except Exception as e:
            print(f"测试请求失败: {e}")
            print("请检查是否已正确登录，如果未登录，请先运行login.py")
            if input("是否继续执行(y/n)? ").lower() != 'y':
                print("退出脚本")
                return
                
        # 第一步：获取排行榜基本信息
        players_basic_info = []
        # 创建一个集合来存储唯一的玩家ID
        unique_player_ids = set()
        
        with ThreadPoolExecutor(max_workers=100) as executor:
            # 按照排名顺序提交任务
            sorted_ranks = sorted(self.target_ranks)
            futures = {
                executor.submit(self.fetch_grade_ranking, rank, idx, len(sorted_ranks)): rank
                for idx, rank in enumerate(sorted_ranks, start=1)
            }
            
            for future in as_completed(futures):
                rank = futures[future]
                if rank > self.stop_rank:
                    # 取消所有更高排名的未完成任务
                    for f, r in futures.items():
                        if not f.done() and r > self.stop_rank:
                            f.cancel()
                    continue
                
                result = future.result()
                if result:
                    for player in result:
                        player_id = player.get("player_id", "")
                        # 检查这个玩家ID是否已经处理过
                        if player_id and player_id not in unique_player_ids:
                            unique_player_ids.add(player_id)
                            players_basic_info.append({
                                "player_id": player_id,
                                "rank": player.get("rank", ""),
                                "point": player.get("point", 0),
                                # "character_id": player.get("character_id", 0),
                                # "character_name": CHARACTER_NAMES.get(player.get("character_id", 0), f"未知_{player.get('character_id', 0)}")
                            })

        # 保存第一步的数据
        df1 = pd.DataFrame(players_basic_info)
        
        # 按照rank列升序排序
        df1 = df1.sort_values(by='rank', ascending=True)
        
        # 只在有数据时才创建文件夹和保存文件
        if not df1.empty:
            # 确保保存目录存在
            if not os.path.exists(SAVE_PATH):
                os.makedirs(SAVE_PATH)
                
            cache_file = os.path.join(SAVE_PATH, "赛季等级排名_基础数据.xlsx")
            df1.to_excel(cache_file, index=False)
            print(f"赛季等级排名基础数据已保存至 {cache_file}，共 {len(players_basic_info)} 名玩家")
        else:
            print("未获取到任何赛季等级排名数据，跳过创建文件夹和保存文件")
            return

        # 第二步：获取详细信息
        data_list = []
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {
                executor.submit(self.fetch_profile, player, idx, len(players_basic_info)): player
                for idx, player in enumerate(players_basic_info, start=1)
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    # 合并基础数据中的特定信息到详细信息中
                    player_id = result["player_id"]
                    matching_players = [p for p in players_basic_info if p["player_id"] == player_id]
                    if matching_players:
                        basic_info = matching_players[0]
                        result["grade"] = basic_info.get("grade", 0)
                        result["character_id"] = basic_info.get("character_id", 0)
                        result["character_name"] = basic_info.get("character_name", "")
                    data_list.append(result)

        # 保存最终数据
        df = pd.DataFrame(data_list)
        
        # 按照rank列升序排序
        df = df.sort_values(by='rank', ascending=True)
        
        # 只在DataFrame不为空时才保存
        if not df.empty:
            output_file = os.path.join(SAVE_PATH, "赛季等级排名_详细数据.xlsx")
            df.to_excel(output_file, index=False)
            print(f"赛季等级排名完整数据已保存至 {output_file}，共 {len(data_list)} 名玩家")
        else:
            print("没有获取到任何玩家详细信息，跳过保存完整数据文件")

def main():
    # 默认使用配置中的season_grade_id
    collector = GradeRankingDataCollector()
    collector.collect_data()

if __name__ == "__main__":
    main() 