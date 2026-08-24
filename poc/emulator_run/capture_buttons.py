"""
按钮截图辅助工具

用法：
  1. 在 MuMu 模拟器中打开步道乐跑到对应页面
  2. 运行本脚本截图
  3. 用鼠标框选按钮区域，自动保存到 img/ 目录

需要的按钮（按流程顺序）：
  - gongzuotai.png    工作台界面
  - tiyv.png          体育应用图标
  - lepao.png         乐跑图标
  - kaishilepao.png   开始乐跑按钮
  - zhenquelepao.png  确认乐跑按钮
  - zhiyoupao.png     自由跑模式
  - kaishil.png       开始按钮
  - jieshu.png        结束按钮（长按）
  - jieshu2.png       结束确认
  - jieshu3.png       结束二次确认
  - diandian.png      点点上传
  - chongxin.png      重新上传
"""

import subprocess
import sys
from pathlib import Path

import cv2

# 先找 MuMu 目录
emu_dir = None
cfg = Path("emu_path.json")
if cfg.exists():
    import json
    emu_dir = Path(json.loads(cfg.read_text(encoding="utf-8"))["emu_dir"])
else:
    search_roots = [
        Path(f"{d}:\\Program Files\\NetEase") for d in "CDEFGHIJKLMNOPQRSTUVWXYZ"
    ] + [
        Path(f"{d}:\\Program Files (x86)\\NetEase") for d in "CDEFGHIJKLMNOPQRSTUVWXYZ"
    ]
    for base in search_roots:
        for p in base.rglob("adb.exe"):
            emu_dir = p.parent
            break
        if emu_dir:
            break

if not emu_dir:
    print("Can't find MuMu directory. Run main.py first to auto-detect.")
    sys.exit(1)

adb = emu_dir / "adb.exe"
adb_info = None

# 尝试连接 ADB
for port in ["16384", "7555", "7556"]:
    r = subprocess.run(
        [str(adb), "connect", f"127.0.0.1:{port}"],
        capture_output=True, text=True, timeout=5,
    )
    if "connected" in r.stdout:
        adb_info = f"127.0.0.1:{port}"
        break

if not adb_info:
    print("Can't connect to MuMu ADB. Make sure MuMu is running.")
    sys.exit(1)

print(f"Connected to MuMu at {adb_info}")
print("Taking screenshot...")

# 截图
screen_png = Path("screen.png")
with screen_png.open("wb") as fp:
    subprocess.run(
        [str(adb), "-s", adb_info, "exec-out", "screencap", "-p"],
        stdout=fp, timeout=10,
    )

img = cv2.imread(str(screen_png))
if img is None:
    print("Screenshot failed")
    sys.exit(1)

h, w = img.shape[:2]
print(f"Screenshot: {w}x{h}")
print()
print("Press 'c' to crop a region, 's' to skip, 'q' to quit")
print("Click and drag to select region, press SPACE/ENTER to confirm")

cv2.namedWindow("Screenshot", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Screenshot", 1200, 800)

roi = cv2.selectROI("Screenshot", img, False)
cv2.destroyAllWindows()

if roi[2] > 0 and roi[3] > 0:
    x, y, rw, rh = [int(v) for v in roi]
    crop = img[y:y+rh, x:x+rw]
    name = input("Save as (e.g. lepao.png): ").strip()
    if name:
        out_path = Path("img") / name
        cv2.imwrite(str(out_path), crop)
        print(f"Saved to {out_path}")
else:
    print("No region selected")