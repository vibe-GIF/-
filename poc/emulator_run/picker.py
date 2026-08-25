"""
run map - 打开地图拾取器，从剪贴板读取坐标

用法：
  run map [次数]

流程：
  1. 打开高德拾取器
  2. 右键地图 -> 这是哪儿 -> 复制坐标
  3. 切回终端，按回车
  4. 脚本从剪贴板读取坐标，保存

依赖：pip install pyperclip
"""

import json
import sys
import time
import webbrowser
import re
from pathlib import Path


def get_clipboard() -> str:
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        pass
    try:
        import subprocess
        r = subprocess.run(
            ["powershell", "-command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def parse_coords(text: str) -> list:
    coords = []
    for match in re.findall(r'([\d.]+),([\d.]+)', text):
        try:
            lon, lat = float(match[0]), float(match[1])
            if 70 < lon < 140 and 15 < lat < 55:
                coords.append([lon, lat])
        except ValueError:
            continue
    return coords


def main():
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.example.json"

    count = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1

    # 打开地图
    webbrowser.open("https://lbs.amap.com/tools/picker")
    print("地图已打开")
    print("操作: 右键地图 -> 这是哪儿 -> 复制坐标")

    all_coords = []
    for i in range(count):
        if i > 0:
            print(f"\n--- 第 {i+1} 次 ---")
        print("复制坐标后，切回终端按回车...")

        try:
            input()
        except EOFError:
            break

        text = get_clipboard()
        coords = parse_coords(text)

        if coords:
            all_coords.extend(coords)
            print(f"OK {len(coords)} coords: {coords}")
        else:
            print(f"FAIL no coords (clipboard: {text[:60]})")

    if all_coords:
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['walk_path'] = all_coords
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"\nSaved {len(all_coords)} coords to config.json")
        for c in all_coords:
            print(f"  {c[0]:.6f}, {c[1]:.6f}")
    else:
        print("\nNo coords saved")


if __name__ == "__main__":
    main()
