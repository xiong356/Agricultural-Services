# 溪山农服（Agricultural Services）

面向农户的**拍照识病虫害 + 地块管理 + 农事预警**微信小程序，前后端一体。

## 项目结构

```
miniprogram/   微信小程序（原生 WXML/WXSS/JS + TDesign 组件库）
backend/       后端 API（Python + FastAPI + SQLite）
```

## 小程序端（miniprogram/）

- **5 个 Tab 页**：首页 / 识病中心 / 预警中心 / 地块列表 / 我的
- **流程页**：登录注册、拍照识病 → 识别结果、病虫害百科、地块添加/详情、病害历史
- 页面数据默认走 mock，对接后端时将 `require('../../mock/data')` 替换为 `require('../../services/xxx')`

### 启动步骤

1. 用微信开发者工具打开 `miniprogram/` 目录
2. 工具栏 → 「工具」→「构建 npm」（安装 TDesign 组件库）
3. 编译运行

## 后端（backend/）

技术栈：FastAPI + Uvicorn + SQLAlchemy + SQLite（开发环境）

- 病虫害识别：上传图片 → 调用硅基流动视觉大模型（Qwen-VL）→ 返回病害、严重度与防治建议
- 用户体系：JWT 登录 / 微信登录 / token 自动刷新
- 业务接口：地块管理、预警、病虫害百科、服务记录等（统一前缀 `/miniapp/v1`）

### 启动步骤

```bash
cd backend
python -m venv venv && source venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # 填入 SILICONFLOW_API_KEY
python app.py           # 默认 8000 端口
```

> 未配置 API Key 时，识别接口自动降级为模拟模式（延迟 2 秒返回 mock 结果）。

## 隐私说明

仓库不含任何真实密钥、数据库或用户数据。密钥通过 `backend/.env` 配置（已被 .gitignore 排除），模板见 `backend/.env.example`。
