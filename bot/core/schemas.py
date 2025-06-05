from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Optional, List
from bot.core.models import BeerTypeEnum
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
        today = pendulum.now().date()
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
    beer_type: BeerTypeEnum = Field(..., description="Type of beer")


class BeerChoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    beer_type: BeerTypeEnum
    selected_at: datetime


class UserWithChoices(UserResponse):
    choices: List[BeerChoiceResponse] = []
