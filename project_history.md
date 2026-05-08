# 项目修改记录 - 会话记录

## 会话概述

本次会话主要完成了以下任务：
1. 表格表头固定功能
2. 页面布局重构（StockList 左右面板对齐）
3. tsconfig 配置修复
4. 股票列表选中高亮功能
5. Git 部署配置（docker-compose.yml 修改）
6. post-receive hook 配置
7. 样式表颜色变量添加
8. 导航栏标题放大
9. stat-card 样式统一

---

## 1. 表格表头固定功能

### 修改文件
- `frontend/src/views/StockList.tsx`

### 修改内容
在 Table 组件上添加 `maxHeight` 限制表格高度：
```jsx
<div className="table-scroll" style={{ maxHeight: 'calc(100vh - 200px)' }}>
```

---

## 2. StockList 页面布局重构

### 问题
右侧面板顶部需要与左侧面板顶部对齐。

### 解决方案
重新划分 div 结构，让左右容器使用相同的 `card` + `card-header` 结构，自然对齐。

### 修改文件
- `frontend/src/views/StockList.tsx`

---

## 3. tsconfig 配置修复

### 问题
VS Code 提示 tsconfig.node.json 配置错误：
1. `may not disable emit`
2. `must have setting "composite": true`

### 解决方案
在 `tsconfig.node.json` 中：
- 添加 `composite: true`
- 移除 `noEmit: true`

### 修改文件
- `frontend/tsconfig.node.json`

---

## 4. Git 部署配置

### 修改 docker-compose.yml
改为挂载代码目录：

```yaml
services:
  frontend:
    image: nginx:alpine
    volumes:
      - /opt/stock-us-code/frontend:/usr/share/nginx/html
    ports:
      - "8081:80"

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - /opt/stock-us-code/backend:/app
      - ./data:/app/data
```

### 服务器端操作

**1. 创建 git 仓库：**
```bash
mkdir -p /opt/stock-us-code
cd /opt/stock-us-code
git init --bare
mkdir -p /opt/stock-us-code/checkout
```

**2. 创建 post-receive hook：**
```bash
vim /opt/stock-us-code/hooks/post-receive
```

内容：
```bash
#!/bin/bash
git --work-tree=/opt/stock-us-code/checkout --git-dir=/opt/stock-us-code checkout -f
```

**3. 添加执行权限：**
```bash
chmod +x /opt/stock-us-code/hooks/post-receive
```

**4. 首次推送：**
```bash
git add .
git commit -m "Initial commit"
git remote add production ssh://user@server:/opt/stock-us-code
git push production main
```

**5. 构建并启动容器：**
```bash
cd /opt/stock-us-code/checkout
docker-compose down
docker-compose up -d --build
```

### 修改文件
- `docker-compose.yml`

---

## 5. 股票列表选中高亮功能

### 功能
选中股票时，股票代码和名称变为指定颜色。

### 实现

**步骤1：** 在样式表添加选中颜色变量
```scss
--selected: #E9ECFC;
```

**步骤2：** 在 StockList 组件中应用颜色
```jsx
<td className="mono" style={{ color: selected === s.symbol ? 'var(--selected)' : 'var(--accent)' }}>
  {s.symbol}
</td>
<td style={{ color: selected === s.symbol ? 'var(--selected)' : undefined }}>
  {s.name || '-'}
</td>
```

### 修改文件
- `frontend/src/styles/index.scss`
- `frontend/src/views/StockList.tsx`

---

## 6. 导航栏标题放大

### 修改文件
- `frontend/src/App.tsx`

### 修改内容
放大标题、图标和副标题：
```jsx
<div className="sidebar-title" style={{ fontSize: 28, gap: 10 }}>
  <LineChart size={32} />
  {t('app.title')}
</div>
<div className="sidebar-subtitle" style={{ fontSize: 14 }}>
  {t('app.subtitle')}
</div>
```

### 效果
- 标题字体：16px → 28px（约 1.75 倍）
- 图标：18px → 32px（约 1.78 倍）
- 副标题：增加至 14px

---

## 7. stat-card 样式统一

### 问题
stats-grid 中各 stat-card 的值显示文字大小不一致。

### 解决方案
1. 统一样式表中的 `stat-value` 字体大小为 20px
2. 调整 StockList 页面 grid 布局为 `1fr 1fr 1fr 2fr`
3. 移除各实例中的内联 `style={{ fontSize: ... }}`

### 修改文件
- `frontend/src/styles/index.scss`
- `frontend/src/views/StockList.tsx`

### 样式表修改
```scss
.stat-card {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
  word-break: break-all;
}
```

### StockList 布局修改
```jsx
<div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr 2fr' }}>
```

---

## 修改文件清单

| 文件 | 修改类型 |
|------|----------|
| `frontend/src/views/StockList.tsx` | 布局重构 + 选中高亮 + stat 样式 |
| `frontend/src/views/AnalysisView.tsx` | table-card 样式 |
| `frontend/tsconfig.node.json` | 修复配置错误 |
| `frontend/src/styles/index.scss` | 颜色变量 + stat-card 样式 |
| `frontend/src/App.tsx` | 导航栏标题放大 |
| `docker-compose.yml` | git 部署配置 |




post-receive hook的作用是什么？

CodeBuddy
post-receive 是 Git hook 的一种，在 push 完成后自动执行。

作用流程：

code
你执行 git push → 服务器接收代码 → post-receive 自动触发 → 自动部署
本例中的具体操作：

bash
git --work-tree=/opt/stock-us-code/checkout --git-dir=/opt/stock-us-code checkout -f
把最新代码 checkout 到 checkout 目录，Docker 挂载的就是这个目录，所以推送后网站自动更新。

本质： 就是推送代码后自动运行一个脚本，省去手动部署。

<think>
The user is asking if doing docker-compose down and then up again after push is unnecessary. They're correct - since the code is mounted via volumes, there's no need to restart the containers after a push. They just need to refresh the browser for frontend, and optionally restart the backend container for Python code changes.
</think>

对，**完全多余**。

因为代码是挂载目录，`git push` 后代码已经更新到 `/opt/stock-us-code/checkout`，容器自动就能读到新代码。

**正确流程：**
```bash
git push production main
# 完成！不需要任何 docker 操作
```

前端直接刷新浏览器即可，后端如果有 Python 代码改动才需要：
```bash
docker-compose restart backend
```

`down` + `up` 只有在修改了 `Dockerfile` 或 `docker-compose.yml` 才需要。


<think>
用户问的是 docker-compose.yml 中是如何配置挂载代码的。让我看一下当前的 docker-compose.yml 配置。
</think>




II see. The user is asking how the containers mount the code. Let me explain the volumes configuration.
就是通过 `volumes` 配置实现的：

**前端 (nginx)：**
```yaml
volumes:
  - /opt/stock-us-code/frontend:/usr/share/nginx/html
```
把服务器上的 `/opt/stock-us-code/frontend` 映射到容器内的 `/usr/share/nginx/html`，nginx 就从那里读取静态文件。

**后端 (Python)：**
```yaml
volumes:
  - /opt/stock-us-code/backend:/app
  - ./data:/app/data
```
把服务器上的 `/opt/stock-us-code/backend` 映射到容器的 `/app`，Python 应用代码就在那里。

**格式：** `宿主机路径:容器内路径`

这样 git push 更新 `checkout` 目录后，容器立刻就能读到新代码。

<think>
用户在问如何把服务器上的路径映射到容器内的路径。用户在之前配置 docker-compose.yml 时已经设置了这个挂载，但用户想确认这步是怎么做的。

实际上这步不需要单独执行命令。当 docker-compose.yml 配置了 volumes 后，运行 `docker-compose up` 时 Docker 会自动处理挂载。

用户可能误解了，以为需要手动执行挂载命令。实际上 docker-compose.yml 中的 volumes 配置就是声明式地告诉 Docker 需要挂载什么。

我应该澄清：这不需要单独命令，只要 docker-compose.yml 配置正确，运行 `docker-compose up -d` 时 Docker 自动完成挂载。
</think>

不需要单独命令，这是在 `docker-compose.yml` 里配置的：

```yaml
services:
  frontend:
    volumes:
      - /opt/stock-us-code/frontend:/usr/share/nginx/html
```

只要 `docker-compose.yml` 里有这个配置，运行 `docker-compose up -d` 时 Docker **自动完成挂载**。

**总结流程：**
1. 修改 `docker-compose.yml` → 添加 volumes 配置
2. `docker-compose up -d` → Docker 读取配置并挂载

你之前做的第 1 步就是配置，第 2 步就是挂载生效。

新增文件：

frontend/src/i18n/index.ts - i18n 配置文件
frontend/src/i18n/en.ts - 英文翻译
frontend/src/i18n/zh.ts - 中文翻译
修改文件：

frontend/src/App.tsx - 添加语言切换按钮和国际化支持
frontend/src/main.tsx - 引入 i18n 配置
frontend/src/styles/index.scss - 添加语言切换按钮样式

 需要在 frontend 目录下安装依赖：

bash
cd frontend && npm install i18next react-i18next
然后右上角会出现一个语言切换按钮，点击可以在 "en" 和 "中文" 之间切换。