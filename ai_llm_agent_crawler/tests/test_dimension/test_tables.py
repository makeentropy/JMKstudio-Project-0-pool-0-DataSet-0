"""
数据表系统测试

测试任务表、事件逻辑表、效率审计表和质能质量子奇点维度空间拓扑数据表。
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from ai_llm_agent_crawler.dimension import (
    # 任务表相关
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskRecord,
    TaskTable,
    # 事件逻辑表相关
    EventType,
    LogicOperator,
    EventCondition,
    EventLogicNode,
    EventRecord,
    EventLogicTable,
    # 效率审计表相关
    AuditLevel,
    ResourceUsage,
    QualityMetrics,
    EfficiencyAuditRecord,
    EfficiencyAuditTable,
    # 拓扑数据表相关
    TopologyType,
    SingularityConnectionType,
    DimensionTopologyNode,
    SingularityTopologyNode,
    SingularityConnection,
    TopologyMetrics,
    MassEnergySingularityTopologyTable,
)


class TestTaskTable:
    """测试任务表"""

    def test_task_status_enum(self):
        """测试任务状态枚举"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert len(list(TaskStatus)) == 7

    def test_task_priority_enum(self):
        """测试任务优先级枚举"""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.URGENT == "urgent"
        assert TaskPriority.CRITICAL == "critical"
        assert len(list(TaskPriority)) == 5

    def test_task_type_enum(self):
        """测试任务类型枚举"""
        assert TaskType.DATA_CRAWL == "data_crawl"
        assert TaskType.DATA_PROCESS == "data_process"
        assert TaskType.QUALITY_ASSESSMENT == "quality_assessment"
        assert len(list(TaskType)) == 10

    def test_task_record_creation(self):
        """测试任务记录创建"""
        task = TaskRecord(
            task_id="task-001",
            task_name="数据爬取任务",
            task_type=TaskType.DATA_CRAWL,
            priority=TaskPriority.HIGH,
            description="测试爬取任务",
        )
        assert task.task_id == "task-001"
        assert task.task_name == "数据爬取任务"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.HIGH
        assert task.progress == 0.0
        assert task.is_active is False
        assert task.is_finished is False

    def test_task_record_active_state(self):
        """测试任务活跃状态"""
        task = TaskRecord(
            task_id="task-002",
            task_name="测试任务",
            status=TaskStatus.RUNNING,
        )
        assert task.is_active is True
        assert task.is_finished is False

    def test_task_record_finished_state(self):
        """测试任务结束状态"""
        task = TaskRecord(
            task_id="task-003",
            task_name="测试任务",
            status=TaskStatus.COMPLETED,
        )
        assert task.is_active is False
        assert task.is_finished is True

    def test_task_record_duration(self):
        """测试任务持续时间计算"""
        start = datetime.now()
        end = start + timedelta(seconds=30)
        task = TaskRecord(
            task_id="task-004",
            task_name="测试任务",
            started_at=start,
            completed_at=end,
            status=TaskStatus.COMPLETED,
        )
        assert task.duration_seconds == 30.0

    def test_task_can_start(self):
        """测试任务依赖检查"""
        task = TaskRecord(
            task_id="task-005",
            task_name="依赖任务",
            dependencies=["task-dep-1", "task-dep-2"],
        )
        assert task.can_start(["task-dep-1", "task-dep-2"]) is True
        assert task.can_start(["task-dep-1"]) is False

    def test_task_table_add_and_get(self):
        """测试任务表添加和获取"""
        table = TaskTable()
        task = TaskRecord(
            task_id="task-101",
            task_name="测试任务",
        )
        table.add_task(task)
        assert table.total_count == 1
        retrieved = table.get_task("task-101")
        assert retrieved is not None
        assert retrieved.task_id == "task-101"

    def test_task_table_update_status(self):
        """测试任务表状态更新"""
        table = TaskTable()
        task = TaskRecord(
            task_id="task-102",
            task_name="测试任务",
        )
        table.add_task(task)

        table.update_task_status("task-102", TaskStatus.RUNNING)
        assert table.get_task("task-102").status == TaskStatus.RUNNING
        assert table.get_task("task-102").started_at is not None

        table.update_task_status("task-102", TaskStatus.COMPLETED)
        assert table.get_task("task-102").status == TaskStatus.COMPLETED
        assert table.get_task("task-102").completed_at is not None

    def test_task_table_get_by_status(self):
        """测试按状态获取任务"""
        table = TaskTable()
        for i in range(5):
            table.add_task(TaskRecord(
                task_id=f"task-{i}",
                task_name=f"任务{i}",
                status=TaskStatus.PENDING if i < 3 else TaskStatus.RUNNING,
            ))
        assert len(table.get_tasks_by_status(TaskStatus.PENDING)) == 3
        assert len(table.get_tasks_by_status(TaskStatus.RUNNING)) == 2

    def test_task_table_get_by_type(self):
        """测试按类型获取任务"""
        table = TaskTable()
        table.add_task(TaskRecord(task_id="t1", task_name="t1", task_type=TaskType.DATA_CRAWL))
        table.add_task(TaskRecord(task_id="t2", task_name="t2", task_type=TaskType.DATA_CRAWL))
        table.add_task(TaskRecord(task_id="t3", task_name="t3", task_type=TaskType.QUALITY_ASSESSMENT))
        assert len(table.get_tasks_by_type(TaskType.DATA_CRAWL)) == 2

    def test_task_table_ready_tasks(self):
        """测试获取可启动任务"""
        table = TaskTable()
        table.add_task(TaskRecord(
            task_id="dep-task",
            task_name="依赖任务",
            status=TaskStatus.COMPLETED,
        ))
        table.add_task(TaskRecord(
            task_id="main-task",
            task_name="主任务",
            dependencies=["dep-task"],
        ))
        ready = table.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "main-task"

    def test_task_table_success_rate(self):
        """测试成功率计算"""
        table = TaskTable()
        for i in range(8):
            table.add_task(TaskRecord(
                task_id=f"success-{i}",
                task_name=f"成功任务{i}",
                status=TaskStatus.COMPLETED,
            ))
        for i in range(2):
            table.add_task(TaskRecord(
                task_id=f"fail-{i}",
                task_name=f"失败任务{i}",
                status=TaskStatus.FAILED,
            ))
        assert table.success_rate == pytest.approx(0.8, rel=0.01)


class TestEventLogicTable:
    """测试事件逻辑表"""

    def test_event_type_enum(self):
        """测试事件类型枚举"""
        assert EventType.TASK_START == "task_start"
        assert EventType.DATA_ARRIVAL == "data_arrival"
        assert EventType.SINGULARITY_DETECTED == "singularity_detected"
        assert len(list(EventType)) == 10

    def test_logic_operator_enum(self):
        """测试逻辑运算符枚举"""
        assert LogicOperator.AND == "and"
        assert LogicOperator.OR == "or"
        assert LogicOperator.XOR == "xor"
        assert LogicOperator.NOT == "not"
        assert len(list(LogicOperator)) == 6

    def test_event_record_creation(self):
        """测试事件记录创建"""
        event = EventRecord(
            event_id="evt-001",
            event_type=EventType.TASK_COMPLETE,
            source="crawler",
            title="任务完成",
            description="数据爬取任务已完成",
        )
        assert event.event_id == "evt-001"
        assert event.event_type == EventType.TASK_COMPLETE
        assert event.processed is False

    def test_event_record_mark_processed(self):
        """测试事件标记已处理"""
        event = EventRecord(
            event_id="evt-002",
            event_type=EventType.SYSTEM_EVENT,
        )
        event.mark_processed("handled")
        assert event.processed is True
        assert event.processed_at is not None
        assert event.processing_result == "handled"

    def test_event_condition_evaluation(self):
        """测试事件条件评估"""
        table = EventLogicTable()
        condition = EventCondition(
            event_type=EventType.QUALITY_ALERT,
            source="quality_checker",
            attribute_filters={"level": "high"},
        )
        matching_event = EventRecord(
            event_id="evt-003",
            event_type=EventType.QUALITY_ALERT,
            source="quality_checker",
            payload={"level": "high"},
        )
        non_matching_event = EventRecord(
            event_id="evt-004",
            event_type=EventType.QUALITY_ALERT,
            source="other_source",
            payload={"level": "high"},
        )
        assert table.evaluate_condition(condition, matching_event) is True
        assert table.evaluate_condition(condition, non_matching_event) is False

    def test_event_logic_table_add_events(self):
        """测试事件表添加事件"""
        table = EventLogicTable()
        event1 = EventRecord(event_id="evt-101", event_type=EventType.TASK_START)
        event2 = EventRecord(event_id="evt-102", event_type=EventType.TASK_COMPLETE)
        table.add_event(event1)
        table.add_event(event2)
        assert table.total_events == 2

    def test_event_logic_table_unprocessed(self):
        """测试获取未处理事件"""
        table = EventLogicTable()
        evt1 = EventRecord(event_id="evt-201", event_type=EventType.SYSTEM_EVENT, processed=True)
        evt2 = EventRecord(event_id="evt-202", event_type=EventType.SYSTEM_EVENT)
        table.add_event(evt1)
        table.add_event(evt2)
        assert len(table.get_unprocessed_events()) == 1

    def test_event_logic_table_get_by_type(self):
        """测试按类型获取事件"""
        table = EventLogicTable()
        table.add_event(EventRecord(event_id="e1", event_type=EventType.DATA_ARRIVAL))
        table.add_event(EventRecord(event_id="e2", event_type=EventType.DATA_ARRIVAL))
        table.add_event(EventRecord(event_id="e3", event_type=EventType.TASK_FAIL))
        assert len(table.get_events_by_type(EventType.DATA_ARRIVAL)) == 2

    def test_event_logic_table_logic_nodes(self):
        """测试逻辑节点评估"""
        table = EventLogicTable()

        cond_node = EventLogicNode(
            node_id="cond-1",
            node_type="condition",
            condition=EventCondition(
                event_type=EventType.QUALITY_ALERT,
                attribute_filters={"severity": "critical"},
            ),
        )
        table.add_logic_node(cond_node)

        event = EventRecord(
            event_id="evt-301",
            event_type=EventType.QUALITY_ALERT,
            payload={"severity": "critical"},
        )
        assert table.evaluate_logic_node("cond-1", event) is True

    def test_event_logic_table_and_operator(self):
        """测试AND逻辑运算符"""
        table = EventLogicTable()

        table.add_logic_node(EventLogicNode(
            node_id="cond-a",
            node_type="condition",
            condition=EventCondition(event_type=EventType.QUALITY_ALERT),
        ))
        table.add_logic_node(EventLogicNode(
            node_id="cond-b",
            node_type="condition",
            condition=EventCondition(event_type=EventType.QUALITY_ALERT,
                                      attribute_filters={"priority": "high"}),
        ))
        table.add_logic_node(EventLogicNode(
            node_id="and-node",
            node_type="operator",
            operator=LogicOperator.AND,
            children=["cond-a", "cond-b"],
        ))

        event = EventRecord(
            event_id="evt-401",
            event_type=EventType.QUALITY_ALERT,
            payload={"priority": "high"},
        )
        assert table.evaluate_logic_node("and-node", event) is True

    def test_event_logic_table_or_operator(self):
        """测试OR逻辑运算符"""
        table = EventLogicTable()

        table.add_logic_node(EventLogicNode(
            node_id="cond-x",
            node_type="condition",
            condition=EventCondition(event_type=EventType.TASK_START),
        ))
        table.add_logic_node(EventLogicNode(
            node_id="cond-y",
            node_type="condition",
            condition=EventCondition(event_type=EventType.TASK_COMPLETE),
        ))
        table.add_logic_node(EventLogicNode(
            node_id="or-node",
            node_type="operator",
            operator=LogicOperator.OR,
            children=["cond-x", "cond-y"],
        ))

        event = EventRecord(
            event_id="evt-501",
            event_type=EventType.TASK_COMPLETE,
        )
        assert table.evaluate_logic_node("or-node", event) is True


class TestEfficiencyAuditTable:
    """测试效率审计表"""

    def test_audit_level_enum(self):
        """测试审计级别枚举"""
        assert AuditLevel.DEBUG == "debug"
        assert AuditLevel.INFO == "info"
        assert AuditLevel.WARNING == "warning"
        assert AuditLevel.ERROR == "error"
        assert AuditLevel.CRITICAL == "critical"
        assert len(list(AuditLevel)) == 5

    def test_resource_usage(self):
        """测试资源使用模型"""
        usage = ResourceUsage(
            cpu_usage_percent=45.5,
            memory_usage_mb=1024.0,
            memory_usage_percent=25.0,
            disk_io_read_mb=100.0,
            disk_io_write_mb=200.0,
        )
        assert usage.cpu_usage_percent == 45.5
        assert usage.total_io_mb == pytest.approx(300.0, rel=0.01)

    def test_quality_metrics(self):
        """测试质量指标模型"""
        metrics = QualityMetrics(
            data_quality_score=0.85,
            completeness=0.9,
            accuracy=0.8,
            consistency=0.85,
            efficiency_score=0.75,
        )
        assert metrics.data_quality_score == 0.85
        assert metrics.completeness == 0.9

    def test_efficiency_audit_record_creation(self):
        """测试效率审计记录创建"""
        record = EfficiencyAuditRecord(
            audit_id="audit-001",
            target_type="task",
            target_id="task-001",
            target_name="数据爬取任务",
            input_count=1000,
            output_count=950,
            error_count=5,
        )
        assert record.audit_id == "audit-001"
        assert record.success is True
        assert record.input_count == 1000

    def test_efficiency_audit_record_complete(self):
        """测试审计记录完成"""
        record = EfficiencyAuditRecord(
            audit_id="audit-002",
            target_type="dataset",
            target_id="ds-001",
        )
        record.complete(success=True, output_count=500, error_count=0)
        assert record.ended_at is not None
        assert record.success is True
        assert record.status == "completed"
        assert record.duration_seconds >= 0

    def test_efficiency_audit_derived_metrics(self):
        """测试派生指标计算"""
        start = datetime.now()
        end = start + timedelta(seconds=10)
        record = EfficiencyAuditRecord(
            audit_id="audit-003",
            target_type="task",
            target_id="task-003",
            started_at=start,
            ended_at=end,
            input_count=100,
            output_count=80,
        )
        assert record.duration_seconds == 10.0
        assert record.efficiency_ratio == 0.8
        assert record.throughput == 8.0  # 80 / 10

    def test_efficiency_audit_table_add(self):
        """测试审计表添加记录"""
        table = EfficiencyAuditTable()
        record = EfficiencyAuditRecord(
            audit_id="audit-101",
            target_type="task",
            target_id="t1",
        )
        table.add_audit(record)
        assert table.total_audits == 1
        assert table.get_audit("audit-101") is not None

    def test_efficiency_audit_table_by_target_type(self):
        """测试按目标类型筛选"""
        table = EfficiencyAuditTable()
        table.add_audit(EfficiencyAuditRecord(audit_id="a1", target_type="task", target_id="t1"))
        table.add_audit(EfficiencyAuditRecord(audit_id="a2", target_type="task", target_id="t2"))
        table.add_audit(EfficiencyAuditRecord(audit_id="a3", target_type="dataset", target_id="d1"))
        assert len(table.get_audits_by_target_type("task")) == 2

    def test_efficiency_audit_table_stats(self):
        """测试统计表数据"""
        table = EfficiencyAuditTable()
        for i in range(10):
            start = datetime.now()
            end = start + timedelta(seconds=5 + i)
            table.add_audit(EfficiencyAuditRecord(
                audit_id=f"audit-{i}",
                target_type="task",
                target_id=f"task-{i}",
                started_at=start,
                ended_at=end,
                input_count=100,
                output_count=90 + i,
            ))
        avg_duration = table.get_average_duration("task")
        assert avg_duration > 0
        success_rate = table.get_success_rate("task")
        assert success_rate == 1.0

    def test_efficiency_audit_table_bottlenecks(self):
        """测试瓶颈点统计"""
        table = EfficiencyAuditTable()
        for i in range(5):
            record = EfficiencyAuditRecord(
                audit_id=f"audit-{i}",
                target_type="task",
                target_id=f"task-{i}",
                bottlenecks=["database_io", "memory_limit"] if i < 3 else ["network_latency"],
            )
            table.add_audit(record)
        summary = table.get_bottlenecks_summary(top_n=5)
        assert "database_io" in summary
        assert summary["database_io"] == 3


class TestTopologyTable:
    """测试质能质量子奇点维度空间拓扑数据表"""

    def test_topology_type_enum(self):
        """测试拓扑类型枚举"""
        assert TopologyType.LINEAR == "linear"
        assert TopologyType.TREE == "tree"
        assert TopologyType.GRID == "grid"
        assert TopologyType.DYNAMIC == "dynamic"
        assert len(list(TopologyType)) == 9

    def test_connection_type_enum(self):
        """测试连接类型枚举"""
        assert SingularityConnectionType.ENTANGLEMENT == "entanglement"
        assert SingularityConnectionType.RESONANCE == "resonance"
        assert SingularityConnectionType.CASCADE == "cascade"
        assert len(list(SingularityConnectionType)) == 5

    def test_dimension_topology_node(self):
        """测试维度拓扑节点"""
        node = DimensionTopologyNode(
            node_id="dim-1",
            dimension_type="content",
            coordinates=[1.0, 2.0, 3.0],
            mass=100.0,
            energy=50.0,
            stability=0.9,
        )
        assert node.node_id == "dim-1"
        assert node.effective_mass == pytest.approx(90.0, rel=0.01)
        assert node.mass_energy_ratio == 0.5

    def test_singularity_topology_node(self):
        """测试奇点拓扑节点"""
        node = SingularityTopologyNode(
            singularity_id="sing-1",
            singularity_type="quality_threshold",
            severity="high",
            position=[5.0, 5.0, 5.0],
            intensity=0.8,
            radius=2.0,
            mass=10.0,
            energy=100.0,
        )
        assert node.singularity_id == "sing-1"
        assert node.intensity == 0.8
        assert node.influence_area == pytest.approx(12.566, rel=0.01)

    def test_singularity_connection(self):
        """测试奇点连接"""
        conn = SingularityConnection(
            connection_id="conn-1",
            source_id="sing-1",
            target_id="sing-2",
            connection_type=SingularityConnectionType.ENTANGLEMENT,
            strength=0.7,
            distance=5.0,
            bidirectional=True,
        )
        assert conn.connection_id == "conn-1"
        assert conn.strength == 0.7
        assert conn.bidirectional is True

    def test_topology_metrics(self):
        """测试拓扑度量指标"""
        metrics = TopologyMetrics(
            total_dimensions=5,
            total_singularities=10,
            total_connections=15,
            connectivity=0.6,
        )
        assert metrics.total_dimensions == 5
        assert metrics.total_singularities == 10
        assert metrics.connectivity == 0.6

    def test_topology_table_add_dimension_nodes(self):
        """测试添加维度节点"""
        table = MassEnergySingularityTopologyTable(dimension_count=3)
        node = DimensionTopologyNode(
            node_id="dim-node-1",
            dimension_type="content",
            coordinates=[0, 0, 0],
            mass=100.0,
            energy=50.0,
        )
        table.add_dimension_node(node)
        assert table.metrics.total_dimensions == 1
        assert table.metrics.total_mass == 100.0

    def test_topology_table_add_singularity_nodes(self):
        """测试添加奇点节点"""
        table = MassEnergySingularityTopologyTable(dimension_count=3)
        sing = SingularityTopologyNode(
            singularity_id="sing-node-1",
            singularity_type="quality_threshold",
            severity="medium",
            position=[1, 1, 1],
            intensity=0.5,
            mass=5.0,
            energy=20.0,
        )
        table.add_singularity_node(sing)
        assert table.metrics.total_singularities == 1

    def test_topology_table_add_connection(self):
        """测试添加连接"""
        table = MassEnergySingularityTopologyTable(dimension_count=3)
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="s1",
            singularity_type="anomaly",
            position=[0, 0, 0],
        ))
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="s2",
            singularity_type="anomaly",
            position=[3, 4, 0],
        ))
        conn = SingularityConnection(
            connection_id="c1",
            source_id="s1",
            target_id="s2",
            connection_type=SingularityConnectionType.ENTANGLEMENT,
            strength=0.8,
            distance=5.0,
        )
        table.add_connection(conn)
        assert table.metrics.total_connections == 1

    def test_topology_table_distance(self):
        """测试距离计算"""
        table = MassEnergySingularityTopologyTable(dimension_count=3)
        dist = table.calculate_distance([0, 0, 0], [3, 4, 0])
        assert dist == pytest.approx(5.0, rel=0.01)

    def test_topology_table_nearby_singularities(self):
        """测试附近奇点查找"""
        table = MassEnergySingularityTopologyTable(dimension_count=2)
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="near-1",
            singularity_type="a",
            position=[1, 1],
        ))
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="near-2",
            singularity_type="b",
            position=[10, 10],
        ))
        nearby = table.find_nearby_singularities([0, 0], radius=5.0)
        assert len(nearby) == 1
        assert nearby[0][0].singularity_id == "near-1"

    def test_topology_table_adjacency_matrix(self):
        """测试邻接矩阵"""
        table = MassEnergySingularityTopologyTable(dimension_count=2)
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="a1", singularity_type="t", position=[0, 0]
        ))
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="a2", singularity_type="t", position=[1, 1]
        ))
        table.add_connection(SingularityConnection(
            connection_id="ac1",
            source_id="a1",
            target_id="a2",
            connection_type=SingularityConnectionType.ENTANGLEMENT,
            strength=0.5,
        ))
        matrix = table.get_adjacency_matrix()
        assert matrix.shape == (2, 2)
        assert matrix[0][1] == 0.5
        assert matrix[1][0] == 0.5  # 双向

    def test_topology_table_remove_singularity(self):
        """测试移除奇点"""
        table = MassEnergySingularityTopologyTable(dimension_count=2)
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="rm-1", singularity_type="t", position=[0, 0]
        ))
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="rm-2", singularity_type="t", position=[1, 1]
        ))
        table.add_connection(SingularityConnection(
            connection_id="rc1", source_id="rm-1", target_id="rm-2",
            connection_type=SingularityConnectionType.ENTANGLEMENT,
        ))
        assert table.metrics.total_singularities == 2
        assert table.metrics.total_connections == 1

        result = table.remove_singularity("rm-1")
        assert result is True
        assert table.metrics.total_singularities == 1
        assert table.metrics.total_connections == 0

    def test_topology_table_criticality(self):
        """测试临界度计算"""
        table = MassEnergySingularityTopologyTable(dimension_count=2)
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="c1", singularity_type="t", severity="high", position=[0, 0]
        ))
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="c2", singularity_type="t", severity="medium", position=[1, 1]
        ))
        assert table.critical_singularity_count == 1
        assert table.is_critical is False

    def test_topology_table_metrics_recalculation(self):
        """测试度量指标自动重计算"""
        table = MassEnergySingularityTopologyTable(dimension_count=3)
        table.add_dimension_node(DimensionTopologyNode(
            node_id="d1", dimension_type="content", coordinates=[0, 0, 0],
            mass=100, energy=50, stability=0.8,
        ))
        table.add_singularity_node(SingularityTopologyNode(
            singularity_id="s1", singularity_type="anomaly", severity="high",
            position=[1, 1, 1], mass=10, energy=100,
        ))
        assert table.metrics.total_mass == 110.0
        assert table.metrics.total_energy == 150.0
        assert table.metrics.stability_index > 0
