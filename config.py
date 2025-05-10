"""
配置文件模块

包含项目的所有配置信息：
1. API URLs和请求头
2. 活动ID配置
3. 文件保存路径和文件名
4. 排行榜目标配置
5. 设备ID和登录信息
6. 角色ID映射
"""
import os
import uuid
import json
from rank_utils import generate_rank_targets
from datetime import datetime

# 从account.json加载账号配置
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
           
        }


# 保存账号配置到account.json
def save_account_config(account_config):
    """保存账号配置到account.json"""
    account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'account.json')
    with open(account_path, 'w', encoding='utf-8') as f:
        json.dump(account_config, f, indent=4)

# 加载账号配置
ACCOUNT_DATA = load_account_config()
CURRENT_ACCOUNT = ACCOUNT_DATA["current_account"]
ACCOUNT_CONFIG = ACCOUNT_DATA["accounts"]

# API URLs
BASE_URL = "https://api.link-like-lovelive.app/v1"
RANKING_URL = f"{BASE_URL}/out_quest_live/grand_prix/get_ranking_list"
PROFILE_URL = f"{BASE_URL}/profile/get_info"
PETAL_EXCHANGE_URL = f"{BASE_URL}/petal_exchange/get_list"
FANLV_URL = f"{BASE_URL}/profile/get_fan_level_info"
CIRCLE_HISTORY_URL = f"{BASE_URL}/out_quest_live/grand_prix/get_history"
GRADE_RANKING_URL = f"{BASE_URL}/out_quest_live/grade/get_ranking_list"

# LGP类型配置（默认为个人战）
BATTLE_TYPE = {
    'personal': True,  # 个人战
    'guild': False,    # 公会战
}

# 更新LGP类型的函数
def update_battle_type(battle_type_str):
    """
    根据传入的LGP类型字符串更新BATTLE_TYPE配置
    
    参数:
        battle_type_str: LGP类型字符串，'personal'或'guild'
    """
    global BATTLE_TYPE
    
    # 重置所有类型为False
    for key in BATTLE_TYPE:
        BATTLE_TYPE[key] = False
    
    # 设置指定类型为True
    if battle_type_str in BATTLE_TYPE:
        BATTLE_TYPE[battle_type_str] = True

# 生成保存目录名称的函数
def generate_save_directory(month=None):
    """
    根据月份和LGP类型生成保存目录名称
    
    参数:
        month: 可选，指定月份（如果不提供则使用当前月份）
    
    返回:
        形如"X月个人战"或"X月公会战"的目录名
    """
    now = datetime.now()
    current_month = month if month is not None else now.month
    
    # 确定LGP类型
    battle_type = "个人战" if BATTLE_TYPE['personal'] else "公会战"
    
    # 生成目录名
    directory_name = f"{current_month}月{battle_type}"
    
    return directory_name

# 计算活动ID的函数
def calculate_event_id(month=None):
    """
    根据当前月份和LGP类型计算活动ID
    规则：
    - 格式: pSS1MM
      - p: 前缀，8(个人战)或7(公会战)
      - SS: 期数，05表示从2025年4月开始的期数
      - 1: 固定值
      - MM: 期数内的月份序号，从01开始
    """
    now = datetime.now()
    
    # 使用提供的月份或当前月份
    current_month = month if month is not None else now.month
    current_year = now.year
    
    # 确定期数和月份序号
    # 假设05期从2025年4月开始
    PERIOD_START_YEAR = 2025
    PERIOD_START_MONTH = 4
    PERIOD_NUMBER = 5  # 05期
    
    # 计算从期数开始到现在过了多少个月
    total_months = (current_year - PERIOD_START_YEAR) * 12 + (current_month - PERIOD_START_MONTH + 1)
    
    # 如果是负数，说明还没到05期开始，按05期第1个月处理
    if total_months <= 0:
        month_in_period = 1
    else:
        # 计算当前是期数内的第几个月(1-12)
        month_in_period = ((total_months - 1) % 12) + 1
    
    # 确定活动类型前缀
    prefix = 8 if BATTLE_TYPE['personal'] else 7
    
    # 活动ID格式：pSS1MM，p是前缀(7或8)，SS是期数，1是固定位，MM是期数内月份序号
    event_id = f"{prefix}{PERIOD_NUMBER:02d}1{month_in_period:02d}"
    
    return int(event_id)

# 活动ID配置
GRAND_PRIX_CONFIG = {
    'current_id': calculate_event_id(),  # 动态计算当前活动ID
    'history': {
        # 可以记录历史活动ID,仅留档,没有实际意义,会返回开催时间外
        '12月个人战': 804109,  # 2024年12月个人战
        '12月公会战': 704109,  # 2024年12月公会战
        '1月个人战': 804110,  # 2025年1月个人战
        '1月公会战': 704110,  # 2025年1月公会战
        '2月个人战': 804111,  # 2025年2月个人战
        '2月公会战': 704111,  # 2025年2月公会战
        '3月个人战': 804112,  # 2025年3月个人战
        '3月公会战': 704112,  # 2025年3月公会战
        '4月个人战': 805101,  # 2025年4月个人战
        '4月公会战': 705101,  # 2025年4月公会战
    }
}

# 计算赛季等级ID的函数
def calculate_grade_id(month=None):
    """
    根据当前月份计算赛季等级ID
    规则：
    - 25年5月和6月为1005006
    - 之后每2个月更新一次，ID值+1
    
    参数:
        month: 可选，指定月份（如果不提供则使用当前月份）
    """
    now = datetime.now()
    current_month = month if month is not None else now.month
    current_year = now.year
    
    # 基准值：25年5月对应ID为1005006
    BASE_YEAR = 2025
    BASE_MONTH = 5
    BASE_ID = 1005006
    
    # 计算从基准月份到当前月份的总月数
    total_months = (current_year - BASE_YEAR) * 12 + (current_month - BASE_MONTH)
    
    # 如果是负数，说明还没到基准月份，按基准ID处理
    if total_months < 0:
        return BASE_ID
    
    # 计算ID增加值：每2个月增加1
    id_increment = total_months // 2
    
    # 计算当前ID
    current_id = BASE_ID + id_increment
    
    return current_id

# 赛季等级排名配置
SEASON_GRADE_ID = {
    'current': calculate_grade_id(),  # 动态计算当前赛季等级ID
    'history': {
        '105期第一term': 1005005,  # 105期第一term,4月
        '105期第二term': 1005006,  # 105期第二term,5月和6月
    }
}

# 保存路径配置
# 使用当前文件所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(CURRENT_DIR, generate_save_directory())  # 动态生成保存路径文件夹

# LGP开始日期配置（默认值，会被GUI覆盖）
LGP_START_DATE = datetime(datetime.now().year, datetime.now().month, 1)  # 默认为当月1日

# 更新LGP开始日期
def update_lgp_start_date(year, month, day):
    """
    更新LGP开始日期
    
    参数:
        year: 年份
        month: 月份
        day: 日期
    """
    global LGP_START_DATE
    LGP_START_DATE = datetime(year, month, day)

# 生成文件名前缀
def generate_filename_prefix(is_previous_day=False):
    """
    根据LGP开始日期和当前日期计算文件名前缀
    
    参数:
        is_previous_day: 是否为前日榜，如果是，则day减1
    
    返回:
        如果当前日期早于开始日期，返回空字符串
        否则返回"dayX_"格式的前缀，X为活动天数
    """
    now = datetime.now()
    
    # 如果当前日期早于开始日期，返回空字符串
    if now.date() < LGP_START_DATE.date():
        return ""
    
    # 计算当前是活动的第几天（当天算第1天）
    day_diff = (now.date() - LGP_START_DATE.date()).days + 1
    
    # 如果是前日榜，则day减1，但确保不小于1
    if is_previous_day and day_diff > 1:
        day_diff -= 1
    
    # 生成前缀
    prefix = f"day{day_diff}_" if day_diff > 0 else ""
    
    return prefix

# 文件名配置
FILE_NAMES = {
    'ranking_cache': lambda is_previous_day=False: f"{generate_filename_prefix(is_previous_day)}排行榜.xlsx",  # 排行榜文件
    'ranking_full': lambda is_previous_day=False: f"{generate_filename_prefix(is_previous_day)}信息.xlsx",  # 完整排行文件
    'profile_patch': lambda is_previous_day=False: f"{generate_filename_prefix(is_previous_day)}补漏信息.xlsx",  # 补漏文件
    'petal_exchange': lambda is_previous_day=False: f"{generate_filename_prefix(is_previous_day)}花瓣兑换信息.xlsx",  # 花瓣兑换文件
    'fanlv': lambda is_previous_day=False: f"{generate_filename_prefix(is_previous_day)}粉丝等级信息.xlsx",  # 粉丝等级文件
    'circle_history': lambda is_previous_day=False: os.path.join(CURRENT_DIR, f"{generate_filename_prefix(is_previous_day)}出刀记录.xlsx")  # 出刀历史文件
}

# 获取文件名的辅助函数
def get_filename(key, is_previous_day=False):
    """
    获取指定类型的文件名
    
    参数:
        key: 文件类型的键名
        is_previous_day: 是否为前日榜，如为True，则day减1
    
    返回:
        生成的文件名
    """
    if key in FILE_NAMES:
        if callable(FILE_NAMES[key]):
            return FILE_NAMES[key](is_previous_day)
        return FILE_NAMES[key]
    return None

# 排行榜目标配置
TARGET_RANK = 99999  # 设置目标排名数，如需要前1000名
TEST_MODE = False   # 测试模式开关，开启后只获取1个目标排名

# 根据配置生成目标排名列表
target_ranks = [1] if TEST_MODE else generate_rank_targets(TARGET_RANK)

# 检查并获取当前使用的账号信息
if CURRENT_ACCOUNT in ACCOUNT_CONFIG:
    DEVICE_ID = ACCOUNT_CONFIG[CURRENT_ACCOUNT]['device_id']
    LOGIN_CONFIG = {
        'player_id': ACCOUNT_CONFIG[CURRENT_ACCOUNT]['player_id'],
        'device_id': DEVICE_ID
    }
else:
    # 使用临时值，之后会通过register.py创建真实账号
    TEMP_DEVICE_ID = str(uuid.uuid4())
    DEVICE_ID = TEMP_DEVICE_ID
    LOGIN_CONFIG = {
        'player_id': '',  # 初始为空，会通过register.py设置
        'device_id': DEVICE_ID
    }

# Player ID 配置
PLAYER_IDS = {
    'single_query': "M8W7X6A8U",  # get_info.py 使用的单个查询ID
}

# 从account.json加载授权信息
AUTH_DATA = ACCOUNT_DATA["auth"]

# API Headers
HEADERS = {
    "x-res-version": AUTH_DATA["resource_version"],  # 从account.json加载
    "x-client-version": AUTH_DATA["client_version"],  # 从account.json加载
    "x-device-specific-id": DEVICE_ID,
    "x-device-type": "android",
    "x-idempotency-key": "c98f77c1cc4a47f4b88720283ca3392b",
    "inspix-user-api-version": "1.0.0",
    "Accept": "application/json",
    "Authorization": f"Bearer {AUTH_DATA['token']}",  # 从account.json加载
    "x-api-key": "4e769efa67d8f54be0b67e8f70ccb23d513a3c841191b6b2ba45ffc6fb498068",
    "User-Agent": "inspix-android/3.0.10",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip, deflate"
}

# 角色ID与名称映射
CHARACTER_NAMES = {
    1031: "花帆",
    1032: "さやか",
    1033: "瑠璃乃",
    1021: "梢",
    1022: "缀理",
    1023: "慈",
    1041: "吟子",
    1042: "小铃",
    1043: "姬芽",
    1051:"泉",
    1052:"塞拉斯"
}
