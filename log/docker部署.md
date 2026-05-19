# Docker 部署

---

**用户**: 在帮我回顾一下，这个项目我如果要部署到服务器docker，忽略的node_modules文件夹和数据库有没有必要上传或者应不应该上传？

**AI**: 看看当前 Dockerfile 的配置。

[查看了 Dockerfile、Dockerfile.frontend、docker-compose.yml]

当前 Dockerfile 已经做到了正确分离，不需要额外改动：

### 现状分析

#### ✅ node_modules — 不需要上传，当前已经是正确的

`Dockerfile.frontend` 采用 **多阶段构建**：

```dockerfile
# 构建阶段：安装依赖、编译
FROM node:20 AS build
COPY frontend/package*.json ./
RUN npm install && npm run build    # ← node_modules 只在这里存在

# 运行阶段：只拷贝编译产物
FROM nginx:alpine
COPY --from=0 /app/dist /usr/share/nginx/html  # ← 只拷贝构建后的静态文件
```

`node_modules` 只在构建容器中存在，**不会进入最终镜像**，`.gitignore` 中也已排除。

#### ✅ SQLite 数据库 — 不需要打包进镜像，当前已经正确处理

`docker-compose.yml` 用 **卷挂载** 分离了数据：

```yaml
volumes:
  - ./data:/app/data # ← 宿主机 data/ 目录挂载到容器内
```

- 数据库文件 **留在宿主机**，不在镜像中
- 容器重启数据不丢失
- 多个容器可共用（如果需要）
- `.gitignore` 中已排除 `data/*.db`

### 总结

| 项目             | 当前处理                                  | 评价    |
| ---------------- | ----------------------------------------- | ------- |
| `node_modules`   | `.gitignore` 排除 + Docker 内 npm install | ✅ 正确 |
| `data/*.db`      | `.gitignore` 排除 + Docker volume 挂载    | ✅ 正确 |
| `backend/` 源码  | COPY 进镜像                               | ✅ 必须 |
| `frontend/` 源码 | 构建阶段 COPY，产物进 nginx               | ✅ 必须 |
| `config.yaml`    | volume 挂载（可外部修改）                 | ✅ 正确 |

**你现在的 Docker 部署方案已经是最佳实践了，不需要改动任何东西。** 只要你构建镜像时 `.dockerignore` 也加上 `data/` 和 `node_modules/`（当前已有 `.dockerignore`），build context 就不会包含这些大文件，构建速度也更快。

---

**用户**: 在服务器上创建并启动容器的命令

**AI**: 在服务器上，依次执行：

### 1. 上传代码到服务器

```bash
# 先把代码传到服务器（本地执行）
scp -r /path/to/project user@your-server:/opt/stock-us
```

### 2. SSH 登录服务器

```bash
ssh user@your-server
cd /opt/stock-us
```

### 3. 构建并启动

```bash
# 构建镜像 + 后台启动
docker compose up -d --build
```

### 4. 验证

```bash
# 查看容器状态
docker compose ps

# 查看日志（按需）
docker compose logs -f backend
docker compose logs -f frontend
```

### 5. 日常管理

```bash
# 停止
docker compose down

# 重启
docker compose restart

# 更新代码后重新部署
git pull
docker compose up -d --build

# 清理旧镜像（可选）
docker image prune -f
```

**部署后访问**：`http://你的服务器IP` → 前端（80端口）
**API**：`http://你的服务器IP:8777`

> 首次启动 `docker compose up -d --build` 会自动执行所有步骤：安装 Python 依赖、编译前端、启动 Nginx + FastAPI。数据库会通过 volume 持久化在 `./data/` 目录。

---

**用户**: 修改dev-tools的构件项目目录结构图的代码，加入生成graph样式的选项

**AI**: [添加了 format_graph 函数并注册到 _FORMATTERS 中]

`graph` 格式已恢复，可选样式共 4 种：

```
--format mindmap   → 思维导图（默认）
--format graph     → 连线图 ← 新增
--format list      → Markdown 嵌套列表
--format plain     → 纯文本树
```

示例文件已生成：`devtools/STRUCTURE_graph.md`。

---

**用户**: failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory

**AI**: 这个错误说明 Windows 上没有 Unix socket，Docker Desktop 用的是命名管道。先检查 Docker 安装状态。

[尝试执行 docker info]

---

**用户**: 这是在linux上执行时提示的

**AI**: 这个错误说明 **服务器上没有安装 Docker** 或 Docker 守护进程未运行。这是服务器环境的问题，需要你在服务器上操作。

### 排查步骤

登录服务器，依次执行：

```bash
# 1. 检查 Docker 是否安装
which docker
# 或
docker --version

# 2. 检查 Docker 守护进程是否运行
sudo systemctl status docker

# 3. 查看 Docker socket 是否存在
ls -la /var/run/docker.sock
```

### 常见原因及对应操作

| 原因                       | 操作                                                                                |
| -------------------------- | ----------------------------------------------------------------------------------- |
| **Docker 未安装**          | `sudo apt install docker.io`（Ubuntu/Debian）或 `sudo yum install docker`（CentOS） |
| **Docker 已安装但未启动**  | `sudo systemctl start docker`                                                       |
| **当前用户不在 docker 组** | `sudo usermod -aG docker $USER` 然后重新登录 (`newgrp docker`)                      |
| **SELinux 阻止**           | 检查 SELinux 状态：`getenforce`                                                     |
| **Docker 刚安装完需重启**  | `sudo systemctl enable docker && sudo systemctl restart docker`                     |

### 免 Docker 替代方案

如果服务器不适合装 Docker，也可以直接运行：

```bash
# 1. 安装 Python 依赖
uv sync

# 2. 启动后端
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8777

# 3. 安装前端依赖并构建
cd frontend
npm install
npm run build

# 4. 用 nginx 或简单 serve 托管前端
npx serve dist -l 80
```

---

**用户**: ls -la /var/run/docker.sock
ls: cannot access '/var/run/docker.sock': No such file or directory

**AI**: Docker 未运行或未安装。继续排查：

```bash
# 检查 Docker 是否安装
which docker && docker --version

# 检查 Docker 服务状态
sudo systemctl status docker

# 如果 systemctl 不可用（如某些最小化系统）
sudo service docker status

# 查看已安装的 docker 相关包
dpkg -l | grep docker
```

把这几条命令的结果发给我，我帮你判断下一步怎么做。

---

**用户**: sudo service docker status
Redirecting to /bin/systemctl status docker.service
○ docker.service - Docker Application Container Engine
Loaded: loaded (/usr/lib/systemd/system/docker.service; disabled; preset: disabled)
Active: inactive (dead)
TriggeredBy: ○ docker.socket
Docs: https://docs.docker.com

**AI**: Docker 已安装但未启动。在服务器上执行：

```bash
# 启动 Docker
sudo systemctl start docker

# 验证
sudo systemctl status docker

# 设置开机自启（可选）
sudo systemctl enable docker
```

启动后回到项目目录重新执行 `docker compose up -d --build` 即可。

---

**用户**: build成功后就运行了吗

**AI**: 是的。`docker compose up -d --build` 做了三件事：

1. **构建**镜像（如果代码有变化）
2. **启动**容器（backend + frontend）
3. **后台运行**（`-d` = detach）

你不需要任何额外命令。验证是否正常运行：

```bash
# 查看容器状态
docker compose ps

# 查看实时日志（按 Ctrl+C 退出）
docker compose logs -f

# 测试 API 是否响应
curl http://localhost:8777/health
```

如果 `docker compose ps` 显示两个容器都是 `Up` 状态，就说明运行成功了。

---

**用户**: 把自：“在帮我回顾一下，这个项目我如果要部署到服务器docker，忽略的node_modules文件夹和数据库有没有必要上传或者应不应该上传？” 以下（包含这句）的聊天记录原封不变的存为一个文档，名字叫"docker部署"

**AI**: [已生成 docker部署.md]
