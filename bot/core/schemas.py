from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime, time
from typing import Optional, List
from pydantic import validator
import pendulum


class UserCreate(BaseModel):
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    username: Optional[str] = Field(
        None, max_length=32, description="Telegram username"
    )
    name: str = Field(..., min_length=1, max_length=50, description="User display name")
    birth_date: date = Field(..., description="User birth date")

    @validator("birth_date")
    def validate_birth_date(cls, value):
        today = pendulum.now("Europe/Moscow").date()
        age = (
            today.year
            - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if age < 18:
            raise ValueError("User must be at least 18 years old")
        if value > today:
            raise ValueError("Birth date cannot be in the future")
        return value


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=32)
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    birth_date: Optional[date] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    telegram_id: int
    username: Optional[str]
    name: str
    birth_date: date
    created_at: datetime
    updated_at: Optional[datetime]


class BeerChoiceCreate(BaseModel):
    user_id: int = Field(..., gt=0, description="User ID")
    beer_choice: str = Field(
        ..., min_length=1, max_length=100, description="Selected beer"
    )


class BeerChoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    beer_choice: str
    selected_at: datetime


class UserWithChoices(BaseModel):
    id: Optional[int]
    choices: List[BeerChoiceResponse] = []


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Event name")
    event_date: date = Field(..., description="Event date")
    event_time: time = Field(..., description="Event time")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    location_name: Optional[str] = Field(
        None, max_length=500, description="Location description"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Event description"
    )
    image_file_id: Optional[str] = Field(
        None, max_length=200, description="Telegram file ID of event image"
    )
    has_beer_choice: bool = Field(
        default=False, description="Whether event has beer choice"
    )
    beer_option_1: Optional[str] = Field(
        None, max_length=100, description="First beer option"
    )
    beer_option_2: Optional[str] = Field(
        None, max_length=100, description="Second beer option"
    )
    created_by: int = Field(..., description="Telegram ID of creator")

    @validator("event_date")
    def validate_event_date(cls, value):
        today = pendulum.now("Europe/Moscow").date()
        if value < today:
            raise ValueError("Event date cannot be in the past")
        return value


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    event_date: date
    event_time: time
    latitude: Optional[float]
    longitude: Optional[float]
    location_name: Optional[str]
    description: Optional[str]
    image_file_id: Optional[str]
    has_beer_choice: bool
    beer_option_1: Optional[str]
    beer_option_2: Optional[str]
    created_by: int
    created_at: datetime
