"""NLPTC文本特征提取单元测试。"""
import pytest

from oath_toolchain.tools.nlptcmodel.text_features import TextFeatureExtractor


class TestTextFeatureExtractor:
    """测试TextFeatureExtractor类。"""

    def setup_method(self):
        """每个测试前初始化提取器。"""
        self.extractor = TextFeatureExtractor()

    def test_init_default_lang(self):
        """测试默认语言设置。"""
        extractor = TextFeatureExtractor()
        assert extractor.lang == 'auto'

    def test_init_custom_lang(self):
        """测试自定义语言设置。"""
        extractor = TextFeatureExtractor(lang='zh')
        assert extractor.lang == 'zh'

    def test_extract_features_english(self):
        """测试英文文本特征提取。"""
        text = "Hello world, this is a test."
        features = self.extractor.extract_features(text)

        assert 'length' in features
        assert features['length'] == len(text)
        assert 'char_distribution' in features
        assert 'char_unigrams' in features
        assert 'char_bigrams' in features
        assert 'char_trigrams' in features
        assert 'word_tokens' in features
        assert 'word_freq' in features
        assert 'entropy' in features
        assert 'lang' in features

    def test_extract_features_chinese(self):
        """测试中文文本特征提取。"""
        text = "你好世界，这是一个测试。"
        features = self.extractor.extract_features(text)

        assert features['length'] == len(text)
        assert 'entropy' in features
        assert features['entropy'] > 0

    def test_extract_features_japanese(self):
        """测试日文文本特征提取。"""
        text = "こんにちは世界"
        features = self.extractor.extract_features(text)

        assert features['length'] == len(text)
        assert 'entropy' in features

    def test_extract_features_empty(self):
        """测试空文本特征提取。"""
        features = self.extractor.extract_features("")

        assert features['length'] == 0
        assert features['entropy'] == 0.0

    def test_extract_features_invalid_type(self):
        """测试无效类型输入。"""
        with pytest.raises(TypeError):
            self.extractor.extract_features(123)

    def test_char_ngrams_unigram(self):
        """测试1-gram提取。"""
        text = "abc"
        ngrams = self.extractor.char_ngrams(text, 1)
        assert len(ngrams) == 3
        assert 'a' in ngrams
        assert 'b' in ngrams
        assert 'c' in ngrams

    def test_char_ngrams_bigram(self):
        """测试2-gram提取。"""
        text = "abcd"
        ngrams = self.extractor.char_ngrams(text, 2)
        assert len(ngrams) == 3
        assert 'ab' in ngrams
        assert 'bc' in ngrams
        assert 'cd' in ngrams

    def test_char_ngrams_trigram(self):
        """测试3-gram提取。"""
        text = "abcde"
        ngrams = self.extractor.char_ngrams(text, 3)
        assert len(ngrams) == 3
        assert 'abc' in ngrams
        assert 'bcd' in ngrams
        assert 'cde' in ngrams

    def test_char_ngrams_invalid_n(self):
        """测试无效的n值。"""
        with pytest.raises(ValueError):
            self.extractor.char_ngrams("test", 0)

    def test_char_ngrams_short_text(self):
        """测试文本短于n的情况。"""
        ngrams = self.extractor.char_ngrams("ab", 5)
        assert len(ngrams) == 0

    def test_word_tokens_english(self):
        """测试英文分词。"""
        text = "Hello world 123 test."
        tokens = self.extractor.word_tokens(text, 'en')
        assert 'hello' in tokens
        assert 'world' in tokens
        assert '123' in tokens
        assert 'test' in tokens

    def test_word_tokens_chinese(self):
        """测试中文分词。"""
        text = "你好世界"
        tokens = self.extractor.word_tokens(text, 'zh')
        assert len(tokens) == 4
        assert '你' in tokens
        assert '好' in tokens
        assert '世' in tokens
        assert '界' in tokens

    def test_word_tokens_japanese(self):
        """测试日文分词。"""
        text = "こんにちは"
        tokens = self.extractor.word_tokens(text, 'ja')
        assert len(tokens) == 5

    def test_word_tokens_auto_detect(self):
        """测试自动语言检测分词。"""
        extractor = TextFeatureExtractor(lang='auto')
        text = "Hello world"
        tokens = extractor.word_tokens(text)
        assert len(tokens) > 0

    def test_compute_entropy(self):
        """测试信息熵计算。"""
        text = "abcdefgh"
        entropy = self.extractor.compute_entropy(text)
        assert entropy > 0
        assert entropy <= 8.0

    def test_compute_entropy_empty(self):
        """测试空文本熵计算。"""
        entropy = self.extractor.compute_entropy("")
        assert entropy == 0.0

    def test_compute_entropy_single_char(self):
        """测试单字符熵计算。"""
        entropy = self.extractor.compute_entropy("aaaaa")
        assert entropy == 0.0

    def test_semantic_seed_deterministic(self):
        """测试语义种子的确定性。"""
        text = "Test text for seed generation"
        seed1 = self.extractor.semantic_seed(text)
        seed2 = self.extractor.semantic_seed(text)
        assert seed1 == seed2

    def test_semantic_seed_length(self):
        """测试语义种子长度。"""
        text = "Test text"
        seed = self.extractor.semantic_seed(text)
        assert len(seed) == 32

    def test_semantic_seed_different_text(self):
        """测试不同文本生成不同种子。"""
        text1 = "Text one"
        text2 = "Text two"
        seed1 = self.extractor.semantic_seed(text1)
        seed2 = self.extractor.semantic_seed(text2)
        assert seed1 != seed2

    def test_semantic_seed_avalanche(self):
        """测试语义种子的雪崩效应。"""
        text1 = "Hello world"
        text2 = "Hello wordl"
        seed1 = self.extractor.semantic_seed(text1)
        seed2 = self.extractor.semantic_seed(text2)
        assert seed1 != seed2

    def test_detect_lang_english(self):
        """测试英文检测。"""
        text = "This is an English text."
        lang = self.extractor._detect_lang(text)
        assert lang == 'en'

    def test_detect_lang_chinese(self):
        """测试中文检测。"""
        text = "这是一段中文文本用于测试"
        lang = self.extractor._detect_lang(text)
        assert lang == 'zh'

    def test_detect_lang_empty(self):
        """测试空文本检测。"""
        lang = self.extractor._detect_lang("")
        assert lang == 'en'

    def test_char_distribution(self):
        """测试字符分布统计。"""
        text = "Hello 123 你好"
        dist = self.extractor._char_distribution(text)
        assert 'letters' in dist
        assert 'digits' in dist
        assert 'symbols' in dist
        assert 'spaces' in dist
        assert 'cjk' in dist
        assert dist['letters'] > 0
        assert dist['digits'] > 0
        assert dist['cjk'] > 0

    def test_char_distribution_empty(self):
        """测试空文本字符分布。"""
        dist = self.extractor._char_distribution("")
        assert dist['letters'] == 0.0
        assert dist['digits'] == 0.0
