# SDD ledger — plan: docs/superpowers/plans/2026-10-22-r1pro-dual-version-usd.md

用户已于 2026-10-22 确认执行。在当前会话依次实施。

Ruling: 仓库尚无提交，使用 codex/r1pro-dual-usd 分支就地工作，避免迁移未跟踪计划与忽略的厂商文件；仅新建工作文件，不改源文件。代价：没有 worktree 文件系统隔离。
Pre-flight: 任务 3 的共同参数基准供任务 4/5 使用；任务 6 消费两版独立资产与配置，任务 7 仅打包通过的版本。
Ruling: 完整任务不以环境可用为假设；若 6.x 无可安装发行版或无法运行，仍完成 5.1 与独立于运行时的工作，6.x 保持未验证，不伪造成功。

Task 1: in progress — official skills download.
Task 2: in progress — local GPU RTX 5070 Ti Laptop 12 GB; driver 580.178.04; /home/xq/isaacsim VERSION 5.1.0-rc.19+release.26219.9c81211b.gl.

Task 1: complete — six requested skills plus installation and troubleshooting installed/read, file hashes and application mapping in skills.json.
Task 2: 5.1 smoke passed 360 steps; 6.2.0.0 isolated pip installation running after explicit user EULA approval.
Task 3: source audit passed, 7135 hash checks, total mass 93.26568518 kg, valid positive inertias, 3 wheel rating warnings.
Task 4: imported 46 bodies / 28 DOFs, static check passed; fixed-base per-joint physics checks 28/28 passed.
Ruling: no mimic relation authored because source has none; fingers remain four independently addressable DOFs. Simulation gains and missing wheel caps are explicit assumptions.
Ruling: native OmniPBR.mdl is an Isaac Sim built-in dependency, exempted from standalone USD filesystem resolution; all other unresolved dependencies still fail.
Ruling: CPU simulation with PhysX and 240 Hz is used for one-robot 5.1 validation. Source masses, limits and geometry retained; visual-only UV overrides mapped for 25 links and neutral fallback recorded for 21, including the changed base geometry.

Task 2: 6.2.0.0 pip installation complete. Native compatibility checker printed System checking result: PASSED; driver supported, VRAM enough (more recommended). Ubuntu native host, not WSL.
Task 4: mobile_v2 passed resting contact, steering and rolling; two rendered views generated. Material-binding regression found inherited stronger binding, fixed at visuals ancestor; image cropping corrected with explicit camera apertures/focal length.
Ruling: test renders show a reference-styled base and sensor heads; do not describe those as exact factory appearance. Geometry retained from 2026 URDF.
Task 5: native 6.2 import running.

Task 5: complete — native 6.2 import, explicit lowercase physx variant selection, 46 bodies / 28 DOFs, common source mass/inertia and appearance overrides. New hierarchical paths captured in asset_configuration.json.
Ruling: both versions are validated with PhysX; Newton and other 6.x versions remain outside verified scope.
Ruling: 5.1 importer principal-axis rounding changed torso_link1 off-diagonals by up to 3.65e-6 kg m²; reauthored source inertia eigensystems for both versions instead of relaxing comparisons.
Task 6: complete — final fixed51 28/28, release fixed62 28/28; release mobile51/mobile62 all contact/steering/mean wheel speed checks passed. Mean wheel speed at 0.5 command: 5.1 0.434–0.438 rad/s; 6.2 0.406–0.417 rad/s. Instantaneous contact-induced velocity variation is retained in reports, not represented as accurate hardware tracking.
Final review: no Critical; Important source-identity and reconversion-staleness findings fixed with shared source_contract and 4 RED→GREEN tests. Mobile displacement anchor corrected to post-steering; mean wheel angular travel checked against original 0.15 rad/s tolerance, final reruns passed.
Final review: dependency-containment comment regraded Important for portability; all resolved USD layers/assets must reside under package root. Both packages pass after relocation to /tmp and real 3-second demo runs. 6.x converter now preserves nonzero failure exit_code; all runtime commands use checked JSON freshness gate.
Final review: 13 unit tests pass; richer static gate checks link poses, masses, COM, inertia, moving/fixed joint endpoints, 46 convex colliders and portable dependency closure. NVIDIA script validator level 2: 0 errors, 3 heuristic warnings (app variable naming, literal headless parsing, World-created stage), all manually checked against execution.
Ruling: Replicator wait_until_complete during non-capture shutdown stalled 6.2. Explicit wait_for_replicator=False after synchronous capture solves it; bounded checked launches and fresh reports prevent false success.
Task 7: asset directories, demo scenes, reproduction code, docs and validation evidence prepared; relocation passed in both native runtimes. ZIP/checksum sealing and final inventory follow.
Skill distillation: reusable lessons recorded here (variant casing/layout differences, source inertia precision, ancestor material-binding precedence, completion-report freshness). Upstream skill files left unchanged.

Task 7: complete — both ZIPs sealed, CRC and every internal SHA-256 verified. Final vendor audit again checked 7135 files with zero mismatches. Release manifest records archive hashes. No unresolved Important review findings; scope limitations are documented in each package.
