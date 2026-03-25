"""
订单分库分表路由模块（Python等价 ShardingSphere-JDBC）

分片策略:
  - 分库: user_id % DB_COUNT → 库索引 (0, 1)
  - 分表: (order_id >> 1) % TABLE_COUNT → 表索引 (0, 1)
  - 基因法: order_id 最低位 = user_id % DB_COUNT
    → 通过 order_id 可直接反查分库，无需额外查询

分片拓扑:
  disseckill_order_0          disseckill_order_1
  ├── df_order_0              ├── df_order_0
  └── df_order_1              └── df_order_1

路由示例:
  user_id=100, order_id=...0 → db_0.df_order_X
  user_id=101, order_id=...1 → db_1.df_order_X
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

logger = logging.getLogger("sharding")

# ==================== 分片常量 ====================
DB_COUNT = 2      # 分库数量
TABLE_COUNT = 2   # 每库分表数量
DB_PREFIX = "disseckill_order"  # 库名前缀
TABLE_PREFIX = "df_order"       # 表名前缀


class ShardingRouter:
    """分片路由器：根据 user_id / order_id 计算目标库表"""

    @staticmethod
    def db_index_by_user(user_id: int) -> int:
        """按用户ID计算分库索引"""
        return user_id % DB_COUNT

    @staticmethod
    def db_index_by_order(order_id: int) -> int:
        """按订单ID反查分库索引（基因法）"""
        return order_id & (DB_COUNT - 1)  # 最低位即基因

    @staticmethod
    def table_index_by_order(order_id: int) -> int:
        """按订单ID计算分表索引"""
        return (order_id >> 1) % TABLE_COUNT

    @staticmethod
    def db_name(db_idx: int) -> str:
        return f"{DB_PREFIX}_{db_idx}"

    @staticmethod
    def table_name(table_idx: int) -> str:
        return f"{TABLE_PREFIX}_{table_idx}"

    @classmethod
    def resolve(cls, user_id: int, order_id: int) -> tuple[str, str]:
        """
        完整路由：返回 (库名, 表名)

        Args:
            user_id:  用户ID（分库依据）
            order_id: 订单ID（分表依据，且最低位=基因=user_id%2）
        """
        db_idx = cls.db_index_by_user(user_id)
        tbl_idx = cls.table_index_by_order(order_id)
        return cls.db_name(db_idx), cls.table_name(tbl_idx)

    @classmethod
    def resolve_by_order_id(cls, order_id: int) -> tuple[str, str]:
        """仅通过订单ID定位库表（利用基因位反查分库）"""
        db_idx = cls.db_index_by_order(order_id)
        tbl_idx = cls.table_index_by_order(order_id)
        return cls.db_name(db_idx), cls.table_name(tbl_idx)

    @classmethod
    def all_shards_for_user(cls, user_id: int) -> list[tuple[str, str]]:
        """获取某用户所有可能的分片（用于按user_id查询全部订单）"""
        db_idx = cls.db_index_by_user(user_id)
        db = cls.db_name(db_idx)
        return [(db, cls.table_name(t)) for t in range(TABLE_COUNT)]


class ShardingManager:
    """
    分片连接管理器

    管理多个数据库的连接池，提供统一的会话获取接口。
    等价于 ShardingSphere-JDBC 的 DataSource 路由层。
    """

    def __init__(self):
        self._engines: dict[str, object] = {}
        self._session_factories: dict[str, async_sessionmaker] = {}

    def init_engines(self, base_url_template: str, pool_size: int = 10, max_overflow: int = 5):
        """
        初始化所有分片库的连接引擎

        Args:
            base_url_template: 数据库URL模板，使用 {db_name} 占位符
                例: "mysql+aiomysql://root:pass@host:3306/{db_name}?charset=utf8mb4"
            pool_size: 每个分片的连接池大小
            max_overflow: 每个分片的最大溢出连接数
        """
        for i in range(DB_COUNT):
            db_name = ShardingRouter.db_name(i)
            url = base_url_template.format(db_name=db_name)
            engine = create_async_engine(url, echo=False, pool_size=pool_size, max_overflow=max_overflow)
            self._engines[db_name] = engine
            self._session_factories[db_name] = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info(f"分片引擎初始化: {db_name}")

    def get_session_factory(self, db_name: str) -> async_sessionmaker:
        """获取指定分片库的会话工厂"""
        if db_name not in self._session_factories:
            raise ValueError(f"未知分片库: {db_name}")
        return self._session_factories[db_name]

    async def get_session(self, db_name: str) -> AsyncSession:
        """获取指定分片库的数据库会话"""
        factory = self.get_session_factory(db_name)
        return factory()

    async def execute_on_shard(
        self, user_id: int, order_id: int, sql_template: str, params: dict
    ) -> object:
        """
        在目标分片上执行SQL

        Args:
            user_id:      用户ID
            order_id:     订单ID
            sql_template: SQL模板，使用 {table} 占位符
            params:       SQL参数字典
        """
        db_name, table_name = ShardingRouter.resolve(user_id, order_id)
        sql = sql_template.replace("{table}", f"{table_name}")
        async with await self.get_session(db_name) as session:
            async with session.begin():
                result = await session.execute(text(sql), params)
                return result

    async def insert_order(self, order_id: int, user_id: int, goods_id: int,
                           count: int, total_price: float, is_seckill: bool = False,
                           address: str | None = None) -> None:
        """插入订单到正确的分片"""
        db_name, table_name = ShardingRouter.resolve(user_id, order_id)
        sql = f"""
            INSERT INTO {table_name}
                (id, user_id, goods_id, `count`, total_price, is_seckill, address, order_status, pay_method)
            VALUES
                (:id, :user_id, :goods_id, :count, :total_price, :is_seckill, :address, 1, 3)
        """
        params = {
            "id": order_id, "user_id": user_id, "goods_id": goods_id,
            "count": count, "total_price": total_price,
            "is_seckill": is_seckill, "address": address,
        }
        async with await self.get_session(db_name) as session:
            async with session.begin():
                await session.execute(text(sql), params)
        logger.info(f"订单写入分片: {db_name}.{table_name}, order_id={order_id}")

    async def query_order_by_id(self, order_id: int, user_id: int | None = None) -> dict | None:
        """
        按订单ID查询订单

        如果提供 user_id，直接定位分片；否则通过基因法从 order_id 反查分库。
        """
        if user_id is not None:
            db_name, table_name = ShardingRouter.resolve(user_id, order_id)
        else:
            db_name, table_name = ShardingRouter.resolve_by_order_id(order_id)

        sql = f"SELECT * FROM {table_name} WHERE id = :order_id"
        async with await self.get_session(db_name) as session:
            result = await session.execute(text(sql), {"order_id": order_id})
            row = result.mappings().first()
            return dict(row) if row else None

    async def query_orders_by_user(
        self, user_id: int, page: int = 1, size: int = 10,
        order_status: int | None = None
    ) -> tuple[list[dict], int]:
        """
        按用户ID查询订单列表（聚合该用户所有分表结果）
        """
        shards = ShardingRouter.all_shards_for_user(user_id)
        all_orders = []
        total = 0

        for db_name, table_name in shards:
            # 查总数
            count_sql = f"SELECT COUNT(*) as cnt FROM {table_name} WHERE user_id = :user_id"
            # 查数据
            data_sql = f"""
                SELECT * FROM {table_name}
                WHERE user_id = :user_id
            """
            params: dict = {"user_id": user_id}

            if order_status is not None:
                count_sql += " AND order_status = :status"
                data_sql += " AND order_status = :status"
                params["status"] = order_status

            data_sql += " ORDER BY create_time DESC"

            async with await self.get_session(db_name) as session:
                cnt_result = await session.execute(text(count_sql), params)
                total += cnt_result.scalar() or 0

                rows = await session.execute(text(data_sql), params)
                for row in rows.mappings():
                    all_orders.append(dict(row))

        # 内存排序 + 分页（多表聚合后在应用层分页）
        all_orders.sort(key=lambda o: o.get("create_time", ""), reverse=True)
        start = (page - 1) * size
        paged = all_orders[start: start + size]
        return paged, total

    async def close(self):
        """关闭所有分片引擎"""
        for db_name, engine in self._engines.items():
            await engine.dispose()
            logger.info(f"分片引擎关闭: {db_name}")


# ==================== 全局单例 ====================
_manager: ShardingManager | None = None


def get_sharding_manager() -> ShardingManager:
    """获取全局分片管理器"""
    global _manager
    if _manager is None:
        _manager = ShardingManager()
    return _manager


def init_sharding_manager(base_url_template: str) -> ShardingManager:
    """初始化全局分片管理器"""
    global _manager
    _manager = ShardingManager()
    _manager.init_engines(base_url_template)
    return _manager
