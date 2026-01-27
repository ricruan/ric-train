import time

import pymysql
import asyncio
from typing import Any, List, Optional, Dict
from dotenv import load_dotenv
import os

from Base.Config.setting import settings

load_dotenv()  # 自动加载 .env 文件

db_config = settings.mysql.dict()


class MySQLClient:
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None,
        charset: str = None,
        max_retries: int = 1
    ):
        self.host = host or db_config['host']
        self.port = port or db_config['port']
        self.user = user or db_config['user']
        self.password = password or db_config['password']
        self.database = database or db_config['database']
        self.charset = charset or db_config['charset']
        self._connection: Optional[pymysql.Connection] = None
        self.max_retries = max_retries

    def connect(self):
        """建立同步连接"""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                autocommit=True,  # 自动提交，避免忘记 commit  不应该加这个，但是演示 无所谓
                connect_timeout = 10
            )

    def close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
        self._connection = None

    def execute_sync(self, sql: str, params: Optional[tuple] = None):
        """
        同步执行 SQL 查询，并增加了自动重连和重试逻辑。
        """
        # 尝试次数 = 1次初始尝试 + max_retries 次重试
        for attempt in range(self.max_retries + 1):
            try:
                # 检查连接是否存在或是否已关闭
                if self._connection is None or not self._connection.open:
                    if self._connection and not self._connection.open:
                        print("连接不存在或已关闭，正在重新连接...")
                    self.connect()

                # *** 核心改动：在执行前检查连接活性 ***
                # ping(reconnect=False) 只检查，不自动重连，让我们自己控制重连逻辑
                self._connection.ping(reconnect=False)

                with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params or ())
                    if sql.strip().upper().startswith("SELECT"):
                        return cursor.fetchall()
                    else:
                        return [{"affected_rows": cursor.rowcount}]

            except pymysql.err.OperationalError as e:
                # 捕获到操作错误（通常是连接问题）
                print(f"执行时捕获到连接错误: {e}. 尝试次数 {attempt + 1}/{self.max_retries + 1}")
                self.close()  # 彻底关闭失效的连接

                # 如果这已经是最后一次尝试，则将异常抛出
                if attempt >= self.max_retries:
                    print("已达到最大重试次数，抛出异常。")
                    raise e

                # 等待一小段时间再重试，避免立即重连给数据库造成压力
                time.sleep(1)

                # 捕获其他 pymysql 错误（如语法错误）并直接抛出，不进行重试
            except pymysql.err.MySQLError as e:
                print(f"捕获到非连接相关的SQL错误: {e}")
                raise e
        return None

    async def execute_async(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        异步执行 SQL（通过线程池运行同步 pymysql 操作）
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_sync, sql, params)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()




class SQLBuilder:
    """
    一个通过链式调用构造 SQL 查询的类，支持 JOIN、GROUP BY 和 ORDER BY。
    """

    def __init__(self, table=None):
        self._table = table
        self._select_fields = None  # 默认为 None，以便在 JOIN 时更好地区分
        self._where_conditions = []
        self._limit_clause = None
        self._offset_clause = None
        self._order_by_clauses = []
        self._group_by_columns = []
        self._joins = []  # 存储 join 信息: (type, other_builder, on_condition)
        self._params = []

    def query(self, table: str):
        """设置要查询的主表名 (FROM 子句)。"""
        self._table = table
        return self

    @staticmethod
    def _quote_field(field):
        """智能地为字段或'table.field'添加反引号。"""
        if '.' in field:
            return '.'.join([f"`{part}`" for part in field.split('.')])
        return f"`{field}`"

    def select(self, *fields):
        """
        设置要查询的字段 (SELECT 子句)。
        支持 'field' 和 'table.field' 格式。
        """
        if fields:
            self._select_fields = ", ".join([self._quote_field(f) for f in fields])
        else:
            self._select_fields = "*"
        return self

    def where(self, condition: str, *params):
        """添加一个 WHERE 条件，支持参数化查询。"""
        self._where_conditions.append(f"({condition})")
        self._params.extend(params)
        return self

    def limit(self, number: int):
        """设置 LIMIT 子句。"""
        self._limit_clause = number
        return self

    def offset(self, number: int):
        """设置 OFFSET 子句。"""
        self._offset_clause = number
        return self

    def order_by(self, *clauses):
        """
        设置 ORDER BY 子句，可接受多个排序条件。
        示例: .order_by('name ASC', 'age DESC')
        """
        self._order_by_clauses.extend(clauses)
        return self

    def group_by(self, *columns):
        """
        设置 GROUP BY 子句。
        示例: .group_by('department', 'city')
        """
        self._group_by_columns.extend([self._quote_field(c) for c in columns])
        return self

    def _add_join(self, join_type: str, other_builder, on_condition: str):
        """内部方法，用于添加 JOIN 信息。"""
        if not isinstance(other_builder, SQLBuilder) or not other_builder._table:
            raise TypeError("join 方法需要一个已指定表名的 QueryBuilder 实例。")
        self._joins.append((join_type, other_builder, on_condition))
        return self

    def join(self, other_builder, on_condition: str):
        """
        添加 INNER JOIN。
        :param other_builder: 另一个 QueryBuilder 实例。
        :param on_condition: ON 条件的字符串, e.g., '`users`.`id` = `profiles`.`user_id`'
        """
        return self._add_join('INNER JOIN', other_builder, on_condition)

    def left_join(self, other_builder, on_condition: str):
        """
        添加 LEFT JOIN。
        :param other_builder: 另一个 QueryBuilder 实例。
        :param on_condition: ON 条件的字符串, e.g., '`users`.`id` = `profiles`.`user_id`'
        """
        return self._add_join('LEFT JOIN', other_builder, on_condition)

    def to_sql(self):
        """
        生成最终的 SQL 查询语句和参数。
        """
        if not self._table:
            raise ValueError("必须通过 query() 方法指定主表名。")

        # 确定 SELECT 字段，如果主查询未指定，则为 *
        select_clause = self._select_fields if self._select_fields is not None else "*"
        sql_parts = [f"SELECT {select_clause}"]

        # FROM 和 JOIN 子句
        from_clause = f"FROM `{self._table}`"

        all_where_conditions = list(self._where_conditions)
        final_params = list(self._params)

        if self._joins:
            join_clauses = []
            for join_type, other_builder, on_condition in self._joins:
                join_clauses.append(f"{join_type} `{other_builder._table}` ON {on_condition}")
                all_where_conditions.extend(other_builder._where_conditions)
                final_params.extend(other_builder._params)
            from_clause += " " + " ".join(join_clauses)

        sql_parts.append(from_clause)

        # WHERE 子句
        if all_where_conditions:
            sql_parts.append("WHERE " + " AND ".join(all_where_conditions))

        # GROUP BY 子句
        if self._group_by_columns:
            sql_parts.append("GROUP BY " + ", ".join(self._group_by_columns))

        # ORDER BY 子句
        if self._order_by_clauses:
            sql_parts.append("ORDER BY " + ", ".join(self._order_by_clauses))

        # LIMIT 和 OFFSET 子句
        # 注意：LIMIT/OFFSET 的参数必须在最后添加
        if self._limit_clause is not None:
            sql_parts.append("LIMIT %s")
            final_params.append(self._limit_clause)

        if self._offset_clause is not None:
            sql_parts.append("OFFSET %s")
            final_params.append(self._offset_clause)

        return " ".join(sql_parts) + ";", tuple(final_params)

    def __str__(self):
        """允许直接打印实例时，显示生成的 SQL 语句和参数。"""
        sql, params = self.to_sql()
        return f"SQL: {sql}\nPARAMS: {params}"


if __name__ == '__main__' :
    _sql = SQLBuilder('daily_report').where('id > 1').to_sql()
    print(str(_sql))
    r = MySQLClient().execute_sync(_sql[0], _sql[1])
    print(r)