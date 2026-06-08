import pandas as pd
from typing import Dict, List
from config import SAVE_PATH, get_filename
import os

def process_fanlv_data(data: Dict) -> None:
    """
    处理粉丝等级数据并输出为Excel表格

    Args:
        data: API返回的粉丝等级数据字典
    """
    # 准备存储数据的列表
    rows = []
    history_rows = []  # 用于存储历史记录

    # 角色ID到名字的映射
    character_map = {
        1031: "花帆",
        1032: "さやか",
        1033: "瑠璃乃",
        1021: "梢",
        1022: "缀理",
        1023: "慈",
        1041: "吟子",
        1042: "小铃",
        1043: "姬芽",
        1051: "泉",
        1052: "塞拉斯",
    }

    # earn_type映射
    earn_type_map = {
        1: "with meets",
        2: "fes live",
        3: "入手",
        4: "特训",
        5: "解放"
    }

    # 遍历每个角色的粉丝等级信息
    for char_info in data['fan_level_info_list']:
        char_id = char_info['character_id']
        char_name = character_map.get(char_id, f"Unknown_{char_id}")

        # 创建基本信息字典
        row = {
            '角色': char_name,
            'D赛季等级': char_info['d_season_fan_level'],
            'D赛季经验': char_info['d_season_fan_experience'],
            '总等级': char_info['member_fan_level'],
            '总经验': char_info['member_fan_experience']
        }

        # 添加各种获取方式的点数
        for progress in char_info['earn_progress_list']:
            earn_type = earn_type_map.get(progress['earn_type'], f"未知类型_{progress['earn_type']}")
            row[earn_type] = progress['total_point']

            # 收集历史记录
            if progress['season_point_history_list']:
                for season in progress['season_point_history_list']:
                    season_id = season['season_id']
                    if season['point_history_list']:
                        for history in season['point_history_list']:
                            history_rows.append({
                                '角色': char_name,
                                '获得类型': earn_type,
                                '赛季ID': season_id,
                                '获得时间': history['date'],
                                '获得内容': history['message'],
                                '获得点数': history['point']
                            })

        rows.append(row)

    # 创建主DataFrame
    df = pd.DataFrame(rows)
    columns = ['角色', 'D赛季等级', 'D赛季经验', '总等级', '总经验',
              'with meets', 'fes live', '入手', '特训', '解放']
    df = df[columns]

    # 创建历史记录DataFrame
    history_df = pd.DataFrame(history_rows)
    
    # 保存为Excel文件，使用多个sheet
    os.makedirs(SAVE_PATH, exist_ok=True)
    output_file = os.path.join(SAVE_PATH, get_filename('fanlv'))
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='总览', index=False)
        history_df.to_excel(writer, sheet_name='历史记录', index=False)
    
    print(f"粉丝等级数据已保存到 {output_file}")
