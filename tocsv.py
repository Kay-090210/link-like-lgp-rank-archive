#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据用户输入的目录，将其中的所有 XLSX 文件转换为 CSV
"""
import pathlib
import pandas as pd


def convert_all_xlsx_to_csv(base_dir: pathlib.Path) -> None:
    """遍历并转换指定目录下的所有 XLSX 文件"""
    count = 0
    for xlsx_path in base_dir.glob("*.xlsx"):
        csv_path = xlsx_path.with_suffix(".csv")
        df = pd.read_excel(xlsx_path)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"已转换: {xlsx_path.name} -> {csv_path.name}")
        count += 1

    if count == 0:
        print("未找到任何 XLSX 文件，请确认目录是否正确。")
    else:
        print(f"转换完成，共生成 {count} 个 CSV 文件。")


if __name__ == "__main__":
    raw_path = input("请输入需要转换的目录路径（直接回车使用当前目录）：").strip()
    target_dir = pathlib.Path(raw_path or ".").expanduser().resolve()

    if not target_dir.exists():
        print(f"目录不存在：{target_dir}")
    elif not target_dir.is_dir():
        print(f"指定路径不是目录：{target_dir}")
    else:
        convert_all_xlsx_to_csv(target_dir)