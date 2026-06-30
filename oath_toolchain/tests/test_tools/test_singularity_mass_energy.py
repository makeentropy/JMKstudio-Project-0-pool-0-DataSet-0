"""数据质能计算模型单元测试。"""
import pytest
import math

from oath_toolchain.tools.singularity.mass_energy import DataMassEnergy


class TestDataMassEnergy:
    """测试DataMassEnergy类。"""

    def test_init_with_bytes(self):
        """测试使用bytes初始化。"""
        data = b"test data"
        me = DataMassEnergy(data)
        assert me.data == data

    def test_init_invalid_type(self):
        """测试无效类型初始化。"""
        with pytest.raises(TypeError):
            DataMassEnergy("not bytes")

    def test_empty_data(self):
        """测试空数据计算。"""
        me = DataMassEnergy(b"")
        result = me.to_dict()
        assert result['data_mass'] == 0.0
        assert result['data_energy'] == 0.0
        assert result['entropy'] == 0.0
        assert result['density'] == 0.0
        assert result['complexity'] == 0.0
        assert result['byte_length'] == 0

    def test_uniform_data_entropy(self):
        """测试均匀分布数据的熵值。"""
        data = bytes(range(256))
        me = DataMassEnergy(data)
        assert 7.5 <= me.entropy <= 8.0

    def test_single_byte_entropy(self):
        """测试单字节数据的熵值。"""
        data = b'\x00' * 100
        me = DataMassEnergy(data)
        assert me.entropy == 0.0

    def test_random_data_entropy(self):
        """测试随机数据的熵值。"""
        import os
        data = os.urandom(256)
        me = DataMassEnergy(data)
        assert me.entropy > 5.0
        assert me.entropy <= 8.0

    def test_data_mass_normalization(self):
        """测试数据质量归一化。"""
        data_1 = b'a' * 10
        data_2 = b'a' * 1000
        me1 = DataMassEnergy(data_1)
        me2 = DataMassEnergy(data_2)
        assert me1.data_mass < me2.data_mass
        assert 0.0 <= me1.data_mass <= 1.0
        assert 0.0 <= me2.data_mass <= 1.0

    def test_data_energy(self):
        """测试数据能量计算。"""
        import os
        data = os.urandom(100)
        me = DataMassEnergy(data)
        assert 0.0 < me.data_energy <= 1.0

    def test_mass_energy_ratio(self):
        """测试质能比计算。"""
        import os
        data = os.urandom(100)
        me = DataMassEnergy(data)
        assert me.mass_energy_ratio > 0.0

    def test_density_calculation(self):
        """测试信息密度计算。"""
        data = bytes(range(256))
        me = DataMassEnergy(data)
        assert 0.8 <= me.density <= 1.0

    def test_complexity_single_byte(self):
        """测试单字节复杂度。"""
        data = b'\x00' * 100
        me = DataMassEnergy(data)
        assert me.complexity < 0.3

    def test_complexity_random(self):
        """测试随机数据复杂度。"""
        import os
        data = os.urandom(100)
        me = DataMassEnergy(data)
        assert me.complexity > 0.3

    def test_to_dict_structure(self):
        """测试to_dict返回结构。"""
        me = DataMassEnergy(b"test")
        result = me.to_dict()
        assert 'data_mass' in result
        assert 'data_energy' in result
        assert 'mass_energy_ratio' in result
        assert 'entropy' in result
        assert 'density' in result
        assert 'complexity' in result
        assert 'byte_length' in result

    def test_calculate_returns_dict(self):
        """测试calculate方法返回字典。"""
        me = DataMassEnergy(b"test")
        result = me.calculate()
        assert isinstance(result, dict)
        assert 'entropy' in result

    def test_high_density_data(self):
        """测试高密度数据。"""
        data = bytes(range(256)) * 4
        me = DataMassEnergy(data)
        assert me.density > 0.8

    def test_low_density_data(self):
        """测试低密度数据。"""
        data = b'\x00\x01' * 50
        me = DataMassEnergy(data)
        assert me.density < 0.5

    def test_mass_energy_imbalance(self):
        """测试质能比在不同数据中的差异。"""
        data_low_entropy = b'\x00' * 100
        data_high_entropy = bytes(range(256))
        me_low = DataMassEnergy(data_low_entropy)
        me_high = DataMassEnergy(data_high_entropy)
        assert me_low.mass_energy_ratio < me_high.mass_energy_ratio

    def test_complexity_increases_with_diversity(self):
        """测试复杂度随多样性增加而增加。"""
        data_simple = b'\x00' * 100
        data_complex = bytes(range(256))
        me_simple = DataMassEnergy(data_simple)
        me_complex = DataMassEnergy(data_complex)
        assert me_simple.complexity < me_complex.complexity

    def test_single_byte_data(self):
        """测试单字节数据。"""
        me = DataMassEnergy(b'\x42')
        assert me.data_mass > 0.0
        assert me.entropy == 0.0
        assert me.complexity >= 0.0

    def test_two_byte_data(self):
        """测试两字节数据。"""
        me = DataMassEnergy(b'\x00\x01')
        assert me.entropy == 1.0
        assert me.density == 1.0 / 8.0
