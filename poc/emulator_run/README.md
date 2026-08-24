# 步道乐跑 电脑端模拟器 PoC（改进版）

> **仅限授权测试**：仅用于步道乐跑团队自有沙箱/测试账号。
> 禁止外传为通用刷分工具。

## 快速开始

### 1. 安装依赖

```bash
pip install numpy opencv-python prettytable
```

### 2. 配置路线

编辑 `config.json`，把 `walk_path` 换成你学校操场的经纬度。

已预置武汉华夏理工学院（光谷校区）路线。

### 3. 截取按钮图片

```bash
# 1. 打开 MuMu 模拟器，进入步道乐跑
# 2. 运行截图辅助工具
python capture_buttons.py

# 3. 鼠标框选按钮，依次保存以下图片到 img/ 目录：
#    lepao.png, kaishilepao.png, jieshu.png, ...
```

需要截取的按钮（按流程顺序）：

| 图片 | 对应界面 |
|------|----------|
| `gongzuotai.png` | 工作台首页 |
| `tiyv.png` | 体育应用图标 |
| `lepao.png` | 乐跑入口 |
| `kaishilepao.png` | 开始乐跑 |
| `zhenquelepao.png` | 确认乐跑 |
| `zhiyoupao.png` | 自由跑模式 |
| `kaishil.png` | 开始按钮 |
| `jieshu.png` | 结束按钮（长按） |
| `jieshu2.png` | 结束确认 |
| `jieshu3.png` | 二次确认 |
| `diandian.png` | 上传 |
| `chongxin.png` | 重新上传 |

### 4. 开跑

```bash
python main.py
```

## 改进项

| 改进 | 对抗检测 |
|------|----------|
| Ornstein-Uhlenbeck 有色噪声 | 噪声谱自相关检验 |
| 正弦波速度轮廓 | 加速度跳变检测 |
| 对数正态时间抖动 | 上报间隔方差异常 |
| 路径横向漂移 | 轨迹过于笔直 |
| 步频 ADB 注入 | GPS-步频零相关 |

## 配置文件

参见 `config.json`，所有参数均可调。

## 学校路线

如需更换学校，找到操场坐标替换 `walk_path` 即可。建议用百度地图/高德地图取 6-8 个点围成一圈。