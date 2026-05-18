import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split


class DataProcessor:
    def __init__(self, dataframe: Optional[pd.DataFrame] = None):
        self.df = dataframe
        self.scalers = {}
        self.encoders = {}

    def load_data(self, dataframe: pd.DataFrame):
        self.df = dataframe
        return self

    def get_info(self) -> Dict[str, Any]:
        if self.df is None:
            return {}
        
        return {
            'shape': self.df.shape,
            'columns': list(self.df.columns),
            'dtypes': self.df.dtypes.astype(str).to_dict(),
            'missing_values': self.df.isnull().sum().to_dict(),
            'summary': self.df.describe().to_dict()
        }

    def handle_missing(self, strategy: str = 'drop', 
                    fill_value: Any = None) -> 'DataProcessor':
        if self.df is None:
            return self
        
        if strategy == 'drop':
            self.df = self.df.dropna()
        elif strategy == 'mean':
            self.df = self.df.fillna(self.df.mean())
        elif strategy == 'median':
            self.df = self.df.fillna(self.df.median())
        elif strategy == 'fill' and fill_value is not None:
            self.df = self.df.fillna(fill_value)
        
        return self

    def encode_categorical(self, columns: List[str]) -> 'DataProcessor':
        if self.df is None:
            return self
        
        for col in columns:
            if col in self.df.columns:
                le = LabelEncoder()
                self.df[col] = le.fit_transform(self.df[col].astype(str))
                self.encoders[col] = le
        
        return self

    def scale_numeric(self, columns: List[str], 
                     method: str = 'standard') -> 'DataProcessor':
        if self.df is None:
            return self
        
        for col in columns:
            if col in self.df.columns:
                if method == 'standard':
                    scaler = StandardScaler()
                    self.df[col] = scaler.fit_transform(self.df[[col]])
                    self.scalers[col] = scaler
        
        return self

    def split_data(self, target_col: str, 
                 test_size: float = 0.2, 
                 random_state: int = 42) -> Dict[str, Any]:
        if self.df is None:
            raise ValueError("No data loaded")
        
        X = self.df.drop(target_col, axis=1)
        y = self.df[target_col]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        return {
            'X_train': X_train,
            'X_test': X_test,
            'y_train': y_train,
            'y_test': y_test
        }

    def apply_transform(self, column: str, 
                       func: Callable) -> 'DataProcessor':
        if self.df is not None and column in self.df.columns:
            self.df[column] = self.df[column].apply(func)
        
        return self

    def create_feature(self, new_col: str, 
                   data: Any) -> 'DataProcessor':
        if self.df is not None:
            self.df[new_col] = data
        
        return self

    def filter_rows(self, condition: Any) -> 'DataProcessor':
        if self.df is not None:
            self.df = self.df[condition]
        
        return self

    def select_columns(self, columns: List[str]) -> 'DataProcessor':
        if self.df is not None:
            self.df = self.df[columns]
        
        return self

    def get_data(self) -> pd.DataFrame:
        return self.df.copy() if self.df is not None else pd.DataFrame()

    def aggregate(self, group_cols: List[str], 
                 agg_dict: Dict[str, str]) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()
        
        return self.df.groupby(group_cols).agg(agg_dict).reset_index()

    def correlate(self) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()
        
        return self.df.corr()
