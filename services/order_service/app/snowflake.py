"""
雪花算法（Snowflake）订单ID生成器 + 基因法分片支持

ID结构（64位）:
┌─────────┬──────────────────────┬────────────┬─────────────┬──────────┐
│ 1 bit   │ 41 bits              │ 10 bits    │ 11 bits     │ 1 bit    │
│ 符号位  │ 毫秒级时间戳         │ 机器ID     │ 序列号      │ 基因位   │
│ (恒为0) │ (约69年)             │ (0~1023)   │ (0~2047)    │ uid%2    │
└─────────┴──────────────────────┴────────────┴─────────────┴──────────┘

基因法说明:
  将 user_id % db_count 嵌入订单ID最低位，使得:
  - order_id % 2 == user_id % 2
  - 通过 order_id 即可反查所在分库，无需额外查询
"""

import time
import threading


# 自定义纪元: 2024-01-01T00:00:00Z (毫秒)
EPOCH = 1704067200000

# 各字段位数
GENE_BITS = 1       # 基因位（用于分库路由）
SEQUENCE_BITS = 11  # 序列号
WORKER_BITS = 10    # 机器ID
TIMESTAMP_BITS = 41 # 时间戳

# 最大值
MAX_GENE = (1 << GENE_BITS) - 1           # 1
MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1   # 2047
MAX_WORKER_ID = (1 << WORKER_BITS) - 1    # 1023

# 位移量
GENE_SHIFT = 0
SEQUENCE_SHIFT = GENE_BITS                              # 1
WORKER_SHIFT = GENE_BITS + SEQUENCE_BITS                # 12
TIMESTAMP_SHIFT = GENE_BITS + SEQUENCE_BITS + WORKER_BITS  # 22


class SnowflakeGenerator:
    """
    线程安全的雪花ID生成器

    使用方法:
        gen = SnowflakeGenerator(worker_id=1, db_count=2)
        order_id = gen.generate(user_id=12345)
    """

    def __init__(self, worker_id: int = 0, db_count: int = 2):
        """
        初始化生成器

        Args:
            worker_id: 机器/实例ID (0~1023)，不同服务实例需不同值
            db_count:  分库数量，基因 = user_id % db_count
        """
        if not 0 <= worker_id <= MAX_WORKER_ID:
            raise ValueError(f"worker_id 必须在 0~{MAX_WORKER_ID} 之间")
        self._worker_id = worker_id
        self._db_count = db_count
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    def generate(self, user_id: int) -> int:
        """
        生成带基因的雪花ID

        Args:
            user_id: 用户ID，用于计算基因位

        Returns:
            64位整数订单ID
        """
        with self._lock:
            timestamp = self._current_millis()

            # 时钟回拨检测
            if timestamp < self._last_timestamp:
                raise RuntimeError(
                    f"时钟回拨! 当前={timestamp}, 上次={self._last_timestamp}, "
                    f"差值={self._last_timestamp - timestamp}ms"
                )

            if timestamp == self._last_timestamp:
                # 同一毫秒内递增序列号
                self._sequence = (self._sequence + 1) & MAX_SEQUENCE
                if self._sequence == 0:
                    # 序列号溢出，等待下一毫秒
                    timestamp = self._wait_next_millis(self._last_timestamp)
            else:
                self._sequence = 0

            self._last_timestamp = timestamp

            # 计算基因位
            gene = user_id % self._db_count

            # 组装ID
            snowflake_id = (
                ((timestamp - EPOCH) << TIMESTAMP_SHIFT)
                | (self._worker_id << WORKER_SHIFT)
                | (self._sequence << SEQUENCE_SHIFT)
                | (gene << GENE_SHIFT)
            )

            return snowflake_id

    @staticmethod
    def extract_gene(order_id: int) -> int:
        """从订单ID中提取基因位（即分库索引）"""
        return order_id & MAX_GENE

    @staticmethod
    def extract_timestamp(order_id: int) -> int:
        """从订单ID中提取时间戳（毫秒）"""
        return ((order_id >> TIMESTAMP_SHIFT) & ((1 << TIMESTAMP_BITS) - 1)) + EPOCH

    @staticmethod
    def _current_millis() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _wait_next_millis(last_ts: int) -> int:
        ts = int(time.time() * 1000)
        while ts <= last_ts:
            ts = int(time.time() * 1000)
        return ts


# ==================== 全局单例 ====================
_generator: SnowflakeGenerator | None = None


def init_snowflake(worker_id: int = 0, db_count: int = 2) -> SnowflakeGenerator:
    """初始化全局雪花ID生成器"""
    global _generator
    _generator = SnowflakeGenerator(worker_id=worker_id, db_count=db_count)
    return _generator


def generate_order_id(user_id: int) -> int:
    """生成订单ID（使用全局生成器）"""
    global _generator
    if _generator is None:
        _generator = SnowflakeGenerator()
    return _generator.generate(user_id)
