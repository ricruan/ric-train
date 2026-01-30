"""
Redis 缓存装饰器使用示例
"""
import time
import random
from Base.Client.redisClient import RedisClient
from Base.RicUtils.redisUtils import redis_cache, cache_result, cache_with_params

# 初始化 Redis 客户端
redis_client = RedisClient()

# 示例1: 简单的无参数函数缓存
@cache_result("expensive_config", expire=10)  # 缓存10秒
def load_expensive_config():
    """模拟加载配置的耗时操作"""
    print("🔄 正在执行 load_expensive_config()...")
    time.sleep(2)  # 模拟耗时操作
    config = {
        "database_url": "mysql://localhost:3306/mydb",
        "api_key": "sk-1234567890",
        "debug_mode": True,
        "timestamp": time.time()
    }
    print(f"✅ 配置加载完成: {config}")
    return config

# 示例2: 带参数的函数缓存
@cache_with_params("user_info:{user_id}", expire=30)  # 缓存30秒
def get_user_info(user_id: int):
    """模拟获取用户信息的耗时操作"""
    print(f"🔄 正在获取用户 {user_id} 的信息...")
    time.sleep(1.5)  # 模拟数据库查询
    user_data = {
        "id": user_id,
        "name": f"用户{user_id}",
        "email": f"user{user_id}@example.com",
        "age": 20 + user_id,
        "created_at": time.time()
    }
    print(f"✅ 用户信息获取完成: {user_data}")
    return user_data

# 示例3: 多参数函数缓存
@redis_cache("search_results:{query}:{page}:{limit}", expire=60)
def search_data(query: str, page: int = 1, limit: int = 10):
    """模拟搜索操作的耗时操作"""
    print(f"🔄 正在搜索: query='{query}', page={page}, limit={limit}")
    time.sleep(1)  # 模拟搜索耗时
    
    # 模拟搜索结果
    results = []
    start_idx = (page - 1) * limit
    for i in range(limit):
        result_id = start_idx + i + 1
        results.append({
            "id": result_id,
            "title": f"{query} 相关结果 {result_id}",
            "content": f"这是关于 {query} 的搜索结果 {result_id}",
            "score": random.uniform(0.5, 1.0)
        })
    
    search_result = {
        "query": query,
        "page": page,
        "limit": limit,
        "total": 100,  # 模拟总结果数
        "results": results,
        "timestamp": time.time()
    }
    print(f"✅ 搜索完成，返回 {len(results)} 条结果")
    return search_result

# 示例4: 使用自定义 Redis 客户端和序列化方式
@redis_cache(
    key_template="complex_data:{data_id}",
    expire=120,
    redis_client=redis_client,
    serializer='pickle'  # 使用 pickle 序列化复杂对象
)
def get_complex_data(data_id: str):
    """模拟获取复杂数据结构"""
    print(f"🔄 正在获取复杂数据 {data_id}...")
    time.sleep(0.8)
    
    # 创建一个包含各种数据类型的复杂对象
    complex_obj = {
        "id": data_id,
        "metadata": {
            "created": time.time(),
            "tags": ["tag1", "tag2", "tag3"],
            "nested": {
                "level1": {
                    "level2": {
                        "value": f"deep_value_{data_id}"
                    }
                }
            }
        },
        "items": [f"item_{i}" for i in range(5)],
        "binary_data": b"some_binary_data_here",
        "none_value": None,
        "boolean": True
    }
    print(f"✅ 复杂数据获取完成")
    return complex_obj

# 示例5: 自定义键生成函数
def custom_key_generator(func_name: str, args: tuple, kwargs: dict) -> str:
    """自定义键生成函数"""
    # 根据函数名和参数生成自定义键
    params_str = f"{func_name}:{args[0] if args else 'no_args'}"
    return f"custom_cache:{hashlib.md5(params_str.encode()).hexdigest()}"

import hashlib

@redis_cache(key_template="custom_key", key_generator=custom_key_generator, expire=45)
def custom_cached_function(param1: str, param2: int = 100):
    """使用自定义键生成器的缓存函数"""
    print(f"🔄 执行自定义缓存函数: {param1}, {param2}")
    time.sleep(0.5)
    result = f"处理结果: {param1}_{param2}_{time.time()}"
    print(f"✅ 自定义函数执行完成")
    return result

def test_cache_decorators():
    """测试各种缓存装饰器"""
    print("🚀 开始测试 Redis 缓存装饰器")
    print("=" * 60)
    
    # 测试1: 无参数函数缓存
    print("\n📋 测试1: 无参数函数缓存")
    print("-" * 40)
    
    print("第一次调用 (应该执行原函数):")
    config1 = load_expensive_config()
    
    print("\n第二次调用 (应该从缓存返回):")
    config2 = load_expensive_config()
    
    print(f"两次结果是否相同: {config1 == config2}")
    
    # 等待缓存过期
    print("\n⏳ 等待缓存过期 (11秒)...")
    time.sleep(11)

    print("\n缓存过期后调用 (应该重新执行):")
    config3 = load_expensive_config()

    # 测试2: 带参数函数缓存
    print("\n📋 测试2: 带参数函数缓存")
    print("-" * 40)

    print("获取用户1信息 (第一次):")
    user1_1 = get_user_info(1)

    print("\n获取用户1信息 (第二次，应该从缓存返回):")
    user1_2 = get_user_info(1)

    print("\n获取用户2信息 (不同参数，应该执行原函数):")
    user2 = get_user_info(2)

    print(f"用户1两次结果是否相同: {user1_1 == user1_2}")
    print(f"用户1和用户2结果是否不同: {user1_1 != user2}")

    # 测试3: 多参数函数缓存
    print("\n📋 测试3: 多参数函数缓存")
    print("-" * 40)

    print("搜索 'Python' (第一次):")
    search1 = search_data("Python", page=1, limit=5)

    print("\n搜索 'Python' (第二次，应该从缓存返回):")
    search2 = search_data("Python", page=1, limit=5)

    print("\n搜索 'Python' 不同页面 (应该执行原函数):")
    search3 = search_data("Python", page=2, limit=5)

    print("\n搜索不同关键词 (应该执行原函数):")
    search4 = search_data("Java", page=1, limit=5)

    # 测试4: 复杂数据缓存
    print("\n📋 测试4: 复杂数据缓存")
    print("-" * 40)

    print("获取复杂数据 (第一次):")
    complex1 = get_complex_data("data_123")

    print("\n获取复杂数据 (第二次，应该从缓存返回):")
    complex2 = get_complex_data("data_123")

    print(f"复杂数据两次结果是否相同: {complex1 == complex2}")

    # 测试5: 自定义键生成
    print("\n📋 测试5: 自定义键生成")
    print("-" * 40)

    print("自定义缓存函数调用 (第一次):")
    custom1 = custom_cached_function("test_param", 200)

    print("\n自定义缓存函数调用 (第二次，应该从缓存返回):")
    custom2 = custom_cached_function("test_param", 200)

    print(f"自定义函数两次结果是否相同: {custom1 == custom2}")

    print("\n🎉 所有测试完成！")
    print("=" * 60)

def show_cache_keys():
    """显示当前缓存中的所有键"""
    print("\n🔍 当前 Redis 缓存中的键:")
    print("-" * 40)
    
    # 查看所有缓存键
    all_keys = redis_client.keys("*cache*")
    for key in all_keys:
        value = redis_client.get(key)
        print(f"键: {key}")
        print(f"值: {str(value)[:100]}...")
        print()

if __name__ == "__main__":
    # 运行测试
    # test_cache_decorators()

    res = get_user_info(1)
    print(res)
    res = get_user_info(1)
    print(res)
    # 显示缓存键
    show_cache_keys()
    
    print("\n💡 使用提示:")
    print("1. @cache_result(key, expire) - 适用于无参数函数")
    print("2. @cache_with_params(template, expire) - 适用于带参数函数")
    print("3. @redis_cache(template, expire, client, serializer) - 完整配置")
    print("4. 支持自定义键生成函数")
    print("5. 支持 JSON 和 Pickle 两种序列化方式")