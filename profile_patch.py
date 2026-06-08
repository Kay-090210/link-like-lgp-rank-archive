#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补漏功能：读取仅包含 player_id 列的 Excel，批量获取玩家详情并导出补漏信息.xlsx
"""
from __future__ import annotations

import sys
from pathlib import Path
import importlib
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event

import pandas as pd

import config
import login
from utils import fetch_player_profile, reorder_and_rename_member_fan_columns


def load_player_ids(xlsx_path: Path) -> List[str]:
    """读取并去重 player_id 列，保留原始顺序。"""
    df = pd.read_excel(xlsx_path, dtype=str)
    if "player_id" not in df.columns:
        raise ValueError("缺少 player_id 列")

    series = df["player_id"].dropna().astype(str).str.strip()
    ids: List[str] = []
    seen = set()
    for player_id in series:
        if not player_id:
            continue
        if player_id in seen:
            continue
        seen.add(player_id)
        ids.append(player_id)
    return ids


def refresh_headers() -> Tuple[dict, str | None]:
    """重新加载配置以获取最新 token。"""
    importlib.reload(config)
    token = config.AUTH_DATA.get("token")
    return config.HEADERS.copy(), token


def main() -> None:
    if len(sys.argv) > 1:
        raw_path = sys.argv[1].strip()
    else:
        raw_path = input("请输入 player_id Excel 文件路径: ").strip()

    if not raw_path:
        print("未提供 Excel 文件路径")
        return

    xlsx_path = Path(raw_path).expanduser().resolve()
    if not xlsx_path.exists() or not xlsx_path.is_file():
        print(f"文件不存在: {xlsx_path}")
        return

    try:
        login.main()
    except Exception as e:
        print(f"登录流程异常: {e}")

    headers, token = refresh_headers()
    if not token:
        print("未获取到有效 token，请先运行 login.py")
        return

    try:
        player_ids = load_player_ids(xlsx_path)
    except Exception as e:
        print(f"读取 Excel 失败: {e}")
        return

    if not player_ids:
        print("未读取到有效的 player_id")
        return

    total = len(player_ids)
    print(f"共读取 {total} 个 player_id（已去重）")

    data_list = [None] * total
    failed_ids: List[str] = []
    completed = 0
    lock = Lock()
    stop_event = Event()

    def fetch_one(index: int, pid: str) -> Tuple[int, str, object]:
        if stop_event.is_set():
            return index, pid, None
        result = fetch_player_profile({"player_id": pid}, headers=headers)
        return index, pid, result

    max_workers = min(100, total) if total > 0 else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_one, idx, player_id): (idx, player_id)
            for idx, player_id in enumerate(player_ids)
        }
        for future in as_completed(futures):
            idx, player_id = futures[future]
            if stop_event.is_set():
                continue
            try:
                index, pid, result = future.result()
            except Exception as e:
                with lock:
                    completed += 1
                    failed_ids.append(player_id)
                    print(f"获取失败: {player_id} - {e}（已完成 {completed}/{total}）")
                    if completed % 500 == 0 or completed == total:
                        print(f"已完成 {completed}/{total}")
                continue

            if isinstance(result, dict) and result.get("error_code"):
                if result.get("error_code") == "21001_210102":
                    print(f"错误: {result.get('message', '未知错误')}")
                    print("检测到非比赛期间，停止执行")
                    stop_event.set()
                    for pending in futures:
                        if not pending.done():
                            pending.cancel()
                    return
                with lock:
                    completed += 1
                    failed_ids.append(pid)
                    print(f"获取失败: {pid} - {result.get('message', '未知错误')}（已完成 {completed}/{total}）")
                    if completed % 500 == 0 or completed == total:
                        print(f"已完成 {completed}/{total}")
                continue

            if not result:
                with lock:
                    completed += 1
                    failed_ids.append(pid)
                    print(f"获取失败: {pid}（已完成 {completed}/{total}）")
                    if completed % 500 == 0 or completed == total:
                        print(f"已完成 {completed}/{total}")
                continue

            data_list[index] = result
            with lock:
                completed += 1
                if completed % 500 == 0 or completed == total:
                    print(f"已完成 {completed}/{total}")

    data_list = [item for item in data_list if item]
    if not data_list:
        print("未获取到任何玩家信息，未生成文件")
        return

    output_path = xlsx_path.parent / "补漏信息.xlsx"
    df = pd.DataFrame(data_list)
    df = reorder_and_rename_member_fan_columns(df)
    df.to_excel(output_path, index=False)
    print(f"已保存: {output_path}")
    if failed_ids:
        print(f"失败数量: {len(failed_ids)}")


if __name__ == "__main__":
    main()
