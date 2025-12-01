import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from typing import List, Tuple, Dict

from Meta.singletonMeta import SingletonMeta

logger = logging.getLogger(__name__)

class MinioClient(metaclass=SingletonMeta):

    def __init__(self, endpoint: str = None, access_key: str = None, secret_key: str = None, secure=False):
        # 防止重复初始化（可选）
        if hasattr(self, 'client'):
            return  # 已初始化过，跳过

        self.endpoint = endpoint or os.getenv('MINIO_ENDPOINT')
        access_key = access_key or os.getenv('MINIO_ACCESS_KEY')
        secret_key = secret_key or os.getenv('MINIO_SECRET_KEY')

        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            self.is_active = True
            print(f"[*] Minio 客户端连接成功: {self.endpoint}")
        except Exception as e:
            self.is_active = False
            print(f"[!] Minio 连接失败: {e}")

    # ==========================
    # Bucket (存储桶) 操作
    # ==========================

    def bucket_exists(self, bucket_name):
        """检查桶是否存在"""
        try:
            result = self.client.bucket_exists(bucket_name)
            return result
        except S3Error as e:
            logger.error(f"[!] 检查桶存在失败: {e}")
            return False

    def make_bucket(self, bucket_name):
        """创建桶"""
        try:
            if not self.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"[*] 桶 '{bucket_name}' 创建成功")
                return True
            else:
                logger.info(f"[*] 桶 '{bucket_name}' 已存在")
                return True
        except S3Error as e:
            logger.error(f"[!] 创建桶失败: {e}")
            return False

    def remove_bucket(self, bucket_name):
        """删除桶 (桶必须为空)"""
        try:
            self.client.remove_bucket(bucket_name)
            logger.info(f"[*] 桶 '{bucket_name}' 删除成功")
            return True
        except S3Error as e:
            logger.error(f"[!] 删除桶失败: {e}")
            return False

    def list_buckets(self):
        """列出所有桶"""
        try:
            buckets = self.client.list_buckets()
            return [bucket.name for bucket in buckets]
        except S3Error as e:
            logger.error(f"[!] 列出桶失败: {e}")
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
            logger.info(f"[*] 文件 '{file_path}' 上传成功 -> '{bucket_name}/{object_name}'")
            return True
        except S3Error as e:
            logger.error(f"[!] 上传文件失败: {e}")
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
            logger.info(f"[*] 文件 '{bucket_name}/{object_name}' 下载成功 -> '{file_path}'")
            return file_path
        except S3Error as e:
            logger.error(f"[!] 下载文件失败: {e}")
            return None

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
            logger.error(f"[!] 列出对象失败: {e}")
            return []

    def remove_object(self, bucket_name, object_name):
        """删除对象"""
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"[*] 对象 '{bucket_name}/{object_name}' 删除成功")
            return True
        except S3Error as e:
            logger.error(f"[!] 删除对象失败: {e}")
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
            logger.error(f"[!] 获取预签名 URL 失败: {e}")
            return None

    def stat_object(self, bucket_name, object_name):
        """获取对象元数据信息"""
        try:
            result = self.client.stat_object(bucket_name, object_name)
            return result
        except S3Error as e:
            logger.error(f"[!] 获取对象信息失败: {e}")
            return None


class MinioAsyncClient(MinioClient):
    """
    MinIO 异步客户端
    继承自 MinioClient，利用线程池处理密集 IO 操作
    """

    def __init__(self, *args, max_workers: int = 5, **kwargs):
        """
        :param max_workers: 线程池最大线程数，建议设置为 CPU核心数 * 2 或根据网络带宽调整
        """
        super().__init__(*args, **kwargs)

        # 确保线程池只被初始化一次 (因为是单例，防止重复 __init__ 覆盖 executor)
        if not hasattr(self, 'executor'):
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
            logger.info(f"[*] MinioAsyncClient 线程池启动，最大工作线程: {max_workers}")

    def _submit_task(self, func, *args, **kwargs) -> Future:
        """通用任务提交方法"""
        return self.executor.submit(func, *args, **kwargs)

    # ==========================
    # 单个异步操作 (返回 Future)
    # ==========================

    def upload_file_async(self, bucket_name, object_name, file_path, content_type="application/octet-stream") -> Future:
        """异步上传单个文件"""
        # 直接复用父类的同步方法，将其放入线程池
        return self._submit_task(self.upload_file, bucket_name, object_name, file_path, content_type)

    def download_file_async(self, bucket_name, object_name, file_path) -> Future:
        """异步下载单个文件"""
        return self._submit_task(self.download_file, bucket_name, object_name, file_path)

    # ==========================
    # 批量/密集 IO 操作 (推荐)
    # ==========================

    def upload_many(self, bucket_name: str, tasks: List[Tuple[str, str]]) -> Dict[str, Future]:
        """
        批量上传文件
        :param bucket_name: 目标桶
        :param tasks: 列表，包含元组 (本地文件路径, 目标对象名)
                      例如: [('./data/1.jpg', 'imgs/1.jpg'), ('./data/2.jpg', 'imgs/2.jpg')]
        :return: 字典 {file_path: Future}
        """
        future_dict = {}
        for file_path, object_name in tasks:
            # 提交任务
            future = self.upload_file_async(bucket_name, object_name, file_path)
            future_dict[file_path] = future
        return future_dict

    def download_many(self, bucket_name: str, tasks: List[Tuple[str, str]]) -> Dict[str, Future]:
        """
        批量下载文件
        :param bucket_name: 源桶
        :param tasks: 列表，包含元组 (Minio对象名, 本地保存路径)
        :return: 字典 {object_name: Future}
        """
        future_dict = {}
        for object_name, local_path in tasks:
            future = self.download_file_async(bucket_name, object_name, local_path)
            future_dict[object_name] = future
        return future_dict

    # ==========================
    # 资源管理
    # ==========================
    @staticmethod
    def wait_and_get_results(futures: List[Future] | Future):
        """
        辅助方法：阻塞等待一组 Future 完成并返回结果
        """
        if isinstance(futures,Future):
            futures = [futures]
        results = []
        for future in as_completed(futures):
            try:
                # result() 会抛出线程中发生的异常，需要捕获
                res = future.result()
                results.append(res)
            except Exception as e:
                logger.error(f"线程执行异常: {e}")
                results.append(None)
        return results

    def shutdown(self, wait=True):
        """关闭线程池"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=wait)
            logger.info("[*] 线程池已关闭")


default_minio_client = MinioClient()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # ==========================================
    # 测试配置 (请根据实际情况修改)
    # ==========================================
    # 如果你在本地运行 minio，通常地址是 127.0.0.1:9000
    # 这里使用 play.min.io 作为公共测试服务 (注意: 公共库数据会被定期清理)

    BUCKET_NAME = "python-sdk-test-bucket-001"
    LOCAL_FILE = "test_data2.txt"
    DOWNLOAD_FILE = "downloaded_test_data.txt"
    OBJECT_NAME = "test_folder/test_data3.txt"

    # ==========================================
    # 开始测试
    # ==========================================
    print("--- 开始 Minio SDK 测试 ---")

    # 1. 初始化客户端
    minio_client = MinioAsyncClient(max_workers=10)

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
    res = minio_client.wait_and_get_results([minio_client.upload_file_async(BUCKET_NAME, OBJECT_NAME, LOCAL_FILE)])
    print(1)
    print(res)
    print(2)




    # 6. 列出桶内文件
    # objects = minio_client.list_objects(BUCKET_NAME)
    # print(f"[*] 桶 '{BUCKET_NAME}' 内的文件: {objects}")
    #
    # # 7. 获取文件元数据
    # stat = minio_client.stat_object(BUCKET_NAME, OBJECT_NAME)
    # if stat:
    #     print(f"[*] 文件大小: {stat.size} 字节, 最后修改: {stat.last_modified}")
    #
    # # 8. 获取下载链接
    # url = minio_client.get_presigned_url(BUCKET_NAME, OBJECT_NAME)
    # print(f"[*] 临时下载链接: {url}")
    #
    # # 9. 下载文件
    res = minio_client.wait_and_get_results(minio_client.download_file_async(BUCKET_NAME, OBJECT_NAME, DOWNLOAD_FILE))
    print(res)
    #
    # # 10. 清理测试数据 (删除对象、删除桶、删除本地文件)
    # print("--- 开始清理测试数据 ---")
    # # minio_client.remove_object(BUCKET_NAME, OBJECT_NAME)
    # # minio_client.remove_bucket(BUCKET_NAME)
    #
    if os.path.exists(LOCAL_FILE):
        os.remove(LOCAL_FILE)
    if os.path.exists(DOWNLOAD_FILE):
        os.remove(DOWNLOAD_FILE)
    # print("[*] 本地清理完成")

    print("--- 测试结束 ---")