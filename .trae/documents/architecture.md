# DataSci Projecter - 技术架构文档

## 一、技术选型

| 层级 | 技术方案 |
|------|----------|
| 前端框架 | React 18 + TypeScript |
| 构建工具 | Vite |
| 样式方案 | Tailwind CSS + CSS Variables |
| 动画库 | Framer Motion |
| 状态管理 | Zustand |
| 图表可视化 | Recharts |
| 图标库 | Lucide React |

---

## 二、项目结构

```
/workspace/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── components/
    │   ├── Layout/
    │   │   ├── Navbar.tsx
    │   │   ├── Sidebar.tsx
    │   │   └── StatusBar.tsx
    │   ├── Dashboard/
    │   │   ├── ProjectCard.tsx
    │   │   ├── ProjectDashboard.tsx
    │   │   └── StatsPanel.tsx
    │   ├── Generator/
    │   │   ├── TemplateMarket.tsx
    │   │   └── ProjectGenerator.tsx
    │   ├── Builder/
    │   │   ├── BuildConsole.tsx
    │   │   ├── BuildHistory.tsx
    │   │   └── ProjectBuilder.tsx
    │   └── Pusher/
    │       ├── RepoConfig.tsx
    │       ├── PushHistory.tsx
    │       └── ProjectPusher.tsx
    ├── store/
    │   └── projectStore.ts
    ├── types/
    │   └── index.ts
    └── utils/
        └── mockData.ts
```

---

## 三、核心模块设计

### 3.1 状态管理（Zustand Store）

```typescript
interface ProjectStore {
  projects: Project[];
  currentProject: Project | null;
  activeView: 'dashboard' | 'generator' | 'builder' | 'pusher';

  // Actions
  addProject: (project: Project) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  setCurrentProject: (project: Project | null) => void;
  setActiveView: (view: ViewType) => void;
  addBuildRecord: (projectId: string, record: BuildRecord) => void;
  addPushRecord: (projectId: string, record: PushRecord) => void;
}
```

### 3.2 视图路由

采用单页应用视图切换模式，无需 React Router：

| 视图 | 路由参数 | 描述 |
|------|----------|------|
| dashboard | 默认 | 项目仪表盘 |
| generator | ?view=generator | 项目生成器 |
| builder | ?view=builder | 构建中心 |
| pusher | ?view=pusher | 推送管理 |

---

## 四、数据流设计

```
用户操作 → 组件事件 → Zustand Action → State 更新 → UI 重渲染
                ↓
         LocalStorage 持久化
```

---

## 五、API 模拟

项目采用前端模拟数据，模拟以下行为：

| 行为 | 模拟方式 |
|------|----------|
| 项目生成 | setTimeout 2s 延迟，生成随机项目 ID |
| 构建流程 | setTimeout 3s 延迟，实时输出日志 |
| 推送操作 | setTimeout 1.5s 延迟，返回成功/失败状态 |

---

## 六、视觉实现

### 6.1 CSS 变量

```css
:root {
  --bg-primary: #0a0e17;
  --bg-secondary: #1a1a2e;
  --bg-card: #16213e;
  --accent-cyan: #00d4ff;
  --accent-orange: #ff6b35;
  --accent-purple: #a855f7;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --border-glow: rgba(0, 212, 255, 0.3);
}
```

### 6.2 动画规范

- 页面切换：fade + slide，300ms
- 卡片悬停：glow border + scale(1.02)，200ms
- 按钮点击：ripple effect，400ms
- 数据加载：skeleton + shimmer，infinite
- 进度更新：spring physics
