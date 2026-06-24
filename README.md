# Email AI Agent - 智能邮件助手

基于LLM的智能邮件代理服务，支持终端Shell交互和HTTP API两种模式。

## 功能特性

### 🤖 聊天智能体 (Chat Agent)
- 多会话管理
- 流式输出支持
- 支持多种LLM后端（OpenAI / DeepSeek / Ollama）
- 上下文记忆

### 📧 邮件智能体 (Email Agent)
- **邮件收发**：IMAP收邮件、SMTP发邮件
- **智能分析**：自动摘要、分类、优先级判断、关键信息提取
- **智能回复**：AI生成邮件回复
- **邮件撰写**：根据要点自动生成完整邮件
- **批量总结**：批量邮件智能分类总结
- **邮件搜索**：关键词搜索邮件

### 💻 终端Shell
- 交互式命令行界面
- Rich美化输出
- 命令自动补全
- 命令历史记录

### 🌐 HTTP Server
- RESTful API接口
- SSE流式输出
- CORS支持
- 完整的聊天和邮件API

## 项目结构

```
email_agent/
├── __init__.py              # 包入口
├── config.py                # 配置管理
├── email_service.py         # 邮件服务（IMAP/SMTP）
├── llm/                     # LLM模块
│   ├── __init__.py
│   ├── base.py              # LLM基类
│   ├── factory.py           # 工厂模式
│   ├── openai_client.py     # OpenAI客户端
│   ├── deepseek_client.py   # DeepSeek客户端
│   └── ollama_client.py     # Ollama本地模型
├── agent/                   # 智能体模块
│   ├── __init__.py
│   ├── chat_agent.py        # 聊天智能体
│   └── email_agent.py       # 邮件智能体
├── terminal/                # 终端界面
│   ├── __init__.py
│   └── shell.py             # Shell交互
└── server/                  # 服务端
    ├── __init__.py
    └── http_server.py       # HTTP服务
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

方式一：使用配置文件
```bash
cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml 填入你的配置
```

方式二：使用环境变量
```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

### 3. 运行

#### 终端Shell模式

```bash
python main.py shell
# 或直接运行
python main.py
```

#### HTTP服务模式

```bash
python main.py server
# 指定端口
python main.py server --port 8080
```

#### 查看状态

```bash
python main.py status
```

## 终端Shell命令

| 命令 | 说明 |
|------|------|
| `help` | 显示帮助信息 |
| `chat` | 进入聊天模式 |
| `inbox [N]` | 查看收件箱（最近N封） |
| `read <ID>` | 读取指定邮件 |
| `analyze <ID>` | 智能分析邮件 |
| `reply <ID> [指令]` | 回复邮件 |
| `compose` | 撰写新邮件 |
| `summarize [N]` | 总结最近N封邮件 |
| `status` | 查看系统状态 |
| `config` | 查看配置 |
| `clear` | 清屏 |
| `exit` | 退出 |

## HTTP API

### 健康检查
```
GET /api/health
```

### 聊天接口
```
GET    /api/chat/conversations          # 列出会话
POST   /api/chat/conversations          # 创建会话
DELETE /api/chat/conversations/<id>     # 删除会话
GET    /api/chat/conversations/<id>/messages  # 获取消息
POST   /api/chat/conversations/<id>/send      # 发送消息（支持SSE流式）
```

### 邮件接口
```
GET    /api/email/inbox                 # 收件箱列表
GET    /api/email/<id>                  # 邮件详情
GET    /api/email/<id>/analyze          # 智能分析
POST   /api/email/<id>/reply            # 生成/发送回复
POST   /api/email/send                  # 发送邮件
POST   /api/email/compose               # AI撰写邮件
GET    /api/email/summarize             # 批量总结
GET    /api/email/unread-count          # 未读数量
```

### 系统状态
```
GET /api/status
```

## 支持的LLM提供商

| 提供商 | 配置值 | 说明 |
|--------|--------|------|
| DeepSeek | `deepseek` | 默认，国内大模型 |
| OpenAI | `openai` | GPT系列 |
| Ollama | `ollama` | 本地开源模型 |

## 配置说明

### 邮箱配置 (yeah.net)
- IMAP服务器: `imap.yeah.net:993` (SSL)
- SMTP服务器: `smtp.yeah.net:465` (SSL)
- 密码建议使用客户端授权码而非登录密码

## License

MIT License
