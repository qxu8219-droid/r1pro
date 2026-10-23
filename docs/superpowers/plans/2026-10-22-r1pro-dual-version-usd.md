# R1Pro 2026 双版本 USD 实施清单

> **For agentic workers:** 使用 superpowers:executing-plans，在本会话按顺序执行并更新勾选状态。用户已确认并执行；完成记录见 reports/validation_summary.json 和 reports/progress.md。

**Goal:** 从指定厂商源文件生成分别适用于 Isaac Sim 5.1 和一个明确的 6.x 小版本的 R1Pro 2026 USD 资产包，并提供两版实际运行验证证据。

**Architecture:** 同一份厂商源文件、共同的机器人参数基准、两套版本适配的转换入口和独立输出目录。先完成 5.1 基线，再完成 6.x；两版共享验证场景与指标，记录差异，不承诺物理轨迹逐帧一致。

**Tech Stack:** Python、URDF、OpenUSD、Isaac Sim 各版本原生导入器及实际支持的物理 API、NVIDIA Isaac Sim skills。

**Spec:** 本文“范围与约束”和用户已提出的双版本需求共同构成此次待确认方案。用户明确要求先审阅 todolist，再按步骤实施；确认前仅进行只读资料检查和计划编写。

## 已完成的只读检查

- [x] 阅读厂商包 README、模型选择记录及历史导入/外观配方。
- [x] 核对选定 URDF 的 SHA-256 与 SELECTED_MODEL.json 一致。
- [x] 解析 URDF：46 个 link；21 个 revolute、3 个 continuous、4 个 prismatic、17 个 fixed joint。
- [x] 检查选择记录列出的 46 项 mesh 依赖均存在；所有 link 均有 inertial 元素。尚未验证惯量数值物理有效性。
- [x] 确认 URDF 没有 mimic 元素；夹爪联动/命令映射仍须结合配套资料核对，不能凭空补设。
- [x] 读取本机 `/home/xq/isaacsim/VERSION`：`5.1.0-rc.19+release.26219.9c81211b.gl`。该版本字符串包含 rc 标记，发行来源及运行情况在环境阶段核实；目前未启动仿真，也未确认 6.x 环境。

## 范围与约束

- 源目录：`deliverables/r1pro_2026_vendor_sources_20261022/`，所有原件保持原样。
- 唯一结构入口：`sdk/r1pro_urdf/share/r1pro_urdf/urdf/r1pro_2026.urdf`。
- 源 URDF SHA-256：`197091db1515a7326ad363b7f9894b3d847518120397f306d001c6ef1218d2e9`。
- 躯干基准来自该 URDF：torso_joint2 为 `0 0 0.35`，torso_joint3 为 `0 0.0001005 0.35`。
- 旧版 `appearance_reference/r1_pro_with_gripper/r1_pro_with_gripper_fixed.usd` 与 `textures/output.jpg` 只作为外观参考，不覆盖 2026 结构、碰撞和惯量。
- `.usd.copy2` 和 HDR 不作为已确认素材。历史诊断记录只作为证据线索，不视为本次验收结果。
- 默认交付可移动底盘的整机资产；固定基座仅用于隔离关节验证的测试场景。实际底盘控制方式依据厂商资料确定。
- 传感器安装坐标随机器人保留；本轮不扩展为完整 ROS 2、相机/雷达数据管线、导航或强化学习任务。相机外参不明确时记录待核实项。
- 缺失的物理/驱动参数应区分厂商值与仿真假设，不将调试增益描述为实机标定值。
- 验收范围为 5.1 和实际记录的一个 6.x 小版本，不泛化为所有 6.x。
- 环境缺失时可继续静态审计和脚本准备，但对应版本保持“未运行验证”，不能交付为已兼容。

## 重点风险与验收对应

1. 多个相近 URDF 导致选错模型：源哈希和结构基准检查。
2. package 路径、纹理或 USD 引用依赖本机绝对路径：移到另一临时目录重新打开资产。
3. 固定关节合并导致 link/传感器坐标丢失：保留源到 USD 的映射，检查所有必要坐标系；不机械要求 USD 刚体数量等于源 link 数量。
4. 四个夹爪滑动关节被误当作已定义 mimic：检查资料、行程和指尖动作，不推断联动比例。
5. 浮动整机接触不稳定，或版本 schema/驱动语义不同：两版独立执行关节、重力、接触及整机测试。

## 已执行任务

### 1. 下载并实际使用 NVIDIA skills

- [x] 从 Isaac Sim 官方仓库安装到本项目 `.agents/skills/`：`urdf-mjcf-to-usd-conversion`、`usd-articulation`、`physics-simulation`、`usd-composition-architecture`、`isaac-sim-validator`、`isaac-sim-orchestrator`。
- [x] 阅读各 SKILL.md 及实际需要的脚本，记录来源、版本/commit；按任务阶段应用，不只完成下载。
- [x] 如需安装环境或排查启动问题，再补充 `isaac-sim-installation`、`isaac-sim-troubleshooting`。
- [x] 识别技能示例针对的版本；5.1 依据本地扩展/API 和对应官方文档适配。

验收：技能文件存在、来源可追溯、后续报告记录每个技能实际用途。

### 2. 确定并验证两版运行环境

- [x] 盘点 `/home/xq/isaacsim`、其他 Python 环境/容器、GPU/驱动、可用磁盘。
- [x] 锁定 5.1 与一个具体 6.x 版本及各自启动命令；若需部署 6.x，使用独立目录/环境，不覆盖现有 5.1。
- [x] 两版分别执行最小启动、USD 打开和物理步进检查，保存版本、日志和退出状态。

产物：`reports/environment.json`。验收：两版有明确可执行入口；缺少环境时明确列出阻塞项。

### 3. 完整审计源资产与机器人参数

- [x] 校验源包清单/哈希，解析所有引用，输出 `reports/source_audit.json`。
- [x] 检查单位、关节拓扑、轴向、限位、质量、惯量正定性、碰撞网格及初始姿态。
- [x] 核对 SDK 配置中的关节名称、夹爪行程/命令映射、底盘转向及轮轴定义。
- [x] 形成 `configs/r1pro_2026_common.json`：明确厂商参数、仿真参数、坐标系和源到 USD 命名映射约定。
- [x] 检查旧版外观与当前几何的对应关系，判断哪些材质可直接迁移、哪些需要 UV/投影；无法可靠对应的部分显式记录。

验收：所有修改或补充参数均有依据；无法确认的物理参数不被静默补全。

### 4. 实现并验证 Isaac Sim 5.1 资产

- [x] 创建 `scripts/convert_51.py` 和 `configs/import_51.json`，使用 5.1 的真实导入 API。
- [x] 保留/映射所需坐标系，明确固定关节合并、碰撞近似、自碰撞、惯量及驱动策略。
- [x] 输出 `outputs/isaacsim_5_1/r1pro_2026.usd` 及全部依赖；配置 Articulation 和底盘/双臂/夹爪驱动。
- [x] 加入外观配置，核对模型尺寸、左右结构、材质和纹理。
- [x] 在 5.1 完成加载与基本关节测试，保存日志与截图。

验收：引用无缺失、无导致仿真失败的错误；关节和源文件映射可核对。

### 5. 实现并验证 Isaac Sim 6.x 资产

- [x] 创建 `scripts/convert_6x.py` 和 `configs/import_6x.json`，使用实际安装版本的导入器和物理后端 API。
- [x] 从同一源 URDF 生成 `outputs/isaacsim_6_x/r1pro_2026.usd` 及依赖，明确记录 schema/驱动差异。
- [x] 使用共同参数基准与外观映射，在 6.x 完成加载与基本关节测试。

验收：两版关节名称、轴向、零位和限位的语义一致；不将 6.x 文件重命名当作 5.1 版本。

### 6. 两版独立完成仿真验收

- [x] 创建 `scripts/validate_robot.py` 和必要的版本适配入口；输出结构化结果及日志。
- [x] 静态检查：资源、尺寸、关节/坐标映射、质量与惯量、碰撞、Articulation、驱动配置。
- [x] 固定基座测试场景：安全范围内逐关节驱动，测试双臂、躯干、夹爪开合，记录目标与实际位置。
- [x] 浮动整机测试场景：启用重力与地面，验证初始稳定性、底盘转向/滚动与接触；检查 NaN、关节发散、穿透和结构脱落。
- [x] 在运行前将步数、步长、目标幅度、误差容限与接触阈值写入 `configs/validation.json`，解释选择依据；不为通过测试而隐式放宽。
- [x] 两版使用相同场景与指标，生成 `reports/isaacsim_5_1/`、`reports/isaacsim_6_x/` 和兼容性对照表。
- [x] 将输出包复制到不同目录后再次加载，验证相对引用和资源完整性。

验收：两版均有实际运行记录；每项标注通过/失败/未验证，重大物理异常解决后才标记完成。

### 7. 打包交付

- [x] 将通过验证的资产分别打包到 `deliverables/r1pro_2026_usd_isaacsim_5_1/` 和 `deliverables/r1pro_2026_usd_isaacsim_6_x/`，保留原厂商包。
- [x] 每包包括入口 USD、依赖、精确软件版本、导入说明、关节控制说明、已知限制、验证报告和校验清单。
- [x] 保留转换脚本、配置与环境记录，保证重新生成步骤可复现。

验收：用户可按说明在两个目标版本中导入和运行，报告明确哪些功能经过测试。

## 用户确认

用户已确认本计划并明确接受 NVIDIA EULA。已在当前会话顺序执行，分别交付 5.1 与 6.2.0 PhysX 资产；硬件标定、其他 6.x 和 Newton 不属于已验证范围。
