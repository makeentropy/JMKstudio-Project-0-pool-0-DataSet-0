"""文本隐写单元测试。"""
import pytest

from oath_toolchain.tools.steganography.text_stego import TextSteganography


class TestTextSteganography:
    """测试TextSteganography类。"""

    def setup_method(self):
        """每个测试前初始化。"""
        self.stego = TextSteganography()

    def test_init(self):
        """测试初始化。"""
        assert len(self.stego.ZERO_WIDTH_CHARS) == 2

    def test_embed_and_extract_whitespace(self):
        """测试空格隐写的嵌入和提取。"""
        lines = ["Line " + str(i) for i in range(100)]
        text = "\n".join(lines)
        secret = b"Hello"
        stego_text = self.stego.embed_whitespace(text, secret)
        extracted = self.stego.extract_whitespace(stego_text)
        assert extracted == secret

    def test_embed_whitespace_multiline(self):
        """测试多行文本空格隐写。"""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        text += "\n".join(["Extra " + str(i) for i in range(100)])
        secret = b"Hi"
        stego_text = self.stego.embed_whitespace(text, secret)
        extracted = self.stego.extract_whitespace(stego_text)
        assert extracted == secret

    def test_embed_whitespace_not_enough_lines(self):
        """测试行数不足时的空格隐写。"""
        text = "Line 1\nLine 2\nLine 3"
        secret = b"A" * 100
        with pytest.raises(ValueError):
            self.stego.embed_whitespace(text, secret)

    def test_embed_and_extract_unicode(self):
        """测试Unicode零宽字符隐写。"""
        text = "Hello world, this is a test text with many spaces. " * 20
        secret = b"Unicode Stego"
        stego_text = self.stego.embed_unicode(text, secret)
        extracted = self.stego.extract_unicode(stego_text)
        assert extracted == secret

    def test_embed_unicode_not_enough_spaces(self):
        """测试空格不足时的Unicode隐写。"""
        text = "nospaceshere"
        secret = b"data"
        with pytest.raises(ValueError):
            self.stego.embed_unicode(text, secret)

    def test_embed_and_extract_case(self):
        """测试大小写隐写。"""
        text = "The quick brown fox jumps over the lazy dog. " * 20
        secret = b"Case Test"
        stego_text = self.stego.embed_case(text, secret)
        extracted = self.stego.extract_case(stego_text)
        assert extracted == secret

    def test_embed_case_not_enough_letters(self):
        """测试字母不足时的大小写隐写。"""
        text = "1234567890!@#$%^&*()"
        secret = b"data"
        with pytest.raises(ValueError):
            self.stego.embed_case(text, secret)

    def test_capacity_whitespace(self):
        """测试空格隐写容量计算。"""
        text = "a\n" * 100
        cap = self.stego.capacity(text, "whitespace")
        assert cap > 0

    def test_capacity_unicode(self):
        """测试Unicode隐写容量计算。"""
        text = "a b c d e f g h i j k l m n o p q r s t u v w x y z " * 10
        cap = self.stego.capacity(text, "unicode")
        assert cap > 0

    def test_capacity_case(self):
        """测试大小写隐写容量计算。"""
        text = "abcdefghijklmnopqrstuvwxyz" * 10
        cap = self.stego.capacity(text, "case")
        assert cap > 0

    def test_capacity_invalid_method(self):
        """测试无效的隐写方法。"""
        with pytest.raises(ValueError):
            self.stego.capacity("text", "invalid")

    def test_capacity_zero(self):
        """测试容量为0的情况。"""
        text = "short"
        cap = self.stego.capacity(text, "case")
        assert cap == 0

    def test_embed_whitespace_invalid_text_type(self):
        """测试无效的文本类型。"""
        with pytest.raises(TypeError):
            self.stego.embed_whitespace(b"not str", b"data")

    def test_embed_whitespace_invalid_secret_type(self):
        """测试无效的秘密数据类型。"""
        with pytest.raises(TypeError):
            self.stego.embed_whitespace("text", "not bytes")

    def test_extract_whitespace_invalid_type(self):
        """测试提取时无效类型。"""
        with pytest.raises(TypeError):
            self.stego.extract_whitespace(b"not str")

    def test_extract_whitespace_insufficient_data(self):
        """测试提取时空格隐写数据不足。"""
        with pytest.raises(ValueError):
            self.stego.extract_whitespace("short")

    def test_extract_unicode_invalid_type(self):
        """测试Unicode提取时无效类型。"""
        with pytest.raises(TypeError):
            self.stego.extract_unicode(b"not str")

    def test_extract_unicode_insufficient_data(self):
        """测试Unicode提取时数据不足。"""
        with pytest.raises(ValueError):
            self.stego.extract_unicode("no hidden data")

    def test_embed_unicode_invalid_text_type(self):
        """测试Unicode隐写无效文本类型。"""
        with pytest.raises(TypeError):
            self.stego.embed_unicode(b"not str", b"data")

    def test_embed_case_invalid_text_type(self):
        """测试大小写隐写无效文本类型。"""
        with pytest.raises(TypeError):
            self.stego.embed_case(b"not str", b"data")

    def test_extract_case_invalid_type(self):
        """测试大小写提取无效类型。"""
        with pytest.raises(TypeError):
            self.stego.extract_case(b"not str")

    def test_extract_case_insufficient_data(self):
        """测试大小写提取数据不足。"""
        with pytest.raises(ValueError):
            self.stego.extract_case("ab")

    def test_capacity_invalid_text_type(self):
        """测试容量计算无效文本类型。"""
        with pytest.raises(TypeError):
            self.stego.capacity(b"not str")

    def test_bytes_to_bits_and_back(self):
        """测试字节和比特的转换。"""
        data = b"Hello, World!"
        bits = self.stego._bytes_to_bits(data)
        result = self.stego._bits_to_bytes(bits)
        assert result == data

    def test_int_to_bits_and_back(self):
        """测试整数和比特的转换。"""
        value = 12345
        bits = self.stego._int_to_bits(value, 32)
        result = self.stego._bits_to_int(bits)
        assert result == value

    def test_empty_secret(self):
        """测试嵌入空秘密数据。"""
        text = "Test text with enough spaces here okay. " * 20
        secret = b""
        stego_text = self.stego.embed_unicode(text, secret)
        extracted = self.stego.extract_unicode(stego_text)
        assert extracted == secret
