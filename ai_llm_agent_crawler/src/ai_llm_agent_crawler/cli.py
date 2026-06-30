"""
命令行接口（CLI）

提供命令行工具，用于管理爬虫、启动GUI、
查看统计等功能。
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ai_llm_agent_crawler import get_logger, setup_logging
from ai_llm_agent_crawler.agent import AttentionScorer, CrawlAgent
from ai_llm_agent_crawler.graph import CrawlGraph
from ai_llm_agent_crawler.seed import SeedCategory, SeedManager

logger = get_logger(__name__)
console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="ai-crawler")
@click.option("--debug", is_flag=True, help="启用调试模式")
@click.option("--config", type=click.Path(), help="配置文件路径")
def cli(debug: bool, config: Optional[str]):
    """AI LLM Agent 爬虫 - 智能爬取框架"""
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(log_level=log_level)


@cli.command()
@click.option("--url", "-u", multiple=True, help="种子URL")
@click.option("--category", "-c", default="custom", help="分类")
@click.option("--priority", "-p", default=5, type=int, help="优先级(1-10)")
@click.option("--storage", type=click.Path(), help="种子存储文件")
def add_seed(url, category: str, priority: int, storage: Optional[str]):
    """添加种子据点"""
    seed_manager = SeedManager(Path(storage) if storage else None)

    for u in url:
        seed_id = seed_manager.add_seed_url(
            u,
            category=SeedCategory(category),
            priority=priority,
        )
        console.print(f"[green]✓[/green] 已添加据点: {u} (ID: {seed_id})")

    if storage:
        seed_manager.export_seeds(Path(storage))

    stats = seed_manager.get_stats()
    console.print(f"\n总计: {stats['total']} 个据点, {stats['active']} 个活跃")


@cli.command()
@click.option("--storage", type=click.Path(), help="种子存储文件")
def list_seeds(storage: Optional[str]):
    """列出所有种子据点"""
    seed_manager = SeedManager(Path(storage) if storage else None)
    seeds = seed_manager.get_all_seeds()

    if not seeds:
        console.print("[yellow]暂无种子据点[/yellow]")
        return

    table = Table(title="种子据点列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("URL", style="blue")
    table.add_column("分类", style="magenta")
    table.add_column("优先级", justify="center")
    table.add_column("状态", style="yellow")
    table.add_column("已爬取", justify="right")

    for seed in seeds:
        table.add_row(
            seed.seed_id,
            seed.name[:20],
            seed.url[:40],
            seed.category,
            str(seed.priority),
            seed.status,
            str(seed.pages_crawled),
        )

    console.print(table)

    stats = seed_manager.get_stats()
    console.print(f"\n总计: {stats['total']} 个据点 | 活跃: {stats['active']}")


@cli.command()
@click.argument("seed_id")
@click.option("--storage", type=click.Path(), help="种子存储文件")
def remove_seed(seed_id: str, storage: Optional[str]):
    """移除种子据点"""
    seed_manager = SeedManager(Path(storage) if storage else None)

    if seed_manager.remove_seed(seed_id):
        console.print(f"[green]✓[/green] 已移除据点: {seed_id}")
        if storage:
            seed_manager.export_seeds(Path(storage))
    else:
        console.print(f"[red]✗[/red] 未找到据点: {seed_id}")


@cli.command(name="gui")
def start_gui():
    """启动图形界面（窗口）"""
    try:
        from ai_llm_agent_crawler.gui import CrawlerGUI

        console.print("[green]启动图形界面...[/green]")
        gui = CrawlerGUI()
        gui.run()
    except ImportError as e:
        console.print(f"[red]GUI启动失败: {e}[/red]")
        console.print("[yellow]请确保已安装 tkinter[/yellow]")
        sys.exit(1)


@cli.command()
@click.option("--seed", "-s", help="种子据点ID")
@click.option("--max-pages", "-n", default=100, type=int, help="最大页面数")
@click.option("--keyword", "-k", multiple=True, help="关注关键词")
@click.option("--storage", type=click.Path(), help="图存储文件")
def crawl(seed: str, max_pages: int, keyword, storage: Optional[str]):
    """启动智能爬取"""
    from ai_llm_agent_crawler.agent import CrawlAgent

    graph = CrawlGraph(Path(storage) if storage else None)
    agent = CrawlAgent(graph=graph)

    if keyword:
        agent.set_focus_keywords(list(keyword))

    console.print(f"[cyan]启动智能爬取...[/cyan]")
    console.print(f"  策略: {agent.config.attention_config.strategy}")
    console.print(f"  关注关键词: {agent.config.attention_config.focus_keywords or '无'}")
    console.print(f"  最大页面数: {max_pages}")

    stats = graph.get_stats()
    console.print(f"\n当前图状态:")
    console.print(f"  节点数: {stats['total_nodes']}")
    console.print(f"  连线数: {stats['total_edges']}")

    console.print("\n[green]爬取准备完成[/green]")
    console.print("[dim]提示: 使用 'ai-crawler gui' 启动图形界面进行可视化操作[/dim]")


@cli.command()
@click.option("--storage", type=click.Path(), help="图存储文件")
@click.option("--by", default="attention", help="排序依据 (attention/importance/pagerank)")
@click.option("--limit", "-n", default=10, type=int, help="显示数量")
def top_nodes(storage: Optional[str], by: str, limit: int):
    """查看Top节点"""
    graph = CrawlGraph(Path(storage) if storage else None)

    nodes = graph.get_top_nodes(by=by, limit=limit)

    if not nodes:
        console.print("[yellow]暂无节点数据[/yellow]")
        return

    table = Table(title=f"Top {limit} 节点 (按{by}排序)")
    table.add_column("排名", justify="center", style="cyan")
    table.add_column("URL", style="blue")
    table.add_column("域名", style="green")
    table.add_column("深度", justify="center")
    table.add_column("注意力", justify="right", style="yellow")
    table.add_column("重要度", justify="right", style="magenta")
    table.add_column("状态", style="red")

    for i, node in enumerate(nodes, 1):
        table.add_row(
            str(i),
            node.url[:50],
            node.domain,
            str(node.depth),
            f"{node.attention_score:.3f}",
            f"{node.importance_score:.3f}",
            node.status,
        )

    console.print(table)


@cli.command()
@click.option("--storage", type=click.Path(), help="图存储文件")
def stats(storage: Optional[str]):
    """查看爬取统计"""
    graph = CrawlGraph(Path(storage) if storage else None)
    stats_data = graph.get_stats()

    table = Table(title="爬取图统计")
    table.add_column("指标", style="cyan")
    table.add_column("数值", style="green", justify="right")

    table.add_row("总节点数", str(stats_data["total_nodes"]))
    table.add_row("总连线数", str(stats_data["total_edges"]))
    table.add_row("域名数", str(stats_data["domains"]))
    table.add_row("最大深度", str(stats_data["max_depth"]))
    table.add_row("平均入度", f"{stats_data['avg_in_degree']:.2f}")
    table.add_row("平均出度", f"{stats_data['avg_out_degree']:.2f}")
    table.add_row("平均重要度", f"{stats_data['avg_importance']:.3f}")

    console.print(table)

    status_counts = stats_data.get("status_counts", {})
    if status_counts:
        status_table = Table(title="节点状态分布")
        status_table.add_column("状态", style="cyan")
        status_table.add_column("数量", justify="right", style="green")
        for status, count in status_counts.items():
            status_table.add_row(status, str(count))
        console.print(status_table)

    domains = graph.get_domains()
    if domains:
        domain_table = Table(title="Top域名分布")
        domain_table.add_column("域名", style="blue")
        domain_table.add_column("节点数", justify="right", style="green")
        for domain, count in list(domains.items())[:10]:
            domain_table.add_row(domain, str(count))
        console.print(domain_table)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="输出文件路径")
@click.option("--storage", type=click.Path(), help="图存储文件")
@click.option("--max-nodes", default=100, type=int, help="最大节点数")
def export_graphviz(output: str, storage: Optional[str], max_nodes: int):
    """导出Graphviz格式"""
    graph = CrawlGraph(Path(storage) if storage else None)
    output_path = Path(output) if output else Path("crawl_graph.dot")

    graph.export_graphviz(output_path, max_nodes=max_nodes)
    console.print(f"[green]✓[/green] 已导出到: {output_path}")
    console.print(f"[dim]使用 'dot -Tpng {output_path} -o graph.png' 生成图片[/dim]")


@cli.command()
def info():
    """显示系统信息"""
    table = Table(title="AI LLM Agent 爬虫系统")
    table.add_column("项目", style="cyan")
    table.add_column("信息", style="green")

    table.add_row("版本", "0.1.0")
    table.add_row("Python", sys.version.split()[0])
    table.add_row("平台", sys.platform)

    console.print(table)

    console.print("\n[bold]核心模块:[/bold]")
    console.print("  • [cyan]seed[/cyan] - 种子据点管理 (据点)")
    console.print("  • [cyan]graph[/cyan] - 爬取图网络 (连线载点)")
    console.print("  • [cyan]agent[/cyan] - LLM Agent 指导 (拉注意力)")
    console.print("  • [cyan]gui[/cyan] - 图形界面 (窗口)")
    console.print("  • [cyan]crawler[/cyan] - 爬虫引擎")
    console.print("  • [cyan]dataset[/cyan] - 数据集生成")
    console.print("  • [cyan]storage[/cyan] - 存储管理")
    console.print("  • [cyan]security[/cyan] - 安全加密")
    console.print("  • [cyan]versioning[/cyan] - 版本控制")


def main():
    """主入口函数"""
    cli()


if __name__ == "__main__":
    main()
