import os
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

class MinioClient:
    def __init__(self, endpoint: str = None, access_key: str = None, secret_key: str = None, secure=False):
        """
        初始化 Minio 客户端
        :param endpoint: Minio 服务地址 (例如: '127.0.0.1:9000' 或 'play.min.io')
        :param access_key: 访问密钥
        :param secret_key: 私有密钥
        :param secure: 是否使用 HTTPS (默认为 False)
        """
        self.endpoint = endpoint
        try:
            self.client = Minio(
                endpoint=endpoint or os.getenv('MINIO_ENDPOINT'),
                access_key=access_key or os.getenv('MINIO_ACCESS_KEY'),
                secret_key=secret_key or os.getenv('MINIO_SECRET_KEY'),
                secure=secure
            )
            print(f"[*] Minio 客户端连接成功: {endpoint}")
        except Exception as e:
            print(f"[!] Minio 连接失败: {e}")

    # ==========================
    # Bucket (存储桶) 操作
    # ==========================

    def bucket_exists(self, bucket_name):
        """检查桶是否存在"""
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error as e:
            print(f"[!] 检查桶存在失败: {e}")
            return False

    def make_bucket(self, bucket_name):
        """创建桶"""
        try:
            if not self.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                print(f"[*] 桶 '{bucket_name}' 创建成功")
                return True
            else:
                print(f"[*] 桶 '{bucket_name}' 已存在")
                return True
        except S3Error as e:
            print(f"[!] 创建桶失败: {e}")
            return False

    def remove_bucket(self, bucket_name):
        """删除桶 (桶必须为空)"""
        try:
            self.client.remove_bucket(bucket_name)
            print(f"[*] 桶 '{bucket_name}' 删除成功")
            return True
        except S3Error as e:
            print(f"[!] 删除桶失败: {e}")
            return False

    def list_buckets(self):
        """列出所有桶"""
        try:
            buckets = self.client.list_buckets()
            return [bucket.name for bucket in buckets]
        except S3Error as e:
            print(f"[!] 列出桶失败: {e}")
            return []

    # ==========================
    # Object (文件对象) 操作
    # ==========================

    def upload_file(self, bucket_name, object_name, file_path, content_type="application/octet-stream"):
        """
        上传本地文件到 Minio
        :param bucket_name: 桶名称
        :param object_name: 在 Minio 中存储的文件名
        :param file_path: 本地文件路径
        :param content_type: 文件类型
        """
        try:
            # 检查桶是否存在，不存在则创建
            if not self.bucket_exists(bucket_name):
                self.make_bucket(bucket_name)

            self.client.fput_object(bucket_name, object_name, file_path, content_type=content_type)
            print(f"[*] 文件 '{file_path}' 上传成功 -> '{bucket_name}/{object_name}'")
            return True
        except S3Error as e:
            print(f"[!] 上传文件失败: {e}")
            return False

    def download_file(self, bucket_name, object_name, file_path):
        """
        下载文件到本地
        :param bucket_name: 桶名称
        :param object_name: Minio 中的文件名
        :param file_path: 本地保存路径
        """
        try:
            self.client.fget_object(bucket_name, object_name, file_path)
            print(f"[*] 文件 '{bucket_name}/{object_name}' 下载成功 -> '{file_path}'")
            return True
        except S3Error as e:
            print(f"[!] 下载文件失败: {e}")
            return False

    def list_objects(self, bucket_name, prefix=None, recursive=True):
        """
        列出桶中的对象
        :param bucket_name: 桶名称
        :param prefix: 文件前缀过滤
        :param recursive: 是否递归查找
        """
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
            obj_list = [obj.object_name for obj in objects]
            return obj_list
        except S3Error as e:
            print(f"[!] 列出对象失败: {e}")
            return []

    def remove_object(self, bucket_name, object_name):
        """删除对象"""
        try:
            self.client.remove_object(bucket_name, object_name)
            print(f"[*] 对象 '{bucket_name}/{object_name}' 删除成功")
            return True
        except S3Error as e:
            print(f"[!] 删除对象失败: {e}")
            return False

    def get_presigned_url(self, bucket_name, object_name, expiry_hours=1):
        """
        获取文件的预签名 URL (临时访问链接)
        :param object_name:
        :param bucket_name:
        :param expiry_hours: 有效期（小时）
        """
        try:
            url = self.client.get_presigned_url(
                "GET",
                bucket_name,
                object_name,
                expires=timedelta(hours=expiry_hours),
            )
            return url
        except S3Error as e:
            print(f"[!] 获取预签名 URL 失败: {e}")
            return None

    def stat_object(self, bucket_name, object_name):
        """获取对象元数据信息"""
        try:
            result = self.client.stat_object(bucket_name, object_name)
            return result
        except S3Error as e:
            print(f"[!] 获取对象信息失败: {e}")
            return None


if __name__ == '__main__':
    # ==========================================
    # 测试配置 (请根据实际情况修改)
    # ==========================================
    # 如果你在本地运行 minio，通常地址是 127.0.0.1:9000
    # 这里使用 play.min.io 作为公共测试服务 (注意: 公共库数据会被定期清理)

    BUCKET_NAME = "python-sdk-test-bucket-001"
    LOCAL_FILE = "test_data.txt"
    DOWNLOAD_FILE = "downloaded_test_data.txt"
    OBJECT_NAME = "test_folder/test_data.txt"

    # ==========================================
    # 开始测试
    # ==========================================
    print("--- 开始 Minio SDK 测试 ---")

    # 1. 初始化客户端
    minio_client = MinioClient()

    # 2. 创建一个本地测试文件
    with open(LOCAL_FILE, "w", encoding="utf-8") as f:
        f.write("Hello, Minio! This is a test file generated by Python.")
    print(f"[*] 本地测试文件已生成: {LOCAL_FILE}")

    # 3. 创建桶
    minio_client.make_bucket(BUCKET_NAME)

    # 4. 列出所有桶
    buckets = minio_client.list_buckets()
    print(f"[*] 当前所有桶: {buckets}")

    # 5. 上传文件
    minio_client.upload_file(BUCKET_NAME, OBJECT_NAME, LOCAL_FILE)

    # 6. 列出桶内文件
    objects = minio_client.list_objects(BUCKET_NAME)
    print(f"[*] 桶 '{BUCKET_NAME}' 内的文件: {objects}")

    # 7. 获取文件元数据
    stat = minio_client.stat_object(BUCKET_NAME, OBJECT_NAME)
    if stat:
        print(f"[*] 文件大小: {stat.size} 字节, 最后修改: {stat.last_modified}")

    # 8. 获取下载链接
    url = minio_client.get_presigned_url(BUCKET_NAME, OBJECT_NAME)
    print(f"[*] 临时下载链接: {url}")

    # 9. 下载文件
    minio_client.download_file(BUCKET_NAME, OBJECT_NAME, DOWNLOAD_FILE)

    # 10. 清理测试数据 (删除对象、删除桶、删除本地文件)
    print("--- 开始清理测试数据 ---")
    # minio_client.remove_object(BUCKET_NAME, OBJECT_NAME)
    # minio_client.remove_bucket(BUCKET_NAME)

    if os.path.exists(LOCAL_FILE):
        os.remove(LOCAL_FILE)
    if os.path.exists(DOWNLOAD_FILE):
        os.remove(DOWNLOAD_FILE)
    print("[*] 本地清理完成")

    print("--- 测试结束 ---")