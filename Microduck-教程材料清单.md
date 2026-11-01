# Microduck 教程编写 · 材料包

> 面向教材 / 课程导入使用。按三类需求组织：**① 产品概述（含宣传视频要点）② 硬件模块介绍 ③ 软件资料与烧录器、调试器、串口等二开资料**。附 BOM、装配、标定、FAQ 与文件清单。

## 一、产品概述（课程导入 / 宣传视频用）

**项目定位**

- Microduck 是一台**双足**桌面机器人（小鸭造型），不是四足。
- 两条腿，每条腿 **5 个关节**：髋 yaw / 髋 roll / 髋 pitch / 膝 / 踝；头部/嘴再 5 个，共 **15 个串行总线舵机**。
- 作者/仓库：kissqy，https://github.com/kissqy/Microduck-kissqy
- 许可：见仓库 LICENSE（引用以仓库为准）。

**能力**

- 站立、行走、坐下、倒地起身、踢球、捡取、前滚翻；可选滑轮（轮滑）动作。
- 控制方式：GameSir Nova 2 Lite 手柄、中控网页虚拟手柄、语音（本项目自研）、手机/热点（可扩展）。

**技术亮点（宣传片可讲）**

- **双足平衡**：IMU 姿态 + 强化学习策略，15 个串行舵机做关节控制。
- **AI 自动化闭环**：训练中控改任务/参数 → 训练 → 评估 → 导出 ONNX → 部署到 Zero → 实机验证。
- **从基础编程到 AI 开发**：课程可对比“手写控制/图形化”与“AI 训练 + 部署”的差异。
- 硬件开源：HAT/IMU 可打板，3D 打印结构，物料可采购。

**宣传视频分镜建议（青少年/家长/老师）**

1. 开箱与整机外观（双足小鸭）。
2. 站立 → 行走 → 坐下 → 倒地起身。
3. 踢球 / 捡取 / 前滚翻。
4. 手柄与语音控制。
5. AI 训练界面：改任务、看奖励曲线、导出模型。
6. 学生在电脑前调参、机器人在旁行走（呼应“AI 时代”）。
7. 安全提示：架空/扶稳、限位、卸力/急停。

**一句话简介**

> 一台用 15 个串行舵机 + IMU + Radxa Zero 3W 实现的**双足**小鸭机器人，支持 AI 训练到实机部署的完整闭环。

## 二、硬件模块介绍（工作原理 + 关键模块）

**系统框图（文字）**

```
NP-F550 7.4V ──► HAT（5V buck / 电平转换 / 总线收发）
                   ├──► Radxa Zero 3W（Linux / robotd / 策略 / 摄像头）
                   ├──► 15 × HD-1910 舵机（1 Mbps 总线，双腿 + 头/嘴）
                   ├──► IMU 板（STM32G031 + LSM6DSV16X，ID 200）
                   └──► 摄像头 22-pin CSI / 音频 / ToF（可选）
```

**关键模块**

| 模块 | 作用 | 备注 |
|---|---|---|
| Radxa Zero 3W | 主控，跑 Linux、robotd、策略推理、摄像头 | 2GB |
| HAT | 电源、总线收发、40-pin 转接、音频/接口 | 自制，EH2.5/AMP2.0 两版 |
| IMU 板 | 姿态/角速度，供平衡与策略 | 总线 ID **200**，固件 FT6 |
| HD-1910 舵机 ×15 | 关节驱动 | 每条腿 5 个 + 头/嘴 5 个；1 Mbps |
| 电池 NP-F550 | 7.4V 供电 | 总进电口并 1000µF/16V |
| 摄像头 | 图像/视觉 | 原生 22-pin IMX219 |
| 手柄 | 手动控制 | GameSir Nova 2 Lite（蓝牙） |

**双足结构说明（避免“四足”误解）**

- 每条腿 5 个关节：髋 yaw / 髋 roll / 髋 pitch / 膝 / 踝。
- 头部/嘴 5 个舵机：颈、头 pitch、头 yaw、头 roll、嘴。
- 双足站立/行走依赖 **IMU + 策略** 的动态平衡，不是四足的静稳结构。

**关键针序**

| 接口 | 针序 |
|---|---|
| HAT J13/J14（舵机总线） | 1 GND、2 BATT_IN、3 DXL_DATA |
| 飞特 HD-1910 舵机 | 1 Signal、2 Vcc、3 GND |
| IMU J1 | 1 GND、2 DXL_VDD、3 DXL_DATA |
| 电池 | + → BATT_IN(2)，− → GND(1)，并 1000µF/16V |
| 摄像头 | Zero 22-pin CSI（不经过 HAT） |
| 喇叭 J1 / 麦 J2·J9 / ToF J5 | 见接线说明 |

**接线关键规则**

- **首舵机必须交叉**：HAT 1→舵机3、2→2、3→1；舵机之间 1:1。
- IMU 接 HAT J14 或总线末端，1:1；建议放末端。
- 舵机 ID：右腿 10–14、左腿 20–24、头/嘴 30–34；IMU 200；1 Mbps。

## 三、软件资料与烧录器、调试器、串口等二开资料

**版本链**

| 组件 | 版本 |
|---|---|
| 系统镜像（TF 卡） | Public Image R1（预装 control.40） |
| 机器人服务 | control.43 |
| 中控 | R17 V167 |
| 训练中控（可选） | R1.5.27 |
| IMU 固件 | FT6（`imu_to_feetech_ReVA_FT6_SYNC15_UART_IRQ_v1.bin`） |

**烧录器 / 镜像**

- 系统镜像：balenaEtcher / Rufus 烧 TF 卡。
- IMU：**ST-LINK V2 + STM32CubeProgrammer**；IMU J2 SWD 针序 `1 3V3 / 2 SWDIO / 3 GND / 4 SWCLK / 5 NRST`；FT6 bin 起始地址 **0x08000000**。
- 注意：刷系统/升级服务不会烧 IMU，IMU 必须单独烧。

**调试器 / 串口**

- Zero 总线串口：`/dev/ttyS2`（robotd 独占；调试前 `fuser /dev/ttyS2`）。
- HAT/IMU 调试口：SWD + UART（IMU J3）。
- SSH：`ssh radxa@<IP>`；中控日志/启动诊断。
- 常用命令：`arecord -l`、`aplay -l`、`i2cdetect`（IMU 不在 I2C，别用）。

**二开接口**

- robotd JSON-RPC：`/run/robotd.sock`，方法 `robot.move / robot.head / robot.mouth / robot.init / robot.relax / robot.do`。
- 本项目 `cmd_relay.py`：TCP `8098` → robotd（PC/手机可直连）。
- 语音：`voice_pc.py`（PC 收音 + Vosk + TCP 下发）。
- 中控 R17：网页/手柄/标定/服务。
- 训练中控 R1.5.27：任务、参数、训练、评估、导出、部署。

**AI 自动化闭环教学路径**

1. 选任务/改奖励/参数（训练中控）。
2. 训练（GPU）。
3. 评估/对比（PT/ONNX）。
4. 导出模型包 → 部署到 Zero。
5. 实机验证（站立/行走/起身）。
6. 强调：从“手写控制/图形化”升级到“训练 + 部署”的 AI 开发方式。

**资料与权限**

- 官方仓库、硬件 `.epro2`、IMU FT6 bin、中控/训练包、模型文件。
- Zero 上 `/run/robotd.sock` 属 root；命令转发/服务需 root 或相应权限。
- 演示网络：可开热点固定 `10.42.0.1`。

## 四、物料清单（BOM）

| 类别 | 型号/规格 | 数量 |
|---|---|---|
| 主控 | Radxa Zero 3W（2GB） | 1 |
| HAT | 自制（打板+贴片） | 1 |
| IMU 板 | 自制（STM32G031 + LSM6DSV16X，ID 200） | 1 |
| 舵机 | 飞特 HD-1910（5–8.4V，串行总线） | 15 |
| 电池 | NP-F550 7.4V（作者设计约 100g；本项目实测 201g，偏重） | 1 |
| 摄像头 | 原生 22-pin IMX219 | 1 |
| 手柄 | GameSir Nova 2 Lite | 1 |
| 连接器/线材 | AMP2.0 / EH2.5；首舵机交叉线 | 若干 |
| 电源 | 1000µF/16V | 1 |
| 其它 | 轴承、M2 螺丝、电池 HUB/接电池板、ToF（可选）、喇叭、麦克风 | 若干 |

文件：`成本估计/BOM.md`、`Microduck-装配BOM.xlsx`、`采购查询链接.md`、作者 `hardware/DUCK-SHOPPING-LIST.md`。

## 五、装配 / 标定

1. 硬件检查：HAT/IMU 目检、3.3V；IMU 烧 FT6。
2. 机械装配（装配说明书 + 3D 打印件）。
3. 接线（断电；首舵机交叉；IMU 末端；电池 +1000µF）。
4. 上电：量 BATT_IN/5V/3.3V、空载电流。
5. 中控连 Zero，等 robotd 四步就绪（15 舵机 + IMU 200）。
6. 标定：15 关节零位/方向/限位；IMU 安装确认。
7. HOME（架空/扶稳）→ 站立 → 行走/坐下/倒地起身。

- 标定报错：`calculated zero is outside 0..4095`（重新对齿）、`joint limits cross the single-turn encoder boundary`（行程跨回绕）、编码器 360°（模式/零位/磁编码）。
- 复现步骤：`成本估计/MICRODUCK-复现步骤清单.md`。

## 六、常见坑 / FAQ

1. 有源晶振 ≠ 无源晶振：Y1 平替错误会让 3.3V 对地短路。
2. 飞特与 HAT 针序相反，首舵机必须交叉。
3. IMU 是总线 ID 200，不是 I2C；新板必须单独烧 FT6。
4. 舵机总线 1 Mbps 单端：怕共地不良/压降/长线/串扰；数据线与 GND 双绞。
5. HOME 是开环：先标定零位/方向/限位 + IMU 安装确认。
6. 电池重量/位置直接影响**双足**重心；策略不感知电池质量。
7. 主控关机：电流拉垮电池/5V、1000µF 缺失、BMS 限流、双供电、误触手柄 Select。
8. IP 变化：演示用热点固定 10.42.0.1。
9. 语音：PC Vosk（faster-whisper 在 Windows 上坑多，已弃用）。

## 七、可交付文件清单

`C:\Users\27994\Desktop\成本估计`：

- `Microduck-电机编号表-含接线.xlsx`、`Microduck-接线说明.md`
- `Microduck-装配安装说明书.pdf`、`Microduck-装配BOM.xlsx`
- `Microduck-电池HUB与接电池板说明.md`、`Microduck-电池HUB打板说明.md`
- `Microduck-摄像头测试.sh`、`MICRODUCK-复现步骤清单.md`
- `Microduck-AMP2.0接口说明-作者原文.md`、`Microduck-IMU总线接线表-社区参考.md`
- `打板/POGO_PIN_1V0A.eprj2`、`打板/wire_hub_1V0A.eprj2`

`C:\Users\27994\Desktop\microduck`：

- `开发日志.md`（完整开发记录）
- `3D打印缝合怪版`、`Microduck-Console-R17-V167`、`Microduck-Training-Studio-R1.5.27`
- 自研脚本：`voice_pc.py`、`cmd_relay.py` 等
