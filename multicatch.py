"""
排行榜数据采集模块

用于批量获取排行榜数据和玩家详细信息：
1. 获取指定范围的排行榜数据
2. 获取每个玩家的详细信息
3. 保存数据到Excel文件
"""
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from config import (
    HEADERS, RANKING_URL, PROFILE_URL, SAVE_PATH, 
    FILE_NAMES, target_ranks, GRAND_PRIX_CONFIG, CHARACTER_NAMES,
    generate_filename_prefix, get_filename
)
from utils import get_player_profile, log_progress, retry_request, fetch_player_profile
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

class RankingDataCollector:
    def __init__(self, ranking_day_type=21):
        """
        初始化排行榜数据收集器
        
        参数:
        ranking_day_type: 排行榜日期类型，20为前日榜，21为当日榜(默认)
        """
        self.lock = Lock()
        self.completed_count_step1 = 0
        self.completed_count_step2 = 0
        self.target_ranks = target_ranks
        self.stop_rank = float('inf')  # 记录获取到空列表的排名
        self.ranking_day_type = ranking_day_type  # 存储排行榜日期类型
        
        # 定义排行榜类型及其对应的名称
        day_type_name = "当日" if ranking_day_type == 21 else "前日"
        self.ranking_types = {
            ranking_day_type: f"{day_type_name}总分",
            10: "A",
            11: "B",
            12: "C"
        }
        # 为每种排行榜类型创建一个停止排名记录
        self.stop_ranks = {rank_type: float('inf') for rank_type in self.ranking_types.keys()}
        # 保存headers的副本，用于请求
        self.headers = HEADERS.copy()
        
    @retry_request
    def fetch_ranking(self, target_rank: int, ranking_type: int, idx: int, total: int) -> list:
        """获取排行榜数据"""
        # 检查当前请求的排名是否超过停止排名
        if target_rank > self.stop_ranks[ranking_type]:
            return []
            
        ranking_payload = {
            "grand_prix_id": GRAND_PRIX_CONFIG['current_id'],
            "ranking_type": ranking_type,  # 1公会榜,2个人榜,3会内榜，20前日榜，21当日榜，10A，11B，12C，31公会当日，30公会前日
            "get_rank_type": 2,
            "target_rank": target_rank
        }
        # 使用实例的headers而不是全局HEADERS
        response = requests.post(RANKING_URL, headers=self.headers, json=ranking_payload)
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
                    if target_rank < self.stop_ranks[ranking_type]:  # 确保记录最小的空列表排名
                        self.stop_ranks[ranking_type] = target_rank
                        log_progress(f"在 {self.ranking_types[ranking_type]} 排行榜 rank {target_rank} 处获取到空列表，将停止获取更高排名")
            
            with self.lock:
                self.completed_count_step1 += 1
                log_progress(f"获取 {self.ranking_types[ranking_type]} 排行榜 target_rank {target_rank} 的数据成功 ({self.completed_count_step1}/{total})")
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
                    if 'get_current_token' in globals():
                        token = get_current_token()
                        print(f"成功获取token: {token[:10]}...")
                    else:
                        print("警告: get_current_token函数未定义，请检查login.py文件")
                except Exception as e:
                    print(f"获取token失败: {e}")
                    print("请确保login.py中定义了get_current_token函数")
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
                                    try:
                                        token = login_module.get_current_token()
                                        print(f"成功获取token: {token[:10]}...")
                                    except Exception as e:
                                        print(f"调用get_current_token失败: {e}")
                                else:
                                    print(f"警告: {path}中未找到get_current_token函数")
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

    def collect_data(self):
        # 先执行登录
        login_success = self.perform_login()
        if not login_success:
            print("警告：登录过程可能未完成，请先运行login.py再执行此脚本")
            if input("是否继续执行(y/n)? ").lower() != 'y':
                print("退出脚本")
                return
        
        # 登录后，先发送一个测试请求检查是否在比赛期间
        print("检查当前是否在比赛期间...")
        try:
            test_result = self.fetch_ranking(1, self.ranking_day_type, 0, 1)  # 尝试获取总分榜第一名数据
            if not test_result:
                print("警告: 测试请求未返回数据，可能不在比赛期间，但继续执行...")
            else:
                print("检查通过，当前在比赛期间，继续执行...")
        except Exception as e:
            print(f"测试请求失败: {e}")
            print("请检查是否已正确登录，如果未登录，请先运行login.py")
            if input("是否继续执行(y/n)? ").lower() != 'y':
                print("退出脚本")
                return
        
        # 确定是否为前日榜
        is_previous_day = self.ranking_day_type == 20
        
        # 第一步：获取所有排行榜的基本信息
        all_players_basic_info = {rank_type: [] for rank_type in self.ranking_types.keys()}
        
        # 确定要获取的排行榜类型
        ranking_types_to_fetch = [self.ranking_day_type]  # 总分榜
        if not is_previous_day:  # 如果不是前日榜,才获取A、B、C榜
            ranking_types_to_fetch.extend([10, 11, 12])  # A、B、C榜
        
        # 为每种排行榜类型获取数据
        for ranking_type in ranking_types_to_fetch:
            with ThreadPoolExecutor(max_workers=100) as executor:
                # 按照排名顺序提交任务
                sorted_ranks = sorted(self.target_ranks)
                futures = {
                    executor.submit(self.fetch_ranking, rank, ranking_type, idx, len(sorted_ranks)): rank
                    for idx, rank in enumerate(sorted_ranks, start=1)
                }
                
                for future in as_completed(futures):
                    rank = futures[future]
                    if rank > self.stop_ranks[ranking_type]:
                        # 取消所有更高排名的未完成任务
                        for f, r in futures.items():
                            if not f.done() and r > self.stop_ranks[ranking_type]:
                                f.cancel()
                        continue
                    
                    result = future.result()
                    if result:
                        for player in result:
                            all_players_basic_info[ranking_type].append({
                                "player_id": player.get("id", ""),
                                "rank": player.get("rank", ""),
                                "point": player.get("point", 0)
                            })

        # 保存第一步的数据到Excel的不同子表中
        # 创建自定义文件名，使用正确的day计算
        ranking_cache_file = get_filename('ranking_cache', is_previous_day)
        day_type_suffix = "当日" if self.ranking_day_type == 21 else "前日"
        
        # 在文件名中添加LGP类型标识
        cache_file_name = ranking_cache_file.replace('.xlsx', f'_{day_type_suffix}.xlsx')
        cache_file_path = os.path.join(SAVE_PATH, cache_file_name)
        
        # 确保有数据才创建文件夹和保存文件
        has_data = False
        for ranking_type in ranking_types_to_fetch:
            if all_players_basic_info[ranking_type]:
                has_data = True
                break
                
        if has_data:
            # 确保保存目录存在
            if not os.path.exists(SAVE_PATH):
                os.makedirs(SAVE_PATH)
                
            with pd.ExcelWriter(cache_file_path) as writer:
                for ranking_type in ranking_types_to_fetch:
                    df = pd.DataFrame(all_players_basic_info[ranking_type])
                    df.to_excel(writer, sheet_name=self.ranking_types[ranking_type], index=False)
                    print(f"{self.ranking_types[ranking_type]}排行榜数据已保存")
        else:
            print("未获取到任何排行榜数据，跳过创建文件夹和保存文件")
            return

        # 第二步：只获取总分排行榜的详细信息，并匹配A、B、C排行榜的数据
        total_players_info = all_players_basic_info[self.ranking_day_type]  # 使用选择的日期类型
        
        # 创建玩家ID到point和rank的映射字典，用于快速查找
        player_maps = {}
        if not is_previous_day:  # 只在当日榜时创建A、B、C榜的映射
            for rank_type in [10, 11, 12]:  # A、B、C排行榜
                player_maps[rank_type] = {
                    player["player_id"]: {
                        "point": player["point"],
                        "rank": player["rank"]
                    }
                    for player in all_players_basic_info[rank_type]
                }
        
        data_list = []
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {
                executor.submit(self.fetch_profile, player, idx, len(total_players_info)): player
                for idx, player in enumerate(total_players_info, start=1)
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    # 只在当日榜时添加A、B、C排行榜的数据
                    if not is_previous_day:
                        player_id = result["player_id"]
                        for rank_type in [10, 11, 12]:  # A、B、C排行榜
                            rank_name = self.ranking_types[rank_type]
                            if player_id in player_maps[rank_type]:
                                result[f"{rank_name}分数"] = player_maps[rank_type][player_id]["point"]
                                result[f"{rank_name} rank"] = player_maps[rank_type][player_id]["rank"]
                            else:
                                result[f"{rank_name}分数"] = None
                                result[f"{rank_name} rank"] = None
                    data_list.append(result)

        # 保存最终数据
        df = pd.DataFrame(data_list)
        
        # 删除"慈"、"梢"、"缀理"这3列
        columns_to_drop = ["慈", "梢", "缀理"]
        df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
        
        # 重新排列列顺序，将A、B、C排行榜的分数和排名列提前到point后面
        # 首先获取所有列名
        all_columns = df.columns.tolist()
        
        # 找出基础列（不包含A、B、C排行榜的分数和排名列）
        base_columns = [col for col in all_columns if not (col.endswith("分数") or col.endswith(" rank"))]
        
        # 找出A、B、C排行榜的分数和排名列
        abc_columns = [col for col in all_columns if (col.endswith("分数") or col.endswith(" rank"))]
        
        # 找出point列的位置
        point_index = base_columns.index("point") if "point" in base_columns else -1
        
        # 重新排列列顺序
        if point_index != -1:
            # 将point列后面的列分为两部分：point后面的基础列和A、B、C排行榜的列
            columns_after_point = base_columns[point_index+1:]
            columns_before_point = base_columns[:point_index+1]
            
            # 新的列顺序：point前面的基础列 + point + A、B、C排行榜的列 + point后面的基础列
            new_columns = columns_before_point + abc_columns + columns_after_point
        else:
            # 如果找不到point列，则保持原顺序
            new_columns = all_columns
        
        # 重新排列DataFrame的列顺序
        df = df[new_columns]
        
        # 按照rank列升序排序
        df = df.sort_values(by='rank', ascending=True)
        
        # 检查A、B、C排行榜列是否有数据，如果全部为None则删除对应列
        abc_rank_types = {10: "A", 11: "B", 12: "C"}
        columns_to_check = []
        
        for rank_type, rank_name in abc_rank_types.items():
            score_column = f"{rank_name}分数"
            rank_column = f"{rank_name} rank"
            
            # 检查这两列是否都是None
            if score_column in df.columns and rank_column in df.columns:
                if df[score_column].isna().all() and df[rank_column].isna().all():
                    columns_to_check.extend([score_column, rank_column])
                    print(f"{rank_name}排行榜无数据，将删除相关列")
        
        # 删除没有数据的列
        if columns_to_check:
            df = df.drop(columns=columns_to_check)
            print(f"已删除无数据的列: {', '.join(columns_to_check)}")
        
        # 根据LGP类型设置输出文件名
        ranking_full_file = get_filename('ranking_full', is_previous_day)
        output_file_name = ranking_full_file.replace('.xlsx', f'_{day_type_suffix}.xlsx')
        output_file = os.path.join(SAVE_PATH, output_file_name)
        
        # 只有在DataFrame不为空时才保存
        if not df.empty:
            df.to_excel(output_file, index=False)
            print(f"{day_type_suffix}排行榜完整数据已保存至 {output_file}")
        else:
            print(f"没有获取到任何玩家详细信息，跳过保存完整数据文件")

def main(ranking_day_type=21):
    """
    主函数
    
    参数:
    ranking_day_type: 排行榜日期类型，20为前日榜，21为当日榜(默认)
    """
    collector = RankingDataCollector(ranking_day_type)
    collector.collect_data()

if __name__ == "__main__":
    # 默认使用当日榜(21)，可以通过命令行参数修改
    day_type = 21  # 默认当日榜
    if len(sys.argv) > 1 and sys.argv[1] == "20":
        day_type = 20  # 前日榜
    main(day_type)
