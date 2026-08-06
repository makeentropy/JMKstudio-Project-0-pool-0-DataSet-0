# JMKstudio Workparty Group Project — OKR & 全景规格

## Why
JMKstudio 团队协作项目需要一套 **数据可保全、版本可追溯、状态可回滚、环境可复现** 的统一基础设施。
当前分散的工具链（虚拟机、NAS、快照、Git、加密工具）缺乏统一编排，导致：
1. 数据在 Workspace / VM / NAS 之间割裂，没有统一快照语义
2. 版本控制只覆盖代码文件，未覆盖二进制数据 / 模型 / 环境状态
3. 数据完整性依赖人工校验，没有不可篡改的校验链
4. 团队协作缺乏"项目快照 → 签名 → 分发 → 验证"的闭环

## What Changes (O — 目标层)
| 目标编号 | 目标名称 | 对应周期 | 负责人域 |
|---------|---------|---------|---------|
| O1 | 建立 Workspace 统一快照与版本控制体系 | Q3 | workspace / versioning |
| O2 | 构建 virtual-fs-container 虚拟文件系统容器框架 | Q3 | storage / fs-container |
| O3 | 落地端到端数据保全与安全校验链（GPG+CA+Merkle+隐写） | Q3-Q4 | security / datachain |
| O4 | 打通 VM 快照与项目快照，实现"环境+数据"联合可复现 | Q4 | vm / snapshot |
| O5 | 接入 NAS / S3 多后端存储池，形成数据保全底座 | Q3 | storage / nas-pool |

## Impact
- Workspace 快照创建时间 < 30s（10GB 以内增量）
- 数据完整性校验覆盖率 100%，篡改可检测率 100%
- 虚拟机 + 项目联合回滚成功率 ≥ 99%
- 存储后端（本地/NAS/S3）切换对上层透明

---

## ADDED Requirements — KR 层（关键结果）

### O1 — Workspace 统一快照与版本控制

#### KR 1.1 Workspace 快照原语
- **Scenario**: 手动创建完整快照
  - **WHEN** 用户执行 `workspace snapshot create --full --tag "milestone-v1"`
  - **THEN** 系统在 60s 内生成完整快照，返回 snapshot_id、版本标签、校验和

- **Scenario**: 自动增量快照
  - **WHEN** Workspace 文件变更超过阈值或定时触发
  - **THEN** 系统基于最近一次完整/增量快照创建差异快照，记录 added/changed/deleted 文件清单

- **Scenario**: 版本标签与分支
  - **WHEN** 用户对快照打 tag 或创建 branch
  - **THEN** tag/branch 元数据写入版本索引，支持按 tag 回滚、按 branch diff

#### KR 1.2 回滚与清理策略
- **Scenario**: 按快照回滚
  - **WHEN** 用户请求 `workspace restore <snapshot_id>`
  - **THEN** 系统先创建当前状态保护快照，再执行回滚，并记录回滚操作日志

- **Scenario**: 快照保留策略
  - **WHEN** 快照数量超过上限或超过保留天数
  - **THEN** 系统按 GFS 风格策略（n 小时内每小时、n 天内每天、每周、每月）清理，保留完整快照链不被截断

---

### O2 — virtual-fs-container 框架

#### KR 2.1 容器抽象层（Container Runtime Interface）
- **Scenario**: 创建虚拟容器挂载 Workspace
  - **WHEN** `vfs create --name proj-dev --backend overlay --source /workspace/project`
  - **THEN** 创建容器元数据（container_id、层栈、后端类型），返回挂载点路径

- **Scenario**: 容器层栈（Layer Stack）
  - **WHEN** 容器进行写操作
  - **THEN** 数据写入 upper（可写层），lower（只读层）保持不变；支持 commit 生成新只读层

#### KR 2.2 OverlayFS / 纯用户态 COW 双实现
- **Scenario**: OverlayFS 后端（Linux Native）
  - **WHEN** 内核支持 overlay 且有特权
  - **THEN** 使用 kernel overlayfs，提供最高性能

- **Scenario**: 纯用户态 COW 后端（跨平台/无特权）
  - **WHEN** 无内核支持或无特权
  - **THEN** 自动降级为用户态 COW 实现，API 与 OverlayFS 后端完全一致

#### KR 2.3 多后端存储适配
- **Scenario**: NAS NFS 后端
  - **WHEN** 容器指定 `--backend-storage nas://192.168.1.10/volume1/pool`
  - **THEN** 容器层数据透明读写 NAS，本地仅缓存元数据

- **Scenario**: S3 兼容后端
  - **WHEN** 容器指定 `--backend-storage s3://bucket/pool`
  - **THEN** 对象级存取 + 本地缓存层，支持部分读取

---

### O3 — 数据保全与安全校验链（baseXOR-prober + GPGCA + Merkle）

#### KR 3.1 Merkle DAG 快照校验树
- **Scenario**: 快照生成校验根
  - **WHEN** 快照创建完成
  - **THEN** 按文件块 → 文件 → 目录 → 快照层级构建 Merkle Tree，生成 root_hash 写入元数据

#### KR 3.2 GPG + CA 签名体系
- **Scenario**: CA 签发快照签名证书
  - **WHEN** 用户是已注册成员
  - **THEN** 由项目 CA 签发快照签名证书，每次快照创建使用成员私钥签名，CA 公钥可验证链

- **Scenario**: 快照验签
  - **WHEN** 从不可信介质恢复快照
  - **THEN** `snapshot verify <id>` 校验 CA 链 → 成员签名 → Merkle root → 数据块哈希，全部通过才标记 VERIFIED

#### KR 3.3 baseXOR-prober 隐写数据空间
- **Scenario**: 隐写注入校验锚点
  - **WHEN** 数据块写入存储池
  - **THEN** baseXOR-prober 在数据块尾部/预留槽位注入不可见的校验锚点（含块哈希、链序号、CA 指纹）

- **Scenario**: 隐写探针扫描（prober）
  - **WHEN** 运行 `prober scan /mnt/nas/pool`
  - **THEN** 分布式扫描所有数据块，提取隐写锚点，检测缺失/错位/篡改块，生成保全审计报告

#### KR 3.4 分布式区块链一致性账本
- **Scenario**: 快照事件上链（轻量链）
  - **WHEN** 快照签名完成
  - **THEN** snapshot_id + root_hash + signer + timestamp 写入团队共享链式账本（HashChain，无需公链）

- **Scenario**: 跨成员一致性校验
  - **WHEN** 成员 A 的快照事件与成员 B 的不一致
  - **THEN** 系统告警并进入仲裁流程，以多数 CA 签名为准

---

### O4 — VM 快照与项目快照联调

#### KR 4.1 统一快照管理器（UnifiedSnapshotManager）
- **Scenario**: 创建联合快照（VM + Workspace）
  - **WHEN** `snapshot create --unified --vm "devbox-01" --workspace /workspace/proj --tag "sprint-5-end"`
  - **THEN** 系统先 quiesce VM 文件系统 → 创建 VM 快照 → 创建 Workspace 快照 → 两者绑定为一个 unified_snapshot_id

- **Scenario**: 联合回滚
  - **WHEN** `snapshot restore <unified_snapshot_id>`
  - **THEN** 先回滚 Workspace（带保护快照）→ 再回滚 VM → 启动后自检版本一致性

#### KR 4.2 libvirt / QEMU 适配层
- 提供 VM adapter 抽象接口，支持 libvirt（KVM）和 VirtualBox 后端
- 每个 adapter 实现：list_snapshots / create_snapshot / restore_snapshot / delete_snapshot

---

### O5 — NAS / S3 存储池底座

#### KR 5.1 存储池抽象（StoragePool）
- 支持 LocalPool、NASNfsPool、NASSmbPool、S3Pool 四种实现
- 统一 API：put / get / stat / list / delete / verify_integrity / replicate

#### KR 5.2 副本与纠删码
- 关键数据（快照元数据、CA 链、账本）≥ 3 副本，跨不同存储池
- 大数据块支持 Reed-Solomon (4+2) 纠删码，单盘损坏可重建

---

## 交付物清单（Delivery）

| 模块 | 文件路径 | 说明 |
|-----|---------|------|
| OKR 文档 | `.trae/specs/jmkstudio-workparty-okr/spec.md` | 本文件 |
| 检查清单 | `.trae/specs/jmkstudio-workparty-okr/checklist.md` | KR 验收清单 |
| 任务拆分 | `.trae/specs/jmkstudio-workparty-okr/tasks.md` | 可执行任务列表 |
| OKR 模块代码 | `src/ai_llm_agent_crawler/okr/` | OKR 领域模型与注册 |
| Workspace 快照 | `src/ai_llm_agent_crawler/workspace/` | WorkspaceSnapshotManager |
| virtual-fs-container | `src/ai_llm_agent_crawler/fs_container/` | VFS Container 框架 |
| GPGCA + Merkle + 隐写 | `src/ai_llm_agent_crawler/security/`（扩展） | MerkleTree、BaseXORProber、HashChainLedger |
| VM 适配层 | `src/ai_llm_agent_crawler/vm_snapshot/` | UnifiedSnapshotManager + VM adapters |
| 存储池扩展 | `src/ai_llm_agent_crawler/storage/`（扩展） | NASPool、S3Pool、Replication、ErasureCoding |
