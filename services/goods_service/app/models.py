from sqlalchemy import BigInteger, String, Boolean, DateTime, SmallInteger, Text, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class GoodsCategory(Base):
    __tablename__ = "df_goods_category"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Goods(Base):
    __tablename__ = "df_goods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    desc: Mapped[str | None] = mapped_column("desc", Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="件")
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_seckill: Mapped[bool] = mapped_column(Boolean, default=False)
    seckill_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    seckill_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    seckill_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
