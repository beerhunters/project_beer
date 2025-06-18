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
    Index,
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
    group_users = relationship(
        "GroupUser", back_populates="user", cascade="all, delete-orphan"
    )
    hero_selections = relationship(
        "HeroSelection", back_populates="user", cascade="all, delete-orphan"
    )
    __table_args__ = (Index("idx_users_created_at", "created_at"),)

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
    event_id = Column(
        Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    beer_choice = Column(String(100), nullable=False)
    selected_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="choices")
    event = relationship("Event")
    __table_args__ = (
        Index("idx_beer_choices_user_id", "user_id"),
        Index("idx_beer_choices_selected_at", "selected_at"),
        Index("idx_beer_choices_beer_choice", "beer_choice"),
        Index("idx_beer_choices_user_id_selected_at", "user_id", "selected_at"),
        Index("idx_beer_choices_event_id", "event_id"),
    )

    def __repr__(self):
        return f"<BeerChoice(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, beer_choice='{self.beer_choice}')>"


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
    __table_args__ = (
        Index("idx_events_event_date", "event_date"),
        Index("idx_events_event_date_time", "event_date", "event_time"),
    )

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
    __table_args__ = (Index("idx_event_participants_event_id", "event_id"),)

    def __repr__(self):
        return f"<EventParticipant(id={self.id}, event_id={self.event_id}, participant_count={self.participant_count})>"


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    group_users = relationship(
        "GroupUser", back_populates="group", cascade="all, delete-orphan"
    )
    hero_selections = relationship(
        "HeroSelection", back_populates="group", cascade="all, delete-orphan"
    )
    __table_args__ = (Index("idx_groups_created_at", "created_at"),)

    def __repr__(self):
        return f"<Group(id={self.id}, chat_id={self.chat_id}, name='{self.name}')>"


class GroupUser(Base):
    __tablename__ = "group_users"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("Group", back_populates="group_users")
    user = relationship("User", back_populates="group_users")
    __table_args__ = (
        Index("idx_group_users_group_id", "group_id"),
        Index("idx_group_users_user_id", "user_id"),
        Index("idx_group_users_group_id_user_id", "group_id", "user_id", unique=True),
    )

    def __repr__(self):
        return f"<GroupUser(id={self.id}, group_id={self.group_id}, user_id={self.user_id})>"


class HeroSelection(Base):
    __tablename__ = "hero_selections"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    selection_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("Group", back_populates="hero_selections")
    user = relationship("User", back_populates="hero_selections")
    __table_args__ = (
        Index("idx_hero_selections_group_id", "group_id"),
        Index("idx_hero_selections_user_id", "user_id"),
        Index("idx_hero_selections_selection_date", "selection_date"),
        Index(
            "idx_hero_selections_group_id_selection_date",
            "group_id",
            "selection_date",
            unique=True,
        ),
    )

    def __repr__(self):
        return f"<HeroSelection(id={self.id}, group_id={self.group_id}, user_id={self.user_id}, date={self.selection_date})>"
