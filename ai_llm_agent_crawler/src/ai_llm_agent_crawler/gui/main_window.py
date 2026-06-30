"""
爬虫GUI主窗口（窗口）

提供图形化界面，展示：
- 爬取图网络（节点 + 连线可视化）
- 种子据点管理
- 注意力评分分布
- 爬取进度和统计
"""

import math
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ai_llm_agent_crawler.graph.graph_store import CrawlGraph, CrawlNode, NodeStatus
from ai_llm_agent_crawler.seed.seed_manager import SeedManager, SeedPoint
from ai_llm_agent_crawler.agent.attention import AttentionScorer
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    logger.warning("Tkinter不可用，GUI功能将受限")


class GraphCanvas:
    """
    图画布

    用于绘制爬取图的节点和连线，实现可视化的
    连线载点网络。
    """

    def __init__(self, parent, width: int = 800, height: int = 600):
        self.parent = parent
        self.width = width
        self.height = height
        self._node_positions: Dict[str, tuple] = {}
        self._selected_node: Optional[str] = None
        self._dragging = False
        self._drag_offset = (0, 0)
        self._zoom = 1.0
        self._pan_offset = (0, 0)

        if TKINTER_AVAILABLE:
            self.canvas = tk.Canvas(
                parent,
                width=width,
                height=height,
                bg="#1e1e2e",
                scrollregion=(0, 0, width, height),
            )
            self._setup_bindings()

    def _setup_bindings(self):
        """设置事件绑定"""
        if not TKINTER_AVAILABLE:
            return

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_in())
        self.canvas.bind("<Button-5>", lambda e: self._zoom_out())

    def _on_click(self, event):
        """处理点击事件"""
        x = (event.x - self._pan_offset[0]) / self._zoom
        y = (event.y - self._pan_offset[1]) / self._zoom

        for node_id, (nx, ny) in self._node_positions.items():
            dist = math.sqrt((x - nx) ** 2 + (y - ny) ** 2)
            if dist < 20:
                self._selected_node = node_id
                self._dragging = True
                self._drag_offset = (x - nx, y - ny)
                return

        self._selected_node = None
        self._dragging = True
        self._drag_offset = (x, y)

    def _on_drag(self, event):
        """处理拖拽事件"""
        if not self._dragging:
            return

        x = (event.x - self._pan_offset[0]) / self._zoom
        y = (event.y - self._pan_offset[1]) / self._zoom

        if self._selected_node:
            new_x = x - self._drag_offset[0]
            new_y = y - self._drag_offset[1]
            self._node_positions[self._selected_node] = (new_x, new_y)
        else:
            dx = x - self._drag_offset[0]
            dy = y - self._drag_offset[1]
            self._pan_offset = (
                self._pan_offset[0] + dx * self._zoom,
                self._pan_offset[1] + dy * self._zoom,
            )

        self.redraw()

    def _on_release(self, event):
        """处理释放事件"""
        self._dragging = False

    def _on_scroll(self, event):
        """处理滚轮缩放"""
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _zoom_in(self):
        """放大"""
        self._zoom = min(self._zoom * 1.2, 5.0)
        self.redraw()

    def _zoom_out(self):
        """缩小"""
        self._zoom = max(self._zoom / 1.2, 0.2)
        self.redraw()

    def layout_nodes(self, graph: CrawlGraph, algorithm: str = "force"):
        """
        布局节点

        Args:
            graph: 爬取图
            algorithm: 布局算法
        """
        nodes = list(graph._nodes.values())
        if not nodes:
            return

        if algorithm == "circular":
            self._circular_layout(nodes)
        elif algorithm == "hierarchical":
            self._hierarchical_layout(nodes)
        else:
            self._force_directed_layout(graph, nodes)

    def _circular_layout(self, nodes: List[CrawlNode]):
        """圆形布局"""
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.width, self.height) * 0.35

        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self._node_positions[node.node_id] = (x, y)

    def _hierarchical_layout(self, nodes: List[CrawlNode]):
        """层次布局"""
        depth_groups: Dict[int, List[CrawlNode]] = {}
        for node in nodes:
            depth = node.depth
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(node)

        max_depth = max(depth_groups.keys()) if depth_groups else 0
        level_width = self.width / (max_depth + 2)

        for depth, depth_nodes in depth_groups.items():
            x = level_width * (depth + 1)
            level_height = self.height / (len(depth_nodes) + 1)
            for i, node in enumerate(depth_nodes):
                y = level_height * (i + 1)
                self._node_positions[node.node_id] = (x, y)

    def _force_directed_layout(
        self,
        graph: CrawlGraph,
        nodes: List[CrawlNode],
        iterations: int = 50,
    ):
        """力导向布局"""
        import random

        random.seed(42)

        for node in nodes:
            x = random.randint(100, self.width - 100)
            y = random.randint(100, self.height - 100)
            self._node_positions[node.node_id] = (x, y)

        if len(nodes) <= 1:
            return

        k = math.sqrt((self.width * self.height) / len(nodes)) * 0.5

        for _ in range(iterations):
            displacements: Dict[str, list] = {}
            for node in nodes:
                displacements[node.node_id] = [0.0, 0.0]

            for i, n1 in enumerate(nodes):
                for j, n2 in enumerate(nodes):
                    if i >= j:
                        continue

                    pos1 = self._node_positions[n1.node_id]
                    pos2 = self._node_positions[n2.node_id]
                    dx = pos2[0] - pos1[0]
                    dy = pos2[1] - pos1[1]
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist < 1:
                        dist = 1

                    force = k * k / dist
                    fx = (dx / dist) * force
                    fy = (dy / dist) * force

                    displacements[n1.node_id][0] -= fx
                    displacements[n1.node_id][1] -= fy
                    displacements[n2.node_id][0] += fx
                    displacements[n2.node_id][1] += fy

            for edge in graph._edges.values():
                pos1 = self._node_positions.get(edge.source_id)
                pos2 = self._node_positions.get(edge.target_id)
                if not pos1 or not pos2:
                    continue

                dx = pos2[0] - pos1[0]
                dy = pos2[1] - pos1[1]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < 1:
                    dist = 1

                force = dist / k
                fx = (dx / dist) * force
                fy = (dy / dist) * force

                displacements[edge.source_id][0] += fx
                displacements[edge.source_id][1] += fy
                displacements[edge.target_id][0] -= fx
                displacements[edge.target_id][1] -= fy

            for node in nodes:
                dx, dy = displacements[node.node_id]
                disp = math.sqrt(dx * dx + dy * dy)
                if disp > 0:
                    limited_disp = min(disp, 30.0)
                    pos = self._node_positions[node.node_id]
                    new_x = pos[0] + (dx / disp) * limited_disp
                    new_y = pos[1] + (dy / disp) * limited_disp

                    new_x = max(50, min(self.width - 50, new_x))
                    new_y = max(50, min(self.height - 50, new_y))

                    self._node_positions[node.node_id] = (new_x, new_y)

    def redraw(self, graph: Optional[CrawlGraph] = None):
        """重绘画布"""
        if not TKINTER_AVAILABLE:
            return

        self.canvas.delete("all")

        if graph:
            self._draw_edges(graph)
            self._draw_nodes(graph)

    def _draw_edges(self, graph: CrawlGraph):
        """绘制连线"""
        for edge in graph._edges.values():
            pos1 = self._node_positions.get(edge.source_id)
            pos2 = self._node_positions.get(edge.target_id)
            if not pos1 or not pos2:
                continue

            x1 = self._pan_offset[0] + pos1[0] * self._zoom
            y1 = self._pan_offset[1] + pos1[1] * self._zoom
            x2 = self._pan_offset[0] + pos2[0] * self._zoom
            y2 = self._pan_offset[1] + pos2[1] * self._zoom

            color = "#4a5568"
            width = max(1, edge.weight * self._zoom)

            self.canvas.create_line(
                x1, y1, x2, y2,
                fill=color,
                width=width,
                smooth=True,
            )

    def _draw_nodes(self, graph: CrawlGraph):
        """绘制节点（载点）"""
        for node in graph._nodes.values():
            pos = self._node_positions.get(node.node_id)
            if not pos:
                continue

            x = self._pan_offset[0] + pos[0] * self._zoom
            y = self._pan_offset[1] + pos[1] * self._zoom

            base_radius = 12
            size_multiplier = 1 + node.attention_score * 2
            radius = base_radius * size_multiplier * self._zoom

            fill_color = self._get_node_color(node)
            outline_color = "#fbbf24" if self._selected_node == node.node_id else "#374151"

            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill=fill_color,
                outline=outline_color,
                width=2 if self._selected_node == node.node_id else 1,
            )

            if self._zoom > 0.5:
                label = node.domain[:15] if node.domain else node.url[:20]
                self.canvas.create_text(
                    x, y + radius + 10,
                    text=label,
                    fill="#e5e7eb",
                    font=("Arial", int(9 * self._zoom)),
                )

            if node.attention_score > 0.7 and self._zoom > 0.5:
                glow_radius = radius * 1.3
                self.canvas.create_oval(
                    x - glow_radius, y - glow_radius,
                    x + glow_radius, y + glow_radius,
                    outline="#fbbf24",
                    width=2,
                    dash=(3, 3),
                )

    @staticmethod
    def _get_node_color(node: CrawlNode) -> str:
        """获取节点颜色"""
        colors = {
            NodeStatus.PENDING: "#3b82f6",
            NodeStatus.CRAWLING: "#f59e0b",
            NodeStatus.CRAWLED: "#10b981",
            NodeStatus.FAILED: "#ef4444",
            NodeStatus.SKIPPED: "#6b7280",
        }
        return colors.get(node.status, "#6b7280")


class CrawlerGUI:
    """
    爬虫GUI主窗口

    提供完整的图形化界面，包括：
    - 爬取图可视化（连线载点网络）
    - 种子据点管理面板
    - 注意力评分监控
    - 爬取进度显示
    """

    def __init__(
        self,
        graph: Optional[CrawlGraph] = None,
        seed_manager: Optional[SeedManager] = None,
        attention_scorer: Optional[AttentionScorer] = None,
    ):
        """
        初始化GUI

        Args:
            graph: 爬取图
            seed_manager: 种子管理器
            attention_scorer: 注意力评分器
        """
        self.graph = graph or CrawlGraph()
        self.seed_manager = seed_manager or SeedManager()
        self.attention_scorer = attention_scorer or AttentionScorer()
        self._running = False
        self._crawl_thread: Optional[threading.Thread] = None

        if not TKINTER_AVAILABLE:
            logger.error("Tkinter不可用，无法启动GUI")
            return

        self.root = tk.Tk()
        self.root.title("AI LLM Agent 爬虫 - 智能爬取控制台")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e2e")

        self._setup_styles()
        self._create_menu()
        self._create_layout()
        self._graph_canvas.layout_nodes(self.graph)
        self._graph_canvas.redraw(self.graph)
        self._refresh_stats()

        logger.info("爬虫GUI已初始化")

    def _setup_styles(self):
        """设置样式"""
        if not TKINTER_AVAILABLE:
            return

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TFrame", background="#1e1e2e")
        style.configure("Dark.TLabelframe", background="#1e1e2e", foreground="#e5e7eb")
        style.configure("Dark.TLabelframe.Label", background="#1e1e2e", foreground="#e5e7eb")
        style.configure("Dark.TButton", background="#3b82f6", foreground="white")
        style.map("Dark.TButton", background=[("active", "#2563eb")])
        style.configure("Dark.TLabel", background="#1e1e2e", foreground="#e5e7eb")
        style.configure("Dark.TEntry", fieldbackground="#374151", foreground="#e5e7eb")
        style.configure("Dark.Treeview", background="#374151", foreground="#e5e7eb", fieldbackground="#374151")
        style.configure("Dark.Treeview.Heading", background="#1f2937", foreground="#e5e7eb")
        style.configure("Dark.Horizontal.TProgressbar", background="#3b82f6")

    def _create_menu(self):
        """创建菜单栏"""
        if not TKINTER_AVAILABLE:
            return

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入种子...", command=self._import_seeds)
        file_menu.add_command(label="导出数据...", command=self._export_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="圆形布局", command=lambda: self._relayout("circular"))
        view_menu.add_command(label="层次布局", command=lambda: self._relayout("hierarchical"))
        view_menu.add_command(label="力导向布局", command=lambda: self._relayout("force"))
        view_menu.add_separator()
        view_menu.add_command(label="放大", command=self._zoom_in)
        view_menu.add_command(label="缩小", command=self._zoom_out)
        view_menu.add_command(label="重置视图", command=self._reset_view)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _create_layout(self):
        """创建主布局"""
        if not TKINTER_AVAILABLE:
            return

        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_paned, style="Dark.TFrame", width=300)
        center_frame = ttk.Frame(main_paned, style="Dark.TFrame")
        right_frame = ttk.Frame(main_paned, style="Dark.TFrame", width=300)

        main_paned.add(left_frame, weight=1)
        main_paned.add(center_frame, weight=3)
        main_paned.add(right_frame, weight=1)

        self._create_left_panel(left_frame)
        self._create_center_panel(center_frame)
        self._create_right_panel(right_frame)

        status_frame = ttk.Frame(self.root, style="Dark.TFrame")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style="Dark.TLabel",
        )
        status_label.pack(side=tk.LEFT)

    def _create_left_panel(self, parent):
        """创建左侧面板（种子据点 + 控制）"""
        if not TKINTER_AVAILABLE:
            return

        control_frame = ttk.LabelFrame(
            parent,
            text=" 爬取控制 ",
            style="Dark.TLabelframe",
            padding=10,
        )
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_button = ttk.Button(
            control_frame,
            text="开始爬取",
            style="Dark.TButton",
            command=self._start_crawling,
        )
        self.start_button.pack(fill=tk.X, pady=2)

        self.stop_button = ttk.Button(
            control_frame,
            text="停止爬取",
            style="Dark.TButton",
            command=self._stop_crawling,
        )
        self.stop_button.pack(fill=tk.X, pady=2)

        seed_frame = ttk.LabelFrame(
            parent,
            text=" 据点管理 (据点) ",
            style="Dark.TLabelframe",
            padding=10,
        )
        seed_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(seed_frame, text="添加据点URL:", style="Dark.TLabel").pack(anchor=tk.W)

        self.seed_url_entry = ttk.Entry(seed_frame, style="Dark.TEntry")
        self.seed_url_entry.pack(fill=tk.X, pady=2)

        add_seed_btn = ttk.Button(
            seed_frame,
            text="添加据点",
            style="Dark.TButton",
            command=self._add_seed,
        )
        add_seed_btn.pack(fill=tk.X, pady=2)

        self.seed_tree = ttk.Treeview(
            seed_frame,
            columns=("name", "priority", "status"),
            show="headings",
            height=8,
            style="Dark.Treeview",
        )
        self.seed_tree.heading("name", text="名称")
        self.seed_tree.heading("priority", text="优先级")
        self.seed_tree.heading("status", text="状态")
        self.seed_tree.column("name", width=120)
        self.seed_tree.column("priority", width=60, anchor=tk.CENTER)
        self.seed_tree.column("status", width=60, anchor=tk.CENTER)
        self.seed_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        attention_frame = ttk.LabelFrame(
            parent,
            text=" 注意力设置 (拉注意力) ",
            style="Dark.TLabelframe",
            padding=10,
        )
        attention_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(attention_frame, text="关注关键词:", style="Dark.TLabel").pack(anchor=tk.W)
        self.keyword_entry = ttk.Entry(attention_frame, style="Dark.TEntry")
        self.keyword_entry.pack(fill=tk.X, pady=2)

        add_kw_btn = ttk.Button(
            attention_frame,
            text="添加关键词",
            style="Dark.TButton",
            command=self._add_keyword,
        )
        add_kw_btn.pack(fill=tk.X, pady=2)

        self.keywords_list = tk.Listbox(
            attention_frame,
            bg="#374151",
            fg="#e5e7eb",
            height=4,
            selectbackground="#3b82f6",
        )
        self.keywords_list.pack(fill=tk.X, pady=2)

    def _create_center_panel(self, parent):
        """创建中央面板（图可视化）"""
        if not TKINTER_AVAILABLE:
            return

        graph_frame = ttk.LabelFrame(
            parent,
            text=" 爬取图网络 (连线载点) ",
            style="Dark.TLabelframe",
            padding=10,
        )
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._graph_canvas = GraphCanvas(graph_frame)
        self._graph_canvas.canvas.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(graph_frame, style="Dark.TFrame")
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text="圆形", style="Dark.TButton",
                   command=lambda: self._relayout("circular")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="层次", style="Dark.TButton",
                   command=lambda: self._relayout("hierarchical")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="力导向", style="Dark.TButton",
                   command=lambda: self._relayout("force")).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar, text="放大", style="Dark.TButton",
                   command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="缩小", style="Dark.TButton",
                   command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="重置", style="Dark.TButton",
                   command=self._reset_view).pack(side=tk.LEFT, padx=2)

        self.progress_var = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(
            graph_frame,
            variable=self.progress_var,
            maximum=100,
            style="Dark.Horizontal.TProgressbar",
        )
        progress_bar.pack(fill=tk.X, pady=(10, 0))

    def _create_right_panel(self, parent):
        """创建右侧面板（统计 + 节点信息）"""
        if not TKINTER_AVAILABLE:
            return

        stats_frame = ttk.LabelFrame(
            parent,
            text=" 统计信息 ",
            style="Dark.TLabelframe",
            padding=10,
        )
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_labels: Dict[str, tk.StringVar] = {}
        stats_items = [
            ("total_nodes", "总节点数"),
            ("total_edges", "总连线数"),
            ("crawled", "已爬取"),
            ("pending", "待爬取"),
            ("domains", "域名数"),
        ]

        for key, label in stats_items:
            var = tk.StringVar(value="0")
            self.stats_labels[key] = var
            row = ttk.Frame(stats_frame, style="Dark.TFrame")
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label + ":", style="Dark.TLabel").pack(side=tk.LEFT)
            ttk.Label(row, textvariable=var, style="Dark.TLabel").pack(side=tk.RIGHT)

        top_nodes_frame = ttk.LabelFrame(
            parent,
            text=" Top注意力节点 ",
            style="Dark.TLabelframe",
            padding=10,
        )
        top_nodes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.top_nodes_tree = ttk.Treeview(
            top_nodes_frame,
            columns=("url", "score"),
            show="headings",
            height=10,
            style="Dark.Treeview",
        )
        self.top_nodes_tree.heading("url", text="节点")
        self.top_nodes_tree.heading("score", text="注意力")
        self.top_nodes_tree.column("url", width=150)
        self.top_nodes_tree.column("score", width=60, anchor=tk.CENTER)
        self.top_nodes_tree.pack(fill=tk.BOTH, expand=True)

        legend_frame = ttk.LabelFrame(
            parent,
            text=" 图例 ",
            style="Dark.TLabelframe",
            padding=10,
        )
        legend_frame.pack(fill=tk.X, padx=5, pady=5)

        legend_items = [
            ("#3b82f6", "待爬取"),
            ("#f59e0b", "爬取中"),
            ("#10b981", "已完成"),
            ("#ef4444", "失败"),
            ("#fbbf24", "高注意力"),
        ]

        for color, label in legend_items:
            row = ttk.Frame(legend_frame, style="Dark.TFrame")
            row.pack(fill=tk.X, pady=1)
            canvas = tk.Canvas(row, width=16, height=16, bg="#1e1e2e", highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=5)
            canvas.create_oval(2, 2, 14, 14, fill=color, outline="")
            ttk.Label(row, text=label, style="Dark.TLabel").pack(side=tk.LEFT)

    def _add_seed(self):
        """添加种子据点"""
        url = self.seed_url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入据点URL")
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        seed_id = self.seed_manager.add_seed_url(url, name=urlparse(url).netloc)
        self.graph.add_node(url, depth=0, seed_id=seed_id)

        self._refresh_seed_list()
        self._refresh_graph()
        self.seed_url_entry.delete(0, tk.END)
        self.status_var.set(f"已添加据点: {url}")

    def _add_keyword(self):
        """添加关注关键词"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            return

        self.attention_scorer.add_focus_keyword(keyword)
        self.keywords_list.insert(tk.END, keyword)
        self.keyword_entry.delete(0, tk.END)
        self.status_var.set(f"已添加关注关键词: {keyword}")

        if self.graph:
            self.attention_scorer.update_graph_attention(self.graph)
            self._refresh_graph()
            self._refresh_top_nodes()

    def _start_crawling(self):
        """开始爬取"""
        if self._running:
            return

        active_seeds = self.seed_manager.get_active_seeds()
        if not active_seeds:
            messagebox.showwarning("警告", "请先添加至少一个种子据点")
            return

        self._running = True
        self.start_button.config(state=tk.DISABLED)
        self.status_var.set("正在爬取...")

        self._crawl_thread = threading.Thread(target=self._crawl_loop, daemon=True)
        self._crawl_thread.start()

    def _crawl_loop(self):
        """爬取循环（模拟）"""
        for i in range(10):
            if not self._running:
                break

            time.sleep(0.5)

            for node_id, node in list(self.graph._nodes.items())[:5]:
                if node.status == NodeStatus.PENDING:
                    self.graph.update_node(node_id, status=NodeStatus.CRAWLED)
                    for j in range(3):
                        new_url = f"{node.url}/page_{i}_{j}"
                        self.graph.add_node(new_url, depth=node.depth + 1)
                        self.graph.add_edge(node.url, new_url)

            self.attention_scorer.update_graph_attention(self.graph)

            self.root.after(0, self._refresh_graph)
            self.root.after(0, self._refresh_stats)

        self._running = False
        self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.status_var.set("爬取完成"))

    def _stop_crawling(self):
        """停止爬取"""
        self._running = False
        self.status_var.set("已停止")
        self.start_button.config(state=tk.NORMAL)

    def _refresh_seed_list(self):
        """刷新种子列表"""
        if not TKINTER_AVAILABLE:
            return

        for item in self.seed_tree.get_children():
            self.seed_tree.delete(item)

        for seed in self.seed_manager.get_all_seeds():
            self.seed_tree.insert(
                "",
                tk.END,
                values=(seed.name[:20], seed.priority, seed.status),
            )

    def _refresh_graph(self):
        """刷新图显示"""
        if not TKINTER_AVAILABLE:
            return

        if not self._graph_canvas._node_positions:
            self._graph_canvas.layout_nodes(self.graph, algorithm="force")

        self._graph_canvas.redraw(self.graph)
        self._refresh_top_nodes()

    def _refresh_stats(self):
        """刷新统计信息"""
        if not TKINTER_AVAILABLE:
            return

        stats = self.graph.get_stats()
        status_counts = stats.get("status_counts", {})

        self.stats_labels["total_nodes"].set(str(stats.get("total_nodes", 0)))
        self.stats_labels["total_edges"].set(str(stats.get("total_edges", 0)))
        self.stats_labels["crawled"].set(str(status_counts.get("crawled", 0)))
        self.stats_labels["pending"].set(str(status_counts.get("pending", 0)))
        self.stats_labels["domains"].set(str(stats.get("domains", 0)))

        total = stats.get("total_nodes", 0)
        crawled = status_counts.get("crawled", 0)
        progress = (crawled / total * 100) if total > 0 else 0
        self.progress_var.set(progress)

    def _refresh_top_nodes(self):
        """刷新Top注意力节点"""
        if not TKINTER_AVAILABLE:
            return

        for item in self.top_nodes_tree.get_children():
            self.top_nodes_tree.delete(item)

        top_nodes = self.graph.get_top_nodes(by="attention", limit=10)
        for node in top_nodes:
            self.top_nodes_tree.insert(
                "",
                tk.END,
                values=(node.domain[:25] or node.url[:25], f"{node.attention_score:.2f}"),
            )

    def _relayout(self, algorithm: str):
        """重新布局"""
        self._graph_canvas.layout_nodes(self.graph, algorithm)
        self._graph_canvas.redraw(self.graph)

    def _zoom_in(self):
        """放大"""
        self._graph_canvas._zoom_in()

    def _zoom_out(self):
        """缩小"""
        self._graph_canvas._zoom_out()

    def _reset_view(self):
        """重置视图"""
        self._graph_canvas._zoom = 1.0
        self._graph_canvas._pan_offset = (0, 0)
        self._graph_canvas.redraw(self.graph)

    def _import_seeds(self):
        """导入种子"""
        if not TKINTER_AVAILABLE:
            return

        file_path = filedialog.askopenfilename(
            title="导入种子文件",
            filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if file_path:
            self.status_var.set(f"已导入种子: {file_path}")

    def _export_data(self):
        """导出数据"""
        if not TKINTER_AVAILABLE:
            return

        file_path = filedialog.asksaveasfilename(
            title="导出数据",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")],
        )
        if file_path:
            self.graph.save(Path(file_path))
            self.status_var.set(f"数据已导出: {file_path}")

    def _show_about(self):
        """显示关于对话框"""
        if not TKINTER_AVAILABLE:
            return

        messagebox.showinfo(
            "关于",
            "AI LLM Agent 爬虫 v1.0\n\n"
            "智能爬取框架，支持：\n"
            "- 据点管理（种子URL）\n"
            "- 连线载点（图网络）\n"
            "- 拉注意力（智能评分）\n"
            "- LLM Agent指导",
        )

    def run(self):
        """运行GUI"""
        if not TKINTER_AVAILABLE:
            logger.error("Tkinter不可用，无法启动GUI")
            return

        self.root.mainloop()

    def close(self):
        """关闭GUI"""
        self._running = False
        if TKINTER_AVAILABLE and hasattr(self, "root"):
            self.root.quit()
