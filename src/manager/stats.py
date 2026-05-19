from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import statistics
from pydantic import BaseModel, Field
from .metadata import DatasetMetadata, DataSource, MetadataManager
from .version_manager import VersionManager, VersionHistoryItem


class AnnotationStats(BaseModel):
    total_annotations: int = Field(default=0, description="总注解数")
    label_distribution: Dict[str, int] = Field(default_factory=dict, description="标签分布")
    avg_confidence: float = Field(default=0.0, description="平均置信度")
    annotator_distribution: Dict[str, int] = Field(default_factory=dict, description="注解者分布")


class QualityStats(BaseModel):
    avg_quality_score: float = Field(default=0.0, description="平均质量分数")
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="质量分数分布")
    verified_count: int = Field(default=0, description="已验证条数")
    unverified_count: int = Field(default=0, description="未验证条数")


class TextStats(BaseModel):
    avg_input_length: float = Field(default=0.0, description="平均输入长度")
    avg_response_length: float = Field(default=0.0, description="平均响应长度")
    input_length_distribution: Dict[str, int] = Field(default_factory=dict, description="输入长度分布")
    response_length_distribution: Dict[str, int] = Field(default_factory=dict, description="响应长度分布")


class DatasetStats(BaseModel):
    dataset_id: str = Field(description="数据集ID")
    dataset_name: str = Field(description="数据集名称")
    total_entries: int = Field(default=0, description="总数据条数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    annotation_stats: AnnotationStats = Field(default_factory=AnnotationStats, description="注解统计")
    quality_stats: QualityStats = Field(default_factory=QualityStats, description="质量统计")
    text_stats: TextStats = Field(default_factory=TextStats, description="文本统计")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OverallStats(BaseModel):
    total_datasets: int = Field(default=0, description="总数据集数")
    total_entries: int = Field(default=0, description="总数据条数")
    total_file_size: int = Field(default=0, description="总文件大小")
    source_distribution: Dict[str, int] = Field(default_factory=dict, description="来源分布")
    datasets_by_source: Dict[str, List[str]] = Field(default_factory=dict, description="各来源的数据集")


class StatsManager:
    def __init__(self, data_dir: Union[str, Path] = "/workspace/data"):
        self.data_dir = Path(data_dir)
        self.metadata_manager = MetadataManager(data_dir)
        self.version_manager = VersionManager(data_dir)

    def analyze_dataset(self, dataset: DatasetMetadata) -> DatasetStats:
        annotation_stats = AnnotationStats()
        quality_stats = QualityStats()
        text_stats = TextStats()

        if not dataset.file_path:
            return DatasetStats(
                dataset_id=dataset.dataset_id,
                dataset_name=dataset.name,
                total_entries=dataset.data_count,
                created_at=dataset.created_at
            )

        path = dataset.file_path
        quality_scores = []
        input_lengths = []
        response_lengths = []
        all_labels = []
        all_annotators = []
        verified_count = 0

        files = []
        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob("*.jsonl")) + list(path.rglob("*.json"))

        for file in files:
            try:
                if file.suffix == ".jsonl":
                    with open(file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            data = json.loads(line)
                            self._process_data_entry(
                                data,
                                quality_scores,
                                input_lengths,
                                response_lengths,
                                all_labels,
                                all_annotators,
                                verified_count
                            )
                elif file.suffix == ".json":
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for entry in data:
                                self._process_data_entry(
                                    entry,
                                    quality_scores,
                                    input_lengths,
                                    response_lengths,
                                    all_labels,
                                    all_annotators,
                                    verified_count
                                )
                        else:
                            self._process_data_entry(
                                data,
                                quality_scores,
                                input_lengths,
                                response_lengths,
                                all_labels,
                                all_annotators,
                                verified_count
                            )
            except Exception:
                continue

        if quality_scores:
            quality_stats.avg_quality_score = statistics.mean(quality_scores)
            quality_dist = Counter()
            for score in quality_scores:
                if score < 0.3:
                    quality_dist["low"] += 1
                elif score < 0.7:
                    quality_dist["medium"] += 1
                else:
                    quality_dist["high"] += 1
            quality_stats.quality_distribution = dict(quality_dist)

        quality_stats.verified_count = verified_count
        quality_stats.unverified_count = dataset.data_count - verified_count

        if all_labels:
            annotation_stats.total_annotations = len(all_labels)
            annotation_stats.label_distribution = dict(Counter(all_labels))

        if all_annotators:
            annotation_stats.annotator_distribution = dict(Counter(all_annotators))

        confidences = []
        for file in files:
            try:
                if file.suffix == ".jsonl":
                    with open(file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            data = json.loads(line)
                            annotations = data.get("annotations", [])
                            for ann in annotations:
                                conf = ann.get("confidence", 1.0)
                                if isinstance(conf, (int, float)):
                                    confidences.append(conf)
                elif file.suffix == ".json":
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        entries = data if isinstance(data, list) else [data]
                        for entry in entries:
                            annotations = entry.get("annotations", [])
                            for ann in annotations:
                                conf = ann.get("confidence", 1.0)
                                if isinstance(conf, (int, float)):
                                    confidences.append(conf)
            except Exception:
                continue

        if confidences:
            annotation_stats.avg_confidence = statistics.mean(confidences)

        if input_lengths:
            text_stats.avg_input_length = statistics.mean(input_lengths)
            input_dist = Counter()
            for length in input_lengths:
                if length < 20:
                    input_dist["short (<20)"] += 1
                elif length < 100:
                    input_dist["medium (20-100)"] += 1
                else:
                    input_dist["long (>100)"] += 1
            text_stats.input_length_distribution = dict(input_dist)

        if response_lengths:
            text_stats.avg_response_length = statistics.mean(response_lengths)
            resp_dist = Counter()
            for length in response_lengths:
                if length < 20:
                    resp_dist["short (<20)"] += 1
                elif length < 100:
                    resp_dist["medium (20-100)"] += 1
                else:
                    resp_dist["long (>100)"] += 1
            text_stats.response_length_distribution = dict(resp_dist)

        return DatasetStats(
            dataset_id=dataset.dataset_id,
            dataset_name=dataset.name,
            total_entries=dataset.data_count,
            created_at=dataset.created_at,
            annotation_stats=annotation_stats,
            quality_stats=quality_stats,
            text_stats=text_stats
        )

    def _process_data_entry(
        self,
        data: Dict[str, Any],
        quality_scores: List[float],
        input_lengths: List[int],
        response_lengths: List[int],
        all_labels: List[str],
        all_annotators: List[str],
        verified_count: int
    ):
        if isinstance(data, dict):
            quality_score = data.get("quality_score")
            if isinstance(quality_score, (int, float)):
                quality_scores.append(quality_score)

            original = data.get("original_interaction", {})
            if isinstance(original, dict):
                user_input = original.get("user_input", "")
                agent_response = original.get("agent_response", "")
                if user_input:
                    input_lengths.append(len(str(user_input)))
                if agent_response:
                    response_lengths.append(len(str(agent_response)))

            annotations = data.get("annotations", [])
            if isinstance(annotations, list):
                for ann in annotations:
                    if isinstance(ann, dict):
                        label = ann.get("label")
                        if label:
                            all_labels.append(str(label))
                        annotator = ann.get("annotator_type")
                        if annotator:
                            all_annotators.append(str(annotator))

            if data.get("is_verified"):
                verified_count += 1

    def get_overall_stats(self) -> OverallStats:
        datasets = self.metadata_manager.list_datasets()
        overall = OverallStats(total_datasets=len(datasets))

        for dataset in datasets:
            overall.total_entries += dataset.data_count
            overall.total_file_size += dataset.file_size

            source = dataset.source.value
            overall.source_distribution[source] = overall.source_distribution.get(source, 0) + 1

            if source not in overall.datasets_by_source:
                overall.datasets_by_source[source] = []
            overall.datasets_by_source[source].append(dataset.name)

        return overall

    def get_version_trend(
        self,
        dataset_id: str,
        metric: str = "data_count"
    ) -> List[Dict[str, Any]]:
        versions = self.version_manager.list_versions(dataset_id)
        trend = []

        for v in versions:
            entry = {
                "version": v.version,
                "timestamp": v.timestamp,
                "value": getattr(v, metric, 0)
            }
            trend.append(entry)

        return sorted(trend, key=lambda x: x["timestamp"])

    def format_size(self, size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def print_stats_report(self, dataset_id: Optional[str] = None):
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        if dataset_id:
            dataset = self.metadata_manager.load_metadata(dataset_id)
            if not dataset:
                console.print(f"[red]Dataset not found: {dataset_id}[/red]")
                return

            stats = self.analyze_dataset(dataset)

            console.print(Panel(f"[bold blue]Dataset Stats: {stats.dataset_name}[/bold blue]"))

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Metric")
            table.add_column("Value")

            table.add_row("Total Entries", str(stats.total_entries))
            table.add_row("Created At", stats.created_at.strftime("%Y-%m-%d %H:%M:%S"))

            console.print(table)

            if stats.annotation_stats.total_annotations > 0:
                console.print("\n[bold]Annotation Stats:[/bold]")
                ann_table = Table(show_header=True, header_style="bold magenta")
                ann_table.add_column("Label")
                ann_table.add_column("Count")

                for label, count in stats.annotation_stats.label_distribution.items():
                    ann_table.add_row(str(label), str(count))

                console.print(ann_table)
                console.print(f"Average Confidence: {stats.annotation_stats.avg_confidence:.2f}")

            if stats.quality_stats.avg_quality_score > 0:
                console.print("\n[bold]Quality Stats:[/bold]")
                console.print(f"Average Quality Score: {stats.quality_stats.avg_quality_score:.2f}")
                console.print(f"Verified: {stats.quality_stats.verified_count}")
                console.print(f"Unverified: {stats.quality_stats.unverified_count}")

        else:
            overall = self.get_overall_stats()
            console.print(Panel("[bold blue]Overall Data Stats[/bold blue]"))

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Metric")
            table.add_column("Value")

            table.add_row("Total Datasets", str(overall.total_datasets))
            table.add_row("Total Entries", str(overall.total_entries))
            table.add_row("Total File Size", self.format_size(overall.total_file_size))

            console.print(table)

            console.print("\n[bold]Datasets by Source:[/bold]")
            source_table = Table(show_header=True, header_style="bold magenta")
            source_table.add_column("Source")
            source_table.add_column("Count")

            for source, count in overall.source_distribution.items():
                source_table.add_row(source, str(count))

            console.print(source_table)
