import argparse
import os
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(
        prog="budaolepao",
        description="Budao Lepao - MuMu emulator runner",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", default="run",
                        choices=["run", "detect", "eval", "capture", "config", "scan", "route", "map", "ocr", "-h", "--help"])
    parser.add_argument("-h", "--help", action="store_true", dest="help_flag")

    args, _ = parser.parse_known_args()

    if args.help_flag or args.command in ("-h", "--help"):
        print("Usage: budaolepao [command]")
        print()
        print("Commands:")
        print("  (default)    Run MuMu emulator script")
        print("  detect       Start detection server (FastAPI)")
        print("  eval         Run evaluation")
        print("  capture      Capture button images")
        print("  config       Show current config")
        print("  scan         Scan all drives for MuMu installation")
        print("  route        Set running route (lon,lat lon,lat ...)")
        print("  map          Open Baidu Maps picker (right-click -> '添加标记' to get coords)")
        print("  ocr          OCR coordinate picker (Amap popup + OCR)")
        return

    root = Path(__file__).parent.parent

    if args.command == "run":
        script = root / "poc" / "emulator_run" / "main.py"
        os.chdir(str(root / "poc" / "emulator_run"))
        import subprocess
        sys.exit(subprocess.run([sys.executable, str(script)],
                                 cwd=str(root / "poc" / "emulator_run")).returncode)

    elif args.command == "detect":
        sys.path.insert(0, str(root / "detection"))
        from server.main import app
        import uvicorn

        print("Starting detection server at http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)

    elif args.command == "eval":
        sys.path.insert(0, str(root / "eval"))
        from metrics import run_eval
        from regression import run_m5

        run_eval(n_normal=30, n_attack=30)
        print()
        run_m5()

    elif args.command == "capture":
        _capture(root)

    elif args.command == "config":
        _show_config(root)

    elif args.command == "scan":
        _scan_mumu(root)

    elif args.command == "route":
        _set_route(root, sys.argv[2:])

    elif args.command == "map":
        _open_map(root)

    elif args.command == "ocr":
        import subprocess
        script = root / "poc" / "emulator_run" / "ocr_picker.py"
        subprocess.run([sys.executable, str(script)], cwd=str(root / "poc" / "emulator_run"))


def _show_config(root: Path):
    cfg = root / "poc" / "emulator_run" / "config.json"
    if cfg.exists():
        import json
        print(json.dumps(json.loads(cfg.read_text(encoding="utf-8")),
                         indent=2, ensure_ascii=False))
    else:
        print("config.json not found")


def _capture(root: Path):
    import subprocess
    import cv2

    emu_run = root / "poc" / "emulator_run"
    cfg = emu_run / "emu_path.json"
    emu_dir = None
    if cfg.exists():
        import json
        emu_dir = Path(json.loads(cfg.read_text(encoding="utf-8"))["emu_dir"])
    else:
        for d in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            for base in [Path(f"{d}:\\Program Files\\NetEase"),
                         Path(f"{d}:\\Program Files (x86)\\NetEase")]:
                if base.exists():
                    for p in base.rglob("adb.exe"):
                        emu_dir = p.parent
                        break
                if emu_dir:
                    break
            if emu_dir:
                break

    if not emu_dir:
        print("MuMu not found. Run 'budaolepao' first to auto-detect.")
        return

    adb = emu_dir / "adb.exe"
    adb_info = None
    for port in ["16384", "7555", "7556"]:
        r = subprocess.run([str(adb), "connect", f"127.0.0.1:{port}"],
                           capture_output=True, text=True, timeout=5)
        if "connected" in r.stdout:
            adb_info = f"127.0.0.1:{port}"
            break

    if not adb_info:
        print("Can't connect. Make sure MuMu is running.")
        return

    print(f"Connected to {adb_info}")
    img_dir = emu_run / "img"
    img_dir.mkdir(exist_ok=True)

    screen = emu_run / "screen.png"
    with screen.open("wb") as fp:
        subprocess.run([str(adb), "-s", adb_info, "exec-out", "screencap", "-p"],
                       stdout=fp, timeout=10)

    img = cv2.imread(str(screen))
    if img is None:
        print("Screenshot failed")
        return

    print(f"Screenshot: {img.shape[1]}x{img.shape[0]}")
    print("Select button region, press SPACE to confirm, ESC to skip")

    cv2.namedWindow("Capture", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Capture", 1200, 800)
    roi = cv2.selectROI("Capture", img, False)
    cv2.destroyAllWindows()

    if roi[2] > 0 and roi[3] > 0:
        x, y, w, h = [int(v) for v in roi]
        crop = img[y:y+h, x:x+w]
        name = input("Save as (e.g. lepao.png): ").strip()
        if name:
            cv2.imwrite(str(img_dir / name), crop)
            print(f"Saved to img/{name}")
        else:
            print("Cancelled")
    else:
        print("No region selected")


def _scan_mumu(root: Path):
    try:
        sys.path.insert(0, str(root / "poc" / "emulator_run"))
        from main import _scan_common_paths, _scan_all_drives
    except ImportError:
        print("Can't import scanner. Make sure dependencies are installed.")
        print("Run: pip install numpy opencv-python prettytable")
        return

    import json

    result = _scan_common_paths() or _scan_all_drives()
    if result:
        mgr_dir, player = result
        Path(root / "poc" / "emulator_run" / "emu_path.json").write_text(
            json.dumps({"emu_dir": str(mgr_dir), "player_path": str(player)}),
            encoding="utf-8")
        print(f"Found MuMu at: {mgr_dir}")
        print(f"Player: {player}")
    else:
        print("MuMu not found on any drive")


def _open_map(root: Path):
    import webbrowser

    cfg_path = root / "poc" / "emulator_run" / "config.json"
    if not cfg_path.exists():
        cfg_path = root / "poc" / "emulator_run" / "config.example.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8"))

    points = config.get("walk_path", [])
    if not points:
        print("No route defined")
        return

    first_lon, first_lat = points[0]
    # 百度地图拾取器
    url = f"https://map.baidu.com/pickplace?query={first_lat},{first_lon}"

    print(f"Opening Baidu Maps picker ({len(points)} points)...")
    print(f"Route: {points}")
    print("Tip: Right-click on map -> '添加标记' -> 标记上显示坐标")
    webbrowser.open(url)


def _set_route(root: Path, args: list):
    import json

    cfg_path = root / "poc" / "emulator_run" / "config.json"
    if not cfg_path.exists():
        cfg_path = root / "poc" / "emulator_run" / "config.example.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8"))

    if not args:
        print("Current route:")
        for i, (lon, lat) in enumerate(config["walk_path"]):
            print(f"  {i+1}. {lon}, {lat}")
        print()
        print("Usage: budaolepao route lon,lat lon,lat ...")
        print("  e.g. budaolepao route 114.405,30.4695 114.4065,30.4705")
        print("  Get coordinates from: https://map.baidu.com")
        return

    points = []
    for arg in args:
        try:
            parts = arg.split(",")
            lon, lat = float(parts[0]), float(parts[1])
            points.append([lon, lat])
        except (ValueError, IndexError):
            print(f"Invalid: {arg} (expected lon,lat)")
            return

    if len(points) < 3:
        print("Need at least 3 points")
        return

    config["walk_path"] = points
    out_path = root / "poc" / "emulator_run" / "config.json"
    out_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Route saved ({len(points)} points):")
    for lon, lat in points:
        print(f"  {lon}, {lat}")
    print(f"Distance: {config.get('dist_limit_m', 3000)}m")