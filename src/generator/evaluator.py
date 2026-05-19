from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

from datasets import Dataset
from config.config import settings


logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    BLEU = "bleu"
    ROUGE = "rouge"
    PERPLEXITY = "perplexity"
    CUSTOM = "custom"


@dataclass
class EvaluationResult:
    metric_name: str
    value: float
    metric_type: MetricType
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BenchmarkResult:
    benchmark_name: str
    model_name: str
    metrics: List[EvaluationResult]
    dataset_info: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "model_name": self.model_name,
            "metrics": [
                {
                    "metric_name": m.metric_name,
                    "value": m.value,
                    "metric_type": m.metric_type.value,
                    "details": m.details,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self.metrics
            ],
            "dataset_info": self.dataset_info,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricCalculator:
    @staticmethod
    def accuracy(predictions: List[Any], references: List[Any]) -> EvaluationResult:
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have the same length")
            
        correct = sum(1 for pred, ref in zip(predictions, references) if pred == ref)
        total = len(predictions)
        accuracy = correct / total if total > 0 else 0.0
        
        return EvaluationResult(
            metric_name="accuracy",
            value=accuracy,
            metric_type=MetricType.ACCURACY,
            details={"correct": correct, "total": total},
        )
        
    @staticmethod
    def exact_match(predictions: List[str], references: List[str]) -> EvaluationResult:
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have the same length")
            
        correct = sum(1 for pred, ref in zip(predictions, references) if pred.strip() == ref.strip())
        total = len(predictions)
        em_score = correct / total if total > 0 else 0.0
        
        return EvaluationResult(
            metric_name="exact_match",
            value=em_score,
            metric_type=MetricType.ACCURACY,
            details={"correct": correct, "total": total},
        )
        
    @staticmethod
    def f1_score(predictions: List[Any], references: List[Any], average: str = "macro") -> EvaluationResult:
        from sklearn.metrics import f1_score as sklearn_f1
        
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have the same length")
            
        f1 = sklearn_f1(references, predictions, average=average, zero_division=0)
        
        return EvaluationResult(
            metric_name=f"f1_{average}",
            value=f1,
            metric_type=MetricType.F1,
            details={"average": average},
        )
        
    @staticmethod
    def rouge_scores(predictions: List[str], references: List[str]) -> List[EvaluationResult]:
        try:
            from rouge_score import rouge_scorer
        except ImportError:
            logger.warning("rouge_score not installed, skipping ROUGE calculation")
            return []
            
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have the same length")
            
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        
        rouge1_scores = []
        rouge2_scores = []
        rougeL_scores = []
        
        for pred, ref in zip(predictions, references):
            scores = scorer.score(ref, pred)
            rouge1_scores.append(scores["rouge1"].fmeasure)
            rouge2_scores.append(scores["rouge2"].fmeasure)
            rougeL_scores.append(scores["rougeL"].fmeasure)
            
        results = []
        
        if rouge1_scores:
            results.append(EvaluationResult(
                metric_name="rouge1",
                value=statistics.mean(rouge1_scores),
                metric_type=MetricType.ROUGE,
                details={"scores": rouge1_scores[:10]},
            ))
            
        if rouge2_scores:
            results.append(EvaluationResult(
                metric_name="rouge2",
                value=statistics.mean(rouge2_scores),
                metric_type=MetricType.ROUGE,
                details={"scores": rouge2_scores[:10]},
            ))
            
        if rougeL_scores:
            results.append(EvaluationResult(
                metric_name="rougeL",
                value=statistics.mean(rougeL_scores),
                metric_type=MetricType.ROUGE,
                details={"scores": rougeL_scores[:10]},
            ))
            
        return results


class AgentEvaluator:
    def __init__(
        self,
        model_name: str,
        test_dataset: Optional[Dataset] = None,
        dataset_dir: Optional[Union[str, Path]] = None,
    ):
        self.model_name = model_name
        self.test_dataset = test_dataset
        self.dataset_dir = Path(dataset_dir) if dataset_dir else settings.FINAL_DATA_DIR
        self.custom_metrics: Dict[str, Callable] = {}
        
    def load_test_dataset(
        self,
        dataset_dir: Optional[Union[str, Path]] = None,
        split: str = "test",
    ) -> Dataset:
        target_dir = Path(dataset_dir) if dataset_dir else self._find_latest_dataset()
        
        if target_dir is None:
            raise ValueError("No dataset found")
            
        test_path = target_dir / split / f"{split}.jsonl"
        if not test_path.exists():
            raise ValueError(f"Test file not found: {test_path}")
            
        from datasets import load_dataset
        self.test_dataset = load_dataset("json", data_files=str(test_path))["train"]
        logger.info(f"Loaded test dataset with {len(self.test_dataset)} examples")
        return self.test_dataset
        
    def _find_latest_dataset(self) -> Optional[Path]:
        if not self.dataset_dir.exists():
            return None
            
        dataset_dirs = sorted(
            [d for d in self.dataset_dir.iterdir() if d.is_dir() and d.name.startswith("dataset_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        return dataset_dirs[0] if dataset_dirs else None
        
    def register_custom_metric(self, name: str, metric_func: Callable) -> None:
        self.custom_metrics[name] = metric_func
        
    def evaluate(
        self,
        agent_fn: Callable[[str], str],
        input_key: str = "user_input",
        reference_key: str = "agent_response",
        metrics: Optional[List[str]] = None,
        benchmark_name: str = "agent_benchmark",
    ) -> BenchmarkResult:
        if self.test_dataset is None:
            self.load_test_dataset()
            
        if metrics is None:
            metrics = ["exact_match", "rouge"]
            
        start_time = datetime.now()
        
        predictions = []
        references = []
        
        logger.info(f"Starting evaluation on {len(self.test_dataset)} examples...")
        
        for i, example in enumerate(self.test_dataset):
            user_input = example.get(input_key, "")
            reference = example.get(reference_key, "")
            
            try:
                prediction = agent_fn(user_input)
                predictions.append(prediction)
                references.append(reference)
            except Exception as e:
                logger.error(f"Error processing example {i}: {e}")
                predictions.append("")
                references.append(reference)
                
        duration = (datetime.now() - start_time).total_seconds()
        
        results = self._calculate_metrics(predictions, references, metrics)
        
        benchmark_result = BenchmarkResult(
            benchmark_name=benchmark_name,
            model_name=self.model_name,
            metrics=results,
            dataset_info={"num_examples": len(self.test_dataset)},
            duration_seconds=duration,
        )
        
        logger.info(f"Evaluation completed in {duration:.2f} seconds")
        self._log_results(benchmark_result)
        
        return benchmark_result
        
    def _calculate_metrics(
        self,
        predictions: List[str],
        references: List[str],
        metrics: List[str],
    ) -> List[EvaluationResult]:
        results = []
        
        for metric_name in metrics:
            if metric_name == "accuracy":
                results.append(MetricCalculator.accuracy(predictions, references))
            elif metric_name == "exact_match":
                results.append(MetricCalculator.exact_match(predictions, references))
            elif metric_name == "rouge":
                results.extend(MetricCalculator.rouge_scores(predictions, references))
            elif metric_name in self.custom_metrics:
                custom_result = self.custom_metrics[metric_name](predictions, references)
                if isinstance(custom_result, list):
                    results.extend(custom_result)
                else:
                    results.append(custom_result)
                    
        return results
        
    def _log_results(self, benchmark_result: BenchmarkResult) -> None:
        logger.info("=" * 60)
        logger.info(f"Benchmark: {benchmark_result.benchmark_name}")
        logger.info(f"Model: {benchmark_result.model_name}")
        logger.info("=" * 60)
        
        for metric in benchmark_result.metrics:
            logger.info(f"{metric.metric_name}: {metric.value:.4f}")
            
        logger.info(f"Duration: {benchmark_result.duration_seconds:.2f}s")
        logger.info("=" * 60)
        
    def save_results(
        self,
        benchmark_result: BenchmarkResult,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        save_dir = Path(output_dir) if output_dir else (
            Path(settings.BASE_DIR) / "evaluation_results"
        )
        save_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{benchmark_result.benchmark_name}_{benchmark_result.model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_path = save_dir / filename
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_result.to_dict(), f, ensure_ascii=False, indent=2)
            
        logger.info(f"Results saved to: {save_path}")
        return save_path


class BenchmarkSuite:
    def __init__(self):
        self.benchmarks: Dict[str, Callable] = {}
        self.results: List[BenchmarkResult] = []
        
    def add_benchmark(self, name: str, benchmark_fn: Callable) -> None:
        self.benchmarks[name] = benchmark_fn
        
    def run_all(
        self,
        evaluator: AgentEvaluator,
        agent_fn: Callable[[str], str],
    ) -> List[BenchmarkResult]:
        self.results = []
        
        for name, benchmark_fn in self.benchmarks.items():
            logger.info(f"Running benchmark: {name}")
            result = benchmark_fn(evaluator, agent_fn)
            self.results.append(result)
            
        return self.results
        
    def compare_models(
        self,
        results: Optional[List[BenchmarkResult]] = None,
    ) -> Dict[str, Dict[str, float]]:
        target_results = results if results else self.results
        
        comparison = defaultdict(dict)
        
        for result in target_results:
            for metric in result.metrics:
                comparison[metric.metric_name][result.model_name] = metric.value
                
        return dict(comparison)
