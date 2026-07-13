"""
HDF5内嵌JS预览框架

提供HDF5文件内嵌JavaScript预览功能，实现浏览器中直接预览和可视化HDF5数据。

核心功能：
- HDF5数据提取：从HDF5文件中提取数据结构和内容
- JS预览生成：生成内嵌的HTML/JavaScript预览代码
- 数据可视化：支持表格、图表、统计等多种可视化方式
- 交互式预览：生成可交互的预览界面
"""

import base64
import json
import os
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import h5py
import numpy as np
import pandas as pd

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class H5DatasetInfo:
    """HDF5数据集信息"""
    name: str
    path: str
    shape: Tuple[int, ...]
    dtype: str
    size: int
    chunks: Optional[Tuple[int, ...]] = None
    compression: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "path": self.path,
            "shape": self.shape,
            "dtype": self.dtype,
            "size": self.size,
            "chunks": self.chunks,
            "compression": self.compression,
            "attributes": self._safe_attributes(),
        }

    def _safe_attributes(self) -> Dict[str, Any]:
        """安全转换属性值"""
        safe = {}
        for key, value in self.attributes.items():
            try:
                json.dumps(value)
                safe[key] = value
            except TypeError:
                safe[key] = str(value)
        return safe


@dataclass
class H5GroupInfo:
    """HDF5组信息"""
    name: str
    path: str
    datasets: List[H5DatasetInfo] = field(default_factory=list)
    sub_groups: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "path": self.path,
            "datasets": [d.to_dict() for d in self.datasets],
            "sub_groups": self.sub_groups,
            "attributes": self._safe_attributes(),
        }

    def _safe_attributes(self) -> Dict[str, Any]:
        """安全转换属性值"""
        safe = {}
        for key, value in self.attributes.items():
            try:
                json.dumps(value)
                safe[key] = value
            except TypeError:
                safe[key] = str(value)
        return safe


@dataclass
class H5PreviewConfig:
    """HDF5预览配置"""
    max_preview_rows: int = 100
    max_preview_columns: int = 50
    max_string_length: int = 200
    enable_charts: bool = True
    enable_statistics: bool = True
    enable_data_table: bool = True
    enable_tree_view: bool = True
    compress_data: bool = True
    include_raw_data: bool = True
    chart_type: str = "auto"


@dataclass
class H5PreviewResult:
    """HDF5预览结果"""
    html_content: str
    data_size: int
    preview_size: int
    datasets_count: int
    groups_count: int
    generated_at: datetime = field(default_factory=datetime.now)

    def save_to_file(self, output_path: str) -> bool:
        """保存预览HTML到文件"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.html_content)
            logger.info(f"预览文件已保存: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存预览文件失败: {e}")
            return False


class H5DataExtractor:
    """
    HDF5数据提取器

    从HDF5文件中提取数据结构和内容，为预览生成做准备。
    """

    def __init__(self, config: Optional[H5PreviewConfig] = None):
        """
        初始化数据提取器

        Args:
            config: 预览配置
        """
        self.config = config or H5PreviewConfig()

    def extract_h5_structure(self, h5_path: str) -> Dict[str, Any]:
        """
        提取HDF5文件结构

        Args:
            h5_path: HDF5文件路径

        Returns:
            文件结构信息
        """
        structure = {
            "file_name": os.path.basename(h5_path),
            "file_size": os.path.getsize(h5_path),
            "groups": [],
            "datasets": [],
            "metadata": {},
        }

        try:
            with h5py.File(h5_path, "r") as f:
                structure["metadata"] = self._extract_file_attributes(f)
                self._extract_group(f, "/", structure)
        except Exception as e:
            logger.error(f"提取HDF5结构失败: {e}")

        return structure

    def extract_dataset_data(
        self,
        h5_path: str,
        dataset_path: str,
    ) -> Optional[Dict[str, Any]]:
        """
        提取数据集内容

        Args:
            h5_path: HDF5文件路径
            dataset_path: 数据集路径

        Returns:
            数据集内容信息
        """
        try:
            with h5py.File(h5_path, "r") as f:
                if dataset_path not in f:
                    return None

                dataset = f[dataset_path]
                data = dataset[:]

                info = {
                    "path": dataset_path,
                    "shape": data.shape,
                    "dtype": str(data.dtype),
                    "ndim": data.ndim,
                    "size": data.size,
                    "preview": self._extract_data_preview(data),
                    "statistics": self._calculate_statistics(data),
                    "attributes": self._extract_dataset_attributes(dataset),
                }

                return info
        except Exception as e:
            logger.error(f"提取数据集 {dataset_path} 失败: {e}")
            return None

    def extract_all_preview_data(
        self,
        h5_path: str,
    ) -> Dict[str, Any]:
        """
        提取所有数据集的预览数据

        Args:
            h5_path: HDF5文件路径

        Returns:
            所有数据集的预览数据
        """
        structure = self.extract_h5_structure(h5_path)
        datasets_data = {}

        for dataset_info in structure["datasets"]:
            dataset_path = dataset_info["path"]
            data = self.extract_dataset_data(h5_path, dataset_path)
            if data:
                datasets_data[dataset_path] = data

        return {
            "structure": structure,
            "datasets": datasets_data,
        }

    def _extract_group(
        self,
        f: h5py.File,
        path: str,
        structure: Dict[str, Any],
    ) -> None:
        """递归提取组信息"""
        group = f[path]

        group_info = H5GroupInfo(
            name=os.path.basename(path) or "/",
            path=path,
            attributes=self._extract_group_attributes(group),
        )

        for name, item in group.items():
            item_path = f"{path}/{name}" if path != "/" else f"/{name}"

            if isinstance(item, h5py.Dataset):
                dataset_info = self._extract_dataset_info(item, item_path)
                group_info.datasets.append(dataset_info.to_dict())
                structure["datasets"].append(dataset_info.to_dict())
            elif isinstance(item, h5py.Group):
                group_info.sub_groups.append(name)
                self._extract_group(f, item_path, structure)

        if path != "/":
            structure["groups"].append(group_info.to_dict())

    def _extract_dataset_info(
        self,
        dataset: h5py.Dataset,
        path: str,
    ) -> H5DatasetInfo:
        """提取数据集信息"""
        return H5DatasetInfo(
            name=os.path.basename(path),
            path=path,
            shape=dataset.shape,
            dtype=str(dataset.dtype),
            size=dataset.size,
            chunks=dataset.chunks,
            compression=dataset.compression,
            attributes=self._extract_dataset_attributes(dataset),
        )

    def _extract_file_attributes(self, f: h5py.File) -> Dict[str, Any]:
        """提取文件级属性"""
        return self._safe_attributes(f.attrs)

    def _extract_group_attributes(self, group: h5py.Group) -> Dict[str, Any]:
        """提取组属性"""
        return self._safe_attributes(group.attrs)

    def _extract_dataset_attributes(self, dataset: h5py.Dataset) -> Dict[str, Any]:
        """提取数据集属性"""
        return self._safe_attributes(dataset.attrs)

    def _safe_attributes(self, attrs: h5py.AttributeManager) -> Dict[str, Any]:
        """安全转换属性"""
        safe = {}
        for key in attrs:
            try:
                value = attrs[key]
                if isinstance(value, np.ndarray):
                    value = value.tolist()
                elif isinstance(value, np.generic):
                    value = value.item()
                json.dumps(value)
                safe[key] = value
            except (TypeError, Exception):
                safe[key] = str(attrs[key])
        return safe

    def _extract_data_preview(self, data: np.ndarray) -> Any:
        """提取数据预览"""
        config = self.config

        if data.size == 0:
            return []

        try:
            if data.ndim == 0:
                return data.item()

            elif data.ndim == 1:
                preview = data[:config.max_preview_rows]
                return self._normalize_array(preview)

            elif data.ndim == 2:
                rows = min(data.shape[0], config.max_preview_rows)
                cols = min(data.shape[1], config.max_preview_columns)
                preview = data[:rows, :cols]
                return self._normalize_array(preview)

            else:
                slices = tuple(slice(0, min(dim, 5)) for dim in data.shape)
                preview = data[slices]
                return self._normalize_array(preview)

        except Exception as e:
            logger.warning(f"提取数据预览失败: {e}")
            return []

    def _normalize_array(self, arr: np.ndarray) -> Any:
        """标准化数组为JSON可序列化格式"""
        try:
            arr = np.asarray(arr)

            if np.issubdtype(arr.dtype, np.floating):
                arr = np.nan_to_num(arr)
                arr = np.round(arr, 6)
            elif np.issubdtype(arr.dtype, np.complexfloating):
                arr = {"real": np.round(arr.real, 6).tolist(), "imag": np.round(arr.imag, 6).tolist()}
                return arr
            elif arr.dtype == np.object_:
                arr = np.vectorize(
                    lambda x: str(x)[:self.config.max_string_length]
                    if isinstance(x, str) else str(x)
                )(arr)

            return arr.tolist()

        except Exception as e:
            logger.warning(f"标准化数组失败: {e}")
            return arr.tolist()

    def _calculate_statistics(self, data: np.ndarray) -> Dict[str, Any]:
        """计算数据统计信息"""
        if not np.issubdtype(data.dtype, np.number) or data.size == 0:
            return {}

        try:
            flat_data = data.flatten()

            if np.issubdtype(data.dtype, np.floating):
                flat_data = flat_data[~np.isnan(flat_data)]

            if len(flat_data) == 0:
                return {}

            stats = {
                "min": float(np.min(flat_data)),
                "max": float(np.max(flat_data)),
                "mean": float(np.mean(flat_data)),
                "median": float(np.median(flat_data)),
                "std": float(np.std(flat_data)),
                "var": float(np.var(flat_data)),
                "sum": float(np.sum(flat_data)),
                "count": int(len(flat_data)),
                "unique": int(np.unique(flat_data).size),
            }

            if len(flat_data) >= 4:
                percs = np.percentile(flat_data, [25, 50, 75])
                stats.update({
                    "p25": float(percs[0]),
                    "p50": float(percs[1]),
                    "p75": float(percs[2]),
                })

            return stats

        except Exception as e:
            logger.warning(f"计算统计信息失败: {e}")
            return {}


class H5JSPreviewGenerator:
    """
    HDF5 JS预览生成器

    生成内嵌JavaScript的HTML预览页面，支持在浏览器中直接预览HDF5数据。
    """

    def __init__(self, config: Optional[H5PreviewConfig] = None):
        """
        初始化预览生成器

        Args:
            config: 预览配置
        """
        self.config = config or H5PreviewConfig()
        self.extractor = H5DataExtractor(config)

    def generate_preview(self, h5_path: str) -> H5PreviewResult:
        """
        生成HDF5预览HTML

        Args:
            h5_path: HDF5文件路径

        Returns:
            预览结果
        """
        data = self.extractor.extract_all_preview_data(h5_path)

        if self.config.compress_data:
            data_json = self._compress_data(data)
        else:
            data_json = json.dumps(data, default=str)

        html_content = self._generate_html(data_json, self.config.compress_data)

        return H5PreviewResult(
            html_content=html_content,
            data_size=os.path.getsize(h5_path),
            preview_size=len(html_content.encode("utf-8")),
            datasets_count=len(data["datasets"]),
            groups_count=len(data["structure"]["groups"]),
        )

    def generate_preview_for_data(self, data: Dict[str, Any]) -> H5PreviewResult:
        """
        为已有数据生成预览HTML

        Args:
            data: 提取的数据

        Returns:
            预览结果
        """
        if self.config.compress_data:
            data_json = self._compress_data(data)
        else:
            data_json = json.dumps(data, default=str)

        html_content = self._generate_html(data_json, self.config.compress_data)

        return H5PreviewResult(
            html_content=html_content,
            data_size=0,
            preview_size=len(html_content.encode("utf-8")),
            datasets_count=len(data.get("datasets", {})),
            groups_count=len(data.get("structure", {}).get("groups", [])),
        )

    def _compress_data(self, data: Dict[str, Any]) -> str:
        """压缩数据为Base64编码的JSON"""
        try:
            json_str = json.dumps(data, default=str)
            compressed = zlib.compress(json_str.encode("utf-8"), level=6)
            encoded = base64.b64encode(compressed).decode("utf-8")
            return encoded
        except Exception as e:
            logger.warning(f"数据压缩失败，使用未压缩数据: {e}")
            return json.dumps(data, default=str)

    def _generate_html(self, data_json: str, is_compressed: bool) -> str:
        """生成HTML预览页面"""
        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HDF5数据预览</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #0f0f23; color: #e0e0e0; min-height: 100vh; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-bottom: 1px solid #2a2a4a; }}
        .header h1 {{ font-size: 24px; color: #00d4ff; margin-bottom: 5px; }}
        .header p {{ font-size: 14px; color: #888; }}
        .container {{ display: flex; height: calc(100vh - 80px); }}
        .sidebar {{ width: 280px; background: #16162a; border-right: 1px solid #2a2a4a; overflow-y: auto; padding: 15px; }}
        .sidebar h3 {{ font-size: 14px; color: #00d4ff; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 1px solid #2a2a4a; }}
        .tree-item {{ padding: 8px 10px; cursor: pointer; border-radius: 4px; margin-bottom: 2px; transition: background 0.2s; }}
        .tree-item:hover {{ background: #2a2a4a; }}
        .tree-item.active {{ background: #00d4ff; color: #000; }}
        .tree-item.group {{ font-weight: 500; }}
        .tree-item.dataset {{ font-size: 13px; padding-left: 20px; color: #aaa; }}
        .main-content {{ flex: 1; overflow-y: auto; padding: 20px; }}
        .tab-bar {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .tab {{ padding: 10px 20px; background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 4px; cursor: pointer; transition: all 0.2s; }}
        .tab:hover {{ background: #2a2a4a; }}
        .tab.active {{ background: #00d4ff; color: #000; border-color: #00d4ff; }}
        .panel {{ display: none; }}
        .panel.active {{ display: block; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #1a1a2e; padding: 15px; border-radius: 8px; border-left: 3px solid #00d4ff; }}
        .stat-card .label {{ font-size: 12px; color: #888; }}
        .stat-card .value {{ font-size: 24px; color: #00d4ff; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #2a2a4a; }}
        th {{ background: #16162a; color: #00d4ff; font-weight: 600; }}
        td {{ color: #ccc; font-size: 13px; }}
        tr:hover td {{ background: #2a2a4a; }}
        .chart-container {{ background: #1a1a2e; padding: 20px; border-radius: 8px; margin-bottom: 20px; height: 400px; }}
        .metadata-panel {{ background: #1a1a2e; padding: 20px; border-radius: 8px; }}
        .metadata-item {{ margin-bottom: 10px; }}
        .metadata-item .key {{ font-weight: 500; color: #00d4ff; }}
        .metadata-item .value {{ color: #888; font-family: monospace; }}
        .dataset-info {{ background: #1a1a2e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .dataset-info .info-row {{ display: flex; gap: 20px; margin-bottom: 10px; }}
        .dataset-info .info-item {{ font-size: 13px; }}
        .dataset-info .info-item .label {{ color: #888; }}
        .dataset-info .info-item .value {{ color: #00d4ff; }}
        .empty-state {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #666; }}
        .empty-state svg {{ width: 64px; height: 64px; margin-bottom: 15px; opacity: 0.3; }}
        .file-info {{ margin-bottom: 20px; padding: 15px; background: #1a1a2e; border-radius: 8px; }}
        .file-info h3 {{ color: #00d4ff; margin-bottom: 10px; }}
        .file-info .info-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }}
        .file-info .info-item {{ font-size: 13px; }}
        .file-info .info-item .label {{ color: #888; }}
        .file-info .info-item .value {{ color: #e0e0e0; }}
        .scrollable-table {{ overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>HDF5 Data Preview</h1>
        <p>交互式数据预览与可视化</p>
    </div>
    <div class="container">
        <div class="sidebar">
            <h3>文件结构</h3>
            <div id="tree-container"></div>
        </div>
        <div class="main-content">
            <div id="file-info-panel" class="file-info">
                <h3>文件信息</h3>
                <div id="file-info-content" class="info-grid"></div>
            </div>
            <div id="dataset-panel" style="display: none;">
                <div class="dataset-info">
                    <div class="info-row">
                        <div class="info-item"><span class="label">路径: </span><span class="value" id="ds-path"></span></div>
                        <div class="info-item"><span class="label">形状: </span><span class="value" id="ds-shape"></span></div>
                        <div class="info-item"><span class="label">类型: </span><span class="value" id="ds-dtype"></span></div>
                        <div class="info-item"><span class="label">大小: </span><span class="value" id="ds-size"></span></div>
                    </div>
                </div>
                <div class="tab-bar">
                    <div class="tab active" data-tab="table">数据预览</div>
                    <div class="tab" data-tab="stats">统计信息</div>
                    <div class="tab" data-tab="chart">图表</div>
                    <div class="tab" data-tab="metadata">元数据</div>
                </div>
                <div class="panel active" id="tab-table">
                    <div class="scrollable-table">
                        <table id="data-table"></table>
                    </div>
                </div>
                <div class="panel" id="tab-stats">
                    <div id="stats-container" class="stats-grid"></div>
                </div>
                <div class="panel" id="tab-chart">
                    <div class="chart-container" id="chart-container"></div>
                </div>
                <div class="panel" id="tab-metadata">
                    <div class="metadata-panel" id="metadata-container"></div>
                </div>
            </div>
            <div id="empty-panel" class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <p>选择一个数据集查看详情</p>
            </div>
        </div>
    </div>
    <script>
        const isCompressed = IS_COMPRESSED_PLACEHOLDER;
        const rawData = 'DATA_JSON_PLACEHOLDER';

        function decompressData(encoded) {
            try {
                const compressed = atob(encoded);
                const uint8Array = new Uint8Array(compressed.length);
                for (let i = 0; i < compressed.length; i++) {
                    uint8Array[i] = compressed.charCodeAt(i);
                }
                const inflated = pako.inflate(uint8Array);
                const json = new TextDecoder('utf-8').decode(inflated);
                return JSON.parse(json);
            } catch (e) {
                console.error('Decompression failed:', e);
                return JSON.parse(encoded);
            }
        }

        const h5Data = isCompressed ? decompressData(rawData) : JSON.parse(rawData);

        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function renderFileInfo() {
            const structure = h5Data.structure;
            const container = document.getElementById('file-info-content');
            const info = [
                { label: '文件名', value: structure.file_name },
                { label: '文件大小', value: formatSize(structure.file_size) },
                { label: '数据集数', value: structure.datasets.length },
                { label: '组数', value: structure.groups.length },
            ];
            container.innerHTML = info.map(i => `
                <div class="info-item"><span class="label">${i.label}: </span><span class="value">${i.value}</span></div>
            `).join('');
        }

        function renderTree() {
            const structure = h5Data.structure;
            const container = document.getElementById('tree-container');

            let html = '';
            structure.groups.forEach(group => {
                html += '<div class="tree-item group" data-path="' + group.path + '">📁 ' + group.name + '</div>';
                group.datasets.forEach(ds => {
                    html += '<div class="tree-item dataset" data-path="' + ds.path + '" data-type="dataset">📊 ' + ds.name + '</div>';
                });
            });

            if (structure.datasets.length === 0) {
                html = '<div style="color: #666; padding: 20px;">没有数据集</div>';
            }

            container.innerHTML = html;

            container.querySelectorAll('.tree-item.dataset').forEach(item => {
                item.addEventListener('click', function() {
                    container.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
                    this.classList.add('active');
                    const path = this.getAttribute('data-path');
                    showDataset(path);
                });
            });
        }

        function showDataset(path) {
            const data = h5Data.datasets[path];
            if (!data) return;

            document.getElementById('empty-panel').style.display = 'none';
            document.getElementById('dataset-panel').style.display = 'block';

            document.getElementById('ds-path').textContent = data.path;
            document.getElementById('ds-shape').textContent = '[' + data.shape.join(', ') + ']';
            document.getElementById('ds-dtype').textContent = data.dtype;
            document.getElementById('ds-size').textContent = data.size.toLocaleString();

            renderTable(data);
            renderStats(data);
            renderMetadata(data);
            renderChart(data);

            switchTab('table');
        }

        function renderTable(data) {
            const table = document.getElementById('data-table');
            const preview = data.preview;

            if (!preview || preview.length === 0) {
                table.innerHTML = '<tr><td colspan="100" style="text-align: center; color: #666;">没有数据</td></tr>';
                return;
            }

            let html = '<thead><tr>';
            if (Array.isArray(preview) && Array.isArray(preview[0])) {
                const cols = Math.min(preview[0].length, 20);
                html += '<th>#</th>';
                for (let i = 0; i < cols; i++) {
                    html += '<th>列 ' + i + '</th>';
                }
                html += '</tr></thead><tbody>';
                preview.slice(0, 50).forEach((row, idx) => {
                    html += '<tr><td>' + idx + '</td>';
                    row.slice(0, cols).forEach(cell => {
                        let val = cell;
                        if (typeof val === 'string' && val.length > 50) {
                            val = val.substring(0, 50) + '...';
                        }
                        html += '<td>' + String(val).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</td>';
                    });
                    html += '</tr>';
                });
            } else if (Array.isArray(preview)) {
                html += '<th>索引</th><th>值</th></tr></thead><tbody>';
                preview.slice(0, 100).forEach((val, idx) => {
                    if (typeof val === 'string' && val.length > 100) {
                        val = val.substring(0, 100) + '...';
                    }
                    html += '<tr><td>' + idx + '</td><td>' + String(val).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</td></tr>';
                });
            } else {
                html += '<th>值</th></tr></thead><tbody><tr><td>' + String(preview).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</td></tr>';
            }
            html += '</tbody>';
            table.innerHTML = html;
        }

        function renderStats(data) {
            const container = document.getElementById('stats-container');
            const stats = data.statistics || {};

            if (Object.keys(stats).length === 0) {
                container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #666;">没有统计信息（非数值类型）</div>';
                return;
            }

            const statItems = [
                { key: 'count', label: '样本数', format: v => v.toLocaleString() },
                { key: 'min', label: '最小值', format: v => v.toFixed(4) },
                { key: 'max', label: '最大值', format: v => v.toFixed(4) },
                { key: 'mean', label: '均值', format: v => v.toFixed(4) },
                { key: 'median', label: '中位数', format: v => v.toFixed(4) },
                { key: 'std', label: '标准差', format: v => v.toFixed(4) },
                { key: 'var', label: '方差', format: v => v.toFixed(4) },
                { key: 'sum', label: '总和', format: v => v.toFixed(2) },
                { key: 'p25', label: '25%分位', format: v => v.toFixed(4) },
                { key: 'p75', label: '75%分位', format: v => v.toFixed(4) },
                { key: 'unique', label: '唯一值', format: v => v.toLocaleString() },
            ];

            let html = '';
            statItems.forEach(item => {
                if (stats[item.key] !== undefined) {
                    html += '<div class="stat-card"><div class="label">' + item.label + '</div><div class="value">' + item.format(stats[item.key]) + '</div></div>';
                }
            });
            container.innerHTML = html;
        }

        function renderMetadata(data) {
            const container = document.getElementById('metadata-container');
            const attrs = data.attributes || {};

            if (Object.keys(attrs).length === 0) {
                container.innerHTML = '<p style="color: #666;">没有元数据</p>';
                return;
            }

            let html = '';
            Object.entries(attrs).forEach(([key, value]) => {
                let valStr = typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
                if (valStr.length > 500) {
                    valStr = valStr.substring(0, 500) + '...';
                }
                html += '<div class="metadata-item"><div class="key">' + key + '</div><div class="value">' + valStr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\\n/g, '<br>') + '</div></div>';
            });
            container.innerHTML = html;
        }

        function renderChart(data) {
            const container = document.getElementById('chart-container');
            const preview = data.preview;

            if (!preview || !Array.isArray(preview)) {
                container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">图表预览不可用</div>';
                return;
            }

            let html = '<canvas id="preview-chart" width="800" height="350"></canvas>';
            container.innerHTML = html;

            const canvas = document.getElementById('preview-chart');
            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;
            const padding = 40;

            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(0, 0, width, height);

            ctx.strokeStyle = '#2a2a4a';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 5; i++) {
                const y = padding + (height - 2 * padding) * i / 5;
                ctx.beginPath();
                ctx.moveTo(padding, y);
                ctx.lineTo(width - padding, y);
                ctx.stroke();
            }

            let dataPoints = [];
            if (Array.isArray(preview[0])) {
                dataPoints = preview.slice(0, 50).map((row, i) => ({x: i, y: typeof row[0] === 'number' ? row[0] : 0}));
            } else {
                dataPoints = preview.slice(0, 100).map((val, i) => ({x: i, y: typeof val === 'number' ? val : 0}));
            }

            if (dataPoints.length === 0) {
                container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">没有可绘制的数据</div>';
                return;
            }

            const minY = Math.min(...dataPoints.map(p => p.y));
            const maxY = Math.max(...dataPoints.map(p => p.y));
            const rangeY = maxY - minY || 1;

            ctx.strokeStyle = '#00d4ff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            dataPoints.forEach((point, i) => {
                const x = padding + (width - 2 * padding) * i / (dataPoints.length - 1 || 1);
                const y = height - padding - (height - 2 * padding) * (point.y - minY) / rangeY;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();

            ctx.fillStyle = '#00d4ff';
            dataPoints.forEach((point, i) => {
                const x = padding + (width - 2 * padding) * i / (dataPoints.length - 1 || 1);
                const y = height - padding - (height - 2 * padding) * (point.y - minY) / rangeY;
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
            });

            ctx.fillStyle = '#888';
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('索引', width / 2, height - 10);
            ctx.save();
            ctx.translate(15, height / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText('值', 0, 0);
            ctx.restore();
        }

        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelector('[data-tab="' + tabName + '"]').classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
        }

        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                switchTab(this.getAttribute('data-tab'));
            });
        });

        document.addEventListener('DOMContentLoaded', function() {
            renderFileInfo();
            renderTree();
        });
    </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js"></script>
</body>
</html>"""

        html_content = html_template.replace(
            'IS_COMPRESSED_PLACEHOLDER',
            'true' if is_compressed else 'false'
        ).replace(
            'DATA_JSON_PLACEHOLDER',
            data_json
        )

        return html_content


class H5PreviewManager:
    """
    HDF5预览管理器

    整合数据提取和预览生成功能，提供完整的HDF5预览解决方案。
    """

    def __init__(self, config: Optional[H5PreviewConfig] = None):
        """
        初始化预览管理器

        Args:
            config: 预览配置
        """
        self.config = config or H5PreviewConfig()
        self.extractor = H5DataExtractor(config)
        self.generator = H5JSPreviewGenerator(config)

    def create_preview(
        self,
        h5_path: str,
        output_path: Optional[str] = None,
    ) -> H5PreviewResult:
        """
        创建HDF5预览

        Args:
            h5_path: HDF5文件路径
            output_path: 输出HTML文件路径（可选）

        Returns:
            预览结果
        """
        result = self.generator.generate_preview(h5_path)

        if output_path:
            result.save_to_file(output_path)

        logger.info(
            f"HDF5预览创建完成: datasets={result.datasets_count}, "
            f"groups={result.groups_count}, size={result.preview_size}"
        )

        return result

    def extract_and_preview(
        self,
        h5_path: str,
    ) -> Tuple[Dict[str, Any], H5PreviewResult]:
        """
        提取数据并生成预览

        Args:
            h5_path: HDF5文件路径

        Returns:
            提取的数据和预览结果
        """
        data = self.extractor.extract_all_preview_data(h5_path)
        result = self.generator.generate_preview_for_data(data)

        return data, result

    def batch_create_previews(
        self,
        h5_files: List[str],
        output_dir: str,
    ) -> List[H5PreviewResult]:
        """
        批量创建HDF5预览

        Args:
            h5_files: HDF5文件路径列表
            output_dir: 输出目录

        Returns:
            预览结果列表
        """
        results = []

        os.makedirs(output_dir, exist_ok=True)

        for h5_file in h5_files:
            try:
                file_name = os.path.basename(h5_file).replace('.h5', '').replace('.hdf5', '')
                output_path = os.path.join(output_dir, f"{file_name}_preview.html")

                result = self.create_preview(h5_file, output_path)
                results.append(result)

                logger.info(f"处理完成: {h5_file} -> {output_path}")
            except Exception as e:
                logger.error(f"处理 {h5_file} 失败: {e}")

        return results

    def get_h5_summary(self, h5_path: str) -> Dict[str, Any]:
        """
        获取HDF5文件摘要

        Args:
            h5_path: HDF5文件路径

        Returns:
            文件摘要信息
        """
        structure = self.extractor.extract_h5_structure(h5_path)

        summary = {
            "file_name": structure["file_name"],
            "file_size": structure["file_size"],
            "file_size_formatted": self._format_size(structure["file_size"]),
            "dataset_count": len(structure["datasets"]),
            "group_count": len(structure["groups"]),
            "datasets": [
                {
                    "name": ds["name"],
                    "path": ds["path"],
                    "shape": ds["shape"],
                    "dtype": ds["dtype"],
                    "size": ds["size"],
                }
                for ds in structure["datasets"]
            ],
            "groups": [
                {
                    "name": g["name"],
                    "path": g["path"],
                    "dataset_count": len(g["datasets"]),
                }
                for g in structure["groups"]
            ],
            "metadata": structure.get("metadata", {}),
        }

        return summary

    def _format_size(self, bytes: int) -> str:
        """格式化文件大小"""
        if bytes == 0:
            return "0 B"
        k = 1024
        sizes = ["B", "KB", "MB", "GB", "TB"]
        i = min(int(np.floor(np.log(bytes) / np.log(k))), len(sizes) - 1)
        return f"{(bytes / k ** i):.2f} {sizes[i]}"