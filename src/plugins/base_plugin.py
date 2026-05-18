from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BasePlugin(ABC):
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True
        self.config = {}

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass

    @abstractmethod
    def cleanup(self) -> bool:
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'enabled': self.enabled
        }

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
