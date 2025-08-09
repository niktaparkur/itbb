from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
    Index,
    Integer,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    subscription_expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    last_url_check_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    single_check_credits: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped["User"] = relationship()


class SearchableItem(Base):
    __tablename__ = "searchable_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text, nullable=True)

    search_vector: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index("ix_search_vector_fulltext", "search_vector", mysql_prefix="FULLTEXT"),
    )

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name[:30]}...')>"
