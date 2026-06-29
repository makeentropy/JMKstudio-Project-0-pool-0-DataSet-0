# Experience 模块系统集成与 API 层 - 产品需求文档

## Overview
- **Summary**: 为 experience 模块添加 `IntrospectiveAgent` 自反思智能体统一入口类，使用 Facade 设计模式整合经验数据池、自我评估、错误归因、经验总结、画像生成、技能迭代、趋势分析、模式挖掘、对比分析和维度空间探测等所有子模块，提供简化的高层 API，隐藏内部复杂性，便于外部调用。
- **Purpose**: 解决 experience 模块各子模块分散、调用复杂的问题，提供一个统一的入口点，降低外部系统集成成本，提高开发效率。
- **Target Users**: 使用 experience 模块的开发者、需要集成自反思能力的 AI Agent 系统。

## Goals
- 提供统一的自反思智能体入口类 `IntrospectiveAgent`
- 整合所有子模块，对外提供简洁直观的 API
- 支持经验记录、自我反思、画像生成、趋势分析、模式挖掘、技能优化、快照管理、数据导出等核心功能
- 支持维度空间探针的可选集成
- 提供完整的集成测试覆盖

## Non-Goals (Out of Scope)
- 不修改现有子模块的内部实现
- 不添加新的子模块功能
- 不涉及数据库持久化方案的变更
- 不提供 GUI 界面
- 不修改除指定文件外的其他现有文件

## Background & Context
- 项目已有完整的 experience 模块，包含多个子模块：pool、self_assessment、attribution、snapshot、profile、iteration、analytics
- 各子模块功能独立，但外部调用需要分别初始化和管理多个对象
- 维度空间探针模块 (dimension/probe.py) 可作为可选组件集成
- 项目使用 pytest 进行测试，使用 pydantic 进行数据建模
- 代码风格要求使用 `from ai_llm_agent_crawler.utils.logging import get_logger`

## Functional Requirements
- **FR-1**: IntrospectiveAgent 初始化，支持 agent_name、storage_path、config 参数，自动创建并关联所有子模块
- **FR-2**: 记录经验功能：简化的 record_experience 接口，自动创建 ExperienceRecord 并添加到数据池
- **FR-3**: 自我反思功能：self_reflect 方法，执行自我评估→错误归因→经验总结→更新画像的完整流程
- **FR-4**: 获取自我画像：get_self_profile 方法，自动重新生成 AgentProfile
- **FR-5**: 趋势分析：analyze_trend 方法，简化的趋势分析报告接口
- **FR-6**: 模式挖掘：mine_patterns 方法，简化的经验模式挖掘接口
- **FR-7**: 技能优化：optimize_skill 方法，对指定技能执行迭代优化
- **FR-8**: 快照管理：create_snapshot 和 restore_snapshot 方法，简化的快照创建和恢复接口
- **FR-9**: 经验导出：export_experience 方法，支持 json/csv 格式导出
- **FR-10**: 状态获取：get_status 方法，获取智能体运行状态摘要
- **FR-11**: 深度自省：introspect_deep 方法，执行完整的分析流程（画像+趋势+模式+迭代建议）
- **FR-12**: 维度空间探测：dimension_probe_dataset 方法，可选的数据集维度空间探测功能
- **FR-13**: 模块导出：在 __init__.py 中导出 IntrospectiveAgent 类

## Non-Functional Requirements
- **NFR-1**: 所有公共方法必须有完整的 docstring
- **NFR-2**: 使用项目统一的日志工具 get_logger
- **NFR-3**: 遵循现有代码风格和命名约定
- **NFR-4**: 空数据池时所有功能应有合理的默认行为，不抛出异常
- **NFR-5**: 边界情况和错误处理要完善
- **NFR-6**: 测试覆盖率需覆盖所有核心功能和边界情况

## Constraints
- **Technical**: Python 3.x, pydantic, pandas, pytest
- **Business**: 不得修改现有子模块的实现，只能在 agent.py 中进行整合
- **Dependencies**: 依赖 experience 模块下所有子模块，可选依赖 dimension 模块

## Assumptions
- 所有子模块的 API 接口稳定且可用
- DimensionSpaceProbe 类具有 probe 和 get_probe_summary 方法
- ExperienceRecord 支持 from_dict 类方法进行反序列化
- 空数据池时各子模块能正常返回合理的默认值

## Acceptance Criteria

### AC-1: IntrospectiveAgent 初始化成功
- **Given**: 正确的初始化参数
- **When**: 创建 IntrospectiveAgent 实例
- **Then**: 实例创建成功，所有子模块属性可用且类型正确
- **Verification**: `programmatic`
- **Notes**: 验证 pool、snapshot_manager、self_assessment、error_attributor、experience_summarizer、profile_generator、iteration_engine、trend_analyzer、pattern_miner、comparator、dimension_probe 等属性

### AC-2: 记录经验功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 record_experience 方法
- **Then**: 返回 ExperienceRecord 对象，经验被添加到数据池，质量评分自动计算
- **Verification**: `programmatic`
- **Notes**: 支持额外 kwargs 参数传递

### AC-3: 自我反思功能正常
- **Given**: IntrospectiveAgent 实例（有或无经验数据）
- **When**: 调用 self_reflect 方法
- **Then**: 返回包含自我评估、错误统计、启发式规则、画像摘要的完整反思结果
- **Verification**: `programmatic`
- **Notes**: 支持指定 experience_id 或对全部经验反思

### AC-4: 获取自我画像功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 get_self_profile 方法
- **Then**: 返回 AgentProfile 对象，包含完整的智能体画像信息
- **Verification**: `programmatic`

### AC-5: 趋势分析功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 analyze_trend 方法
- **Then**: 返回趋势分析摘要，包含整体趋势、趋势斜率、关键发现等
- **Verification**: `programmatic`
- **Notes**: 支持 days 参数指定分析范围

### AC-6: 模式挖掘功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 mine_patterns 方法
- **Then**: 返回模式列表，支持 min_frequency 参数
- **Verification**: `programmatic`

### AC-7: 技能优化功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 optimize_skill 方法
- **Then**: 返回优化结果摘要，包含成功状态、改进率等信息
- **Verification**: `programmatic`
- **Notes**: 经验不足时返回合理的失败提示

### AC-8: 快照创建和恢复功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 create_snapshot 和 restore_snapshot 方法
- **Then**: 快照创建成功返回 snapshot_id，恢复成功返回 True，数据池状态正确恢复
- **Verification**: `programmatic`

### AC-9: 经验导出功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 export_experience 方法，指定 json 或 csv 格式
- **Then**: 返回正确格式的导出数据，数据内容与数据池一致
- **Verification**: `programmatic`
- **Notes**: 无效格式应抛出 ValueError

### AC-10: 状态获取功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 get_status 方法
- **Then**: 返回包含经验统计、快照信息、画像评分、趋势信息的状态摘要
- **Verification**: `programmatic`

### AC-11: 深度自省功能正常
- **Given**: IntrospectiveAgent 实例
- **When**: 调用 introspect_deep 方法
- **Then**: 返回完整的自省报告，包含画像、趋势、模式、洞察、错误统计、迭代建议和整体摘要
- **Verification**: `programmatic`

### AC-12: 维度空间探测功能正常
- **Given**: 配置了 dimension_probe 的 IntrospectiveAgent 实例
- **When**: 调用 dimension_probe_dataset 方法
- **Then**: 未配置时返回 None，配置后返回探测结果摘要
- **Verification**: `programmatic`

### AC-13: 空数据池时各功能有合理行为
- **Given**: 空数据池的 IntrospectiveAgent 实例
- **When**: 调用各主要方法
- **Then**: 所有方法正常返回，不抛出异常，返回合理的默认值
- **Verification**: `programmatic`

### AC-14: 边界情况和错误处理完善
- **Given**: 各种边界输入
- **When**: 调用相关方法
- **Then**: 系统正确处理，不崩溃，返回合理结果或错误提示
- **Verification**: `programmatic`

### AC-15: 模块正确导出
- **Given**: 安装好的包
- **When**: 从 ai_llm_agent_crawler.experience 导入 IntrospectiveAgent
- **Then**: 导入成功，类可用
- **Verification**: `programmatic`

## Open Questions
- 无
