# DataSci Projecter - 产品需求文档

## 一、产品概述

**产品名称**：DataSci Projecter（数据科学项目工程管理器）

**核心定位**：基于数据科学项目工程管理思维的全链路项目生命周期管理平台，覆盖「生成→编码→构建→推送」四大核心阶段，为数据科学团队提供一站式工程化协作工具。

**目标用户**：数据科学工程师、MLOps 团队、研究型开发者

---

## 二、核心功能需求

### 2.1 项目生成（Generate Projects）

| 功能点 | 描述 |
|--------|------|
| 模板市场 | 提供多种项目模板（数据集构建、模型训练、Pipeline 工程、XOR 池化存储等） |
| 快速初始化 | 基于模板一键生成项目结构，包含标准目录、配置文件、依赖声明 |
| 元数据配置 | 设置项目名称、描述、标签、版本、作者等基础信息 |
| 驱动层配置 | 支持配置 XOR POOL、baseXOR 等底层存储驱动参数 |

### 2.2 编码项目与项目管理（Coding Projects & Projecter）

| 功能点 | 描述 |
|--------|------|
| 项目仪表盘 | 可视化展示所有项目状态、进度、资源占用 |
| 文件浏览器 | 树形结构展示项目目录，支持代码文件预览 |
| 多项目管理 | 统一界面管理多个并行项目，支持分组、筛选、搜索 |
| 项目卡片 | 展示项目核心信息：名称、状态、最后修改、负责人 |

### 2.3 构建项目与构建器（Build Projects & Builder）

| 功能点 | 描述 |
|--------|------|
| 一键构建 | 触发项目构建流程，自动执行依赖安装、编译、打包 |
| 构建日志 | 实时展示构建过程日志，支持展开/折叠、搜索筛选 |
| 构建历史 | 记录每次构建的时间、状态、产物、耗时 |
| 缓存管理 | 支持构建缓存配置，加速增量构建 |

### 2.4 推送项目（Push Projects）

| 功能点 | 描述 |
|--------|------|
| 仓库配置 | 配置远程仓库地址（Git、Artifact Registry） |
| 推送历史 | 记录推送时间、目标仓库、版本标签 |
| 自动化推送 | 支持构建成功后自动推送到指定仓库 |
| 推送产物管理 | 管理已推送的版本产物、可追溯可回滚 |

---

## 三、视觉与交互需求

### 3.1 视觉风格

- **设计语言**：深邃科技感 + 精密工程美学，融合深空灰与荧光数据流
- **主色调**：深色背景（#0a0e17）配合霓虹蓝（#00d4ff）和警示橙（#ff6b35）
- **辅助色**：暗紫色渐变（#1a1a2e → #16213e）作为卡片背景
- **字体**：JetBrains Mono（代码/数据）+ Outfit（UI 标题）
- **动效**：霓虹光晕、微光呼吸、数据流动画、流畅过渡

### 3.2 布局结构

```
┌─────────────────────────────────────────────────────┐
│  顶部导航栏（Logo / 功能切换 / 用户信息）            │
├───────────┬─────────────────────────────────────────┤
│           │                                         │
│  侧边栏   │         主内容区                         │
│  项目列表 │  (根据功能展示不同内容)                   │
│           │                                         │
├───────────┴─────────────────────────────────────────┤
│  底部状态栏（构建状态 / 推送状态 / 系统信息）         │
└─────────────────────────────────────────────────────┘
```

### 3.3 交互规范

- 卡片悬停：发光边框 + 微缩放（scale: 1.02）
- 按钮点击：脉冲波纹 + 颜色渐变
- 数据加载：骨架屏 + 流光动画
- 状态切换：平滑过渡（300ms ease-out）
- 拖拽排序：镜像预览 + 阴影轨迹

---

## 四、数据模型

### 4.1 项目（Project）

```typescript
interface Project {
  id: string;
  name: string;
  description: string;
  template: 'dataset-builder' | 'model-training' | 'pipeline' | 'xor-pool' | 'custom';
  status: 'idle' | 'generating' | 'coding' | 'building' | 'pushing' | 'completed' | 'error';
  driverConfig?: DriverConfig;
  createdAt: Date;
  updatedAt: Date;
  buildHistory: BuildRecord[];
  pushHistory: PushRecord[];
}
```

### 4.2 构建记录（BuildRecord）

```typescript
interface BuildRecord {
  id: string;
  projectId: string;
  status: 'success' | 'failed' | 'in-progress';
  logs: string;
  duration: number;
  artifacts: string[];
  timestamp: Date;
}
```

### 4.3 推送记录（PushRecord）

```typescript
interface PushRecord {
  id: string;
  projectId: string;
  targetRepo: string;
  version: string;
  status: 'success' | 'failed';
  timestamp: Date;
}
```

---

## 五、验收标准

1. ✅ 项目生成：可选择模板并成功生成项目结构
2. ✅ 项目管理：可在仪表盘查看、新建、删除项目
3. ✅ 构建功能：点击构建按钮可触发模拟构建流程并显示日志
4. ✅ 推送功能：可配置仓库并执行模拟推送
5. ✅ 视觉体验：深色科技风格，动画流畅，交互响应及时
6. ✅ 响应式：支持桌面端主流分辨率（1920×1080+）
