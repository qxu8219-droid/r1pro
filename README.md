# R1Pro 2026：Isaac Sim 5.1 / 6.2 USD

本项目从指定 SDK 2026 URDF 分别生成两个版本的机器人资产，并保留转换、静态核对和物理运行证据。原厂资料在 `deliverables/r1pro_2026_vendor_sources_20261022/`，不作修改。

## 交付与运行范围

- `deliverables/r1pro_2026_usd_isaacsim_5_1/`：Isaac Sim 5.1，PhysX。
- `deliverables/r1pro_2026_usd_isaacsim_6_x/`：Isaac Sim **6.2.0**，PhysX；其他 6.x 小版本及 Newton 尚未验证。
- 各包入口为 `r1pro_2026.usd`，另有可直接打开的 `demo.usda`。应复制整个包，不要只复制入口文件。
- 精确版本和验收结果以各包 `validation/` 中的报告为准。Linux 本机 5.1 版本字符串含 `rc.19`，不是本项目修改或构建的软件。

## 使用资产

在对应版本的 Isaac Sim 中打开 `demo.usda` 后开始播放，可查看机器人在地面上的初始状态。机器人入口本身不附带地面、灯光或世界固定约束；添加到已有场景时，场景应具有 PhysicsScene 和地面。

6.2 选择 **PhysX** 物理后端。命令行启动可以使用：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venvs/isaacsim62/bin/isaacsim \
  --/exts/isaacsim.physics.newton/auto_switch_on_startup=false \
  --/exts/isaacsim.core.simulation_manager/default_engine=physx
```

源文件共有 46 个 link、17 个固定关节、28 个活动关节，整机质量约 93.266 kg。5.1 的 Articulation 根位于 `/r1pro_2026/base_link`；6.2 位于 `/r1pro_2026/Geometry/base_link`。实例化后要替换根路径前缀。通过关节名称查找控制索引，不要假定两版 DOF 数组顺序固定。

四个夹爪滑动关节保持独立：joint1 范围 `[0, 0.05]` m，joint2 范围 `[-0.05, 0]` m。对称开合时可分别给 `+s/-s`，但该约定只是当前模型的对称命令方式，不证明实机的电机单位或传动关系。转动关节的控制 API 使用弧度，直接编辑 USD drive target 时使用度；滑动关节使用米。

## 复现

独立工具环境需要 Python 3.12、`numpy scipy pillow trimesh usd-core`。本机工具解释器为 `.venvs/tools/bin/python`。两版 Kit 环境必须分别运行转换和仿真，不能把 6.2 包装进 5.1 Python。

先在项目根目录定义：

```bash
SOURCE=deliverables/r1pro_2026_vendor_sources_20261022
OUT=outputs/rebuild_51  # 必须是全新或空目录
```

5.1 转换：

```bash
.venvs/tools/bin/python scripts/run_checked.py --report "$OUT/conversion.json" --accept imported -- \
  /home/xq/isaacsim/python.sh scripts/convert_51.py --source "$SOURCE" --output "$OUT"
```

6.2 转换（改用另一个全新 OUT）：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venvs/tools/bin/python scripts/run_checked.py --report "$OUT/conversion.json" --accept imported -- \
  .venvs/isaacsim62/bin/python scripts/convert_6x.py --source "$SOURCE" --output "$OUT"
```

随后对各自 OUT 依次执行：

```bash
.venvs/tools/bin/python scripts/configure_asset.py "$OUT"
.venvs/tools/bin/python scripts/appearance.py "$OUT" --source "$SOURCE"
.venvs/tools/bin/python tests/check_usd_asset.py "$OUT/r1pro_2026.usd"
```

物理验证示例（把 `ISAAC_PYTHON` 改为对应版本解释器；6.2 需已接受 EULA）：

```bash
ISAAC_PYTHON=/home/xq/isaacsim/python.sh
.venvs/tools/bin/python scripts/run_checked.py --report reports/recheck_fixed/results.json --timeout 240 -- \
  "$ISAAC_PYTHON" scripts/validate_robot.py --asset "$OUT/r1pro_2026.usd" --output reports/recheck_fixed --mode fixed
.venvs/tools/bin/python scripts/run_checked.py --report reports/recheck_mobile/results.json --timeout 240 -- \
  "$ISAAC_PYTHON" scripts/validate_robot.py --asset "$OUT/r1pro_2026.usd" --output reports/recheck_mobile --mode mobile --render
```

`run_checked.py` 同时检查进程退出和本轮新生成的结构化报告，防止 Kit 提前退出、旧报告残留导致假成功。源文件与选择清单均被固定 SHA-256 校验，转换拒绝写入非空目录和厂商源目录。

## 已知边界

- 验收是小幅关节运动、夹爪行程、落地、底盘转向与滚动的基础仿真检查。未验证全工作空间、负载抓取、长时间导航或真实硬件响应。
- 驱动增益和接触摩擦为仿真配置。三个轮子在 URDF 中缺少 effort/velocity，当前采用显式的测试假设：10 N·m、8 rad/s；需要实机标定后再用于定量控制研究。
- 自碰撞关闭；碰撞使用厂商网格的凸包。凹面精细接触、夹持力和碰撞简化误差尚未标定。
- 25 个部件采用厂商 UV，其中 3 个有少量明确记录的面级回退；其余 21 个采用参考配色，包括新旧几何不一致的底盘。该外观不是完整厂商复原。
- 相机/雷达安装坐标保留，未激活传感器渲染、相机外参转换、ROS 2 或实机 SDK 启动器。
- 5.1 使用内置 `OmniPBR.mdl`，无需将其从 Isaac Sim 安装目录复制到资产包；所有其他资产依赖须在包内。

技能来源及实际应用记录见 `reports/skills.json`；执行记录见 `reports/progress.md`。
