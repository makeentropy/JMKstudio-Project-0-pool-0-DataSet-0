#!/usr/bin/env python3
"""
经验自省智能体 - 完整演示

展示从经验采集、自我反思、画像生成到技能迭代的完整闭环。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
import random
import json

from ai_llm_agent_crawler.experience.agent import IntrospectiveAgent
from ai_llm_agent_crawler.utils.logging import LogManager

LogManager.initialize(log_level="WARNING", enable_file_logging=False)

SEPARATOR = "=" * 70
SUB_SEPARATOR = "-" * 50


def print_title(title: str, chapter: int = None):
    print("\n" + SEPARATOR)
    if chapter:
        print(f"  第{chapter}章：{title}")
    else:
        print(f"  {title}")
    print(SEPARATOR)


def print_section(title: str):
    print(f"\n  {title}")
    print("  " + SUB_SEPARATOR)


def generate_mock_experiences(agent: IntrospectiveAgent, count: int = 50):
    task_types = [
        "data_cleaning",
        "data_exploration",
        "model_training",
        "report_generation",
        "data_annotation",
        "quality_validation",
    ]

    statuses = ["success", "success", "success", "partial", "failed", "skipped"]

    error_messages = [
        "Connection timeout after 30s",
        "Invalid data format: missing required field 'id'",
        "Memory allocation failed: out of memory",
        "Permission denied: cannot access file",
        "Data parsing error: unexpected JSON format",
        "Network error: connection refused",
        "Validation failed: value out of range",
    ]

    warning_messages = [
        "Performance degraded: response time > 5s",
        "Data quality warning: high null ratio",
        "Deprecation warning: using legacy API",
        "Resource usage high: CPU > 80%",
    ]

    base_time = datetime.now() - timedelta(days=30)

    for i in range(count):
        task_type = random.choice(task_types)
        status = random.choice(statuses)
        duration_ms = random.uniform(100, 5000)

        if status == "success":
            accuracy = random.uniform(0.75, 0.99)
            efficiency = random.uniform(0.6, 0.95)
        elif status == "partial":
            accuracy = random.uniform(0.5, 0.8)
            efficiency = random.uniform(0.4, 0.7)
        elif status == "failed":
            accuracy = random.uniform(0.1, 0.4)
            efficiency = random.uniform(0.1, 0.5)
        else:
            accuracy = random.uniform(0.3, 0.6)
            efficiency = random.uniform(0.2, 0.5)

        errors = []
        warnings = []

        if status == "failed":
            errors.append(random.choice(error_messages))
            if random.random() > 0.5:
                errors.append(random.choice(error_messages))
        elif status == "partial":
            if random.random() > 0.6:
                errors.append(random.choice(error_messages))
            warnings.append(random.choice(warning_messages))
        elif status == "success":
            if random.random() > 0.8:
                warnings.append(random.choice(warning_messages))

        timestamp = base_time + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        record = agent.record_experience(
            task_id=f"task_{i:04d}",
            task_type=task_type,
            task_name=f"{task_type}_job_{i}",
            status=status,
            duration_ms=duration_ms,
            performance_metrics={
                "accuracy": accuracy,
                "efficiency": efficiency,
                "completeness": random.uniform(0.6, 1.0),
            },
            input_summary=f"Input dataset for {task_type} task #{i}",
            output_summary=f"Processed {random.randint(100, 10000)} records",
            errors=errors,
            warnings=warnings,
            metadata={
                "dataset_size": random.randint(1000, 100000),
                "priority": random.choice(["low", "medium", "high"]),
            },
        )

        record.timestamp = timestamp
        agent.pool._update_dataframe()


def main():
    print("\n" + SEPARATOR)
    print("  经验自省智能体 IntrospectiveAgent - 完整功能演示")
    print(SEPARATOR)
    print("\n  本演示将展示从经验采集到自我优化的完整闭环")
    print("  预计演示时长：约 2-3 分钟")

    print_title("初始化智能体", 1)
    agent = IntrospectiveAgent(agent_name="demo_agent")
    status = agent.get_status()
    print(f"  智能体名称: {status['agent_name']}")
    print(f"  经验总数: {status['experience']['total_records']}")
    print(f"  状态: 初始化完成，等待经验采集")
    print("\n  组件列表:")
    print(f"    - 经验数据池 (ExperienceDataPool)")
    print(f"    - 快照管理器 (ExperienceSnapshotManager)")
    print(f"    - 自我评估器 (SelfAssessment)")
    print(f"    - 错误归因器 (ErrorAttributor)")
    print(f"    - 经验总结器 (ExperienceSummarizer)")
    print(f"    - 画像生成器 (AgentProfileGenerator)")
    print(f"    - 技能迭代引擎 (SkillIterationEngine)")
    print(f"    - 趋势分析器 (TrendAnalyzer)")
    print(f"    - 模式挖掘器 (PatternMiner)")
    print(f"    - 经验对比器 (ExperienceComparator)")

    print_title("采集经验数据", 2)
    print("  正在模拟生成 50 条经验记录...")
    print("  包含任务类型: data_cleaning, data_exploration, model_training,")
    print("               report_generation, data_annotation, quality_validation")
    print("  状态分布: success, partial, failed, skipped")

    generate_mock_experiences(agent, count=50)

    stats = agent.pool.get_statistics()
    print(f"\n  采集完成！")
    print(f"  总经验数: {stats['total_records']}")
    print(f"  平均质量分: {stats['average_quality_score']:.3f}")
    print(f"  平均耗时: {stats['avg_duration_ms']:.1f} ms")
    print(f"  总错误数: {stats['total_errors']}")
    print(f"  总警告数: {stats['total_warnings']}")

    print_section("按任务类型分布:")
    for task_type, count in stats['by_task_type'].items():
        print(f"    {task_type}: {count} 条")

    print_section("按状态分布:")
    for status_name, count in stats['by_status'].items():
        print(f"    {status_name}: {count} 条")

    print_title("第一次自我反思", 3)
    print("  调用 self_reflect() 方法...")
    reflection = agent.self_reflect()

    print(f"\n  反思结果:")
    print(f"    反思时间: {reflection['reflection_time']}")
    print(f"    经验数量: {reflection['experience_count']}")
    print(f"    综合评分: {reflection['self_assessment']['overall_score']:.3f}")

    print_section("评估摘要:")
    print(f"    {reflection['self_assessment']['summary']}")

    print_section("优势项:")
    for i, strength in enumerate(reflection['self_assessment']['strengths'][:3], 1):
        print(f"    {i}. {strength}")

    print_section("劣势项:")
    for i, weakness in enumerate(reflection['self_assessment']['weaknesses'][:3], 1):
        print(f"    {i}. {weakness}")

    print_section("各维度评分:")
    for dim, info in reflection['self_assessment']['dimensions'].items():
        bar = "█" * int(info['score'] * 30)
        print(f"    {dim:15s} [{bar:<30s}] {info['score']:.3f} (置信度: {info['confidence']:.1%})")

    print_section("错误归因统计:")
    error_stats = reflection['error_statistics']
    if isinstance(error_stats, dict):
        for key, value in list(error_stats.items())[:5]:
            print(f"    {key}: {value}")

    print_section("经验启发 (Top 5):")
    for i, heuristic in enumerate(reflection['top_heuristics'], 1):
        print(f"    {i}. {heuristic['name']} "
              f"(频率: {heuristic['frequency']}, "
              f"置信度: {heuristic['confidence']:.2f})")

    print_title("查看自我认知画像", 4)
    print("  调用 get_self_profile() 方法...")
    profile = agent.get_self_profile()

    print(f"\n  画像摘要:")
    print(f"    画像ID: {profile.profile_id}")
    print(f"    智能体名称: {profile.agent_name}")
    print(f"    基于经验数: {profile.experience_count}")
    print(f"    综合能力评分: {profile.overall_score:.3f}")
    print(f"    近期趋势: {profile.recent_trend}")

    print_section("核心优势:")
    for i, strength in enumerate(profile.strengths[:5], 1):
        print(f"    {i}. {strength}")

    print_section("主要劣势:")
    for i, weakness in enumerate(profile.weaknesses[:5], 1):
        print(f"    {i}. {weakness}")

    print_section("改进方向:")
    for i, direction in enumerate(profile.improvement_directions[:5], 1):
        print(f"    {i}. {direction}")

    print_section("技能领域详情:")
    for domain in profile.skill_domains:
        proficiency_bar = "█" * int(domain.proficiency * 20)
        print(f"\n    领域: {domain.domain_name}")
        print(f"      任务数: {domain.task_count}, 成功率: {domain.success_rate:.1%}")
        print(f"      准确率: {domain.avg_accuracy:.1%}, 效率: {domain.avg_efficiency:.1%}")
        print(f"      熟练度: [{proficiency_bar:<20s}] {domain.proficiency:.2%}")

    print_section("知识边界:")
    kb = profile.knowledge_boundary
    print(f"    已知领域 ({len(kb.known_domains)}): {', '.join(kb.known_domains)}")
    print(f"    前沿领域 ({len(kb.frontier_domains)}): {', '.join(kb.frontier_domains)}")
    print(f"    未知领域 ({len(kb.unknown_domains)}): {', '.join(kb.unknown_domains)}")
    print(f"    整体确定性: {kb.overall_certainty:.1%}")

    print_title("趋势分析", 5)
    print("  调用 analyze_trend() 方法...")
    trend = agent.analyze_trend(days=30)

    print(f"\n  趋势分析结果:")
    print(f"    分析时间范围: {trend['start_date'][:10]} ~ {trend['end_date'][:10]}")
    print(f"    数据点数: {trend['total_points']}")
    print(f"    整体趋势: {trend['overall_trend']}")
    print(f"    趋势斜率: {trend['trend_slope']:.6f}")

    print_section("各维度趋势:")
    for dim, trend_dir in trend['dimension_trends'].items():
        trend_icon = {"improving": "↑", "declining": "↓", "stable": "→"}.get(trend_dir, "?")
        print(f"    {trend_icon} {dim}: {trend_dir}")

    print_section("关键发现:")
    for i, finding in enumerate(trend['key_findings'], 1):
        print(f"    {i}. {finding}")

    print_section("预测信息:")
    pred = trend['prediction']
    print(f"    预测方法: {pred.get('method', 'N/A')}")
    print(f"    置信度: {pred.get('confidence', 0):.1%}")
    if 'predictions' in pred and pred['predictions']:
        print("    未来预测:")
        for p in pred['predictions'][:3]:
            print(f"      周期 {p['period_index']}: 预计评分 {p['predicted_score']:.3f}")

    print_title("模式挖掘", 6)
    print("  调用 mine_patterns() 方法...")
    patterns = agent.mine_patterns(min_frequency=2)

    print(f"\n  模式挖掘结果:")
    print(f"    发现模式总数: {len(patterns)}")

    success_patterns = [p for p in patterns if p.get('pattern_type') == 'success_pattern']
    failure_patterns = [p for p in patterns if p.get('pattern_type') == 'failure_pattern']

    print(f"    成功模式: {len(success_patterns)} 个")
    print(f"    失败模式: {len(failure_patterns)} 个")

    print_section("成功模式:")
    for i, pattern in enumerate(success_patterns[:5], 1):
        print(f"\n    模式 #{i}: {pattern['name']}")
        print(f"      频率: {pattern['frequency']}, 置信度: {pattern['confidence']:.2f}")
        print(f"      典型特征:")
        for feature in pattern.get('typical_features', [])[:3]:
            print(f"        - {feature}")

    print_section("失败模式:")
    for i, pattern in enumerate(failure_patterns[:5], 1):
        print(f"\n    模式 #{i}: {pattern['name']}")
        print(f"      频率: {pattern['frequency']}, 置信度: {pattern['confidence']:.2f}")
        print(f"      典型特征:")
        for feature in pattern.get('typical_features', [])[:3]:
            print(f"        - {feature}")

    print_title("快照管理", 7)
    print("  创建经验池快照...")
    snapshot_id = agent.create_snapshot(name="baseline_snapshot")

    print(f"\n  快照创建成功:")
    snapshot = agent.snapshot_manager.get_snapshot(snapshot_id)
    print(f"    快照ID: {snapshot.snapshot_id}")
    print(f"    名称: {snapshot.name}")
    print(f"    版本: {snapshot.version}")
    print(f"    创建时间: {snapshot.created_at}")
    print(f"    记录数量: {snapshot.record_count}")
    print(f"    大小: {snapshot.total_size_bytes} bytes")
    print(f"    校验和: {snapshot.checksum[:20]}...")

    print_section("当前快照列表:")
    snapshots = agent.snapshot_manager.list_snapshots()
    for i, snap in enumerate(snapshots, 1):
        print(f"    {i}. {snap.snapshot_id} (v{snap.version}) - {snap.name or '未命名'} - {snap.record_count} 条记录")

    print("\n  新增 10 条经验以演示快照恢复...")
    for i in range(10):
        agent.record_experience(
            task_id=f"snapshot_test_{i}",
            task_type="data_cleaning",
            task_name=f"Snapshot Test Task {i}",
            status=random.choice(["success", "partial", "failed"]),
            duration_ms=random.uniform(500, 3000),
            performance_metrics={
                "accuracy": random.uniform(0.6, 0.95),
                "efficiency": random.uniform(0.5, 0.9),
            },
        )

    stats_before = agent.pool.get_statistics()
    print(f"  当前经验数: {stats_before['total_records']}")

    print("\n  恢复快照...")
    restore_success = agent.restore_snapshot(snapshot_id)
    stats_after = agent.pool.get_statistics()
    print(f"  恢复结果: {'成功' if restore_success else '失败'}")
    print(f"  恢复后经验数: {stats_after['total_records']}")

    print_title("技能自迭代", 8)
    print("  调用 optimize_skill() 方法...")

    skill_id = "data_cleaning_skill"
    optimization_result = agent.optimize_skill(skill_id)

    if optimization_result['success']:
        print(f"\n  技能优化成功:")
        print(f"    技能ID: {optimization_result['skill_id']}")
        print(f"    迭代ID: {optimization_result['iteration_id']}")
        print(f"    技能名称: {optimization_result['skill_name']}")
        print(f"    触发类型: {optimization_result['trigger_type']}")
        print(f"    优化策略: {optimization_result['strategy']}")
        print(f"    原始版本: {optimization_result['original_version']}")
        print(f"    优化版本: {optimization_result['optimized_version']}")
        print(f"    综合改进率: {optimization_result['overall_improvement']:.1%}")
        print(f"    已批准: {optimization_result['is_approved']}")
        print(f"    已应用: {optimization_result['is_applied']}")

        print_section("改进指标:")
        for metric, improvement in optimization_result['improvements'].items():
            direction = "↑" if improvement > 0 else "↓" if improvement < 0 else "→"
            print(f"    {direction} {metric}: {improvement:+.4f}")

        print_section("优化前后对比:")
        print(f"    {'指标':<20s} {'优化前':>10s} {'优化后':>10s} {'变化':>10s}")
        print(f"    {'-'*50}")
        for metric in optimization_result['before_metrics']:
            before = optimization_result['before_metrics'][metric]
            after = optimization_result['after_metrics'].get(metric, before)
            diff = after - before
            print(f"    {metric:<20s} {before:>10.4f} {after:>10.4f} {diff:>+10.4f}")

        print_section("变更列表:")
        for i, change in enumerate(optimization_result['changes'], 1):
            print(f"    {i}. {change}")

        print_section("迭代原因:")
        print(f"    {optimization_result['reason']}")
    else:
        print(f"\n  技能优化未能执行:")
        print(f"    {optimization_result.get('message', '未知原因')}")

    print_section("迭代历史:")
    history = agent.iteration_engine.get_iteration_history(skill_id)
    if history:
        for i, record in enumerate(history, 1):
            print(f"    {i}. {record.iteration_id} (v{record.optimized_version}) "
                  f"- 改进率: {record.overall_improvement:.1%}")
    else:
        print("    暂无迭代历史")

    print_title("深度自省报告", 9)
    print("  调用 introspect_deep() 方法...")
    deep_report = agent.introspect_deep()

    print(f"\n  深度自省报告:")
    print(f"    自省时间: {deep_report['introspection_time']}")
    print(f"    智能体: {deep_report['agent_name']}")

    print_section("画像摘要:")
    ps = deep_report['profile']
    print(f"    综合评分: {ps['overall_score']:.3f}")
    print(f"    经验数量: {ps['experience_count']}")
    print(f"    近期趋势: {ps['recent_trend']}")
    print(f"    知识确定性: {ps['knowledge_certainty']:.1%}")
    print(f"    已知领域数: {ps['known_domains_count']}")

    print_section("趋势分析:")
    tr = deep_report['trend']
    print(f"    整体趋势: {tr['overall_trend']}")
    print(f"    趋势斜率: {tr['trend_slope']:.6f}")

    print_section("关键发现:")
    for i, finding in enumerate(tr['key_findings'][:3], 1):
        print(f"    {i}. {finding}")

    print_section("模式挖掘:")
    pt = deep_report['patterns']
    print(f"    模式总数: {pt['total_count']}")
    print(f"    Top 模式:")
    for i, pattern in enumerate(pt['top_patterns'][:3], 1):
        print(f"      {i}. {pattern.get('name', 'N/A')} "
              f"(频率: {pattern.get('frequency', 0)})")

    print_section("迭代建议:")
    if deep_report['iteration_suggestions']:
        for i, suggestion in enumerate(deep_report['iteration_suggestions'], 1):
            print(f"    {i}. [{suggestion['priority'].upper()}] "
                  f"{suggestion['skill_id']}: {suggestion['reason']}")
    else:
        print("    暂无迭代建议")

    print_section("总体总结:")
    print(f"    {deep_report['overall_summary']}")

    print_title("经验导出", 10)
    print("  导出经验数据为 JSON 格式...")
    json_data = agent.export_experience(format="json")

    import json as json_module
    records = json_module.loads(json_data)

    print(f"\n  导出结果:")
    print(f"    格式: JSON")
    print(f"    记录数: {len(records)}")
    print(f"    数据大小: {len(json_data.encode('utf-8'))} bytes")

    print_section("样本记录 (前 3 条):")
    for i, record in enumerate(records[:3], 1):
        print(f"\n    记录 #{i}:")
        print(f"      ID: {record['experience_id']}")
        print(f"      任务: {record['task_name']} ({record['task_type']})")
        print(f"      状态: {record['status']}")
        print(f"      质量分: {record['quality_score']}")
        print(f"      时间: {record['timestamp']}")

    print("\n" + SEPARATOR)
    print("  演示总结")
    print(SEPARATOR)
    print("""
  本演示展示了 IntrospectiveAgent 的完整功能：

  1. 经验采集 - 支持多类型、多状态的经验记录
  2. 自我反思 - 自动评估、错误归因、经验总结
  3. 自我认知画像 - 综合评分、优劣势、技能领域、知识边界
  4. 趋势分析 - 能力变化趋势、拐点检测、未来预测
  5. 模式挖掘 - 成功模式、失败模式识别
  6. 快照管理 - 经验池版本控制、回滚
  7. 技能自迭代 - 自动优化策略生成与效果验证
  8. 深度自省 - 全面的自我分析报告
  9. 数据导出 - JSON/CSV 格式支持

  使用提示：
  - 在实际项目中，经验数据应来自真实任务执行
  - 定期调用 self_reflect() 保持自我认知更新
  - 使用快照功能保存重要里程碑
  - 结合维度探针进行更深入的数据分析
""")
    print(SEPARATOR)
    print("  演示完成！感谢观看。")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    main()
