import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, Any, List
import os


class DataVisualizer:
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), 'data', 'visualizations')
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        plt.style.use('dark_background')

    def plot_histogram(self, dataframe: pd.DataFrame, column: str, 
                      title: str = '', 
                      save_path: Optional[str] = None) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(data=dataframe, x=column, kde=True, 
                      ax=ax, color='#00ffff')
        ax.set_title(title or f'Distribution of {column}', color='#00ffff')
        ax.set_xlabel(column, color='#88ff88')
        ax.set_ylabel('Frequency', color='#88ff88')
        ax.tick_params(colors='#88ff88')
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, f'histogram_{column}.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def plot_scatter(self, dataframe: pd.DataFrame, x_col: str, y_col: str,
                   hue_col: Optional[str] = None,
                   title: str = '',
                   save_path: Optional[str] = None) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if hue_col:
            sns.scatterplot(data=dataframe, x=x_col, y=y_col, 
                          hue=hue_col, ax=ax, palette='cool')
        else:
            sns.scatterplot(data=dataframe, x=x_col, y=y_col, 
                          color='#00ffff', ax=ax)
        
        ax.set_title(title or f'{y_col} vs {x_col}', color='#00ffff')
        ax.set_xlabel(x_col, color='#88ff88')
        ax.set_ylabel(y_col, color='#88ff88')
        ax.tick_params(colors='#88ff88')
        ax.grid(True, alpha=0.3)
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, f'scatter_{x_col}_{y_col}.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def plot_correlation_heatmap(self, dataframe: pd.DataFrame,
                                 title: str = 'Correlation Heatmap',
                                 save_path: Optional[str] = None) -> str:
        corr = dataframe.corr()
        fig, ax = plt.subplots(figsize=(12, 10))
        
        mask = np.triu(np.ones_like(corr.shape, dtype=bool))
        sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', 
                      cmap='coolwarm', center=0,
                      square=True, linewidths=1, ax=ax,
                      cbar_kws={"shrink": 0.8})
        
        ax.set_title(title, color='#00ffff', fontsize=14)
        ax.tick_params(colors='#88ff88')
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, 'correlation_heatmap.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def plot_box(self, dataframe: pd.DataFrame, x_col: str, y_col: str,
                title: str = '',
                save_path: Optional[str] = None) -> str:
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.boxplot(data=dataframe, x=x_col, y=y_col, ax=ax, palette='cool')
        ax.set_title(title or f'{y_col} by {x_col}', color='#00ffff')
        ax.set_xlabel(x_col, color='#88ff88')
        ax.set_ylabel(y_col, color='#88ff88')
        ax.tick_params(colors='#88ff88')
        plt.xticks(rotation=45)
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, f'box_{x_col}_{y_col}.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def plot_line(self, dataframe: pd.DataFrame, x_col: str, y_col: str,
                  title: str = '',
                  save_path: Optional[str] = None) -> str:
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.lineplot(data=dataframe, x=x_col, y=y_col, 
                     ax=ax, color='#00ffff', marker='o')
        ax.set_title(title or f'{y_col} over {x_col}', color='#00ffff')
        ax.set_xlabel(x_col, color='#88ff88')
        ax.set_ylabel(y_col, color='#88ff88')
        ax.tick_params(colors='#88ff88')
        ax.grid(True, alpha=0.3)
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, f'line_{x_col}_{y_col}.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def plot_pair(self, dataframe: pd.DataFrame,
                 columns: Optional[List[str]] = None,
                 hue_col: Optional[str] = None,
                 save_path: Optional[str] = None) -> str:
        if columns:
            df_subset = dataframe[columns]
        else:
            df_subset = dataframe
        
        g = sns.pairplot(df_subset, hue=hue_col, 
                         palette='cool', corner=True)
        g.fig.suptitle('Pairwise Relationships', y=1.02)
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, 'pairplot.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def plot_count(self, dataframe: pd.DataFrame, column: str,
                  title: str = '',
                  save_path: Optional[str] = None) -> str:
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.countplot(data=dataframe, x=column, ax=ax, palette='cool')
        ax.set_title(title or f'Count of {column}', color='#00ffff')
        ax.set_xlabel(column, color='#88ff88')
        ax.set_ylabel('Count', color='#88ff88')
        ax.tick_params(colors='#88ff88')
        plt.xticks(rotation=45)
        
        if save_path is None:
            save_path = os.path.join(self.output_dir, f'count_{column}.png')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path

    def create_dashboard(self, dataframe: pd.DataFrame,
                        target_col: Optional[str] = None,
                        save_dir: Optional[str] = None) -> Dict[str, str]:
        if save_dir is None:
            save_dir = self.output_dir
        
        plots = {}
        
        numeric_cols = dataframe.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols[:3]:
            plots[f'hist_{col}'] = self.plot_histogram(dataframe, col, 
                                                        save_path=os.path.join(save_dir, f'hist_{col}.png'))
        
        if len(numeric_cols) >= 2:
            plots['scatter'] = self.plot_scatter(dataframe, 
                                                numeric_cols[0], 
                                                numeric_cols[1],
                                                save_path=os.path.join(save_dir, 'scatter.png'))
        
        if len(numeric_cols) >= 3:
            plots['heatmap'] = self.plot_correlation_heatmap(
                dataframe[numeric_cols],
                save_path=os.path.join(save_dir, 'heatmap.png'))
        
        return plots
