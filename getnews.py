import requests
import os
import json
import re
from datetime import datetime

def parse_lgp_news():
    """
    解析LGP新闻，提取开催信息和图片链接
    
    返回:
        list: 包含新闻信息的字典列表
    """
    newsurl = "https://link-like-lovelive.app/client.mjs"
    news_items = []
    
    try:
        # 获取响应内容
        response = requests.get(newsurl)
        response.raise_for_status()
        
        # 获取原始内容
        content = response.text
        
        # Unicode解码
        try:
            decoded_content = content.encode().decode('unicode_escape')
        except Exception as e:
            print(f"解码错误: {e}")
            decoded_content = content
        
        # 使用正则表达式提取每条新闻
        pattern = r'\{id:"([^"]+)",metadata:\{title:"([^"]+)",.*?markdown:`(.*?)`'
        matches = re.finditer(pattern, decoded_content, re.DOTALL)
        
        for match in matches:
            news_id = match.group(1)
            title = match.group(2)
            markdown_content = match.group(3).strip()
            
            # 处理ライブグランプリ开催通知和预定通知
            if "ライブグランプリ" in title and ("開催のお知らせ" in title or "開催予定のお知らせ" in title):
                # 提取开催期间
                period_match = re.search(r'◆開催期間\s*(.+?)(?=\n\n|$)', markdown_content, re.DOTALL)
                period = period_match.group(1).strip() if period_match else "未找到开催期间"
                
                # 解析日期 - 在格式化之前提取日期
                date_match = re.search(r'(\d+)/(\d+)\(.*?\) \d+:\d+ ～', period)
                start_month = None
                start_day = None
                
                if date_match:
                    start_month = int(date_match.group(1))
                    start_day = int(date_match.group(2))
                
                # 美化时间显示
                # 原始格式：5/11(日) 12:00 ～ 5/17(土) 3:59
                # 美化后：5月11日(日) 12:00 ～ 5月17日(土) 3:59
                if period != "未找到开催期间":
                    # 替换斜杠为"月"，为日期添加"日"后缀
                    period = re.sub(r'(\d+)/(\d+)(\([^)]+\))', r'\1月\2日\3', period)
                    
                    # 进一步简化，去除不必要的空格和非关键信息
                    period = period.strip()
                    # 替换多个空格为单个空格
                    period = re.sub(r'\s+', ' ', period)
                
                news_item = {
                    'id': news_id,
                    'title': title,
                    'period': period,
                    'markdown_content': markdown_content,  # 保存markdown内容用于后续查找图片
                    'start_month': start_month,
                    'start_day': start_day
                }
                
                news_items.append(news_item)
        
        # if news_items:
        #     # 将提取的内容写入文件
        #     with open('lgp_news.txt', 'w', encoding='utf-8') as f:
        #         for item in news_items:
        #             f.write(f"=== {item['title']} ===\n\n")
        #             f.write(f"開催期間:\n{item['period']}\n\n")
        #             f.write(f"第一张图片:\n{item['first_img']}\n\n")
        #             f.write("-" * 50 + "\n\n")
        #     print(f"成功提取了 {len(news_items)} 条ライブグランプリ新闻")
        # else:
        #     print("未找到任何ライブグランプリ新闻")
        #     # 保存部分原始内容用于调试
        #     with open('debug.txt', 'w', encoding='utf-8') as f:
        #         f.write(decoded_content[:1000])
        #     print("已将部分原始内容保存到debug.txt用于调试")

    except requests.RequestException as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        if 'decoded_content' in locals():
            with open('error.txt', 'w', encoding='utf-8') as f:
                f.write(decoded_content[:1000])
            print("已将部分内容保存到error.txt用于调试")
    
    return news_items

def find_image_url(markdown_content):
    """
    从markdown内容中查找图片URL
    
    参数:
        markdown_content: markdown格式的内容
    
    返回:
        str: 图片URL，如果未找到则返回"未找到图片"
    """
    img_url = "未找到图片"
    
    # 尝试不同的图片格式
    img_patterns = [
        r'<img src="([^"]+)"',  # HTML格式
        r'!\[.*?\]\(([^)]+)\)',  # Markdown格式
        r'https?://[^\s<>"]+?(?:jpg|jpeg|png|gif|webp)',  # 直接URL
        r'//[^\s<>"]+?(?:jpg|jpeg|png|gif|webp)'  # 协议相对URL
    ]
    
    for pattern in img_patterns:
        img_match = re.search(pattern, markdown_content)
        if img_match:
            img_url = img_match.group(1) if '(' in pattern else img_match.group(0)
            # 处理协议相对URL
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            break
    
    return img_url

def get_latest_lgp_info():
    """
    获取最新的LGP信息
    
    返回:
        dict: 包含最新LGP信息的字典，如果没有找到则返回None
    """
    news_items = parse_lgp_news()
    
    # 使用公告发布日期和开赛日期进行排序
    def sort_key(item):
        # 优先使用公告ID中的发布日期，兼容「Chapter PERENNIAL」这类不含“数字期”的新标题
        published_match = re.match(r'(\d{4})-(\d{2})-(\d{2})-', item['id'])
        if published_match:
            published_date = tuple(int(part) for part in published_match.groups())
        else:
            published_date = (0, 0, 0)
        
        # 如果没有日期信息，则放到最后
        if item['start_month'] is None or item['start_day'] is None:
            return (*published_date, 0, 0)
        
        return (*published_date, item['start_month'], item['start_day'])
    
    # 根据期数和日期排序（从最新到最旧）
    sorted_items = sorted(news_items, key=sort_key, reverse=True)
    
    # 获取最新的LGP信息
    if sorted_items:
        latest_item = sorted_items[0]
        # 只为最新的新闻查找图片URL
        img_url = find_image_url(latest_item['markdown_content'])
        print(f"找到图片URL: {img_url}")
        
        # 添加图片URL到结果中
        latest_item['first_img'] = img_url
        # 删除markdown_content，不需要返回
        del latest_item['markdown_content']
        
        return latest_item
    
    return None

# 如果直接运行此脚本，则执行解析并输出结果
if __name__ == "__main__":
    news_items = parse_lgp_news()
    
    # 尝试获取最新的LGP信息
    latest_lgp = get_latest_lgp_info()
    
    if latest_lgp:
        print("\n最新的LGP信息:")
        print(f"标题: {latest_lgp['title']}")
        print(f"开始日期: {latest_lgp['start_month']}月{latest_lgp['start_day']}日")
        print(f"图片链接: {latest_lgp['first_img']}")
    else:
        print("\n未能找到有效的LGP信息")

