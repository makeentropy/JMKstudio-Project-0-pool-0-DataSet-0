import type { Project, Template, ProjectTemplate } from '../types';

export const templates: Template[] = [
  {
    id: 'dataset-builder',
    name: '数据集构建',
    description: '基于 XOR 池化存储底座的生成式数据集构建系统',
    icon: 'Database',
    features: ['四级数据池', '元数据管理', '版本控制', '质量校验'],
  },
  {
    id: 'model-training',
    name: '模型训练',
    description: '端到端机器学习模型训练 Pipeline',
    icon: 'Brain',
    features: ['数据预处理', '模型编排', '超参调优', '结果可视化'],
  },
  {
    id: 'pipeline',
    name: 'Pipeline 工程',
    description: '模块化数据处理流水线框架',
    icon: 'GitBranch',
    features: ['节点编排', '流式处理', '错误重试', '监控告警'],
  },
  {
    id: 'xor-pool',
    name: 'XOR 池化存储',
    description: '基于 baseXOR 的纠删码分布式存储引擎',
    icon: 'HardDrive',
    features: ['XOR 纠删', '块设备抽象', '动态扩容', '故障恢复'],
  },
  {
    id: 'custom',
    name: '自定义项目',
    description: '从空白项目开始，自由定义结构',
    icon: 'Sparkles',
    features: ['完全自定义', '灵活配置', '一键初始化'],
  },
];

export const generateId = (): string => {
  return `proj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const createProject = (
  name: string,
  description: string,
  template: ProjectTemplate,
  driverConfig?: Project['driverConfig']
): Project => {
  return {
    id: generateId(),
    name,
    description,
    template,
    status: 'idle',
    driverConfig,
    createdAt: new Date(),
    updatedAt: new Date(),
    buildHistory: [],
    pushHistory: [],
  };
};

export const getTemplateById = (id: ProjectTemplate): Template | undefined => {
  return templates.find((t) => t.id === id);
};
