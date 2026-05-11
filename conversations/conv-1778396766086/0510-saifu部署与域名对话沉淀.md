# Saifu 部署与域名 — 对话沉淀

> 日期：2026-05-10  
> 用途：下一轮对话快速接手

---

## 项目概况

- **项目名**：赛赋 SaiFu — 智能竞赛匹配
- **GitHub**：`guolei95/saifu`
- **本地路径**：`D:\我的竞赛项目-AI赋能竞赛系统\saifu\`
- **技术栈**：纯 HTML + CSS + JS（Vanilla），后端 Python FastAPI
- **前后端分离**：前端部署到云端，后端跑在本地电脑 + Cloudflare Tunnel

---

## 当前状态

### 前端
| 平台 | 地址 | 状态 |
|------|------|------|
| Vercel | `saifu-75e4.vercel.app` | ❌ 国内被墙 |
| Cloudflare Pages | `saifu.3359717058.workers.dev` | ⚠️ 手机流量加载错误 |

### 后端
- 跑在本地电脑，通过 Cloudflare Tunnel 暴露（`trycloudflare.com`）
- 隧道地址写在 `frontend/js/app.js` 的 `API_BASE_URL` 里
- 电脑重启后隧道地址会变，需重新启动并更新 `app.js`

### 域名
- 已购买 `saifu.asia`（阿里云，¥8/年）
- 已添加 DNS 解析到 Vercel（A 记录 → 76.76.21.21）
- **审核状态**：阿里云注册局审核中（预计 ~8 小时）
- 已收到短信通知审核中

---

## 本次对话操作记录

### 1. 手机端适配（已做 ✅）
- 在 `style.css` 末尾加了 `@media (max-width: 480px)` 响应式规则
- 在 `index.html` 内联样式的 `@media (max-width: 600px)` 中修正了 `.option-tag` 触摸尺寸
- **效果**：电脑端不受影响，手机端卡片不溢出、按钮好按

### 2. 前端文件结构调整（最后一次 commit）
- 把 `frontend/index.html`、`frontend/css/`、`frontend/js/`、`frontend/images/` 移动到了仓库根目录
- 目的：让 Cloudflare Pages 能找到 `index.html`（默认在根目录找）
- 已 commit 并 push 到 GitHub main 分支
- **Commit**：`a137fba` — "fix: 移动前端文件到根目录，适配 Cloudflare Pages 自动部署"

### 3. 当前文件结构
```
saifu/ (GitHub 仓库根目录)
├── index.html          ← 移动上来的
├── css/style.css       ← 移动上来的
├── js/app.js           ← 移动上来的
├── images/wechat-qr.jpg ← 移动上来的
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── data/84项A类竞赛知识库.json
│   ├── services/
│   │   ├── ai_client.py
│   │   ├── knowledge_base.py
│   │   ├── search.py
│   │   └── validation.py
│   └── match/
│       └── engine.py
├── Procfile
├── vercel.json
├── cloudflared.exe
└── .gitignore
```

---

## 待解决的问题

1. **国内访问**：Vercel `.vercel.app` 域名被墙，Cloudflare Pages 加载似乎也有问题
2. **域名绑定**：等 `saifu.asia` 审核通过后绑定（Vercel 或 Cloudflare）
3. **后端持续运行**：电脑关机就停，需考虑免费云部署（Railway/Render）
4. **wrangler.toml**：Cloudflare Pages 部署时检测到 wrangler，可能需清理无关配置

---

## ⚠️ 用户要求

用户最后说手机适配暂时放弃，要求**把改动恢复原样**（即把 index.html/css/js/images 移回 `frontend/` 子目录）。这个操作还没做——下一个聊天框接手时需要处理。

---

## 关键文件路径

| 文件 | 路径 |
|------|------|
| 前端页面 | `saifu/frontend/index.html`（原始位置） |
| 样式 | `saifu/frontend/css/style.css` |
| 逻辑 | `saifu/frontend/js/app.js` |
| 后端入口 | `saifu/backend/main.py` |
| 竞赛知识库 | `saifu/backend/data/84项A类竞赛知识库.json` |
