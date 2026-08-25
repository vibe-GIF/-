"""
高德地图 OCR 坐标拾取器 (简化版)

用法：
  1. 运行本脚本，打开高德地图拾取器
  2. 右键地图 → "这是哪儿"
  3. 手动复制弹窗中的坐标
  4. 粘贴到终端，脚本自动解析并保存

或者安装 OCR 库后使用自动提取：
  pip install pytesseract pyautogui Pillow
"""

import json
import sys
import webbrowser
from pathlib import Path


def open_amap_picker(center_lon: float = 114.407, center_lat: float = 30.469):
    """打开高德地图拾取器"""
    url = f"https://lbs.amap.com/tools/picker?center={center_lon},{center_lat}&showtools=true"
    print(f"打开高德地图拾取器...")
    print(f"提示：右键地图 → '这是哪儿'，复制弹窗中的坐标")
    webbrowser.open(url)


def parse_coords(text: str) -> list:
    """解析坐标文本。按取值范围自动识别经度(70-140)/纬度(15-55)，不依赖粘贴顺序。"""
    import re
    nums = re.findall(r'[\d.]+', text)
    coords = []
    i = 0
    while i + 1 < len(nums):
        try:
            a, b = float(nums[i]), float(nums[i + 1])
        except ValueError:
            i += 1
            continue
        if 15 <= a <= 55 and 70 <= b <= 140:
            coords.append([b, a])  # a=纬度 b=经度
        elif 15 <= b <= 55 and 70 <= a <= 140:
            coords.append([a, b])  # a=经度 b=纬度
        i += 2
    return coords


def save_route(coords: list, config_path: Path):
    """保存路线到 config.json"""
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['walk_path'] = coords
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"已保存 {len(coords)} 个坐标点到 {config_path}")


def main():
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.example.json"

    print("=" * 50)
    print("高德地图坐标拾取器")
    print("=" * 50)
    print()

    # 打开高德地图拾取器
    open_amap_picker()

    # 等待用户输入坐标
    print("\n操作步骤：")
    print("1. 在地图上右键 → '这是哪儿'")
    print("2. 复制弹窗中的坐标 (纬度/经度)")
    print("3. 粘贴到下方，按回车确认")
    print("4. 输入 'done' 结束")
    print()

    coords = []
    try:
        while True:
            text = input("粘贴坐标 (或 'done' 结束): ").strip()
            if text.lower() == 'done':
                break
            if not text:
                continue

            extracted = parse_coords(text)
            if extracted:
                coords.extend(extracted)
                print(f"提取到 {len(extracted)} 个坐标，共 {len(coords)} 个")
                print(f"坐标: {coords}")
            else:
                print("未识别到坐标，请重试")

        if coords:
            save_route(coords, config_path)
            print("\n完成!")
        else:
            print("\n未提取到坐标")

    except KeyboardInterrupt:
        print("\n退出")
        if coords:
            save_route(coords, config_path)
            print("已保存!")


if __name__ == "__main__":
    main()
