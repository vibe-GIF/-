"""
高德地图坐标拾取器 - 简化版

用法：
  budaolepao picker 3

功能：
  1. 打开高德拾取器
  2. 你搜索地址、点击地图
  3. 每次点击后按回车，自动记录坐标
  4. 最后让你选择保留哪些坐标
"""

import json
import sys
import time
import webbrowser
import re
from pathlib import Path

import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from PIL import Image, ImageGrab, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def open_picker():
    """打开高德拾取器"""
    url = "https://lbs.amap.com/tools/picker"
    print(f"打开高德拾取器: {url}")
    webbrowser.open(url)
    time.sleep(3)


def capture_coords() -> list:
    """截图坐标获取结果区域并 OCR"""
    if not HAS_PIL or not HAS_TESSERACT:
        print("需要安装: pip install pytesseract Pillow")
        print("手动复制坐标获取结果区域的坐标")
        return []

    try:
        screenshot = ImageGrab.grab()
        width, height = screenshot.size

        # 裁剪坐标获取结果区域（右上角）
        left = int(width * 0.62)
        top = int(height * 0.18)
        right = int(width * 0.92)
        bottom = int(height * 0.24)

        cropped = screenshot.crop((left, top, right, bottom))

        # 增强对比度
        enhancer = ImageEnhance.Contrast(cropped)
        cropped = enhancer.enhance(1.5)

        # OCR
        text = pytesseract.image_to_string(
            cropped, lang='eng', config='--psm 7'
        )

        # 解析坐标
        coords = []
        matches = re.findall(r'([\d.]+),([\d.]+)', text)
        for match in matches:
            try:
                lon = float(match[0])
                lat = float(match[1])
                if 70 < lon < 140 and 15 < lat < 55:
                    coords.append([lon, lat])
            except ValueError:
                continue

        return coords
    except Exception as e:
        print(f"截图/OCR 错误: {e}")
        return []


def pick_coords(all_coords: list):
    """让用户选择保留哪些坐标"""
    print(f"\n共获取 {len(all_coords)} 个坐标:")
    for i, coord in enumerate(all_coords):
        print(f"  {i+1}. {coord[0]:.6f}, {coord[1]:.6f}")

    print(f"\n选择要保留的 (输入序号，如 1,3,5，或 'all' 全部保留):")
    choice = input().strip()

    if choice.lower() == 'all':
        return all_coords

    indices = []
    for idx in choice.split(','):
        idx = idx.strip()
        if idx.isdigit():
            i = int(idx) - 1
            if 0 <= i < len(all_coords):
                indices.append(i)

    if indices:
        return [all_coords[i] for i in indices]
    else:
        print("无效选择，返回全部坐标")
        return all_coords


def save_route(coords: list, config_path: Path):
    """保存路线到 config.json"""
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['walk_path'] = coords
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n已保存 {len(coords)} 个坐标点到 {config_path}")
    print("路线:")
    for coord in coords:
        print(f"  {coord[0]:.6f}, {coord[1]:.6f}")


def main():
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.example.json"

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    print("=" * 50)
    print("高德地图坐标拾取器")
    print("=" * 50)
    print(f"获取次数: {count}")
    print()
    print("操作流程:")
    print("  1. 在地图中搜索地址")
    print("  2. 点击地图获取坐标")
    print("  3. 看到坐标后按回车记录")
    print("  4. 重复 N 次")
    print("  5. 选择保留哪些坐标")
    print()

    open_picker()

    all_coords = []
    for i in range(count):
        print(f"[{i+1}/{count}] 点击地图后按回车记录坐标...")
        input()

        coords = capture_coords()
        if coords:
            all_coords.extend(coords)
            print(f"✓ 记录 {len(coords)} 个坐标: {coords}")
        else:
            print("✗ 未记录到坐标，请重试")

    if not all_coords:
        print("\n未获取到任何坐标")
        return

    selected = pick_coords(all_coords)
    save_route(selected, config_path)


if __name__ == "__main__":
    main()
