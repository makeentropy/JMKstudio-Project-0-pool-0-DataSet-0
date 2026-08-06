# JMKstudio Workparty OKR — Tasks 任务拆分

## Phase 1 — OKR 落地与核心骨架（本周）
- [x] T1.1 创建 OKR spec / checklist / tasks 文档
- [ ] T1.2 创建 `okr/` 模块：OKR 领域模型、Objective/KeyResult/Task 注册
- [ ] T1.3 创建 `workspace/` 模块骨架：WorkspaceSnapshotManager 接口
- [ ] T1.4 创建 `fs_container/` 模块骨架：VFS Container 接口
- [ ] T1.5 创建 `vm_snapshot/` 模块骨架：VM Adapter + UnifiedSnapshotManager
- [ ] T1.6 security 模块扩展骨架：MerkleTree / BaseXORProber / HashChainLedger
- [ ] T1.7 storage 模块扩展骨架：NASPool / S3Pool / ErasureCoding

## Phase 2 — O1 Workspace 快照（Q3 前 2 周）
- [ ] T2.1 WorkspaceSnapshotManager：create_full_snapshot
- [ ] T2.2 WorkspaceSnapshotManager：create_incremental_snapshot + diff 计算
- [ ] T2.3 Tag/Branch 元数据索引（refs/tags、refs/heads）
- [ ] T2.4 restore_snapshot：保护快照 + 回滚 + audit log
- [ ] T2.5 GFS 风格保留策略（RetentionPolicy）

## Phase 3 — O2 virtual-fs-container（Q3 第 3-4 周）
- [ ] T3.1 Container 抽象层 + Layer Stack 数据结构
- [ ] T3.2 OverlayFSBackend 实现（依赖 mount / umount）
- [ ] T3.3 UserSpaceCOWBackend 纯用户态实现
- [ ] T3.4 commit 生成只读层 + 层 GC
- [ ] T3.5 NASNfsBackend / S3Backend 存储后端接入

## Phase 4 — O3 数据保全链（Q3-Q4）
- [ ] T4.1 MerkleTree：块级树构建 + 根哈希 + 包含性证明
- [ ] T4.2 ProjectCA：根证书生成 + 成员证书签发 + 证书链验证
- [ ] T4.3 SnapshotSigner：成员签名 + CA 链验签
- [ ] T4.4 BaseXORProber：隐写锚点编码 / 解码 / 注入 / 提取
- [ ] T4.5 DistributedProber：多 worker 分布式扫描 + 审计报告
- [ ] T4.6 HashChainLedger：append-only 链 + 跨成员 sync + 多数仲裁

## Phase 5 — O4 VM 快照联调（Q4）
- [ ] T5.1 VM Adapter 接口：create/restore/list/delete
- [ ] T5.2 LibvirtKVMAdapter 实现（对接 virsh）
- [ ] T5.3 UnifiedSnapshotManager：create_unified（quiesce → vm_snap → ws_snap → bind）
- [ ] T5.4 UnifiedSnapshotManager：restore_unified（保护→回滚→自检）

## Phase 6 — O5 存储池底座（Q3 并行）
- [ ] T6.1 StoragePool 接口 + LocalPool
- [ ] T6.2 NASNfsPool / NASSmbPool
- [ ] T6.3 S3Pool（Boto3 / Minio SDK）
- [ ] T6.4 ReplicationManager：3 副本跨池复制
- [ ] T6.5 ReedSolomonCodec：(4+2) 纠删码编解码 + 重建

## Phase 7 — E2E 集成测试
- [ ] T7.1 Workspace → snapshot → Merkle + GPG签名 → HashChain 闭环测试
- [ ] T7.2 Container 创建 → 写入 → commit → 还原 测试
- [ ] T7.3 VM+Workspace 联合快照回滚测试
- [ ] T7.4 Prober 扫描 + 篡改检测 + 审计报告生成
