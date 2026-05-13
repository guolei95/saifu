# 赛赋 SaiFu 开发/生产环境分离规范

> 本文档是 AI 工作手册。每次涉及部署、发布、分支操作时必须遵守。

---

## 一、架构总览

```
dev 分支（草稿本）               main 分支（正式版）
┌─────────────────┐            ┌─────────────────┐
│ 本地 localhost   │  改好了   │ GitHub Pages     │
│ 随便改随便测     │──merge──→│ Render 云端      │
│ 改坏了不影响线上  │           │ 公众使用的稳定版  │
└─────────────────┘            └─────────────────┘
```

---

## 二、分支规则

| 分支 | 用途 | 部署位置 | 谁访问 |
|------|------|----------|--------|
| `dev` | 日常开发、新功能、修 bug | 本地 localhost | 只有开发者 |
| `main` | 稳定发布版 | GitHub Pages + Render | 所有用户 |

**铁律**：
- 永远在 `dev` 上改代码，**禁止直接在 main 上改**
- `main` 只接受来自 `dev` 的 merge
- 每次 merge 前必须在本地完整测试通过

---

## 三、日常开发流程

### 3.1 开始新功能

```powershell
# 确保在 dev 分支
git checkout dev

# 拉取最新代码（如果有远程 dev）
git pull origin dev
```

### 3.2 开发 + 测试

```powershell
# 1. 改代码（在 saifu/ 目录下随便改）

# 2. 启动本地后端测试
cd saifu\backend
python main.py
# 后端运行在 http://localhost:8000

# 3. 浏览器打开前端测试
# 直接打开 saifu/index.html（自动连 localhost:8000）
```

前端 `app.js` 中的环境判断逻辑（已内置，不用改）：
```javascript
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://saifu-backend-pk86.onrender.com';
```

### 3.3 提交到 dev

```powershell
git add <改动的文件>
git commit -m "描述改动内容"

# 推送到远程 dev 分支（备份 + 方便多设备同步）
git push origin dev
```

### 3.4 测试通过 → 发布到生产

```powershell
# 1. 切到 main
git checkout main
git pull origin main

# 2. 把 dev 的改动合并过来
git merge dev

# 3. 推送到远程（触发 Render 自动部署）
git push origin main

# 4. 切回 dev 继续开发
git checkout dev
```

---

## 四、Render 部署说明

- **服务地址**：`https://saifu-backend-pk86.onrender.com`
- **部署方式**：Render 监听 GitHub `main` 分支，push 后自动部署
- **环境变量**：在 Render Dashboard → saifu-backend → Environment 中配置
  - `LLM_API_KEY`：AI API 密钥
  - `FRONTEND_URL`：前端地址（可选，默认允许所有来源）
- **免费版限制**：15 分钟无请求会休眠，首次请求需冷启动（~30s）

---

## 五、前端部署说明

- **生产地址**：GitHub Pages（仓库 Settings → Pages 中配置）
- **部署方式**：push 到 main 后 GitHub Actions 自动构建部署
- **测试**：本地直接用浏览器打开 `index.html`，自动连 localhost 后端

---

## 六、首次初始化（新环境/新机器）

```powershell
# 1. 克隆仓库
git clone https://github.com/guolei95/saifu.git
cd saifu

# 2. 创建 dev 分支（基于 main）
git checkout -b dev
git push -u origin dev

# 3. 安装 Python 依赖
cd backend
pip install -r requirements.txt
```

---

## 七、注意事项

1. **密钥安全**：`.env` 文件不要提交到 Git
2. **dev 分支也推送**：`git push origin dev` 作为云端备份
3. **冲突处理**：如果 merge 时有冲突，在 main 分支上解决冲突后再 push
4. **回滚**：如果发布后发现问题，`git revert` 上一次 merge 的 commit
5. **前端改 API 地址**：如果 Render 后端地址变了，只需改 `app.js` 中的 `API_BASE`
