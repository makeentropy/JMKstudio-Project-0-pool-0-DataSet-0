"""
data_science - Data science dimension space.

Implements:
- File management science (scientific file operations)
- Data ordering (sorting, data order / 数据秩序)
- Data science agent interface for the dimension space dataset
"""

from .file_mgmt import FileManager, FileRecord, OrderStrategy
from .data_order import DataOrder, SortEngine, OrderRule

__all__ = [
    "FileManager",
    "FileRecord",
    "OrderStrategy",
    "DataOrder",
    "SortEngine",
    "OrderRule",
]
