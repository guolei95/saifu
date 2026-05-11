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

### 前端部署
| 平台 | 地址 | 国内访问 |
|------|------|---------|
| Vercel | `saifu-75e4.vercel.app` | ❌ 被墙 |
| Cloudflare Pages | `saifu.3359717058.workers.dev` | ❌ 也不通 |

### 域名
- 已购买 `saifu.asia`（阿里云，¥8/年）
- **审核状态**：注册局审核中（~8小时），审核通过会有短信通知
- **DNS 配了但指向错了**：之前指向 Vercel（76.76.21.21），需要改指向 Cloudflare Pages

### 后端
- 跑在本地电脑，Cloudflare Tunnel 暴露
- 隧道地址写在 `js/app.js` 的 `API_BASE_URL`
- 电脑重启后需重新启动并更新 app.js

---

## 下一个 AI 需要做的事

### 优先级 1：改 DNS 指向（让域名生效）

**任务**：帮用户在阿里云 DNS 解析中添加 CNAME 记录

**操作**：阿里云域名解析页面 → 添加记录：

| 记录类型 | 主机记录 | 记录值 |
|---------|---------|--------|
| CNAME | @ | saifu.3359717058.workers.dev |

> 注意：如果已有旧记录（指向 Vercel 的 A 记录）要先删掉。

**为什么**：域名审核通过后，DNS 指向 Cloudflare Pages，国内有可能访问。如果还不行，只能走阿里云 OSS + 备案。

### 优先级 2：恢复文件目录结构

用户最后要求把前端文件移回 `frontend/` 子目录。

当前结构（移动后，最后一次 commit `a137fba`）：
```
saifu/
├── index.html    ← 在根目录（不对）
├── css/          ← 在根目录（不对）
├── js/           ← 在根目录（不对）
├── images/       ← 在根目录（不对）
├── backend/
└── ...
```

需要恢复成：
```
saifu/
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── images/
├── backend/
└── ...
```

恢复后需 commit + push 到 GitHub。

### 优先级 3：手机端适配继续或放弃

- 上次已加了响应式 CSS（`@media max-width: 480px`），但用户要求恢复原样
- 恢复文件结构时不要丢掉已有的 CSS 改动（style.css 里的响应式规则保留）

---

## 已做操作记录

1. ✅ 手机端响应式 CSS 适配（style.css + index.html）
2. ✅ 购买域名 `saifu.asia`
3. ✅ 域名 DNS 配到 Vercel（76.76.21.21）
4. ✅ Cloudflare Pages 部署临时地址 `saifu.3359717058.workers.dev`
5. ✅ 文件结构调整：frontend/ 移到根目录（commit `a137fba`）
6. ❌ 国内访问：两个临时域名都不通
7. ❌ DNS 指向 Cloudflare Pages：还没改

---

## 关键文件路径

| 文件 | 路径 |
|------|------|
| 前端页面 | `saifu/index.html`（当前在根目录，需移回 frontend/） |
| 样式 | `saifu/css/style.css`（含响应式规则） |
| 逻辑 | `saifu/js/app.js` |
| 后端入口 | `saifu/backend/main.py` |
| 竞赛知识库 | `saifu/backend/data/84项A类竞赛知识库.json` |
| DNS 操作指南 | 本文档「优先级 1」章节 |
