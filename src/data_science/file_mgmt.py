"""
File Management Science - scientific approach to file management.

Implements the 'file management science / 文件管理科学' concept:
a structured, metadata-rich approach to managing files within the
steganographic data ecosystem, with ordering strategies.
"""

import os
import time
import hashlib
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from ..utils import generate_id, hash_data


class OrderStrategy(Enum):
    BY_NAME = "by_name"
    BY_SIZE = "by_size"
    BY_TIME = "by_time"
    BY_HASH = "by_hash"
    BY_TYPE = "by_type"
    CUSTOM = "custom"


@dataclass
class FileRecord:
    record_id: str
    path: str
    name: str
    size: int
    created_at: float
    modified_at: float
    file_hash: str
    file_type: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: str) -> "FileRecord":
        stat = os.stat(path)
        name = os.path.basename(path)
        _, ext = os.path.splitext(name)
        file_hash = "unknown"
        try:
            with open(path, "rb") as f:
                file_hash = hash_data(f.read())
        except Exception:
            pass
        return cls(
            record_id=generate_id("file"),
            path=os.path.abspath(path),
            name=name,
            size=stat.st_size,
            created_at=stat.st_ctime,
            modified_at=stat.st_mtime,
            file_hash=file_hash,
            file_type=ext.lstrip(".").lower() or "unknown",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "file_hash": self.file_hash[:16] + "...",
            "file_type": self.file_type,
            "tags": self.tags,
        }


class FileManager:
    """
    Scientific file manager - catalogs, indexes, and orders files.

    The '文件管理科学' concept: treat file management as a scientific
    discipline with rigorous indexing, hashing, and ordered classification.
    """

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or os.getcwd()
        self._records: Dict[str, FileRecord] = {}
        self._path_index: Dict[str, str] = {}
        self._type_index: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}

    @property
    def count(self) -> int:
        return len(self._records)

    def scan_directory(self, directory: Optional[str] = None,
                       recursive: bool = True) -> List[FileRecord]:
        target = directory or self.root_dir
        records = []
        if not os.path.exists(target):
            return records

        if os.path.isfile(target):
            rec = self._add_file(target)
            if rec:
                records.append(rec)
            return records

        for root, dirs, files in os.walk(target):
            for fname in files:
                fpath = os.path.join(root, fname)
                rec = self._add_file(fpath)
                if rec:
                    records.append(rec)
            if not recursive:
                break
        return records

    def _add_file(self, path: str) -> Optional[FileRecord]:
        try:
            rec = FileRecord.from_path(path)
        except Exception:
            return None
        self._records[rec.record_id] = rec
        self._path_index[rec.path] = rec.record_id
        if rec.file_type not in self._type_index:
            self._type_index[rec.file_type] = []
        self._type_index[rec.file_type].append(rec.record_id)
        return rec

    def get_by_path(self, path: str) -> Optional[FileRecord]:
        rid = self._path_index.get(os.path.abspath(path))
        return self._records.get(rid) if rid else None

    def get_by_type(self, file_type: str) -> List[FileRecord]:
        rids = self._type_index.get(file_type.lower(), [])
        return [self._records[r] for r in rids if r in self._records]

    def list_all(self, strategy: OrderStrategy = OrderStrategy.BY_NAME,
                 reverse: bool = False) -> List[FileRecord]:
        records = list(self._records.values())
        key_func = self._get_sort_key(strategy)
        records.sort(key=key_func, reverse=reverse)
        return records

    def _get_sort_key(self, strategy: OrderStrategy):
        if strategy == OrderStrategy.BY_NAME:
            return lambda r: r.name.lower()
        elif strategy == OrderStrategy.BY_SIZE:
            return lambda r: r.size
        elif strategy == OrderStrategy.BY_TIME:
            return lambda r: r.modified_at
        elif strategy == OrderStrategy.BY_HASH:
            return lambda r: r.file_hash
        elif strategy == OrderStrategy.BY_TYPE:
            return lambda r: (r.file_type, r.name.lower())
        return lambda r: r.name.lower()

    def add_tag(self, record_id: str, tag: str) -> bool:
        rec = self._records.get(record_id)
        if not rec:
            return False
        if tag not in rec.tags:
            rec.tags.append(tag)
        if tag not in self._tag_index:
            self._tag_index[tag] = []
        if record_id not in self._tag_index[tag]:
            self._tag_index[tag].append(record_id)
        return True

    def get_by_tag(self, tag: str) -> List[FileRecord]:
        rids = self._tag_index.get(tag, [])
        return [self._records[r] for r in rids if r in self._records]

    def search(self, query: str) -> List[FileRecord]:
        q = query.lower()
        results = []
        for rec in self._records.values():
            if (q in rec.name.lower() or
                q in rec.file_type or
                q in " ".join(rec.tags).lower()):
                results.append(rec)
        return results

    def stats(self) -> Dict[str, Any]:
        total_size = sum(r.size for r in self._records.values())
        types = {t: len(rids) for t, rids in self._type_index.items()}
        return {
            "total_files": len(self._records),
            "total_size_bytes": total_size,
            "file_types": types,
            "tag_count": len(self._tag_index),
            "root_dir": self.root_dir,
        }
