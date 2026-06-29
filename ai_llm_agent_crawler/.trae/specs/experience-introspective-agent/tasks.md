# Experience 模块系统集成与 API 层 - 实施计划

## [x] Task 1: 创建 IntrospectiveAgent 类骨架和初始化
- **Priority**: high
- **Depends On**: None
- **Description**:
  - 创建 src/ai_llm_agent_crawler/experience/agent.py 文件
  - 实现 IntrospectiveAgent 类的 __init__ 方法
  - 初始化所有子模块：pool、snapshot_manager、self_assessment、error_attributor、experience_summarizer、profile_generator、iteration_engine、trend_analyzer、pattern_miner、comparator、dimension_probe
  - 实现 _init_snapshot_manager 和 _init_dimension_probe 私有方法
  - 使用 get_logger 进行日志记录
- **Acceptance Criteria Addressed**: AC-1, AC-15
- **Test Requirements**:
  - `programmatic` TR-1.1: 默认参数初始化成功，所有子模块属性存在且类型正确
  - `programmatic` TR-1.2: 自定义 agent_name 初始化正确
  - `programmatic` TR-1.3: 带 storage_path 初始化正确
  - `programmatic` TR-1.4: 带 config 初始化正确
  - `programmatic` TR-1.5: 启用 dimension_probe 时正确初始化
  - `human-judgement` TR-1.6: 代码风格符合项目规范，使用 get_logger，有完整 docstring

## [x] Task 2: 实现核心经验管理方法
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - 实现 record_experience 方法：创建 ExperienceRecord 并添加到数据池，自动计算质量评分
  - 实现 export_experience 方法：支持 json/csv 格式导出
  - 实现 create_snapshot 和 restore_snapshot 方法：简化的快照管理接口
- **Acceptance Criteria Addressed**: AC-2, AC-8, AC-9
- **Test Requirements**:
  - `programmatic` TR-2.1: 记录成功经验，返回正确的 ExperienceRecord
  - `programmatic` TR-2.2: 记录带额外 kwargs 参数的经验
  - `programmatic` TR-2.3: 记录多条经验，数量正确
  - `programmatic` TR-2.4: 记录后质量评分自动计算
  - `programmatic` TR-2.5: JSON 导出格式正确，数据一致
  - `programmatic` TR-2.6: CSV 导出格式正确
  - `programmatic` TR-2.7: 无效导出格式抛出 ValueError
  - `programmatic` TR-2.8: 创建快照成功，返回正确的 snapshot_id
  - `programmatic` TR-2.9: 恢复快照成功，数据池状态正确恢复
  - `programmatic` TR-2.10: 恢复无效快照返回 False

## [x] Task 3: 实现反思和分析方法
- **Priority**: high
- **Depends On**: Task 2
- **Description**:
  - 实现 self_reflect 方法：执行自我评估→错误归因→经验总结→更新画像的完整流程
  - 实现 get_self_profile 方法：获取当前自我认知画像
  - 实现 analyze_trend 方法：趋势分析简化接口
  - 实现 mine_patterns 方法：模式挖掘简化接口
  - 实现 optimize_skill 方法：技能迭代优化
  - 实现 get_status 方法：获取智能体运行状态
  - 实现 introspect_deep 方法：深度自省完整分析流程
- **Acceptance Criteria Addressed**: AC-3, AC-4, AC-5, AC-6, AC-7, AC-10, AC-11
- **Test Requirements**:
  - `programmatic` TR-3.1: 空数据池自我反思返回正确结构
  - `programmatic` TR-3.2: 有数据时自我反思结果正确
  - `programmatic` TR-3.3: 指定 experience_id 的自我反思正常
  - `programmatic` TR-3.4: 无效 experience_id 返回错误提示
  - `programmatic` TR-3.5: 空数据池获取画像返回正确默认值
  - `programmatic` TR-3.6: 有数据时获取画像信息完整
  - `programmatic` TR-3.7: 空数据池趋势分析返回合理结果
  - `programmatic` TR-3.8: 有数据时趋势分析包含关键发现
  - `programmatic` TR-3.9: 空数据池模式挖掘返回空列表
  - `programmatic` TR-3.10: 有数据时模式挖掘返回正确数量
  - `programmatic` TR-3.11: 技能优化返回正确结构
  - `programmatic` TR-3.12: 经验不足时技能优化返回合理提示
  - `programmatic` TR-3.13: 空数据池状态获取结构完整
  - `programmatic` TR-3.14: 有数据时状态获取信息正确
  - `programmatic` TR-3.15: 空数据池深度自省结构完整
  - `programmatic` TR-3.16: 有数据时深度自省包含所有分析维度

## [x] Task 4: 实现维度空间探测集成
- **Priority**: medium
- **Depends On**: Task 1
- **Description**:
  - 实现 dimension_probe_dataset 方法：对数据集进行维度空间探测
  - 未配置探针时返回 None，配置后执行探测并返回摘要
- **Acceptance Criteria Addressed**: AC-12
- **Test Requirements**:
  - `programmatic` TR-4.1: 探针未启用时返回 None
  - `programmatic` TR-4.2: 探针启用时返回正确的探测结果摘要

## [x] Task 5: 修改 __init__.py 导出新类
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - 在 src/ai_llm_agent_crawler/experience/__init__.py 中添加 IntrospectiveAgent 的导入
  - 在 __all__ 列表中添加 IntrospectiveAgent
- **Acceptance Criteria Addressed**: AC-15
- **Test Requirements**:
  - `programmatic` TR-5.1: 从 ai_llm_agent_crawler.experience 可以成功导入 IntrospectiveAgent

## [x] Task 6: 编写集成测试
- **Priority**: high
- **Depends On**: Task 2, Task 3, Task 4, Task 5
- **Description**:
  - 创建 tests/test_experience/test_agent.py 文件
  - 覆盖所有核心功能测试
  - 覆盖空数据池行为测试
  - 覆盖边界情况和错误处理测试
  - 使用 pytest 框架
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15
- **Test Requirements**:
  - `programmatic` TR-6.1: 所有测试用例通过
  - `programmatic` TR-6.2: 测试覆盖所有公共方法
  - `programmatic` TR-6.3: 测试覆盖空数据池场景
  - `programmatic` TR-6.4: 测试覆盖边界情况和错误处理
  - `human-judgement` TR-6.5: 测试代码结构清晰，命名规范

## [x] Task 7: 空数据池行为和边界情况验证
- **Priority**: medium
- **Depends On**: Task 6
- **Description**:
  - 验证空数据池时所有主要方法的合理行为
  - 验证边界情况和错误处理的完善性
- **Acceptance Criteria Addressed**: AC-13, AC-14
- **Test Requirements**:
  - `programmatic` TR-7.1: 空数据池所有主要方法不抛出异常
  - `programmatic` TR-7.2: 最少参数记录经验正常
  - `programmatic` TR-7.3: 重复恢复快照正常
  - `programmatic` TR-7.4: 导出导入数据一致性验证
