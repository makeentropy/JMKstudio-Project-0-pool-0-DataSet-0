# Tasks

- [x] Task 1: 创建项目目录结构与基础配置文件
  - [x] SubTask 1.1: 创建 engineer-framework 主目录
  - [x] SubTask 1.2: 初始化 package.json 或 pyproject.toml
  - [x] SubTask 1.3: 创建基础配置文件

- [x] Task 2: 实现 hex_toolchain 工具链模块
  - [x] SubTask 2.1: 实现 Base16/32/64 编码解码器
  - [x] SubTask 2.2: 实现 XOR 运算工具
  - [x] SubTask 2.3: 实现 boost container 容器类

- [x] Task 3: 实现 compression_dict 压缩字典模块
  - [x] SubTask 3.1: 实现字典加载器
  - [x] SubTask 3.2: 实现压缩算法
  - [x] SubTask 3.3: 实现解压缩算法

- [x] Task 4: 实现串口工具 serial_port 模块
  - [x] SubTask 4.1: 实现串口连接管理
  - [x] SubTask 4.2: 实现数据收发接口
  - [x] SubTask 4.3: 实现配置管理

- [x] Task 5: 实现串口信号模拟器 signal_simulator
  - [x] SubTask 5.1: 实现脚本模板解析器
  - [x] SubTask 5.2: 实现信号响应引擎
  - [x] SubTask 5.3: 实现载点挂载机制

- [x] Task 6: 实现模型式补件生成池虚拟机 component_pool_vm
  - [x] SubTask 6.1: 实现种子标注器
  - [x] SubTask 6.2: 实现块生成器
  - [x] SubTask 6.3: 实现向量空间与 size 编码

- [x] Task 7: 实现有线连接脚本映射模拟引擎
  - [x] SubTask 7.1: 实现线连脚本解析器
  - [x] SubTask 7.2: 实现 XORtag pool 宏处理
  - [x] SubTask 7.3: 实现映射模拟器

- [x] Task 8: 编写单元测试与集成测试
  - [x] SubTask 8.1: 为 hex_toolchain 编写测试
  - [x] SubTask 8.2: 为 serial_port 编写测试
  - [x] SubTask 8.3: 为 component_pool_vm 编写测试

# Task Dependencies
- Task 2, 3, 4, 5 可并行开发
- Task 6 依赖 Task 2, 3 的完成
- Task 7 依赖 Task 5 的完成
- Task 8 依赖 Task 1-7 的完成
