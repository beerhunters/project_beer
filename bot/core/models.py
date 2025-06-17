from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    BigInteger,
    func,
    Boolean,
    Text,
    Time,
    Float,
)
from sqlalchemy.orm import relationship
from bot.core.database import Base
import pendulum


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
    beer_choice = Column(String(100), nullable=False)
    selected_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="choices")

    def __repr__(self):
        return f"<BeerChoice(id={self.id}, user_id={self.user_id}, beer_choice='{self.beer_choice}')>"


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    event_date = Column(Date, nullable=False)
    event_time = Column(Time, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String(500), nullable=True)
    description = Column(String(1000))
    image_file_id = Column(String(200))
    has_beer_choice = Column(Boolean, default=False, nullable=False)
    beer_option_1 = Column(String(100), nullable=True)
    beer_option_2 = Column(String(100), nullable=True)
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    celery_task_id = Column(String(200), nullable=True)

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', date={self.event_date}, time={self.event_time})>"


class EventParticipant(Base):
    __tablename__ = "event_participants"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    participant_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EventParticipant(id={self.id}, event_id={self.event_id}, participant_count={self.participant_count})>"
