import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Union

from pymysql.err import OperationalError

logger = logging.getLogger(__name__)


class OperationType:
    """操作类型常量"""
    QUERY = "query"  # 查询操作 (SELECT)
    INSERT = "insert"  # 插入操作 (INSERT)
    UPDATE = "update"  # 更新操作 (UPDATE)
    DELETE = "delete"  # 删除操作 (DELETE)
    EXECUTE = "execute"  # 通用执行 (其他)


class BaseConnection(ABC):
    """
    数据库连接抽象基类

    定义了所有数据库连接应该实现的核心接口。
    具体的数据库实现（MySQL, PostgreSQL, Oracle, SQLite）应该继承此类。
    """

    def __init__(
            self,
            host: str,
            user: str,
            password: str,
            database: str,
            port: int,
            charset: str,
            # 连接池通用参数
            mincached: int,
            maxcached: int,
            maxconnections: int,
            blocking: bool,
    ):
        self.config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "charset": charset,
        }
        self.pool_config = {
            "mincached": mincached,  # 连接池中最小空闲连接数，启动时创建
            "maxcached": maxcached,  # 连接池中最大空闲连接数，超过此数的空闲连接会被关闭
            "maxconnections": maxconnections,  # 连接池允许的最大连接数（包括空闲和正在使用的）
            "blocking": blocking,  # 连接池满时是否阻塞等待，False则抛出异常
        }
        self._connection_pool = None
        # 标识符：数据库连接是否可用
        self._is_available = True

    # ======================
    # 抽象方法（必须由子类实现）
    # ======================

    @abstractmethod
    def _ensure_database_exists(self):
        """如果数据库不存在，则自动创建"""
        pass

    @abstractmethod
    def _create_connection_pool(self):
        """创建连接池（子类根据具体数据库实现）"""
        pass

    @abstractmethod
    def _get_raw_connection(self):
        """获取原生数据库连接（不使用连接池时）"""
        pass

    @abstractmethod
    def get_connection_url(self) -> str:
        """
        获取数据库连接URL（遵循 SQLAlchemy 数据库URL格式）
        
        Returns:
            数据库连接URL字符串
            例如: "mysql+pymysql://root:123456@localhost:3306/mydb?charset=utf8mb4"
                  "postgresql+psycopg2://user:password@localhost:5432/mydb"
                  "sqlite:///path/to/database.db"
        """
        pass

    # ======================
    # 公共方法（所有数据库通用）
    # ======================

    def get_connection(self):
        """从连接池获取一个数据库连接"""
        # 如果连接不可用，直接抛出异常
        if not self._is_available:
            raise RuntimeError("数据库连接不可用，已标记为不可用状态")
        
        if self._connection_pool is not None:
            return self._connection_pool.connection()
        else:
            return self._get_raw_connection()

    @contextmanager
    def get_connection_context(self):
        """获取连接的上下文管理器，自动归还连接到池中"""
        # 如果连接不可用，直接返回 None
        if not self._is_available:
            yield None
            return
        
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()  # 关闭连接会自动归还到连接池

    def execute(
            self,
            sql: str,
            params: Optional[tuple] = None,
            operation_type: Optional[str] = None,
            commit: bool = True
    ) -> Union[List[Dict[str, Any]], int]:
        """
        执行SQL语句的统一接口

        Args:
            sql: SQL语句
            params: SQL参数
            operation_type: 操作类型，不指定则自动从SQL中推断
                - "query": 查询操作，返回结果列表
                - "insert": 插入操作，返回插入的ID
                - "update": 更新操作，返回影响行数
                - "delete": 删除操作，返回影响行数
                - "execute": 其他操作，返回影响行数
            commit: 是否自动提交事务（仅对非查询操作有效）

        Returns:
            - query: List[Dict[str, Any]] - 查询结果列表
            - insert: int - 插入的ID
            - update/delete/execute: int - 影响的行数

        Examples:
            >>> conn.execute("SELECT * FROM users WHERE id = %s", (1,))
            >>> conn.execute("INSERT INTO users (name) VALUES (%s)", ("Alice",), "insert")
            >>> conn.execute("UPDATE users SET name = %s WHERE id = %s", ("Bob", 1))
        """
        # 优先检查连接是否可用，避免无意义的尝试
        if not self._is_available:
            logger.debug(f"数据库连接不可用，跳过操作: {operation_type if operation_type else 'auto-detect'}")
            # 返回适当的默认值
            if operation_type is None:
                operation_type = self._detect_operation_type(sql)
            if operation_type == OperationType.QUERY:
                return []
            elif operation_type == OperationType.INSERT:
                return -1
            else:  # UPDATE, DELETE, EXECUTE
                return 0

        if operation_type is None:
            operation_type = self._detect_operation_type(sql)

        # 记录 SQL 执行日志
        self._log_sql_execution(sql, params, operation_type)

        try:
            conn = self.get_connection()
        except Exception as e:
            logger.warning(f"获取数据库连接失败，标记连接为不可用：{e}")
            self._is_available = False
            # 返回适当的默认值
            if operation_type == OperationType.QUERY:
                return []
            elif operation_type == OperationType.INSERT:
                return -1
            else:  # UPDATE, DELETE, EXECUTE
                return 0

        try:
            # logger.debug(f"准备执行 SQL: {sql}")
            with conn.cursor() as cur:
                cur.execute(sql, params)

                # 根据操作类型返回不同的结果
                if operation_type == OperationType.QUERY:
                    result = cur.fetchall()
                    logger.debug(f"查询返回 {len(result)} 行数据")
                    return result
                elif operation_type == OperationType.INSERT:
                    last_id = cur.lastrowid
                    if commit:
                        conn.commit()
                        logger.debug(f"提交事务，插入 ID: {last_id}")
                    else:
                        logger.debug(f"未提交事务，插入 ID: {last_id}")
                    return last_id
                else:  # UPDATE, DELETE, EXECUTE
                    affected = cur.rowcount
                    if commit:
                        conn.commit()
                        logger.debug(f"提交事务，影响行数: {affected}")
                    else:
                        logger.debug(f"未提交事务，影响行数: {affected}")
                    return affected
        except OperationalError as oe:
            if oe.args[0] == 1050:
                logger.debug(f"表已存在，跳过创建表：{oe}")
                # 表已存在  忽略
                return 0
            # 非 1050 的 OperationalError 需要正确处理，不能吞掉异常后隐式返回 None
            logger.warning(f"SQL 执行 OperationalError，标记连接为不可用：{oe}")
            self._is_available = False
            logger.debug(f"失败 SQL: {sql}")
            logger.debug(f"参数: {params}")
            if operation_type == OperationType.QUERY:
                return []
            elif operation_type == OperationType.INSERT:
                return -1
            else:  # UPDATE, DELETE, EXECUTE
                return -1
        except Exception as e:
            logger.warning(f"SQL 执行失败，标记连接为不可用：{e}")
            self._is_available = False
            logger.debug(f"失败 SQL: {sql}")
            logger.debug(f"参数: {params}")
            # 返回适当的默认值
            if operation_type == OperationType.QUERY:
                return []
            elif operation_type == OperationType.INSERT:
                return -1
            else:  # UPDATE, DELETE, EXECUTE
                return -1
        finally:
            conn.close()

    def _log_sql_execution(self, sql: str, params: Optional[tuple], operation_type: str):
        """
        记录 SQL 执行日志

        Args:
            sql: SQL语句
            params: SQL参数
            operation_type: 操作类型
        """
        # 格式化 SQL 和参数
        if params:
            # 将 SQL 中的占位符替换为实际参数值（仅用于日志显示）
            try:
                formatted_sql = self._format_sql_with_params(sql, params)
                logger.debug(f"[{operation_type.upper()}] {formatted_sql}")
            except Exception:
                # 如果格式化失败，则分别记录 SQL 和参数
                logger.debug(f"[{operation_type.upper()}] SQL: {sql} | Params: {params}")
        else:
            logger.debug(f"[{operation_type.upper()}] {sql}")

    @staticmethod
    def _format_sql_with_params(sql: str, params: tuple) -> str:
        """
        将参数值格式化到 SQL 语句中（仅用于日志显示）

        Args:
            sql: SQL语句
            params: SQL参数

        Returns:
            格式化后的 SQL 语句
        """
        formatted_sql = sql
        # 处理 %s 占位符（MySQL, PostgreSQL）
        if "%s" in formatted_sql:
            for param in params:
                param_str = _format_param_value(param)
                formatted_sql = formatted_sql.replace("%s", param_str, 1)
        # 处理 ? 占位符（SQLite）
        elif "?" in formatted_sql:
            for param in params:
                param_str = _format_param_value(param)
                formatted_sql = formatted_sql.replace("?", param_str, 1)

        return formatted_sql

    @staticmethod
    def _detect_operation_type(sql: str) -> str:
        """
        自动检测SQL语句的操作类型

        Args:
            sql: SQL语句

        Returns:
            操作类型字符串
        """
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT") or sql_upper.startswith("SHOW") or sql_upper.startswith("DESCRIBE"):
            return OperationType.QUERY
        elif sql_upper.startswith("INSERT"):
            return OperationType.INSERT
        elif sql_upper.startswith("UPDATE"):
            return OperationType.UPDATE
        elif sql_upper.startswith("DELETE"):
            return OperationType.DELETE
        else:
            return OperationType.EXECUTE

    @contextmanager
    def get_connection_for_transaction(self):
        """
        获取用于事务的连接上下文管理器
        用于需要跨多个操作的事务，连接不会在每次操作后自动归还
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()  # 事务结束后归还连接到连接池

    def is_available(self) -> bool:
        """检查数据库连接是否可用"""
        return self._is_available

    def close(self) -> None:
        """关闭连接池（释放所有连接）"""
        if self._connection_pool is not None:
            logger.info("连接池已关闭")
        logger.debug("DatabaseConnection 已释放")


def _format_param_value(param: Any) -> str:
    """
    格式化参数值，用于 SQL 日志显示

    Args:
        param: 参数值

    Returns:
        格式化后的字符串
    """
    if param is None:
        return "NULL"
    elif isinstance(param, str):
        # 转义单引号，并使用单引号包裹字符串
        escaped = param.replace("'", "''")
        return f"'{escaped}'"
    elif isinstance(param, (int, float)):
        return str(param)
    elif isinstance(param, bool):
        return "1" if param else "0"
    elif isinstance(param, (list, tuple)):
        # 处理列表和元组
        return ", ".join(_format_param_value(p) for p in param)
    else:
        # 其他类型转字符串
        escaped = str(param).replace("'", "''")
        return f"'{escaped}'"
