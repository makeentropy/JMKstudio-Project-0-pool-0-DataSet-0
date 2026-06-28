"""
数据处理器模块

提供数据清洗、转换和增强功能。
"""

from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class DataProcessor:
    """
    数据处理器
    
    提供数据清洗、转换和增强功能。
    """
    
    def __init__(self, df: Optional[pd.DataFrame] = None):
        """
        初始化数据处理器
        
        Args:
            df: 要处理的DataFrame
        """
        self.df = df
    
    def set_data(self, df: pd.DataFrame) -> "DataProcessor":
        """
        设置要处理的数据
        
        Args:
            df: 数据框
            
        Returns:
            self，支持链式调用
        """
        self.df = df
        return self
    
    def drop_duplicates(self, subset: Optional[List[str]] = None) -> "DataProcessor":
        """
        删除重复行
        
        Args:
            subset: 用于判断重复的列
            
        Returns:
            self
        """
        if self.df is not None:
            before = len(self.df)
            self.df = self.df.drop_duplicates(subset=subset)
            after = len(self.df)
            logger.info(f"删除了 {before - after} 条重复记录")
        return self
    
    def drop_na(self, subset: Optional[List[str]] = None, how: str = "any") -> "DataProcessor":
        """
        删除缺失值
        
        Args:
            subset: 要检查的列
            how: 删除方式 ('any' 或 'all')
            
        Returns:
            self
        """
        if self.df is not None:
            before = len(self.df)
            self.df = self.df.dropna(subset=subset, how=how)
            after = len(self.df)
            logger.info(f"删除了 {before - after} 条缺失值记录")
        return self
    
    def fill_na(
        self, value: Optional[Any] = None, method: Optional[str] = None, columns: Optional[List[str]] = None
    ) -> "DataProcessor":
        """
        填充缺失值
        
        Args:
            value: 填充值
            method: 填充方法 ('ffill', 'bfill')
            columns: 要填充的列
            
        Returns:
            self
        """
        if self.df is not None:
            if columns:
                for col in columns:
                    if value is not None:
                        self.df[col] = self.df[col].fillna(value)
                    elif method:
                        self.df[col] = self.df[col].fillna(method=method)
            else:
                if value is not None:
                    self.df = self.df.fillna(value)
                elif method:
                    self.df = self.df.fillna(method=method)
            logger.info("缺失值已填充")
        return self
    
    def rename_columns(self, columns: Dict[str, str]) -> "DataProcessor":
        """
        重命名列
        
        Args:
            columns: 列名映射字典
            
        Returns:
            self
        """
        if self.df is not None:
            self.df = self.df.rename(columns=columns)
            logger.info(f"重命名了 {len(columns)} 列")
        return self
    
    def select_columns(self, columns: List[str]) -> "DataProcessor":
        """
        选择列
        
        Args:
            columns: 要保留的列名列表
            
        Returns:
            self
        """
        if self.df is not None:
            self.df = self.df[columns]
            logger.info(f"选择了 {len(columns)} 列")
        return self
    
    def drop_columns(self, columns: List[str]) -> "DataProcessor":
        """
        删除列
        
        Args:
            columns: 要删除的列名列表
            
        Returns:
            self
        """
        if self.df is not None:
            self.df = self.df.drop(columns=columns, errors="ignore")
            logger.info(f"删除了 {len(columns)} 列")
        return self
    
    def apply_column(self, column: str, func: Callable) -> "DataProcessor":
        """
        对列应用函数
        
        Args:
            column: 列名
            func: 要应用的函数
            
        Returns:
            self
        """
        if self.df is not None and column in self.df.columns:
            self.df[column] = self.df[column].apply(func)
            logger.info(f"已对列 {column} 应用转换函数")
        return self
    
    def filter(self, condition: Callable[[pd.Series], bool]) -> "DataProcessor":
        """
        过滤数据
        
        Args:
            condition: 过滤条件函数
            
        Returns:
            self
        """
        if self.df is not None:
            before = len(self.df)
            self.df = self.df[self.df.apply(condition, axis=1)]
            after = len(self.df)
            logger.info(f"过滤后保留了 {after} 条记录（删除了 {before - after} 条）")
        return self
    
    def sort(self, by: Union[str, List[str]], ascending: bool = True) -> "DataProcessor":
        """
        排序
        
        Args:
            by: 排序列
            ascending: 是否升序
            
        Returns:
            self
        """
        if self.df is not None:
            self.df = self.df.sort_values(by=by, ascending=ascending)
            logger.info(f"按 {by} 排序完成")
        return self
    
    def transform(self, func: Callable[[pd.DataFrame], pd.DataFrame]) -> "DataProcessor":
        """
        应用自定义转换函数
        
        Args:
            func: 转换函数
            
        Returns:
            self
        """
        if self.df is not None:
            self.df = func(self.df)
            logger.info("已应用自定义转换")
        return self
    
    def get_result(self) -> pd.DataFrame:
        """
        获取处理结果
        
        Returns:
            处理后的DataFrame
        """
        return self.df