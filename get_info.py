"""
单一查询模块

用于测试API会返回什么东西,从而进一步分析需要提取其中的什么数据
"""
from config import HEADERS, PROFILE_URL, PLAYER_IDS, PETAL_EXCHANGE_URL, FANLV_URL,RANKING_URL,target_ranks,CIRCLE_HISTORY_URL,GRADE_RANKING_URL,GET_DESCRIPTION_URL
from utils import get_player_profile, get_petal_exchange_info, get_fanlv,get_ranking,get_circle_history,log_progress,get_grade_ranking,get_description
from fanlv import process_fanlv_data
import requests





def main():
    # 记录当前使用的API类型
    api_type = "profile"  # 默认为profile
    
    # 获取玩家信息
    # result = get_player_profile('6CF3EJTER', HEADERS, PROFILE_URL)
    # result = get_petal_exchange_info(HEADERS, PETAL_EXCHANGE_URL); api_type = "petal"
    # result = get_fanlv(HEADERS, FANLV_URL, PLAYER_IDS['single_query']); api_type = "fanlv"
    # result = get_ranking(HEADERS, RANKING_URL); api_type = "ranking"
    # result = get_grade_ranking(HEADERS, GRADE_RANKING_URL); api_type = "grade"
    # result = get_circle_history(HEADERS, CIRCLE_HISTORY_URL, 704109); api_type = "history"
    result = get_description(HEADERS, GET_DESCRIPTION_URL)

    print("响应内容：", result)
    # 输出结果
    if result:
        print("请求成功!")
        
        # 只在使用get_fanlv时处理fanlv数据
        if api_type == "fanlv":
            process_fanlv_data(result)
    else:
        print("请求失败:")
    
if __name__ == "__main__":
    main()