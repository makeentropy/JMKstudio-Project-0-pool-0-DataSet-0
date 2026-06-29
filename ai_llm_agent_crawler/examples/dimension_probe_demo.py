#!/usr/bin/env python3
"""
维度空间探针 - 完整演示

展示数据集的多维度探测、路径扫描、奇点检测和空间拓扑分析。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np

from ai_llm_agent_crawler.dimension.probe import DimensionSpaceProbe
from ai_llm_agent_crawler.utils.logging import LogManager

LogManager.initialize(log_level="WARNING", enable_file_logging=False)

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

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


def generate_test_dataset(n_rows: int = 500) -> pd.DataFrame:
    np.random.seed(42)

    data = {}

    data['id'] = range(1, n_rows + 1)

    data['normal_dist'] = np.random.normal(loc=50, scale=10, size=n_rows)

    data['uniform_dist'] = np.random.uniform(low=0, high=100, size=n_rows)

    data['skewed_dist'] = np.random.exponential(scale=20, size=n_rows)

    outliers_idx = np.random.choice(n_rows, size=20, replace=False)
    data['with_outliers'] = np.random.normal(loc=30, scale=8, size=n_rows)
    data['with_outliers'][outliers_idx[:10]] += 50
    data['with_outliers'][outliers_idx[10:]] -= 40

    categories = ['A', 'B', 'C', 'D', 'E']
    data['category'] = np.random.choice(categories, size=n_rows, p=[0.3, 0.25, 0.2, 0.15, 0.1])

    sub_categories = ['X', 'Y', 'Z']
    data['sub_category'] = np.random.choice(sub_categories, size=n_rows)

    text_samples = [
        'This is a sample text for testing purposes.',
        'Data quality is important for analysis.',
        None,
        'Another example text with more content.',
        '',
        'Short text.',
        None,
        'Medium length text content here.',
    ]
    data['text_column'] = np.random.choice(text_samples, size=n_rows)

    data['name'] = [f'item_{i}' for i in range(n_rows)]
    data['name'][0] = None

    data['description'] = [
        f'Description for item {i}' if i % 5 != 0 else None
        for i in range(n_rows)
    ]

    dates = pd.date_range(start='2024-01-01', periods=n_rows, freq='h')
    data['date_column'] = dates

    data['date_with_missing'] = dates.copy()
    missing_dates = list(data['date_with_missing'])
    missing_idx = np.random.choice(n_rows, size=50, replace=False)
    for idx in missing_idx:
        missing_dates[idx] = pd.NaT
    data['date_with_missing'] = missing_dates

    data['correlated_a'] = data['normal_dist'] * 2 + np.random.normal(0, 2, n_rows)

    data['correlated_b'] = data['normal_dist'] * -1.5 + np.random.normal(0, 3, n_rows)

    data['score'] = np.clip(
        data['normal_dist'] * 0.5 + data['uniform_dist'] * 0.3 + np.random.normal(0, 5, n_rows),
        0, 100
    )

    df = pd.DataFrame(data)

    dup_indices = np.random.choice(n_rows, size=30, replace=False)
    df = pd.concat([df, df.iloc[dup_indices].copy()], ignore_index=True)

    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


def main():
    print("\n" + SEPARATOR)
    print("  维度空间探针 DimensionSpaceProbe - 完整功能演示")
    print(SEPARATOR)
    print("\n  本演示将展示数据集的多维度探测与分析功能")
    print("  包含质量、结构、统计、内容、关系五大维度")

    print_title("初始化探针", 1)

    config = {
        "probe_depth": 2,
        "sensitivity": 0.8,
    }
    probe = DimensionSpaceProbe(config=config)

    print(f"\n  探针配置:")
    print(f"    探测深度: {probe.probe_depth}")
    print(f"    奇点检测灵敏度: {config.get('sensitivity', 'default')}")
    print(f"    组件:")
    print(f"      - 质量评估器 (QualityAssessor)")
    print(f"      - 奇点检测器 (SingularityDetector)")

    print_title("准备测试数据集", 2)

    print("  正在生成测试数据集...")
    df = generate_test_dataset(n_rows=500)

    print(f"\n  数据集概览:")
    print(f"    记录数: {len(df)}")
    print(f"    字段数: {len(df.columns)}")
    print(f"    字段列表: {', '.join(df.columns)}")

    print_section("数据类型分布:")
    dtype_counts = df.dtypes.value_counts()
    for dtype, count in dtype_counts.items():
        print(f"    {dtype}: {count} 个字段")

    print_section("数值字段列表:")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    print(f"    {len(numeric_cols)} 个数值字段: {', '.join(numeric_cols)}")

    print_section("文本/分类字段列表:")
    text_cols = [col for col in df.columns if df[col].dtype == 'object' or df[col].dtype == 'string' or pd.api.types.is_string_dtype(df[col])]
    print(f"    {len(text_cols)} 个文本/分类字段: {', '.join(text_cols)}")

    print_section("日期字段列表:")
    date_cols = df.select_dtypes(include=['datetime64[ns]']).columns.tolist()
    print(f"    {len(date_cols)} 个日期字段: {', '.join(date_cols)}")

    print_section("缺失值统计:")
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0].sort_values(ascending=False)
    for col, count in null_cols.items():
        pct = count / len(df) * 100
        print(f"    {col}: {count} 个缺失值 ({pct:.1f}%)")

    print_title("全维度探测", 3)
    print("  调用 probe() 方法进行全维度探测...")

    report = probe.probe(df, dataset_name="demo_dataset")

    print(f"\n  探测报告摘要:")
    print(f"    报告ID: {report.report_id}")
    print(f"    数据集名称: {report.dataset_name}")
    print(f"    记录数: {report.record_count}")
    print(f"    字段数: {report.field_count}")
    print(f"    整体健康度: {report.overall_health_score:.3f}")
    print(f"    严重问题数: {len(report.critical_issues)}")
    print(f"    警告数: {len(report.warnings)}")
    print(f"    建议数: {len(report.recommendations)}")
    print(f"    探测耗时: {report.total_duration_ms:.2f}ms")

    print_section("数据概览:")
    print(f"    数据集规模: {report.record_count} 条记录 × {report.field_count} 个字段")

    health_bar = "█" * int(report.overall_health_score * 30)
    print(f"    整体健康度: [{health_bar:<30s}] {report.overall_health_score:.1%}")

    print_section("质量评分 - 各维度健康度:")
    for dim_key, dim_result in report.dimension_results.items():
        bar = "█" * int(dim_result.health_score * 30)
        print(f"    {dim_key:<15s} [{bar:<30s}] {dim_result.health_score:.3f}")
        print(f"      异常数: {dim_result.anomalies_found}, "
              f"耗时: {dim_result.execution_time_ms:.1f}ms")

    print_section("结构特征:")
    structural = report.dimension_results.get('structural')
    if structural:
        metrics = structural.quantitative_metrics
        print(f"    字段数: {int(metrics.get('field_count', 0))}")
        print(f"    记录数: {int(metrics.get('record_count', 0))}")
        print(f"    数据类型数: {int(metrics.get('type_count', 0))}")
        print(f"    嵌套层级: {int(metrics.get('nested_level', 1))}")
        print(f"    数据稀疏度: {metrics.get('sparsity', 0):.1%}")

    print_section("统计特征:")
    statistical = report.dimension_results.get('statistical')
    if statistical:
        metrics = statistical.quantitative_metrics
        print(f"    数值字段数: {int(metrics.get('numeric_field_count', 0))}")
        print(f"    平均均值: {metrics.get('avg_mean', 0):.2f}")
        print(f"    平均标准差: {metrics.get('avg_std', 0):.2f}")
        print(f"    平均偏度: {metrics.get('avg_skewness', 0):.2f}")
        print(f"    平均峰度: {metrics.get('avg_kurtosis', 0):.2f}")
        print(f"    平均离群点比例: {metrics.get('avg_outlier_ratio', 0):.1%}")

    print_section("内容特征:")
    content = report.dimension_results.get('content')
    if content:
        metrics = content.quantitative_metrics
        print(f"    文本字段数: {int(metrics.get('text_field_count', 0))}")
        print(f"    平均文本长度: {metrics.get('avg_text_length', 0):.1f} 字符")
        print(f"    平均空值率: {metrics.get('avg_null_ratio', 0):.1%}")
        print(f"    平均重复率: {metrics.get('avg_duplicate_ratio', 0):.1%}")
        print(f"    平均唯一值率: {metrics.get('avg_unique_ratio', 0):.1%}")

    print_section("关系特征:")
    relational = report.dimension_results.get('relational')
    if relational:
        metrics = relational.quantitative_metrics
        print(f"    数值字段数: {int(metrics.get('numeric_field_count', 0))}")
        print(f"    字段对总数: {int(metrics.get('total_field_pairs', 0))}")
        print(f"    高相关对数: {int(metrics.get('high_correlation_pairs', 0))}")
        print(f"    独立性得分: {metrics.get('independence_score', 0):.3f}")

    print_title("质量维度详解", 4)

    quality_result = report.dimension_results.get('quality')

    if quality_result:
        print(f"\n  质量维度详细信息:")
        print(f"    健康度: {quality_result.health_score:.3f}")
        print(f"    定性描述: {quality_result.qualitative_description}")
        print(f"    异常指标数: {quality_result.anomalies_found}")

        print_section("各项质量指标:")
        for metric_name, score in quality_result.quantitative_metrics.items():
            bar = "█" * int(score * 25)
            status = "✓" if score >= 0.7 else "!"
            print(f"    {status} {metric_name:<20s} [{bar:<25s}] {score:.3f}")

        print_section("缺失值统计:")
        null_counts = df.isnull().sum()
        total_cells = len(df) * len(df.columns)
        total_null = null_counts.sum()
        print(f"    总缺失值数: {total_null}")
        print(f"    整体缺失率: {total_null / total_cells:.2%}")
        print(f"    含缺失值的字段数: {int((null_counts > 0).sum())}")

        print("\n    各字段缺失值详情:")
        null_cols = null_counts[null_counts > 0].sort_values(ascending=False)
        for col, count in null_cols.items():
            pct = count / len(df) * 100
            bar = "▓" * int(pct / 2)
            print(f"      {col:<25s} {count:>6d} [{bar:<20s}] {pct:>5.1f}%")

        print_section("重复值统计:")
        dup_count = df.duplicated().sum()
        print(f"    完全重复行数: {dup_count}")
        print(f"    重复率: {dup_count / len(df):.2%}")

        print_section("异常值统计:")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        total_outliers = 0
        outlier_details = []

        for col in numeric_cols:
            values = df[col].dropna()
            if len(values) < 2:
                continue
            z_scores = np.abs((values - values.mean()) / values.std())
            col_outliers = (z_scores > 3).sum()
            total_outliers += col_outliers
            if col_outliers > 0:
                outlier_details.append((col, col_outliers, col_outliers / len(values) * 100))

        print(f"    总异常值数 (Z-score > 3): {total_outliers}")
        print(f"    含异常值的字段数: {len(outlier_details)}")

        if outlier_details:
            print("\n    各字段异常值详情:")
            for col, count, pct in sorted(outlier_details, key=lambda x: -x[1]):
                print(f"      {col:<25s} {count:>6d} 个 ({pct:.1f}%)")

        print_title("路径探测", 5)
    print("  沿数值维度进行路径探测...")

    field_name = 'normal_dist'
    path_result = probe.probe_path(df, field_name, step_size=0.05)

    print(f"\n  路径探测结果 - {field_name}:")
    print(f"    维度: {path_result.dimension}")
    print(f"    探测点数: {len(path_result.path_points)}")
    print(f"    步长: {path_result.step_size}")
    print(f"    临界点数: {len(path_result.critical_points)}")
    print(f"    异常区域数: {len(path_result.anomaly_regions)}")
    print(f"    执行时间: {path_result.execution_time_ms:.2f}ms")

    print_section("数据分布统计:")
    dist = path_result.distribution
    if dist:
        print(f"    最小值: {dist.get('min', 0):.2f}")
        print(f"    最大值: {dist.get('max', 0):.2f}")
        print(f"    均值: {dist.get('mean', 0):.2f}")
        print(f"    中位数: {dist.get('median', 0):.2f}")
        print(f"    标准差: {dist.get('std', 0):.2f}")
        print(f"    偏度: {dist.get('skew', 0):.3f}")
        print(f"    峰度: {dist.get('kurtosis', 0):.3f}")

    print_section("路径点 (前 10 个点):")
    for i, point in enumerate(path_result.path_points[:10]):
        marker = "!" if point.is_critical else " "
        print(f"    {marker} 位置 {point.position:.3f}: "
              f"值={point.value:.2f}, "
              f"密度={point.density:.3f}, "
              f"异常分={point.anomaly_score:.3f}"
              + (f" - {point.description}" if point.description else ""))

    print_section("临界点:")
    if path_result.critical_points:
        for i, point in enumerate(path_result.critical_points[:5], 1):
            print(f"    {i}. 位置 {point.position:.3f}: "
                  f"值={point.value:.2f}, "
                  f"异常分={point.anomaly_score:.2f}")
            if point.description:
                print(f"       {point.description}")
    else:
        print("    未检测到临界点")

    print_section("异常区域:")
    if path_result.anomaly_regions:
        for i, region in enumerate(path_result.anomaly_regions, 1):
            print(f"    {i}. [{region['start']:.3f} - {region['end']:.3f}] "
                  f"({region['severity']}) - "
                  f"连续 {region['consecutive_count']} 个点, "
                  f"最大异常分 {region['max_anomaly_score']:.2f}")
            print(f"       {region['description']}")
    else:
        print("    未检测到连续异常区域")

    print_title("多维度路径探测", 6)
    print("  沿多个维度组合进行路径探测...")

    fields_to_probe = ['uniform_dist', 'skewed_dist', 'with_outliers', 'score']
    multi_path = probe.probe_path_multi(df, fields_to_probe, step_size=0.1)

    print(f"\n  多维度路径探测结果:")
    print(f"    探测字段数: {len(multi_path)}")

    for field_name, result in multi_path.items():
        print(f"\n  字段: {field_name}")
        print(f"    探测点数: {len(result.path_points)}")
        print(f"    临界点数: {len(result.critical_points)}")
        print(f"    异常区域数: {len(result.anomaly_regions)}")

        dist = result.distribution
        if dist and 'mean' in dist:
            print(f"    均值: {dist['mean']:.2f}, "
                  f"标准差: {dist.get('std', 0):.2f}")

    print_title("空间拓扑分析", 7)
    print("  调用 analyze_topology() 分析维度空间拓扑结构...")

    topology = probe.analyze_topology(df)

    print(f"\n  维度空间拓扑分析:")
    print(f"    数值维度数: {topology.num_dimensions}")
    print(f"    聚类数: {topology.cluster_count}")

    print_section("质心 (各维度均值):")
    for dim, value in topology.centroid.items():
        print(f"    {dim}: {value:.3f}")

    print_section("密度分布:")
    for dim, density in topology.density_distribution.items():
        print(f"    {dim}: {density:.4f}")

    print_section("边界点 (各维度范围):")
    for bp in topology.boundary_points:
        print(f"    {bp['field']}: [{bp['min']:.2f}, {bp['max']:.2f}] "
              f"(范围: {bp['range']:.2f})")

    print_section("聚类信息:")
    if topology.cluster_info:
        for i, cluster in enumerate(topology.cluster_info, 1):
            print(f"\n    聚类 #{cluster['cluster_id'] + 1}:")
            print(f"      大小: {cluster['size']} 条记录")
            print(f"      范围: [{cluster['range']['min']:.2f} ~ {cluster['range']['max']:.2f}]")
            features = cluster.get('feature_description', {})
            if features:
                print(f"      特征统计:")
                for feat, stats in list(features.items())[:3]:
                    print(f"        {feat}: mean={stats.get('mean', 0):.2f}, "
                          f"std={stats.get('std', 0):.2f}")

    print_section("距离矩阵 (前 5 个维度):")
    if topology.distance_matrix:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:5]
        print(f"    矩阵大小: {len(topology.distance_matrix)} × {len(topology.distance_matrix[0])}")
        print(f"    (距离 = 1 - |相关系数|)")
        print(f"    值越小表示越相关")

        if len(numeric_cols) >= 2:
            header = "        " + "".join(f"{col[:8]:>9s}" for col in numeric_cols[:5])
            print(header)
            for i, col in enumerate(numeric_cols[:5]):
                row = f"    {col[:8]:8s}"
                for j in range(min(5, len(topology.distance_matrix[i]))):
                    row += f"{topology.distance_matrix[i][j]:>9.3f}"
                print(row)

    print_title("奇点检测", 8)
    print("  检测数据中的奇点 (异常点、临界点)...")

    singularities = probe.detect_singularities(df)

    print(f"\n  奇点检测结果:")
    print(f"    发现奇点总数: {len(singularities)}")

    if singularities:
        by_severity = {}
        for sing in singularities:
            sev = sing.get('severity', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1

        print_section("按严重程度分布:")
        for sev, count in by_severity.items():
            print(f"    {sev}: {count} 个")

        by_type = {}
        for sing in singularities:
            typ = sing.get('type', 'unknown')
            by_type[typ] = by_type.get(typ, 0) + 1

        print_section("按类型分布:")
        for typ, count in by_type.items():
            print(f"    {typ}: {count} 个")

        print_section("奇点详情 (前 10 个):")
        for i, sing in enumerate(singularities[:10], 1):
            print(f"\n    奇点 #{i}:")
            print(f"      类型: {sing.get('type', 'N/A')}")
            print(f"      维度: {sing.get('dimension', 'N/A')}")
            print(f"      严重程度: {sing.get('severity', 'N/A')}")
            print(f"      描述: {sing.get('description', 'N/A')}")
            print(f"      质量分: {sing.get('quality_score', 'N/A')}")
            print(f"      影响记录数: {sing.get('affected_records', 'N/A')}")
    else:
        print("\n    未检测到明显奇点")

    print_title("数据质量建议", 9)

    print(f"\n  基于探测结果的优化建议:")
    print(f"    共 {len(report.recommendations)} 条建议")

    for i, recommendation in enumerate(report.recommendations, 1):
        print(f"\n  {i}. {recommendation}")

    print_section("严重问题列表:")
    if report.critical_issues:
        for i, issue in enumerate(report.critical_issues, 1):
            print(f"    [{issue['severity'].upper()}] [{issue['dimension']}] "
                  f"{issue['description']}")
    else:
        print("    无严重问题 ✓")

    print_section("警告列表:")
    if report.warnings:
        for i, issue in enumerate(report.warnings[:10], 1):
            print(f"    [{issue['severity'].upper()}] [{issue['dimension']}] "
                  f"{issue['description']}")
        if len(report.warnings) > 10:
            print(f"    ... 还有 {len(report.warnings) - 10} 条警告")
    else:
        print("    无警告 ✓")

    print("\n" + SEPARATOR)
    print("  演示总结")
    print(SEPARATOR)
    print("""
  本演示展示了 DimensionSpaceProbe 的完整功能：

  1. 全维度探测 - 质量、结构、统计、内容、关系五大维度
  2. 质量评估 - 完整性、准确性、一致性、有效性、唯一性
  3. 路径探测 - 沿单维度扫描数据分布和异常
  4. 多维度路径探测 - 多字段组合分析
  5. 空间拓扑分析 - 质心、密度、边界、聚类
  6. 奇点检测 - 异常点、临界点识别
  7. 优化建议 - 基于探测结果的改进建议

  使用提示：
  - 使用 probe() 方法获取完整探测报告
  - 使用 probe_path() 深入分析特定字段分布
  - 使用 analyze_topology() 了解数据空间结构
  - 使用 detect_singularities() 发现数据异常
  - 结合 report.recommendations 进行数据清洗
""")
    print(SEPARATOR)
    print("  演示完成！感谢观看。")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    main()
