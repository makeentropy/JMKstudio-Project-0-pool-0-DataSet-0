from .base_plugin import BasePlugin
from typing import Optional, Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class HuggingFacePlugin(BasePlugin):
    def __init__(self):
        super().__init__("Hugging Face Integration", "1.0.0")
        self.transformers = None
        self.datasets = None
        self.torch = None

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        if config:
            self.config.update(config)
        
        try:
            import transformers
            import datasets
            import torch
            
            self.transformers = transformers
            self.datasets = datasets
            self.torch = torch
            
            return True
        except ImportError as e:
            print(f"Warning: Hugging Face libraries not available: {e}")
            return False

    def execute(self, **kwargs) -> Any:
        action = kwargs.get('action')
        
        if action == 'load_model':
            return self._load_model(**kwargs)
        elif action == 'load_dataset':
            return self._load_dataset(**kwargs)
        elif action == 'text_classification':
            return self._text_classification(**kwargs)
        elif action == 'text_generation':
            return self._text_generation(**kwargs)
        elif action == 'tokenize':
            return self._tokenize(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _load_model(self, model_name: str, task: Optional[str] = None) -> Dict[str, Any]:
        if not self.transformers:
            raise ImportError("transformers library not available")
        
        pipeline = self.transformers.pipeline(task=task, model=model_name)
        
        return {
            'status': 'success',
            'pipeline': pipeline,
            'model_name': model_name
        }

    def _load_dataset(self, dataset_name: str, split: str = 'train') -> Dict[str, Any]:
        if not self.datasets:
            raise ImportError("datasets library not available")
        
        dataset = self.datasets.load_dataset(dataset_name, split=split)
        
        return {
            'status': 'success',
            'dataset': dataset,
            'name': dataset_name,
            'split': split
        }

    def _text_classification(self, text: str, model_name: str = 'distilbert-base-uncased-finetuned-sst-2-english') -> Dict[str, Any]:
        if not self.transformers:
            raise ImportError("transformers library not available")
        
        classifier = self.transformers.pipeline('text-classification', model=model_name)
        result = classifier(text)
        
        return {
            'status': 'success',
            'input': text,
            'result': result
        }

    def _text_generation(self, prompt: str, model_name: str = 'gpt2', 
                        max_length: int = 100) -> Dict[str, Any]:
        if not self.transformers:
            raise ImportError("transformers library not available")
        
        generator = self.transformers.pipeline('text-generation', model=model_name)
        result = generator(prompt, max_length=max_length)
        
        return {
            'status': 'success',
            'prompt': prompt,
            'result': result
        }

    def _tokenize(self, text: str, model_name: str = 'bert-base-uncased') -> Dict[str, Any]:
        if not self.transformers:
            raise ImportError("transformers library not available")
        
        tokenizer = self.transformers.AutoTokenizer.from_pretrained(model_name)
        tokens = tokenizer.tokenize(text)
        token_ids = tokenizer.encode(text)
        
        return {
            'status': 'success',
            'text': text,
            'tokens': tokens,
            'token_ids': token_ids
        }

    def cleanup(self) -> bool:
        if self.torch and hasattr(self.torch, 'cuda'):
            self.torch.cuda.empty_cache()
        return True
