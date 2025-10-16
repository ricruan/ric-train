# FastAPI MySQL 项目

基于 FastAPI 和 MySQL 的 Web API 项目。

## 项目结构

```
pym/
├── main.py              # FastAPI 主应用
├── mysqlClient.py       # MySQL 客户端
├── .env                 # 环境变量配置
├── requirements.txt     # Python 依赖
├── Dockerfile          # Docker 镜像构建文件
├── docker-compose.yml  # Docker Compose 配置
├── .dockerignore       # Docker 忽略文件
├── init.sql            # 数据库初始化脚本
└── README.md           # 项目说明
```

## 快速开始

### 使用 Docker Compose（推荐）

1. 启动所有服务：
```bash
docker-compose up -d
```

2. 查看服务状态：
```bash
docker-compose ps
```

3. 查看日志：
```bash
docker-compose logs -f app
```

4. 停止服务：
```bash
docker-compose down
```

### 仅构建应用镜像

1. 构建镜像：
```bash
docker build -t pym-app .
```

2. 运行容器（需要外部 MySQL）：
```bash
docker run -d \
  --name pym-app \
  -p 8000:8000 \
  -e DB_HOST=your_mysql_host \
  -e DB_PORT=3306 \
  -e DB_USER=your_user \
  -e DB_PASSWORD=your_password \
  -e DB_NAME=worlin \
  pym-app
```

## API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| DB_HOST | MySQL 主机地址 | localhost |
| DB_PORT | MySQL 端口 | 3306 |
| DB_USER | MySQL 用户名 | root |
| DB_PASSWORD | MySQL 密码 | root |
| DB_NAME | 数据库名 | worlin |
| DB_CHARSET | 字符集 | utf8mb4 |

## 开发说明

### 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动开发服务器：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 数据库连接

确保 MySQL 服务正在运行，并且配置了正确的连接参数。

## 注意事项

1. 生产环境请修改默认密码
2. 根据实际需求调整 `init.sql` 中的表结构
3. 建议使用环境变量管理敏感信息
4. 定期备份数据库数据