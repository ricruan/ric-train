# FastAPI AI 便捷开发脚手架 项目

TODO: 以后再写


## 常用命令备忘录
这是实际开发中打包镜像 部署docker容器时会用的命令  [wolin-ai:0.1.5] 镜像名和版本可自行修改 

``` bash 
docker build -t wolin-ai:0.1.10 .


docker save -o wolin-ai-0.1.10.tar wolin-ai:0.1.10


docker load -i wolin-ai-0.1.10.tar


docker run -p 8000:8000 --env-file .env -d -v ai_upload_volume:/app/uploads --name wolin-ai-0110 wolin-ai:0.1.10
docker run --name wolin-ai -p 8000:8000 --env-file .env --restart unless-stopped wolin-ai:0.1.10
```


  docker run -d \
  --name minio \
  --restart=unless-stopped \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER="xxx" \
  -e MINIO_ROOT_PASSWORD="xxxAr!" \
  -v minio_data:/data \
  minio/minio \
    server /data --address ":9000" --console-address ":9001"
  

uvicorn Wolin.main:app --host 0.0.0.0 --port 8001