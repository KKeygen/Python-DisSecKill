from sqlalchemy import BigInteger, String, SmallInteger, Boolean, DateTime, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "df_order"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    goods_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    count: Mapped[int] = mapped_column(default=1)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    pay_method: Mapped[int] = mapped_column(SmallInteger, default=3)
    order_status: Mapped[int] = mapped_column(SmallInteger, default=1)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_seckill: Mapped[bool] = mapped_column(Boolean, default=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
