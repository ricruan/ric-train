import hashlib
import base64
import string

# Base62 字符集（数字 + 大小写字母）
BASE62 = string.digits + string.ascii_letters


def _to_base62(num: int) -> str:
    if num == 0:
        return BASE62[0]
    arr = []
    base = len(BASE62)
    while num:
        num, rem = divmod(num, base)
        arr.append(BASE62[rem])
    return ''.join(reversed(arr))


def short_unique_hash(input_str: str, length: int = 10) -> str:
    """
    生成一个较短的、近似唯一的哈希字符串。

    Args:
        input_str (str): 输入字符串
        length (int): 输出哈希长度（建议 >= 8，越大越不易碰撞）

    Returns:
        str: 长度为 `length` 的 Base62 编码哈希字符串
    """
    if not isinstance(input_str, str):
        raise ValueError("Input must be a string")

    # 使用 SHA-256 生成稳定且分布均匀的哈希
    sha256_hash = hashlib.sha256(input_str.encode('utf-8')).digest()

    # 将二进制哈希转为大整数
    hash_int = int.from_bytes(sha256_hash, byteorder='big')

    # 转为 Base62 字符串
    base62_str = _to_base62(hash_int)

    # 截取指定长度（从开头取，因为 SHA-256 输出均匀）
    return base62_str[:length].ljust(length, '0')  # 若太短则补0（理论上不会）


