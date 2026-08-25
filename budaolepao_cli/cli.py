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
                        choices=["run", "detect", "eval", "capture", "config", "scan", "route", "map", "settings", "dashboard", "setup", "-h", "--help"])
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
        print("  config       Read/write config (show | set | route | map)")
        print("               用法: budaolepao config show")
        print("                      budaolepao config set --speed <m/s> --distance <m>")
        print("                      budaolepao config route lon,lat lon,lat ...")
        print("                      budaolepao config map [次数]")
        print("  scan         Scan all drives for MuMu installation")
        print("  dashboard    TUI detection dashboard (real-time)")
        print("               用法: budaolepao dashboard [--demo]")
        print("  setup        Install budaolepao (pip install -e .)")
        print()
        print("兼容别名: route / settings / map = config 的子动作")
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
        _config(root, sys.argv[2:])

    elif args.command == "scan":
        _scan_mumu(root)

    elif args.command == "route":
        _set_route(root, sys.argv[2:])

    elif args.command == "map":
        _map(root, sys.argv[2:])

    elif args.command == "settings":
        _set_settings(root, sys.argv[2:])

    elif args.command == "dashboard":
        import subprocess
        script = root / "detection" / "dashboard.py"
        cmd = [sys.executable, str(script)]
        if "--demo" in sys.argv:
            cmd.append("--demo")
        subprocess.run(cmd, cwd=str(root / "detection"))

    elif args.command == "setup":
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(root), "-q"],
            cwd=str(root),
        )
        print("Done. Try: budaolepao -h")


def _show_config(root: Path):
    cfg = root / "poc" / "emulator_run" / "config.json"
    if cfg.exists():
        import json
        print(json.dumps(json.loads(cfg.read_text(encoding="utf-8")),
                         indent=2, ensure_ascii=False))
    else:
        print("config.json not found")


def _config(root: Path, args: list):
    """统一配置入口：budaolepao config [show|set|route|map] [options]"""
    if not args or args[0] == "show":
        _show_config(root)
    elif args[0] == "set":
        _set_settings(root, args[1:])
    elif args[0] == "route":
        _set_route(root, args[1:])
    elif args[0] == "map":
        _map(root, args[1:])
    else:
        print("Usage: budaolepao config [show|set|route|map]")
        print("  config show                          # 显示当前配置")
        print("  config set --speed <m/s> --distance <m>  # 设置配速/里程")
        print("  config route lon,lat lon,lat ...     # 设置路线")
        print("  config map [次数]                    # 拾取器读剪贴板坐标")


def _map(root: Path, args: list):
    import subprocess
    script = root / "poc" / "emulator_run" / "picker.py"
    args_list = [sys.executable, str(script)]
    if len(args) > 0 and args[0].isdigit():
        args_list.append(args[0])  # count
    if len(args) > 1:
        args_list.append(args[1])  # mode (auto/manual)
    if len(args) > 2:
        args_list.append(args[2])  # address
    subprocess.run(args_list, cwd=str(root / "poc" / "emulator_run"))


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


def _set_settings(root: Path, args: list):
    import json

    cfg_path = root / "poc" / "emulator_run" / "config.json"
    if not cfg_path.exists():
        cfg_path = root / "poc" / "emulator_run" / "config.example.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8"))

    if not args:
        # Show current settings
        print("Current settings:")
        print(f"  Speed:     {config.get('base_speed_mps', 4.0)} m/s")
        print(f"  Distance:  {config.get('dist_limit_m', 3000)} m")
        print(f"  Route:     {len(config.get('walk_path', []))} points")
        print()
        print("Usage: budaolepao settings --speed <m/s> --distance <m>")
        print("  e.g. budaolepao settings --speed 5 --distance 5000")
        return

    # Parse flags
    speed = config.get("base_speed_mps")
    distance = config.get("dist_limit_m")
    i = 0
    while i < len(args):
        if args[i] == "--speed" and i + 1 < len(args):
            try:
                speed = float(args[i + 1])
            except ValueError:
                print(f"Invalid speed: {args[i + 1]}")
                return
            i += 2
        elif args[i] == "--distance" and i + 1 < len(args):
            try:
                distance = float(args[i + 1])
            except ValueError:
                print(f"Invalid distance: {args[i + 1]}")
                return
            i += 2
        else:
            print(f"Unknown or incomplete option: {args[i]}")
            return

    config["base_speed_mps"] = speed
    config["dist_limit_m"] = distance

    out_path = root / "poc" / "emulator_run" / "config.json"
    out_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Settings saved:")
    print(f"  Speed:     {speed} m/s")
    print(f"  Distance:  {distance} m")