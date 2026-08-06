# JMKstudio Workparty OKR — Checklist 验收清单

## O1 — Workspace 统一快照与版本控制
- [ ] KR 1.1.1 手动创建完整快照，返回 snapshot_id / tag / checksum
- [ ] KR 1.1.2 增量快照自动计算 added/changed/deleted
- [ ] KR 1.1.3 Tag / Branch 元数据写入版本索引
- [ ] KR 1.1.4 按 tag 回滚、按 branch diff
- [ ] KR 1.2.1 回滚前自动创建保护快照
- [ ] KR 1.2.2 回滚操作日志（audit log）
- [ ] KR 1.2.3 GFS 风格保留策略（小时/天/周/月）
- [ ] KR 1.2.4 快照链完整性保护（不截断完整链）

## O2 — virtual-fs-container 框架
- [ ] KR 2.1.1 Container 抽象层：create / destroy / mount / umount
- [ ] KR 2.1.2 Layer Stack 抽象：lower / upper / workdir / merged
- [ ] KR 2.1.3 commit 生成新只读层
- [ ] KR 2.2.1 OverlayFS 后端（kernel native）
- [ ] KR 2.2.2 纯用户态 COW 后端（无特权、跨平台）
- [ ] KR 2.2.3 双后端 API 完全一致
- [ ] KR 2.3.1 NAS NFS 后端（nas:// URI）
- [ ] KR 2.3.2 S3 兼容后端（s3:// URI + 本地缓存）

## O3 — 数据保全与安全校验链
- [ ] KR 3.1.1 文件块级 Merkle Tree 构建
- [ ] KR 3.1.2 目录级 / 快照级 Merkle root 聚合
- [ ] KR 3.1.3 root_hash 写入快照元数据
- [ ] KR 3.2.1 项目 CA：根证书 / 成员证书签发
- [ ] KR 3.2.2 成员私钥签名快照
- [ ] KR 3.2.3 CA 链 → 成员签名 → Merkle root → 块哈希 四级验签
- [ ] KR 3.3.1 baseXOR-prober 隐写锚点注入（块哈希 + 链序号 + CA 指纹）
- [ ] KR 3.3.2 prober scan 分布式扫描
- [ ] KR 3.3.3 缺失 / 错位 / 篡改块检测 + 审计报告
- [ ] KR 3.4.1 HashChain 轻量账本：append / verify / sync
- [ ] KR 3.4.2 跨成员一致性对比 + 多数签名仲裁

## O4 — VM 快照联调
- [ ] KR 4.1.1 UnifiedSnapshotManager：create_unified / restore_unified
- [ ] KR 4.1.2 VM quiesce → VM snap → WS snap → 绑定 unified_id 流程
- [ ] KR 4.1.3 联合回滚：WS 保护快照 → WS 回滚 → VM 回滚 → 一致性自检
- [ ] KR 4.2.1 VM Adapter 抽象接口定义
- [ ] KR 4.2.2 libvirt/KVM Adapter 实现
- [ ] KR 4.2.3 VirtualBox Adapter 实现（可选）

## O5 — NAS / S3 存储池底座
- [ ] KR 5.1.1 StoragePool 统一接口：put/get/stat/list/delete/verify/replicate
- [ ] KR 5.1.2 LocalPool 实现
- [ ] KR 5.1.3 NASNfsPool / NASSmbPool 实现
- [ ] KR 5.1.4 S3Pool 实现
- [ ] KR 5.2.1 三副本跨池复制（关键数据）
- [ ] KR 5.2.2 Reed-Solomon (4+2) 纠删码编解码
