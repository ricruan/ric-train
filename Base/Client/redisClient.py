import logging
import os

import redis
import threading
from typing import Optional, List, Generator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# 读取 Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None


class RedisClient:
    """
    Redis 客户端单例类，封装基本的增删改查、模糊查询和模糊删除功能。
    使用 redis-py 客户端库。
    """

    _instance: Optional['RedisClient'] = None
    _lock = threading.Lock()

    def __new__(cls, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True):
        """
        实现单例模式，确保全局只有一个 RedisClient 实例。
        如果实例已存在，则忽略传入的参数，直接返回现有实例。
        """
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定，确保线程安全
                if cls._instance is None:
                    cls._instance = super(RedisClient, cls).__new__(cls)
                    cls._instance._initialized = False
                    cls._instance.host = host
                    cls._instance.port = port
                    cls._instance.db = db
                    cls._instance.password = password
                    cls._instance.decode_responses = decode_responses
        return cls._instance

    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True):
        """
        初始化 Redis 连接池和客户端。
        注意：由于是单例，__init__ 可能会被多次调用，但连接只创建一次。
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return

            # 创建连接池
            self.connection_pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,  # 确保获取的字符串是 str 而不是 bytes
                max_connections=20  # 可根据需要调整
            )
            # 创建客户端实例
            self.client = redis.Redis(connection_pool=self.connection_pool)
            if self.ping():
                self._initialized = True
                logger.error(f"RedisClient 单例已初始化，连接到 {self.host}:{self.port}")

    def set(self, key: str, value: str, ex: int = None) -> bool:
        """
        设置键值对。
        :param key: 键
        :param value: 值
        :param ex: 过期时间（秒），可选
        :return: 成功返回 True，失败返回 False
        """
        try:
            self.client.set(key, value, ex=ex)
            return True
        except redis.RedisError as e:
            print(f"设置键 {key} 失败: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """
        获取键对应的值。
        :param key: 键
        :return: 值（字符串）或 None（如果键不存在）
        """
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.error(f"获取键 {key} 失败: {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        删除指定的键。
        :param key: 键
        :return: 成功返回被删除的键的数量（通常为 1 或 0），失败返回 0
        """
        try:
            count = self.client.delete(key)
            return count > 0
        except redis.RedisError as e:
            logger.error(f"删除键 {key} 失败: {e}")
            return False

    def update(self, key: str, value: str, ex: int = None) -> bool:
        """
        更新键的值（等同于 set，因为 set 会覆盖已存在的键）。
        :param key: 键
        :param value: 新值
        :param ex: 新的过期时间（秒），可选
        :return: 成功返回 True，失败返回 False
        """
        return self.set(key, value, ex)

    def keys(self, pattern: str = "*") -> List[str | bytes]:
        """
        模糊查询键（使用 KEYS 命令）。
        ⚠️ 警告：在大数据量下使用 KEYS 会阻塞 Redis，生产环境慎用！
        推荐在生产环境使用 scan_keys_generator() 进行迭代查询。
        :param pattern: 匹配模式，如 "user:*", "session:*" 等
        :return: 匹配的键列表
        """
        try:
            # 使用 decode_responses=True 时，返回的是字符串列表
            return self.client.keys(pattern)
        except redis.RedisError as e:
            logger.error(f"模糊查询键 {pattern} 失败: {e}")
            return []

    def scan_keys_generator(self, match: str = "*", count: int = 10) -> Generator[str|bytes, None, None]:
        """
        使用 SCAN 命令迭代查询键（生产环境推荐）。
        这是一个生成器，可以避免一次性加载所有匹配的键，减少内存占用和对 Redis 的阻塞。
        :param match: 匹配模式
        :param count: 每次迭代的近似元素数量（提示，非精确）
        :yield: 每个匹配的键
        """
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor=cursor, match=match, count=count)
            for key_item in keys:
                yield key_item
            if cursor == 0:
                break

    def fuzzy_delete(self, pattern: str) -> int:
        """
        模糊删除匹配模式的键（使用 KEYS + delete）。
        ⚠️ 警告：在大数据量下使用 KEYS 会阻塞 Redis，生产环境慎用！
        :param pattern: 匹配模式
        :return: 成功删除的键的数量
        """
        try:
            keys_to_delete = self.keys(pattern)
            if keys_to_delete:
                # 使用 pipeline 可以提高删除大量键的效率
                pipe = self.client.pipeline()
                for key in keys_to_delete:
                    pipe.delete(key)
                # 执行所有删除命令
                results = pipe.execute()
                # 返回实际删除成功的数量（结果为1表示删除成功）
                return sum(results)
            return 0
        except redis.RedisError as e:
            logger.error(f"模糊删除键 {pattern} 失败: {e}")
            return 0

    def fuzzy_delete_safe(self, match: str = "*", count: int = 10) -> int:
        """
        使用 SCAN 和 pipeline 安全地模糊删除键（生产环境推荐）。
        避免了 KEYS 命令的阻塞问题。
        :param match: 匹配模式
        :param count: 每次 SCAN 的近似数量
        :return: 成功删除的键的数量
        """
        deleted_count = 0
        try:
            pipe = self.client.pipeline()
            for key in self.scan_keys_generator(match=match, count=count):
                pipe.delete(key)
                deleted_count += 1
                # 为了避免 pipeline 过大，可以定期执行
                if deleted_count % 1000 == 0:
                    pipe.execute()
                    pipe = self.client.pipeline() # 重置 pipeline
            # 执行剩余的命令
            if deleted_count > 0:
                pipe.execute()
        except redis.RedisError as e:
            logger.error(f"安全模糊删除键 {match} 失败: {e}")
            # 如果出错，可能需要手动检查状态
        return deleted_count

    def ping(self) -> bool:
        """
        测试 Redis 连接是否正常。
        :return: 连通返回 True，否则返回 False
        """
        try:
            return self.client.ping()
        except redis.RedisError as e:
            logger.error(f"Ping Redis 失败: {e}")
            return False

# --- 使用示例 ---
if __name__ == "__main__":
    # 获取单例实例（第一次调用会创建连接）
    # 后续调用即使参数不同，也会返回同一个实例
    redis_client1 = RedisClient()

    # 再次获取，仍然是同一个实例
    redis_client2 = RedisClient(host="localhost", port=6379, db=0, password=None)
    print(f"redis_client1 is redis_client2: {redis_client1 is redis_client2}")  # 输出: True

    # 测试连接
    if redis_client1.ping():
        print("Redis 连接成功！")

        # 基本操作
        redis_client1.set("name", "Alice", ex=3600)
        print("获取 name:", redis_client1.get("name"))

        redis_client1.update("name", "Bob")
        print("更新后 name:", redis_client1.get("name"))

        # 模糊查询 (谨慎使用)
        print("所有键:", redis_client1.keys("*"))
        print("以 'name' 开头的键:", redis_client1.keys("name*"))

        # 使用推荐的 SCAN 方式进行模糊查询
        print("使用 SCAN 查询以 'name' 开头的键:")
        for key in redis_client1.scan_keys_generator("name*"):
            print(f"  - {key}")

        # 模糊删除 (谨慎使用)
        # redis_client1.fuzzy_delete("temp:*")  # 删除所有以 temp: 开头的键

        # 安全的模糊删除 (推荐)
        # deleted = redis_client1.fuzzy_delete_safe("temp:*")
        # print(f"安全删除了 {deleted} 个键")

        # 删除单个键
        if redis_client1.delete("name"):
            print("键 'name' 已删除")
    else:
        print("无法连接到 Redis，请检查服务是否运行。")