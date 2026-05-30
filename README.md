# CaseWise - 法律AI助手

基于 RAG（检索增强生成）的智能法律合规审查平台，提供法律问答、合同风险审查、复核反馈等核心功能。每条AI回答均附带法条引用与溯源校验，支持人工复核与合规声明。

## 核心功能

### 🤖 法律问答
- 基于 Hybrid RAG 的智能法律咨询（语义检索 + BM25关键词检索 + RRF融合排序）
- SSE 流式输出，实时渲染 Markdown 格式回答
- 法条引用卡片：自动附带关联法条，支持验证状态标识（已验证/待确认/无法验证）
- 合规声明：每条AI回答自动附加合规免责声明

### 📄 合同审查
- 支持 PDF/Word 文件上传，自动提取合同文本
- AI 自动识别风险条款，按风险等级（高/中/低）分类
- Word 文件 HTML 预览（iframe 渲染）
- 风险摘要 4TAB 展示（概览/高风险/中风险/低风险）
- 审查历史记录，支持回看历史审查详情

### ✅ 复核统计
- 采纳/误报一键标记，数据持久化到后端
- 复核统计汇总：确认数、误报数、采纳率
- 按来源类型（合同/问答）分组统计

### 📊 数据管理
- 法律数据采集：支持民法典、公司法、劳动合同法等多类法条
- ChromaDB 向量数据库 + BM25 关键词索引
- 采集进度实时监控

### 🔐 用户认证与权限
- JWT Token 认证，3种角色权限控制

| 角色 | 权限范围 |
|------|---------|
| **管理员** (admin) | 系统管理、模型配置、数据备份、全部功能 |
| **律师** (lawyer) | 数据抓取、合同审核、复核统计、法律问答 |
| **客户** (client) | 提交合同、法律问询、获取报告 |

- 角色菜单过滤：不同角色看到不同菜单项
- 路由守卫：无权限页面自动重定向
- 自助注册仅允许客户角色，管理员/律师由管理员创建

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Ant Design)         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ 首页 │ │ 问答 │ │ 合同 │ │ 复核 │ │ 数据 │ │ 登录 │ │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ │
│     └─────────┴────────┴────────┴────────┴────────┘     │
│                    Axios + Vite Proxy                    │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────┴────────────────────────────────┐
│                  Backend (FastAPI + Uvicorn)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Auth API │ │ Chat API │ │Contract  │ │ Review   │    │
│  │ 认证鉴权  │ │ 法律问答  │ │ 合同审查  │ │ 复核统计  │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       │            │            │            │           │
│  ┌────┴────────────┴────────────┴────────────┴─────┐    │
│  │              Service 业务逻辑层                    │    │
│  │  AuthService / ChatService / ContractService     │    │
│  └────┬────────────┬────────────┬────────────┬──────┘    │
│       │            │            │            │           │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐   │
│  │ JWT认证   │ │ RAG引擎   │ │ LLM抽象层 │ │ 溯源校验  │   │
│  │ bcrypt   │ │HybridRAG │ │OpenAI兼容 │ │Citation  │   │
│  └──────────┘ │BM25+RRF  │ │流式/非流式 │ │Verifier  │   │
│               └────┬─────┘ └────┬─────┘ └──────────┘   │
│                    │            │                        │
│  ┌─────────────────┴────────────┴──────────────────┐    │
│  │              Core 基础设施层                      │    │
│  │  EmbeddingService / ComplianceService            │    │
│  │  DataCollector / ChromaDB Client                 │    │
│  └──────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                     Data Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ SQLite   │  │ ChromaDB │  │ 文件存储   │              │
│  │ WAL模式   │  │ 向量数据库 │  │ uploads/ │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

## 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| FastAPI | Web 框架，异步 API |
| Uvicorn | ASGI 服务器 |
| OpenAI SDK (兼容) | 调用火山方舟大模型 |
| ChromaDB | 向量数据库（法条语义检索） |
| BM25 (rank-bm25) | 关键词检索（RRF融合排序） |
| SQLite (aiosqlite) | 关系型数据存储（WAL模式） |
| PyJWT + bcrypt | JWT认证 + 密码哈希 |
| Pydantic Settings | 配置管理 |
| markitdown | Word/PDF 文件解析 |

### 前端
| 技术 | 用途 |
|------|------|
| React 18 | UI 框架 |
| TypeScript | 类型安全 |
| Ant Design 5 | 组件库 |
| React Router 6 | 路由管理 |
| Axios | HTTP 客户端 |
| react-markdown | Markdown 渲染 |
| Vite | 构建工具 |

## 项目结构

```
CaseWise/
├── backend/
│   ├── app/
│   │   ├── api/                    # API 路由层
│   │   │   ├── auth.py             # 认证接口（登录/注册/用户管理）
│   │   │   ├── chat.py             # 法律问答接口（同步/SSE流式）
│   │   │   ├── contract.py         # 合同审查接口（上传/分析/历史）
│   │   │   ├── data.py             # 数据管理接口（采集/进度/状态）
│   │   │   └── review.py           # 复核统计接口（提交/统计）
│   │   ├── core/                   # 核心引擎层
│   │   │   ├── auth.py             # JWT + bcrypt 认证核心
│   │   │   ├── llm.py              # LLM 抽象层（OpenAI兼容格式）
│   │   │   ├── rag.py              # Hybrid RAG 引擎（BM25+向量+RRF）
│   │   │   ├── embedding.py        # Embedding 服务
│   │   │   ├── citation.py         # 法条引用溯源校验
│   │   │   ├── compliance.py       # 合规声明生成
│   │   │   ├── data_collector.py   # 法律数据采集器
│   │   │   └── chroma_client.py    # ChromaDB 客户端
│   │   ├── db/
│   │   │   └── database.py         # SQLite 数据库初始化与连接
│   │   ├── models/                 # Pydantic 数据模型
│   │   │   ├── user.py             # 用户模型（角色/登录/注册）
│   │   │   ├── chat.py             # 问答模型
│   │   │   ├── contract.py         # 合同模型
│   │   │   └── review.py           # 复核模型
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── auth_service.py     # 认证业务（注册/登录/权限）
│   │   │   ├── chat_service.py     # 问答业务（RAG检索+LLM生成）
│   │   │   ├── contract_service.py # 合同审查业务
│   │   │   └── review_service.py   # 复核统计业务
│   │   ├── config.py               # 配置管理（pydantic-settings）
│   │   └── main.py                 # FastAPI 应用入口
│   ├── data/                       # 数据目录（gitignore）
│   ├── uploads/                    # 上传文件目录（gitignore）
│   ├── logs/                       # 日志目录
│   ├── .env.example                # 环境变量模板
│   └── requirements.txt            # Python 依赖
├── frontend/
│   ├── src/
│   │   ├── components/             # 通用组件
│   │   │   ├── AppLayout.tsx       # 全局布局（侧边栏+顶栏+角色菜单过滤）
│   │   │   ├── ChatBubble.tsx      # 对话气泡（Markdown渲染）
│   │   │   ├── CitationCard.tsx    # 法条引用卡片
│   │   │   ├── ComplianceTag.tsx   # 合规声明标签
│   │   │   ├── ContractViewer.tsx  # 合同预览（iframe HTML）
│   │   │   ├── ReviewMark.tsx      # 复核标记组件（采纳/误报）
│   │   │   └── RiskCard.tsx        # 风险条款卡片
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx      # 认证上下文（全局状态+Token持久化）
│   │   ├── pages/                  # 页面组件
│   │   │   ├── LoginPage.tsx       # 登录/注册页
│   │   │   ├── HomePage.tsx        # 首页
│   │   │   ├── ChatPage.tsx        # 法律问答页
│   │   │   ├── ContractPage.tsx    # 合同审查页
│   │   │   ├── ReviewPage.tsx      # 复核统计页
│   │   │   └── DataPage.tsx        # 数据管理页
│   │   ├── services/
│   │   │   └── api.ts              # API 调用封装（含认证拦截器）
│   │   ├── types/
│   │   │   └── index.ts            # TypeScript 类型定义
│   │   ├── styles/
│   │   │   └── global.css          # 全局样式
│   │   ├── App.tsx                 # 应用根组件（路由+认证守卫）
│   │   └── main.tsx                # 入口文件
│   ├── index.html
│   ├── vite.config.ts              # Vite 配置（开发代理）
│   ├── package.json
│   └── tsconfig.json
├── scripts/                        # 数据初始化脚本
│   ├── seed_laws.py                # 法条数据种子
│   ├── seed_cases.py               # 案例数据种子
│   ├── seed_rules.py               # 规则数据种子
│   └── build_vector_db.py          # 向量数据库构建
├── .env.example                    # 根目录环境变量模板
├── .gitignore
├── LICENSE                         # Apache 2.0
└── README.md
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Conda（推荐）

### 1. 克隆项目

```bash
git clone https://github.com/chenzq1604/casewise.git
cd casewise
```

### 2. 后端配置

```bash
# 创建 Conda 环境
conda create -n casewise python=3.11 -y
conda activate casewise

# 安装依赖
cd backend
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 ARK_API_KEY（火山方舟 API Key）
```

### 3. 前端配置

```bash
cd frontend
npm install
```

### 4. 启动服务

```bash
# 启动后端（端口 6800）
cd backend
conda activate casewise
python -m uvicorn app.main:app --host 0.0.0.0 --port 6800

# 启动前端（端口 3000，自动代理到后端）
cd frontend
npm run dev
```

访问 http://localhost:3000 即可使用。

### 5. 默认账号

首次启动自动创建3个默认用户：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 律师 | lawyer | lawyer123 |
| 客户 | client | client123 |

> ⚠️ 生产环境请务必修改默认密码，并在 `.env` 中设置 `JWT_SECRET_KEY`。

## API 概览

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户登录 | 公开 |
| POST | `/api/auth/register` | 用户注册（仅客户） | 公开 |
| GET | `/api/auth/me` | 获取当前用户 | 已登录 |
| GET | `/api/auth/users` | 用户列表 | 管理员 |
| POST | `/api/chat` | 法律问答（同步） | 已登录 |
| POST | `/api/chat/stream` | 法律问答（SSE流式） | 已登录 |
| POST | `/api/contract/upload` | 上传合同 | 已登录 |
| POST | `/api/contract/analyze` | 分析合同风险 | 已登录 |
| GET | `/api/contract/history` | 审查历史 | 已登录 |
| GET | `/api/contract/detail/{id}` | 审查详情 | 已登录 |
| POST | `/api/review` | 提交复核反馈 | 已登录 |
| GET | `/api/review/stats` | 复核统计 | 已登录 |
| POST | `/api/data/collect` | 启动数据采集 | 律师/管理员 |
| GET | `/api/data/progress` | 采集进度 | 律师/管理员 |
| GET | `/api/data/status` | 数据状态 | 律师/管理员 |

## RAG 架构说明

CaseWise 采用三层 RAG 策略融合：

1. **Hybrid RAG**：语义检索（ChromaDB 向量相似度）+ BM25 关键词检索，通过 RRF（Reciprocal Rank Fusion）融合排序，兼顾语义理解和关键词精确匹配
2. **Parent-Child RAG**：使用小 chunk（laws_child）进行精确检索，返回大 chunk（laws_parent）作为上下文，解决上下文截断问题
3. **Self-RAG**：LLM 生成回答后，自动校验法条引用是否在法条库中真实存在，标注验证状态

```
用户提问 → Embedding → ChromaDB检索 + BM25检索 → RRF融合
                                                    ↓
                                          Parent-Child扩展上下文
                                                    ↓
                                              LLM生成回答
                                                    ↓
                                          法条引用溯源校验
                                                    ↓
                                          合规声明附加 → 返回
```

## 安全设计

- **JWT 认证**：Token 24小时过期，密钥自动生成或通过环境变量配置
- **bcrypt 哈希**：密码使用 bcrypt（rounds=10）哈希存储，异步执行避免阻塞
- **角色权限**：RBAC 模型，API 层通过 FastAPI 依赖注入校验
- **CORS 限制**：开发环境仅允许 localhost，生产环境需显式配置
- **输入验证**：Pydantic 模型校验所有请求参数
- **SQL 注入防护**：全程使用参数化查询
- **错误信息**：生产环境不泄露内部异常细节

## License

[Apache License 2.0](LICENSE)
