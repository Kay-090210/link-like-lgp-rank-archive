"""
排名相关的工具函数
"""

def generate_rank_targets(target_count: int) -> list:
    """
    生成目标排名列表
    :param target_count: 目标名次数（如 500 表示要获取前500名）
    :return: 返回需要请求的排名列表
    """
    STEP = 26  # 每次请求返回26个数据
    ranks = []
    current_rank = 1
    
    while current_rank <= target_count:
        ranks.append(current_rank)
        current_rank += STEP
    
    return ranks 