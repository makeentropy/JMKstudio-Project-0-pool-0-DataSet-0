# 经验数据池与自反思智能体系统 - 实施计划（分解与优先级任务列表）

## [x] Task 1: 经验数据模型与数据池核心模块
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 设计并实现经验数据模型（ExperienceRecord），定义标准字段结构
  - 实现 ExperienceDataPool 核心类，提供经验数据的写入、查询、过滤、删除接口
  - 基于现有 NASStoragePool 实现经验数据的持久化存储
  - 实现经验数据质量评分与自动清洗（去重、降噪）
  - 建立索引机制，支持按时间、类型、质量等多维度快速查询
- **Acceptance Criteria Addressed**: [AC-1]
- **Test Requirements**:
  - `programmatic` TR-1.1: 经验记录写入后可通过 ID 查询到，字段完整
  - `programmatic` TR-1.2: 支持按时间范围、任务类型、结果状态等条件过滤查询
  - `programmatic` TR-1.3: 重复经验数据可被去重识别
  - `programmatic` TR-1.4: 1000 条经验数据的查询响应时间 < 1 秒
- **Notes**: 复用现有 storage/pool.py 进行底层存储，dataset 模块进行数据处理

## [x] Task 2: 经验池快照与版本管理
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 基于现有 versioning 模块扩展，实现经验池的快照创建功能
  - 支持快照版本号管理（语义化版本）和元数据记录
  - 实现快照对比功能，可对比两个版本间的经验数据差异
  - 支持快照回滚，可将经验池恢复到指定历史版本
  - 实现快照生命周期管理（自动清理过期快照、归档）
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `programmatic` TR-2.1: 创建快照后可通过版本号查询到快照元数据
  - `programmatic` TR-2.2: 两个不同快照的差异对比能正确列出新增/删除/修改的经验记录
  - `programmatic` TR-2.3: 回滚到指定版本后，经验池数据与该版本快照一致
  - `programmatic` TR-2.4: 连续创建 10 个快照，版本号正确递增
- **Notes**: 复用现有 versioning/snapshot_manager.py 和 versioning/version_manager.py

## [x] Task 3: 自反思智能体 - 自我评估模块
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 实现 SelfAssessment 类，提供多维度自我评估能力
  - 定义评估维度：准确性、效率、完整性、资源使用率、创新性
  - 实现可配置的评分算法，支持自定义维度和权重
  - 每个评分附详细依据说明（哪些经验数据支撑了该评分）
  - 与经验池集成，自动从最近经验中提取评估数据
- **Acceptance Criteria Addressed**: [AC-3]
- **Test Requirements**:
  - `programmatic` TR-3.1: 给定一组经验数据，自我评估输出 5 个维度的评分，均在 0-1 范围内
  - `programmatic` TR-3.2: 每个维度评分都有对应的依据说明
  - `programmatic` TR-3.3: 修改权重配置后，综合评分按预期变化
  - `programmatic` TR-3.4: 空经验数据输入有合理的默认评分和说明
- **Notes**: 参考现有 dataset/quality_validator.py 的评估模式

## [x] Task 4: 自反思智能体 - 错误归因与经验总结
- **Priority**: high
- **Depends On**: Task 3
- **Description**: 
  - 实现 ErrorAttributor 类，支持 5 种以上错误分类
  - 实现基于规则的错误归因引擎，结合历史相似案例计算置信度
  - 实现 ExperienceSummarizer 类，从成功/失败案例中提炼经验模式
  - 定义 Heuristic 数据模型，表示可复用的经验法则
  - 实现模式提取算法，识别高频出现的成功/失败模式
- **Acceptance Criteria Addressed**: [AC-4]
- **Test Requirements**:
  - `programmatic` TR-4.1: 给定一个失败案例，错误归因输出分类和置信度
  - `programmatic` TR-4.2: 至少支持 5 种错误分类（数据/策略/参数/环境/未知）
  - `programmatic` TR-4.3: 从 100 条经验中能提取出至少 3 条可复用的经验模式
  - `programmatic` TR-4.4: 归因结果包含关键证据（指向具体的经验记录）
- **Notes**: 可使用聚类或频度统计进行模式挖掘

## [x] Task 5: 维度空间探针 - 核心探测引擎
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 实现 DimensionSpaceProbe 类，作为维度空间探针的核心入口
  - 整合现有 dimension 模块的质量评估、奇点检测、质能模型功能
  - 实现 5 大维度的全面探测：质量维度、结构维度、统计维度、内容维度、关系维度
  - 每个维度生成量化指标和定性描述
  - 输出结构化探测报告（ProbeReport）
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - `programmatic` TR-5.1: 对标准数据集进行全维度探测，输出包含 5 个维度的报告
  - `programmatic` TR-5.2: 每个维度都有量化指标（数值）和定性描述（文本）
  - `programmatic` TR-5.3: 探测报告中标记了发现的奇点和异常点
  - `programmatic` TR-5.4: 空数据集或极端数据集不会导致探针崩溃
- **Notes**: 大量复用现有 dimension/ 模块代码，主要做整合和增强

## [x] Task 6: 维度空间探针 - 路径探测与空间分析
- **Priority**: medium
- **Depends On**: Task 5
- **Description**: 
  - 实现路径探测功能：沿着指定维度方向进行深度扫描
  - 支持自定义探测步长和探测深度
  - 输出维度方向上的数据分布、密度变化、临界点位置
  - 实现维度空间的拓扑描述和距离矩阵
  - 实现异常区域坐标定位和边界识别
- **Acceptance Criteria Addressed**: [AC-6]
- **Test Requirements**:
  - `programmatic` TR-6.1: 沿指定维度路径探测，输出该维度上的数据分布直方图
  - `programmatic` TR-6.2: 能识别出维度上的临界点（如密度突变点、异常值）
  - `programmatic` TR-6.3: 修改步长参数后，探测结果粒度相应变化
  - `programmatic` TR-6.4: 支持多维度组合路径探测
- **Notes**: 可使用直方图、核密度估计等统计方法

## [x] Task 7: 自反思智能体 - 自我认知画像
- **Priority**: medium
- **Depends On**: Task 4
- **Description**: 
  - 实现 AgentProfile 类，维护智能体能力画像
  - 画像内容：擅长领域、薄弱环节、知识边界、典型错误类型、改进方向
  - 画像基于历史经验数据动态生成，而非静态配置
  - 实现画像更新机制：随新经验积累自动更新画像
  - 提供画像查询和导出接口
- **Acceptance Criteria Addressed**: [AC-10]
- **Test Requirements**:
  - `programmatic` TR-7.1: 给定一定量历史经验，能生成包含 5 个方面的能力画像
  - `human-judgement` TR-7.2: 画像内容与实际经验数据表现一致，具有合理性
  - `programmatic` TR-7.3: 添加新经验后，画像内容有相应更新
  - `programmatic` TR-7.4: 支持画像的 JSON 格式导出
- **Notes**: 画像是自省结果的高层抽象，需要结合统计和规则

## [x] Task 8: 技能自迭代闭环
- **Priority**: high
- **Depends On**: Task 4, Task 2
- **Description**: 
  - 基于现有 SkillOptimizer 扩展，实现完整的自迭代闭环
  - 实现优化触发机制：性能下降触发、经验积累触发、手动触发
  - 实现优化策略生成：基于反省分析结果生成具体优化方案
  - 集成版本验证：优化后自动运行测试，对比新旧版本
  - 实现渐进部署：灰度发布、A/B 测试、自动回滚机制
  - 记录完整迭代轨迹：原因、变更、效果、时间戳
- **Acceptance Criteria Addressed**: [AC-7]
- **Test Requirements**:
  - `programmatic` TR-8.1: 积累足够反馈经验后，自动触发优化流程
  - `programmatic` TR-8.2: 优化后生成新版本 Skill，版本号正确递增
  - `programmatic` TR-8.3: 自动运行测试验证，输出性能对比报告
  - `programmatic` TR-8.4: 性能下降时支持自动回滚到上一版本
- **Notes**: 大量复用现有 dataset/skill_optimizer.py，主要增强反省驱动的优化

## [x] Task 9: 经验分析工具集 - 趋势分析与模式挖掘
- **Priority**: medium
- **Depends On**: Task 2
- **Description**: 
  - 实现 TrendAnalyzer 类，分析智能体能力随时间的变化趋势
  - 输出整体能力曲线、各维度趋势、关键拐点标注
  - 实现 PatternMiner 类，从历史经验中挖掘高频模式
  - 识别成功模式和失败模式，附频率、特征、适用场景
  - 实现对比分析功能：不同版本/任务类型/策略间的效果对比
- **Acceptance Criteria Addressed**: [AC-8, AC-9]
- **Test Requirements**:
  - `programmatic` TR-9.1: 有 10 个以上时间点的经验数据时，能生成趋势分析报告
  - `human-judgement` TR-9.2: 趋势曲线和拐点标注合理，符合数据实际走向
  - `programmatic` TR-9.3: 从 100 条以上经验中能挖掘出至少 3 种有意义的模式
  - `human-judgement` TR-9.4: 挖掘出的模式具有可解释性和实用价值
- **Notes**: 可使用滑动窗口、移动平均、聚类等算法

## [x] Task 10: 系统集成与 API 层
- **Priority**: medium
- **Depends On**: Task 8, Task 6, Task 9, Task 7
- **Description**: 
  - 实现统一的 IntrospectiveAgent 类，整合所有子模块
  - 提供简洁的高层 API：run_task_with_introspection, get_profile, probe_dataset 等
  - 实现命令行接口（CLI），支持常用操作
  - 编写集成测试，验证端到端流程
  - 与现有项目模块无缝集成，不破坏现有功能
- **Acceptance Criteria Addressed**: [AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-10]
- **Test Requirements**:
  - `programmatic` TR-10.1: 端到端流程：执行任务 → 沉积经验 → 自省分析 → 生成报告
  - `programmatic` TR-10.2: CLI 命令可正常执行并输出结果
  - `programmatic` TR-10.3: 现有模块的所有原有测试仍然通过
  - `programmatic` TR-10.4: 导入新模块不会导致现有导入链断裂
- **Notes**: 这是整合性任务，确保所有模块协同工作

## [x] Task 11: 文档与示例
- **Priority**: low
- **Depends On**: Task 10
- **Description**: 
  - 编写模块 API 文档和使用指南
  - 提供完整的使用示例代码
  - 编写最佳实践文档
  - 更新项目 README
- **Acceptance Criteria Addressed**: [AC-8, AC-9, AC-10]
- **Test Requirements**:
  - `human-judgement` TR-11.1: 文档清晰易懂，覆盖所有主要功能
  - `programmatic` TR-11.2: 示例代码可直接运行并产生预期结果
  - `human-judgement` TR-11.3: README 准确描述项目功能和使用方法
- **Notes**: 文档质量影响项目可用性，不可忽视
