# 轻工大乐跑（微信小程序）攻防分析

> 红队视角：分析微信小游戏/小程序类校园跑系统的攻击面与检测对策。
> 仅用于授权测试与检测能力建设。

## 1. 系统架构

小程序跑在**微信沙箱**内，客户端能力受微信 API 限制，无法像原生 APP
（步道乐跑）那样做底层设备指纹。检测重心因此从"客户端指纹"转向
"服务端多源融合"。

## 2. 数据通道与可伪性

| 通道 | API | 模拟器可伪 | 说明 |
|------|-----|-----------|------|
| GPS 轨迹 | `wx.getLocation` | 是 | MuMu 注入坐标，微信透传 |
| 加速度 | `wx.onAccelerometerChange` | 部分 | 默认静止，需主动注入 |
| 微信步数 | `wx.getWeRunData` | 否 | 硬件步数+加密签名，需 hook 微信 |
| 人脸抓拍 | `<camera>` | 是 | 照片级，喂静态图即可 |
| 设备信息 | `wx.getSystemInfo` | 部分 | brand/model 可伪装 |
| 在场证明 | 操场监控 | 真人满足 | 独立信号，与 app 设备无关 |

## 3. 自洽攻击需同时赢

1. GPS 伪出合理轨迹（过轨迹分析）
2. 加速度注入成跑步态
3. **微信步数对上**（最难，需 hook 微信）
4. 人脸喂图过比对
5. 设备 profile 不漏模拟器特征
6. 真人到场过监控

短板在第 3 条：GPS 跑 3km 但 WeRun 步数≈0，服务端一比对即穿。
步数不在小程序沙箱、也不在模拟器控制下，它在微信+硬件层。

## 4. 检测对策映射

| 攻击动作 | 命中规则 |
|----------|----------|
| GPS 伪轨迹 | `noise_spectrum` / `speed_physiological` / `accuracy_stability` |
| 加速度静止 vs GPS 跑 | `sensor_consistency` |
| WeRun 步数 vs GPS 里程 | `sensor_consistency`（数据源换 WeRun） |
| 模拟器 profile | `emulator_fingerprint` |
| 跑区外启动 | `zone_enforcement` |
| 不经过打卡点 | `checkpoint` |

## 5. 结论

- 小程序削弱客户端指纹层，比原生 APP 好骗一点
- 但服务端融合层（GPS vs 加速度 vs WeRun 步数）没削弱
- 学校若用 WeRun，模拟器方案死在步数；若不用，死在加速度注入质量+轨迹分析
- 检测框架把 `sensor_consistency` 数据源接上 WeRun/加速度，即为该系统服务端防线

## 6. 新增规则配置示例

```python
config.zone_enforcement.zone_bounds = (114.40, 30.46, 114.42, 30.48)  # lon_min,lat_min,lon_max,lat_max
config.checkpoint.checkpoints = ((114.407, 30.469), (114.409, 30.470))
config.checkpoint.checkpoint_radius_m = 30.0
```

未配置时两条规则返回 `applicable=False`，不参与评分，避免稀释风险分。
