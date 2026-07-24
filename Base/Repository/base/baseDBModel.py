import logging
from abc import ABC
from typing import Optional, Dict, Any, List, Type, TypeVar, ClassVar, Literal

from pydantic import BaseModel, Field, ConfigDict

from Base.Repository.base.baseConnection import BaseConnection

logger = logging.getLogger(__name__)
T = TypeVar('T', bound='BaseDBModel')


class BaseDBModel(BaseModel, ABC):
    """
    数据库模型基类，继承自 Pydantic BaseModel 和 ABC
    
    子类需要定义：
    - table_alias (ClassVar[str]): 表别名（可选），默认使用类名小写作为表名
    - id (Optional[int]): 主键字段（基类已定义，子类可覆盖以自定义类型或描述）
    
    支持多数据源/多数据库：
    1. 设置默认连接：BaseDBModel.set_default_db_connection()
    2. 为实例设置连接：model.set_connection()
    3. 为类设置连接：MyModel.set_db_connection()
    
    使用示例：
        # 初始化默认连接
        BaseDBModel.set_default_db_connection(default_db)
        
        # 为特定类设置连接
        User.set_db_connection(user_db)
        Order.set_db_connection(order_db)
        
        # 为实例设置连接（支持读写分离）
        user = User.get_by_id(1)
        user.set_connection(write_db)
        user.update(name="李四")
        
        # 插入
        user = User(name="张三", email="zhangsan@example.com")
        user_id = user.save()
        
        # 查询（使用类的默认连接）
        user = User.get_by_id(1)
        
        # 更新（使用实例的特定连接）
        user.name = "李四"
        user.update()
        
        # 删除
        user.delete()
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

    # 类变量：表名别名（可选）
    table_alias: ClassVar[Optional[str]] = None
    # 类变量：手动声明的建表 SQL（可选，如果声明则优先使用）
    create_table_sql: ClassVar[Optional[str]] = None
    # 类变量：默认数据库连接（全局默认）
    _default_db_connection: ClassVar[Optional[BaseConnection]] = None
    # 类变量：每个类可以有自己的连接
    _db_connection: ClassVar[Optional[BaseConnection]] = None
    # 实例变量：实例级别的连接（优先级最高）
    _instance_db_connection: Optional[BaseConnection] = None
    # 类变量：表检查缓存（避免重复检查）
    _table_checked: ClassVar[bool] = False

    # 抽象属性：主键字段（子类可以覆盖此属性以自定义类型或描述）
    # 注意：id 字段在基类中已定义，子类可以覆盖此字段以自定义类型或验证规则
    id: Optional[int] = Field(None, description="主键ID", exclude=True)

    def __init_subclass__(cls, **kwargs):
        """子类初始化时调用，用于验证子类是否满足要求"""
        super().__init_subclass__(**kwargs)

        # 检查子类是否包含 id 字段（继承或重新定义都可以）
        # 注意：因为基类已经定义了 id 字段，子类会自动继承
        # 这个检查主要确保子类不会意外排除 id 字段
        if 'id' not in cls.model_fields:
            raise NotImplementedError(
                f"子类 {cls.__name__} 必须包含 'id' 字段作为主键。\n"
                f"原因：id 字段可能在子类中被意外排除。\n"
                f"请在子类中定义：id: Optional[int] = Field(..., description='主键描述')\n"
                f"或者确保没有通过 model_config 或其他方式排除 id 字段。"
            )

        # 检查 id 字段是否被意外标记为 required（应该是 Optional）
        id_field = cls.model_fields['id']
        if not id_field.is_required():
            logger.debug(f"子类 {cls.__name__} 已通过 BaseDBModel 初始化检查，包含 id 字段")
        else:
            logger.warning(
                f"子类 {cls.__name__} 的 id 字段被标记为必填字段（is_required=True）。\n"
                f"建议：id 字段应该是 Optional[int] 类型，以便在插入新记录时可以自动生成。"
            )

    @classmethod
    def set_default_db_connection(cls, db_connection: BaseConnection):
        """设置全局默认数据库连接（所有模型类的默认连接）"""
        cls._default_db_connection = db_connection
        logger.debug(f"设置全局默认数据库连接")

    @classmethod
    def set_db_connection(cls, db_connection: BaseConnection):
        """为特定模型类设置数据库连接（覆盖默认连接）"""
        cls._db_connection = db_connection
        logger.debug(f"为 {cls.__name__} 设置数据库连接")

    def set_connection(self, db_connection: BaseConnection):
        """为实例设置数据库连接（支持读写分离等场景，优先级最高）"""
        self._instance_db_connection = db_connection
        logger.debug(f"为 {self.__class__.__name__} 实例设置数据库连接")

    def get_connection(self) -> Optional[BaseConnection]:
        """获取数据库连接（优先级：实例 > 类 > 默认），如果未设置则返回 None"""
        # 优先级1：实例级别的连接
        if self._instance_db_connection is not None:
            # 检查连接是否可用
            if hasattr(self._instance_db_connection,
                       'is_available') and not self._instance_db_connection.is_available():
                logger.debug(f"实例级别的数据库连接不可用，操作将被跳过")
                return None
            return self._instance_db_connection
        # 优先级2：类级别的连接
        if self.__class__._db_connection is not None:
            # 检查连接是否可用
            if hasattr(self.__class__._db_connection,
                       'is_available') and not self.__class__._db_connection.is_available():
                logger.debug(f"类级别的数据库连接不可用，操作将被跳过")
                return None
            return self.__class__._db_connection
        # 优先级3：全局默认连接
        if self.__class__._default_db_connection is not None:
            # 检查连接是否可用
            if hasattr(self.__class__._default_db_connection,
                       'is_available') and not self.__class__._default_db_connection.is_available():
                logger.debug(f"全局默认数据库连接不可用，操作将被跳过")
                return None
            return self.__class__._default_db_connection
        # 返回 None 而不是抛出异常
        logger.warning(f"数据库连接未设置，操作将被跳过")
        return None

    @classmethod
    def get_db_connection(cls) -> Optional[BaseConnection]:
        """获取数据库连接（类方法，用于类级别的操作），如果未设置则返回 None"""
        if cls._db_connection is not None:
            # 检查连接是否可用
            if hasattr(cls._db_connection, 'is_available') and not cls._db_connection.is_available():
                logger.debug(f"类级别的数据库连接不可用，操作将被跳过")
                return None
            return cls._db_connection
        if cls._default_db_connection is not None:
            # 检查连接是否可用
            if hasattr(cls._default_db_connection, 'is_available') and not cls._default_db_connection.is_available():
                logger.debug(f"全局默认数据库连接不可用，操作将被跳过")
                return None
            return cls._default_db_connection
        # 返回 None 而不是抛出异常
        logger.warning(f"数据库连接未设置，操作将被跳过")
        return None

    @classmethod
    def get_table_name(cls) -> str:
        """获取表名，优先使用 table_alias，否则使用类名小写"""
        if cls.table_alias:
            return cls.table_alias
        # 将类名从驼峰转换为下划线命名
        class_name = cls.__name__
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        table_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        return table_name

    @classmethod
    def get_table_name_with_db(cls) -> str:
        """获取带数据库名的表名，格式：`database`.`table`"""
        db = cls.get_db_connection()
        if db and db.config.get("database"):
            database = db.config["database"]
            table_name = cls.get_table_name()
            return f"`{database}`.`{table_name}`"
        else:
            # 如果没有配置数据库名，则只返回表名
            return f"`{cls.get_table_name()}`"

    @classmethod
    def table_exists(cls) -> bool:
        """
        检查表是否存在
        支持 MySQL、PostgreSQL 和 SQLite
        """
        db = cls.get_db_connection()
        if db is None:
            logger.warning(f"检查表 {cls.get_table_name()} 是否存在失败：数据库连接未设置")
            return False

        table_name = cls.get_table_name()

        # 根据数据库类型使用不同的查询方式
        db_type = db.config.get("type", "mysql").lower()

        try:
            if db_type == "sqlite":
                # SQLite 使用 sqlite_master 表
                sql = """
                      SELECT 1
                      FROM sqlite_master
                      WHERE type = 'table'
                        AND name = %s \
                      """
                result = db.execute(sql, (table_name,))
            elif db_type == "postgresql":
                # PostgreSQL 使用 information_schema
                sql = """
                      SELECT 1
                      FROM information_schema.tables
                      WHERE table_schema = 'public'
                        AND table_name = %s \
                      """
                result = db.execute(sql, (table_name,))
            else:
                # MySQL 使用 information_schema
                database = db.config.get("database")
                if database is None:
                    logger.warning(f"检查表 {table_name} 是否存在失败：MySQL 配置中缺少 database 参数")
                    return False
                sql = """
                      SELECT 1
                      FROM information_schema.tables
                      WHERE table_schema = %s
                        AND table_name = %s \
                      """
                result = db.execute(sql, (database, table_name))

            return len(result) > 0
        except Exception as e:
            logger.error(f"检查表 {table_name} 是否存在失败：{str(e)}")
            return False

    @classmethod
    def get_create_table_sql(cls) -> Optional[str]:
        """
        获取建表 SQL
        优先级：手动声明的 SQL > 自动生成的 SQL
        """
        # 暂时只支持手动声明
        if cls.create_table_sql is None:
            logger.warning(f"类 {cls.__name__} 未定义 create_table_sql，无法创建表")
            return None

        # 替换表名占位符（如果有）
        table_name = cls.get_table_name()
        return cls.create_table_sql.replace("{{table_name}}", table_name)

    @classmethod
    def create_table(cls) -> bool:
        """创建表（使用手动声明的建表 SQL），返回是否成功"""
        db = cls.get_db_connection()
        if db is None:
            logger.warning(f"创建表 {cls.get_table_name()} 失败：数据库连接未设置")
            return False

        sql = cls.get_create_table_sql()
        if sql is None:
            return False

        try:
            res = db.execute(sql, commit=True)
            if res >= 0:
                logger.info(f"表 {cls.get_table_name()} 创建成功")
                return True
            else:
                logger.error(f"表 {cls.get_table_name()} 创建失败")
                return False

        except Exception as e:
            logger.error(f"创建表 {cls.get_table_name()} 失败：{str(e)}")
            return False

    @classmethod
    def _ensure_table_exists(cls) -> None:
        """
        确保表存在，不存在则自动创建；同时自动补齐缺失的列
        使用缓存机制避免重复检查
        """
        # 如果已经检查过，直接返回
        if cls._table_checked:
            return

        # 检查表是否存在
        table_just_created = False
        try:
            if not cls.table_exists():
                logger.info(f"表 {cls.get_table_name()} 不存在，开始创建...")
                cls.create_table()
                table_just_created = True
        except Exception as e:
            logger.warning(f"检查或创建表 {cls.get_table_name()} 失败：{str(e)}")

        # 新创建的表不需要检查列（建表 SQL 已包含所有列）
        if not table_just_created:
            cls._ensure_columns_exist()

        # 标记为已检查
        cls._table_checked = True

    @classmethod
    def _get_db_columns(cls) -> set:
        """获取数据库中表的现有列名集合"""
        db = cls.get_db_connection()
        if db is None:
            return set()

        table_name = cls.get_table_name()
        db_type = db.config.get("type", "mysql").lower()

        try:
            if db_type == "sqlite":
                sql = f"PRAGMA table_info(`{table_name}`)"
                result = db.execute(sql)
                return {row['name'] for row in result} if result else set()
            elif db_type == "postgresql":
                sql = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                """
                result = db.execute(sql, (table_name,))
            else:
                # MySQL
                database = db.config.get("database")
                sql = """
                    SELECT COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """
                result = db.execute(sql, (database, table_name))

            return {row[list(row.keys())[0]] for row in result} if result else set()
        except Exception as e:
            logger.warning(f"获取表 {table_name} 列信息失败：{str(e)}")
            return set()

    @classmethod
    def _parse_column_defs_from_sql(cls) -> dict:
        """
        从 create_table_sql 中解析列定义。
        返回 {列名: 列定义} 的字典，如 {'audio_text_origin_path': 'VARCHAR(500) COMMENT ...'}
        """
        if not cls.create_table_sql:
            return {}

        import re
        defs = {}
        # 逐行解析，只匹配以反引号列名开头的行（排除 KEY/INDEX/PRIMARY/UNIQUE 等约束行）
        for line in cls.create_table_sql.splitlines():
            stripped = line.strip()
            # 跳过空行、注释行
            if not stripped or stripped.startswith('--') or stripped.startswith('/*'):
                continue
            # 跳过约束/索引行（PRIMARY KEY, UNIQUE KEY, KEY, INDEX, CONSTRAINT, CHECK）
            upper_stripped = stripped.upper()
            if any(upper_stripped.startswith(kw) for kw in
                   ('PRIMARY', 'UNIQUE', 'KEY', 'INDEX', 'CONSTRAINT', 'CHECK',
                    'CREATE', 'ENGINE', ')')):
                continue
            # 匹配 `column_name` definition ...
            match = re.match(r'`(\w+)`\s+(.+)', stripped)
            if match:
                col_name = match.group(1)
                col_def = match.group(2).rstrip(',').strip()
                defs[col_name] = col_def
        return defs

    @classmethod
    def _ensure_columns_exist(cls) -> None:
        """
        检查模型中定义的字段是否在数据库表中都存在，缺失的自动 ALTER TABLE 添加。
        仅处理模型字段（model_fields），跳过非 DB 列。
        """
        if not cls.create_table_sql:
            return

        db = cls.get_db_connection()
        if db is None:
            return

        existing_cols = cls._get_db_columns()
        if not existing_cols:
            return

        # 从建表 SQL 中解析列定义
        col_defs = cls._parse_column_defs_from_sql()

        # 获取模型字段名
        model_fields = set(cls.model_fields.keys())

        # 找出模型中有定义但数据库中不存在的列
        missing_cols = model_fields - existing_cols
        # 排除 id（通常已有）和 ClassVar 等非 DB 字段
        missing_cols.discard('id')

        if not missing_cols:
            return

        table_name = cls.get_table_name_with_db()

        for col_name in missing_cols:
            if col_name not in col_defs:
                logger.warning(
                    f"表 {cls.get_table_name()} 缺少列 `{col_name}`，"
                    f"但未在建表 SQL 中找到定义，跳过自动添加"
                )
                continue

            col_def = col_defs[col_name]
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN `{col_name}` {col_def}"
            try:
                db.execute(alter_sql, commit=True)
                logger.info(f"表 {cls.get_table_name()} 自动添加缺失列：`{col_name}`")
            except Exception as e:
                logger.warning(f"添加缺失列 `{col_name}` 失败：{str(e)}")

    @classmethod
    def get_by_id(cls: Type[T], id_val: int) -> Optional[T]:
        """根据ID查询记录"""
        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                logger.warning(f"{cls.__name__}.get_by_id({id_val}) 失败：数据库连接未设置")
                return None
            table_name = cls.get_table_name_with_db()
            sql = f"SELECT * FROM {table_name} WHERE id = %s"
            result = db.execute(sql, (id_val,))

            if not result:
                return None

            return cls(**result[0])
        except Exception as e:
            logger.error(f"{cls.__name__}.get_by_id({id_val}) 失败：{str(e)}")
            return None

    @classmethod
    def get_all(cls: Type[T], limit: Optional[int] = None, offset: int = 0,
                order_by: Optional[str] = None, order: Literal['ASC', 'DESC'] = 'ASC') -> List[T]:
        """
        查询所有记录，支持排序和分页

        Args:
            limit: 返回记录数限制（可选）
            offset: 起始偏移量，默认为0
            order_by: 排序字段名（可选），如 'id', 'created_at'
            order: 排序方向，'ASC'（升序）或 'DESC'（降序），默认为 'ASC'

        Returns:
            所有记录列表

        Example:
            # 查询所有记录
            users = User.get_all()

            # 分页查询
            users = User.get_all(limit=20, offset=10)

            # 按ID升序查询
            users = User.get_all(order_by='id', order='ASC')

            # 按创建时间降序查询
            users = User.get_all(order_by='created_at', order='DESC')

            # 分页 + 排序
            users = User.get_all(limit=20, offset=10, order_by='created_at', order='DESC')
        """
        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                logger.warning(f"{cls.__name__}.get_all() 失败：数据库连接未设置")
                return []
            table_name = cls.get_table_name_with_db()
            sql = f"SELECT * FROM {table_name}"

            # 添加 ORDER BY 子句
            if order_by is not None:
                sql += f" ORDER BY `{order_by}` {order}"

            # 添加 LIMIT 和 OFFSET
            if limit is not None:
                sql += f" LIMIT {offset}, {limit}"

            results = db.execute(sql)
            return [cls(**row) for row in results]
        except Exception as e:
            logger.error(f"{cls.__name__}.get_all() 失败：{str(e)}")
            return []

    @classmethod
    def find_by(cls: Type[T], limit: Optional[int] = None, offset: int = 0,
                order_by: Optional[str] = None, order: Literal['ASC', 'DESC'] = 'ASC', **filters) -> List[T]:
        """
        根据条件查询记录，支持排序和分页

        Args:
            limit: 返回记录数限制（可选）
            offset: 起始偏移量，默认为0
            order_by: 排序字段名（可选），如 'id', 'created_at'
            order: 排序方向，'ASC'（升序）或 'DESC'（降序），默认为 'ASC'
            **filters: 查询条件（键值对）

        Returns:
            符合条件的记录列表

        Example:
            # 基本查询
            users = User.find_by(status='active')

            # 分页查询（从第10条开始，返回20条）
            users = User.find_by(status='active', limit=20, offset=10)

            # 按ID升序查询
            users = User.find_by(status='active', order_by='id', order='ASC')

            # 按创建时间降序查询
            users = User.find_by(status='active', order_by='created_at', order='DESC')

            # 分页 + 排序
            users = User.find_by(status='active', limit=20, offset=10, order_by='created_at', order='DESC')
        """
        if not filters:
            return cls.get_all(limit=limit, offset=offset, order_by=order_by, order=order)

        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                logger.warning(f"{cls.__name__}.find_by({filters}) 失败：数据库连接未设置")
                return []
            table_name = cls.get_table_name_with_db()

            where_clauses = []
            params = []
            for key, value in filters.items():
                where_clauses.append(f"`{key}` = %s")
                params.append(value)

            sql = f"SELECT * FROM {table_name} WHERE {' AND '.join(where_clauses)}"

            # 添加 ORDER BY 子句
            if order_by is not None:
                sql += f" ORDER BY `{order_by}` {order}"

            # 添加 LIMIT 和 OFFSET
            if limit is not None:
                sql += f" LIMIT {offset}, {limit}"

            results = db.execute(sql, tuple(params))
            return [cls(**row) for row in results]
        except Exception as e:
            logger.error(
                f"{cls.__name__}.find_by({filters}, limit={limit}, offset={offset}, order_by={order_by}, order={order}) 失败：{str(e)}")
            return []

    @classmethod
    def find_one_by(cls: Type[T], order_by: Optional[str] = None, order: Literal['ASC', 'DESC'] = 'ASC', **filters) -> \
    Optional[T]:
        """
        根据条件查询单条记录（只返回第一条）

        Args:
            order_by: 排序字段名（可选），如 'id', 'created_at'
            order: 排序方向，'ASC'（升序）或 'DESC'（降序），默认为 'ASC'
            **filters: 查询条件（键值对）

        Returns:
            第一条匹配的记录，未找到返回 None

        Example:
            # 查询单条记录
            user = User.find_one_by(email='test@example.com')

            # 按ID升序查询单条记录
            user = User.find_one_by(email='test@example.com', order_by='id', order='ASC')

            # 按创建时间降序查询单条记录
            user = User.find_one_by(status='active', order_by='created_at', order='DESC')
        """
        results = cls.find_by(limit=1, order_by=order_by, order=order, **filters)
        return results[0] if results else None

    def save(self) -> int:
        """保存记录（插入或更新），返回ID"""
        try:
            self.__class__._ensure_table_exists()
            if self.id is None:
                return self._insert()
            else:
                self._update()
                return self.id
        except Exception as e:
            logger.error(f"{self.__class__.__name__}.save() 失败：{str(e)}")
            return -1

    def _insert(self) -> int:
        """插入记录，返回新插入的ID"""
        db = self.get_db_connection()
        if db is None:
            logger.warning(f"{self.__class__.__name__}._insert() 失败：数据库连接未设置")
            return -1

        table_name = self.get_table_name_with_db()

        # 获取所有字段（排除 None 值和内部字段）
        data = self.model_dump(exclude_none=True, exclude={'id'})

        if not data:
            logger.warning(f"{self.__class__.__name__}._insert() 失败：没有可插入的数据")
            return -1

        try:
            keys = list(data.keys())
            placeholders = ",".join(["%s"] * len(keys))
            # 为列名添加反引号，避免 MySQL 保留关键字冲突
            quoted_keys = [f"`{k}`" for k in keys]
            sql = f"INSERT INTO {table_name} ({','.join(quoted_keys)}) VALUES ({placeholders})"

            self.id = db.execute(sql, tuple(data[k] for k in keys))
            return self.id
        except Exception as e:
            logger.error(f"{self.__class__.__name__}._insert() 失败：{str(e)}")
            return -1

    def _update(self) -> bool:
        """更新记录，返回是否成功"""
        db = self.get_db_connection()
        if db is None:
            logger.warning(f"{self.__class__.__name__}._update() 失败：数据库连接未设置")
            return False

        table_name = self.get_table_name_with_db()

        # 获取所有字段（排除 None 值和内部字段）
        data = self.model_dump(exclude_none=True, exclude={'id'})

        if not data:
            return True

        try:
            # 为列名添加反引号，避免 MySQL 保留关键字冲突
            sets = ",".join([f"`{k}`=%s" for k in data])
            sql = f"UPDATE {table_name} SET {sets} WHERE id = %s"

            affected = db.execute(sql, tuple(data.values()) + (self.id,))
            if affected is None or affected < 0:
                logger.warning(f"{self.__class__.__name__}._update() 执行异常，affected={affected}, id={self.id}")
                return False
            return True
        except Exception as e:
            logger.error(f"{self.__class__.__name__}._update() 失败：{str(e)}")
            return False

    def update(self, **fields) -> bool:
        """更新指定字段"""
        try:
            for key, value in fields.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return self._update()
        except Exception as e:
            logger.error(f"{self.__class__.__name__}.update({fields}) 失败：{str(e)}")
            return False

    def delete(self) -> bool:
        """删除记录，返回是否成功"""
        if self.id is None:
            logger.warning(f"{self.__class__.__name__}.delete() 失败：无法删除未保存的记录")
            return False

        try:
            self.__class__._ensure_table_exists()
            db = self.get_db_connection()
            if db is None:
                logger.warning(f"{self.__class__.__name__}.delete() 失败：数据库连接未设置")
                return False
            table_name = self.get_table_name_with_db()
            sql = f"DELETE FROM {table_name} WHERE id = %s"

            affected = db.execute(sql, (self.id,))
            return affected > 0
        except Exception as e:
            logger.error(f"{self.__class__.__name__}.delete() 失败：{str(e)}")
            return False

    @classmethod
    def delete_by_id(cls, id_val: int) -> bool:
        """根据ID删除记录"""
        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                logger.warning(f"{cls.__name__}.delete_by_id({id_val}) 失败：数据库连接未设置")
                return False
            table_name = cls.get_table_name_with_db()
            sql = f"DELETE FROM {table_name} WHERE id = %s"

            affected = db.execute(sql, (id_val,))
            return affected > 0
        except Exception as e:
            logger.error(f"{cls.__name__}.delete_by_id({id_val}) 失败：{str(e)}")
            return False

    @classmethod
    def bulk_insert(cls, instances: List['BaseDBModel'], batch_size: int = 1000) -> List[int]:
        """
        批量插入记录（高效插入）

        使用单条 SQL 语句插入多条记录，提高性能。

        Args:
            instances: BaseDBModel 实例列表
            batch_size: 每批插入的记录数，默认 1000（大数据量时建议分批）

        Returns:
            新插入记录的 ID 列表

        Example:
            # 创建多个对象
            users = [
                User(name="张三", email="zhangsan@example.com"),
                User(name="李四", email="lisi@example.com"),
                User(name="王五", email="wangwu@example.com")
            ]

            # 批量插入
            ids = User.bulk_insert(users)
            print(f"插入了 {len(ids)} 条记录，IDs: {ids}")

            # 大数据量分批插入
            large_data = [User(name=f"用户{i}") for i in range(10000)]
            ids = User.bulk_insert(large_data, batch_size=500)
        """
        if not instances:
            logger.warning(f"{cls.__name__}.bulk_insert() 失败：实例列表为空")
            return []

        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                logger.warning(f"{cls.__name__}.bulk_insert() 失败：数据库连接未设置")
                return []

            table_name = cls.get_table_name_with_db()

            # 确定所有对象共有的字段（取所有字段的并集）
            all_fields = set()
            for instance in instances:
                data = instance.model_dump(exclude_none=True, exclude={'id'})
                all_fields.update(data.keys())

            if not all_fields:
                logger.warning(f"{cls.__name__}.bulk_insert() 失败：没有可插入的数据")
                return []

            fields = list(all_fields)
            quoted_fields = [f"`{f}`" for f in fields]

            # 分批插入
            all_ids = []
            total_instances = len(instances)

            for i in range(0, total_instances, batch_size):
                batch = instances[i:i + batch_size]
                batch_data = []

                # 构建批量数据
                for instance in batch:
                    data = instance.model_dump(exclude_none=False, exclude={'id'})
                    # 按照字段顺序取值
                    row_data = [data.get(field) for field in fields]
                    batch_data.append(row_data)

                # 构建批量插入 SQL
                placeholders = ",".join([f"({','.join(['%s'] * len(fields))})"] * len(batch_data))
                sql = f"INSERT INTO {table_name} ({','.join(quoted_fields)}) VALUES {placeholders}"

                # 展平参数列表
                params = [item for row in batch_data for item in row]

                # 执行批量插入
                try:
                    batch_size_actual = len(batch_data)
                    db.execute(sql, tuple(params), commit=True)
                    logger.info(f"批量插入SQL执行成功，本批 {batch_size_actual} 条")

                    # 获取插入的 ID（MySQL）
                    # 注意：不同数据库获取批量插入 ID 的方式不同
                    db_config = getattr(db, 'config', {})
                    logger.debug(f"数据库配置: {db_config}, type类型: {db_config.get('type', 'mysql')}")

                    if hasattr(db, 'config') and db.config.get("type", "mysql").lower() == "mysql":
                        logger.info("检测到MySQL数据库，尝试获取插入ID")
                        # MySQL: 获取最后插入的 ID，批量插入的 ID 是连续的
                        result = db.execute("SELECT LAST_INSERT_ID() as last_id")
                        logger.info(f"LAST_INSERT_ID() 查询结果: {result}")

                        if result and result[0]:
                            last_id = int(result[0]['last_id'])
                            logger.info(f"last_id 值: {last_id}, 类型: {type(last_id)}")
                            if last_id > 0:
                                start_id = last_id - batch_size_actual + 1
                                id_range = list(range(start_id, last_id + 1))
                                all_ids.extend(id_range)
                                logger.info(f"成功添加ID到列表: {id_range}, 当前all_ids长度: {len(all_ids)}")
                    else:
                        # 其他数据库：无法准确获取批量插入的 ID，返回空列表
                        logger.warning(
                            f"{cls.__name__}.bulk_insert() 批量插入成功，但当前数据库类型不支持返回 ID 列表"
                        )

                    logger.info(
                        f"{cls.__name__}.bulk_insert() 成功：第 {i // batch_size + 1} 批，"
                        f"本批插入 {batch_size_actual} 条记录，累计插入 {len(all_ids) + batch_size_actual} 条"
                    )

                except Exception as e:
                    logger.error(
                        f"{cls.__name__}.bulk_insert() 批量插入失败（第 {i // batch_size + 1} 批）：{str(e)}"
                    )
                    raise

            return all_ids

        except Exception as e:
            logger.error(f"{cls.__name__}.bulk_insert() 失败：{str(e)}")
            return []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()

    @classmethod
    def count(cls) -> int:
        """查询记录总数"""
        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                logger.warning(f"{cls.__name__}.count() 失败：数据库连接未设置")
                return 0
            table_name = cls.get_table_name_with_db()
            sql = f"SELECT COUNT(*) as count FROM {table_name}"
            result = db.execute(sql)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"{cls.__name__}.count() 失败：{str(e)}")
            return 0
