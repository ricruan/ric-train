import time
import logging

import pymysql
import asyncio
from typing import Any, List, Optional, Dict
from dotenv import load_dotenv
import os

from Base.Config.setting import settings

logger = logging.getLogger(__name__)

load_dotenv()  # 自动加载 .env 文件

db_config = settings.mysql.model_dump()


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
        self.host = host or db_config.get('host')
        self.port = port or db_config.get('port')
        self.user = user or db_config.get('user')
        self.password = password or db_config.get('password')
        self.database = database or db_config.get('database')
        self.charset = charset or db_config.get('charset')
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
                autocommit=False,  # 关闭自动提交，需要手动控制事务
                connect_timeout = 10
            )

    def close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
        self._connection = None

    def commit(self):
        """提交当前事务"""
        if self._connection and self._connection.open:
            self._connection.commit()
            logger.info("事务已提交")

    def rollback(self):
        """回滚当前事务"""
        if self._connection and self._connection.open:
            self._connection.rollback()
            logger.warning("事务已回滚")

    def execute_sync(self, sql: str, params: Optional[tuple] = None, auto_commit: bool = False):
        """
        同步执行 SQL 查询，并增加了自动重连和重试逻辑。

        Args:
            sql: SQL语句
            params: SQL参数
            auto_commit: 是否自动提交（默认False，SELECT查询会自动提交，非SELECT需要手动提交）
        """
        logger.info(f"执行SQL: {sql}")
        if params:
            logger.info(f"参数: {params}")

        # 尝试次数 = 1次初始尝试 + max_retries 次重试
        for attempt in range(self.max_retries + 1):
            try:
                # 检查连接是否存在或是否已关闭
                if self._connection is None or not self._connection.open:
                    if self._connection and not self._connection.open:
                        logger.warning("连接不存在或已关闭，正在重新连接...")
                    self.connect()

                # *** 核心改动：在执行前检查连接活性 ***
                # ping(reconnect=False) 只检查，不自动重连，让我们自己控制重连逻辑
                self._connection.ping(reconnect=False)

                with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params or ())

                    # SELECT 查询自动提交，非 SELECT 查询根据参数决定
                    is_select = sql.strip().upper().startswith("SELECT")

                    if is_select:
                        result = cursor.fetchall()
                        # SELECT 查询自动提交
                        self._connection.commit()
                        # 打印查询结果统计信息
                        logger.info(f"查询结果总条数: {len(result)}")
                        # 打印前3条详情
                        if result:
                            preview_count = min(3, len(result))
                            logger.info(f"前{preview_count}条结果详情:")
                            for i in range(preview_count):
                                logger.info(f"  第{i+1}条: {result[i]}")
                        return result
                    else:
                        affected_rows = cursor.rowcount
                        logger.info(f"影响行数: {affected_rows}")

                        # 如果指定了 auto_commit，则提交事务
                        if auto_commit:
                            self._connection.commit()
                            logger.info("SQL执行成功，已自动提交")
                        else:
                            logger.info("SQL执行成功，等待手动提交或回滚")

                        return [{"affected_rows": affected_rows}]

            except pymysql.err.OperationalError as e:
                # 捕获到操作错误（通常是连接问题）
                logger.error(f"执行时捕获到连接错误: {e}. 尝试次数 {attempt + 1}/{self.max_retries + 1}")
                self.close()  # 彻底关闭失效的连接

                # 如果这已经是最后一次尝试，则将异常抛出
                if attempt >= self.max_retries:
                    logger.error("已达到最大重试次数，抛出异常。")
                    raise e

                # 等待一小段时间再重试，避免立即重连给数据库造成压力
                time.sleep(1)

                # 捕获其他 pymysql 错误（如语法错误）并直接抛出，不进行重试
            except pymysql.err.MySQLError as e:
                logger.error(f"捕获到非连接相关的SQL错误: {e}")
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
        self._update_data = None  # 存储 UPDATE 数据
        self._operation = 'SELECT'  # 操作类型：SELECT, UPDATE, INSERT, DELETE

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
        self._operation = 'SELECT'
        if fields:
            self._select_fields = ", ".join([self._quote_field(f) for f in fields])
        else:
            self._select_fields = "*"
        return self

    def update(self, data: Dict[str, Any]) -> 'SQLBuilder':
        """
        设置 UPDATE 操作的数据。
        :param data: 要更新的字段和值，如 {'desc': 'processing', 'status': 'done'}
        """
        self._operation = 'UPDATE'
        self._update_data = data
        return self

    def insert(self, data: Dict[str, Any] | List[Dict[str, Any]]) -> 'SQLBuilder':
        """
        设置 INSERT 操作的数据。
        :param data: 要插入的数据，可以是单条字典或多条字典列表
        """
        self._operation = 'INSERT'
        self._update_data = data
        return self

    def delete(self) -> 'SQLBuilder':
        """
        设置 DELETE 操作。
        """
        self._operation = 'DELETE'
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
        支持 SELECT、UPDATE、INSERT、DELETE 操作。
        """
        if not self._table:
            raise ValueError("必须通过 query() 方法指定主表名。")

        # 根据 operation 类型生成不同的 SQL
        if self._operation == 'UPDATE':
            return self._to_update_sql()
        elif self._operation == 'INSERT':
            return self._to_insert_sql()
        elif self._operation == 'DELETE':
            return self._to_delete_sql()
        else:
            return self._to_select_sql()

    def _to_select_sql(self):
        """生成 SELECT SQL"""
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

    def _to_update_sql(self):
        """生成 UPDATE SQL"""
        if not self._update_data:
            raise ValueError("UPDATE 操作必须提供数据。")

        sql_parts = [f"UPDATE `{self._table}` SET"]

        # 构建更新字段
        set_clauses = []
        params = []
        for field, value in self._update_data.items():
            set_clauses.append(f"{self._quote_field(field)} = %s")
            params.append(value)

        sql_parts.append(", ".join(set_clauses))

        # WHERE 子句
        if self._where_conditions:
            sql_parts.append("WHERE " + " AND ".join(self._where_conditions))
            params.extend(self._params)

        return " ".join(sql_parts) + ";", tuple(params)

    def _to_insert_sql(self):
        """生成 INSERT SQL"""
        if not self._update_data:
            raise ValueError("INSERT 操作必须提供数据。")

        # 处理单条或多条插入
        if isinstance(self._update_data, list):
            # 多条插入
            if not self._update_data:
                raise ValueError("插入数据不能为空。")
            fields = list(self._update_data[0].keys())
            quoted_fields = [self._quote_field(f) for f in fields]

            placeholders = []
            params = []
            for row in self._update_data:
                placeholders.append("(" + ", ".join(["%s"] * len(fields)) + ")")
                params.extend(row.get(f) for f in fields)

            sql = f"INSERT INTO `{self._table}` ({', '.join(quoted_fields)}) VALUES {', '.join(placeholders)}"
            return sql + ";", tuple(params)
        else:
            # 单条插入
            fields = list(self._update_data.keys())
            quoted_fields = [self._quote_field(f) for f in fields]
            values = [self._update_data[f] for f in fields]
            placeholders = ", ".join(["%s"] * len(fields))

            sql = f"INSERT INTO `{self._table}` ({', '.join(quoted_fields)}) VALUES ({placeholders})"
            return sql + ";", tuple(values)

    def _to_delete_sql(self):
        """生成 DELETE SQL"""
        sql_parts = [f"DELETE FROM `{self._table}`"]
        params = list(self._params)

        # WHERE 子句
        if self._where_conditions:
            sql_parts.append("WHERE " + " AND ".join(self._where_conditions))

        return " ".join(sql_parts) + ";", tuple(params)

    def __str__(self):
        """允许直接打印实例时，显示生成的 SQL 语句和参数。"""
        sql, params = self.to_sql()
        return f"SQL: {sql}\nPARAMS: {params}"


if __name__ == '__main__':

    def test_simple_query():
        # 示例1：简单查询（自动提交）
        print("=" * 50)
        print("示例1：简单查询")
        print("=" * 50)
        _sql = SQLBuilder('daily_report').where('id > 1').to_sql()
        r = MySQLClient(database='worlin').execute_sync(_sql[0], _sql[1])

    def test_use_backticks():
        # 示例2：方案1 - 使用反引号包裹保留关键字
        print("\n" + "=" * 50)
        print("示例2：方案1 - 使用反引号包裹保留关键字")
        print("=" * 50)
        with MySQLClient(database='worlin') as client:
            try:
                # 方案1：手动使用反引号包裹 desc（保留关键字）
                client.execute_sync("UPDATE daily_report SET `desc` = 'processing' WHERE id = 1")
                client.commit()
                print("方案1：事务已提交（使用反引号）")
            except Exception as e:
                client.rollback()
                print(f"发生错误，事务已回滚: {e}")

    def test_use_sqlbuilder():
        # 示例3：方案2 - 使用 SQLBuilder 自动处理字段引号
        print("\n" + "=" * 50)
        print("示例3：方案2 - 使用 SQLBuilder 自动处理字段引号")
        print("=" * 50)
        with MySQLClient(database='worlin') as client:
            try:
                # 方案2：使用 SQLBuilder 自动添加反引号
                _sql = SQLBuilder('daily_report').update({'desc': 'done'}).where('id = %s', 1).to_sql()
                print(f"生成的SQL: {_sql[0]}")
                print(f"参数: {_sql[1]}")
                client.execute_sync(_sql[0], _sql[1])
                client.commit()
                print("方案2：事务已提交（使用 SQLBuilder）")
            except Exception as e:
                client.rollback()
                print(f"发生错误，事务已回滚: {e}")

    def test_trans_success():
        # 示例4：事务控制 - 成功提交（多条 SQL）
        print("\n" + "=" * 50)
        print("示例4：事务控制 - 成功提交（多条 SQL）")
        print("=" * 50)
        with MySQLClient(database='worlin') as client:
            try:
                # 执行多条SQL
                client.execute_sync("UPDATE daily_report SET `desc` = 'processing' WHERE id = 1")
                client.execute_sync("UPDATE daily_report SET `desc` = 'done' WHERE id = 2")
                # 手动提交事务
                client.commit()
                print("事务已提交")
            except Exception as e:
                # 发生错误时回滚
                client.rollback()
                print(f"发生错误，事务已回滚: {e}")

    def test_trans_fail():
        # 示例5：事务控制 - 发生错误回滚
        print("\n" + "=" * 50)
        print("示例5：事务控制 - 发生错误回滚")
        print("=" * 50)
        with MySQLClient(database='worlin') as client:
            try:
                # 执行多条SQL，最后一条会失败
                client.execute_sync("UPDATE daily_report SET `desc` = 'processing' WHERE id = 1")
                client.execute_sync("UPDATE daily_report SET `desc` = 'done' WHERE id = 2")
                # 故意执行一个错误的SQL
                client.execute_sync("UPDATE daily_report SET invalid_column = 'test' WHERE id = 1")
                client.commit()
            except Exception as e:
                # 发生错误时回滚
                client.rollback()
                print(f"发生错误，事务已回滚: {e}")

    def test_auto_commit():
        # 示例6：使用 auto_commit 参数自动提交
        print("\n" + "=" * 50)
        print("示例6：使用 auto_commit 参数自动提交")
        print("=" * 50)
        with MySQLClient(database='worlin') as client:
            # 直接自动提交，不需要手动 commit
            client.execute_sync("UPDATE daily_report SET `desc` = 'auto_commit_test' WHERE id = 1", auto_commit=True)
            print("SQL已自动提交")

    def test_sqlbuilder_operations():
        # 示例7：SQLBuilder 支持的操作演示
        print("\n" + "=" * 50)
        print("示例7：SQLBuilder 支持的操作演示")
        print("=" * 50)

        # UPDATE 操作
        print("\n--- UPDATE 操作 ---")
        update_sql = SQLBuilder('daily_report').update({'desc': 'testing', 'status': 'pending'}).where('id = %s', 1).to_sql()
        print(f"UPDATE SQL: {update_sql[0]}, 参数: {update_sql[1]}")

        # INSERT 操作
        print("\n--- INSERT 操作（单条）---")
        insert_sql = SQLBuilder('daily_report').insert({'desc': 'new record', 'status': 'new'}).to_sql()
        print(f"INSERT SQL: {insert_sql[0]}, 参数: {insert_sql[1]}")

        print("\n--- INSERT 操作（多条）---")
        insert_multi_sql = SQLBuilder('daily_report').insert([
            {'desc': 'record1', 'status': 'new'},
            {'desc': 'record2', 'status': 'new'}
        ]).to_sql()
        print(f"INSERT SQL: {insert_multi_sql[0]}, 参数: {insert_multi_sql[1]}")

        # DELETE 操作
        print("\n--- DELETE 操作 ---")
        delete_sql = SQLBuilder('daily_report').delete().where('status = %s', 'test').to_sql()
        print(f"DELETE SQL: {delete_sql[0]}, 参数: {delete_sql[1]}")

        # SELECT 操作（复杂查询）
        print("\n--- SELECT 操作（复杂查询）---")
        select_sql = SQLBuilder('daily_report')\
            .select('id', 'desc', 'status')\
            .where('status = %s', 'done')\
            .order_by('id DESC')\
            .limit(10)\
            .to_sql()
        print(f"SELECT SQL: {select_sql[0]}, 参数: {select_sql[1]}")

    # 运行测试
    test_simple_query()
    test_use_backticks()
    test_use_sqlbuilder()
    test_trans_success()
    test_trans_fail()
    test_auto_commit()
    test_sqlbuilder_operations()
