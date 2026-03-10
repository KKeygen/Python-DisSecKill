from sqlalchemy import BigInteger, Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Inventory(Base):
    __tablename__ = "df_inventory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    goods_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    locked_stock: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
