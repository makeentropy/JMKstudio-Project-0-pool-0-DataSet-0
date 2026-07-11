"""
IDE 模块

提供 H5 内嵌 Jupyter IDE：
- :class:`Notebook` / :class:`Cell` —— 内存中的 notebook 模型与代码执行；
- :mod:`ai_llm_agent_crawler.ide.server` —— FastAPI 后端，暴露所有模块 API
  与静态前端（浏览器预览 / 可隐藏商用）；
- ``ide/static/`` —— H5 内嵌前端（index.html + app.js + styles.css）。
"""

from ai_llm_agent_crawler.ide.notebook import Notebook, Cell, CellType, ExecutionResult

__all__ = [
    "Notebook",
    "Cell",
    "CellType",
    "ExecutionResult",
]
