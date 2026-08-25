"""
高德地图坐标拾取器 - 全自动版

自动打开浏览器，搜索地址，自动点击地图获取坐标，自动提取。

用法：
  budaolepao map 5          # 自动模式，获取 5 个坐标
  budaolepao map 5 manual   # 手动模式，点击后按回车

依赖：
  pip install selenium webdriver-manager
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
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False


def setup_driver():
    """设置 Selenium WebDriver"""
    if not HAS_SELENIUM:
        return None

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    try:
        if HAS_WDM:
            service = Service(ChromeDriverManager().install())
        else:
            service = Service(r"C:\Program Files\Google\Chrome\Application\chromedriver.exe")

        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"浏览器启动失败: {e}")
        return None


def get_current_coords(driver) -> list:
    """从坐标获取结果区域提取坐标"""
    try:
        # 尝试多种选择器定位坐标输入框
        selectors = [
            'input[placeholder*="坐标"]',
            '.picker-result input',
            '#coord-result',
            '.result-text',
        ]

        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.get_attribute("value") or element.text
                if text:
                    # 解析坐标
                    matches = re.findall(r'([\d.]+),([\d.]+)', text)
                    coords = []
                    for match in matches:
                        try:
                            lon = float(match[0])
                            lat = float(match[1])
                            if 70 < lon < 140 and 15 < lat < 55:
                                coords.append([lon, lat])
                        except ValueError:
                            continue
                    if coords:
                        return coords
            except Exception:
                continue

        return []
    except Exception:
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


def auto_mode(driver, count: int, address: str = ""):
    """自动模式：自动搜索、自动点击、自动提取"""
    # 打开高德拾取器
    url = "https://lbs.amap.com/tools/picker"
    print(f"打开: {url}")
    driver.get(url)
    time.sleep(3)

    # 搜索地址
    if address:
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search-input"))
            )
            search_input.clear()
            search_input.send_keys(address)

            search_btn = driver.find_element(By.ID, "search-btn")
            search_btn.click()
            time.sleep(2)
        except Exception as e:
            print(f"搜索失败: {e}")

    all_coords = []
    for i in range(count):
        print(f"\n[{i+1}/{count}] 自动获取坐标...")

        # 自动点击地图中心区域（需要调整坐标）
        try:
            # 点击地图中心
            driver.execute_script("arguments[0].click();", 
                driver.find_element(By.TAG_NAME, "div").find_element(By.CSS_SELECTOR, "[class*='map']"))
            time.sleep(1)

            # 提取坐标
            coords = get_current_coords(driver)
            if coords:
                all_coords.extend(coords)
                print(f"✓ 记录 {len(coords)} 个坐标: {coords}")
            else:
                print("✗ 未提取到坐标")
        except Exception as e:
            print(f"✗ 点击失败: {e}")

        time.sleep(2)  # 等待下一次点击

    return all_coords


def manual_mode(driver, count: int):
    """手动模式：用户点击地图，程序提取坐标"""
    url = "https://lbs.amap.com/tools/picker"
    driver.get(url)
    time.sleep(3)

    all_coords = []
    for i in range(count):
        print(f"\n[{i+1}/{count}] 请在地图中点击获取坐标...")
        print("点击后按回车记录坐标...")

        input()  # 等待用户操作

        coords = get_current_coords(driver)
        if coords:
            all_coords.extend(coords)
            print(f"✓ 记录 {len(coords)} 个坐标: {coords}")
        else:
            print("✗ 未记录到坐标，请重试")

    return all_coords


def main():
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.example.json"

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    mode = sys.argv[2] if len(sys.argv) > 2 else "auto"
    address = sys.argv[3] if len(sys.argv) > 3 else "武汉华夏理工学院"

    print("=" * 50)
    print("高德地图坐标拾取器")
    print("=" * 50)
    print(f"获取次数: {count}")
    print(f"模式: {mode}")
    print(f"地址: {address}")
    print()

    if not HAS_SELENIUM:
        print("需要安装:")
        print("  pip install selenium webdriver-manager")
        print()
        print("或者手动操作:")
        print("  1. 打开 https://lbs.amap.com/tools/picker")
        print("  2. 搜索地址")
        print("  3. 点击地图获取坐标")
        print("  4. 复制坐标获取结果区域的坐标")
        print("  5. 使用 budaolepao route 设置路线")
        return

    driver = setup_driver()
    if not driver:
        print("无法启动浏览器")
        return

    try:
        if mode == "auto":
            all_coords = auto_mode(driver, count, address)
        else:
            all_coords = manual_mode(driver, count)

        if not all_coords:
            print("\n未获取到任何坐标")
            return

        selected = pick_coords(all_coords)
        save_route(selected, config_path)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
