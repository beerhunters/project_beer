from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    BigInteger,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import relationship
from bot.core.database import Base
import enum


class BeerTypeEnum(enum.Enum):
    LAGER = "LAGER"
    HAND_OF_GOD = "HAND_OF_GOD"


# Изменено: create_type=False на create_type=True
BeerType = PgEnum(BeerTypeEnum, name="beer_type_enum", create_type=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(32), nullable=True)
    name = Column(String(50), nullable=False)
    birth_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    choices = relationship(
        "BeerChoice", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, name='{self.name}')>"
        )


class BeerChoice(Base):
    __tablename__ = "beer_choices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    beer_type = Column(BeerType, nullable=False)
    selected_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="choices")

    def __repr__(self):
        return f"<BeerChoice(id={self.id}, user_id={self.user_id}, beer_type='{self.beer_type.value if isinstance(self.beer_type, enum.Enum) else self.beer_type}')>"
