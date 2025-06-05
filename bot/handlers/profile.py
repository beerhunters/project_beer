import logging
from aiogram import Router, types
from aiogram.filters import Command
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.beer_repo import BeerRepository
from bot.core.models import BeerTypeEnum
import pendulum

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("profile"))
async def profile_handler(message: types.Message):
    try:
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(  # get_user_with_choices не нужен, т.к. статистика получается отдельно
                session, message.from_user.id
            )
            if not user:
                await message.answer(
                    "❌ Ты не зарегистрирован!\n"
                    "Используй команду /start для регистрации."
                )
                return
            today = pendulum.now().date()
            age = (
                today.year
                - user.birth_date.year
                - (
                    (today.month, today.day)
                    < (user.birth_date.month, user.birth_date.day)
                )
            )
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)
            latest_choice = await BeerRepository.get_latest_user_choice(
                session, user.id
            )
            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }
            profile_text = f"👤 **Твой профиль**\n\n"
            profile_text += f"📛 Имя: {user.name}\n"
            profile_text += (
                f"🎂 Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
            )
            profile_text += f"📅 Возраст: {age} лет\n"
            profile_text += f"🆔 Telegram ID: {user.telegram_id}\n"
            profile_text += (
                f"📪 Username: @{user.username if user.username else 'не указан'}\n"
            )
            profile_text += (
                f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            )
            profile_text += "🍺 **Твои выборы пива**:\n"
            if user_stats:
                for beer_type_value, count in user_stats.items():
                    profile_text += f"{beer_names.get(beer_type_value, beer_type_value)}: {count} раз(а)\n"  # Добавлено "раз(а)" для ясности
            else:
                profile_text += "Ты еще не выбирал пиво!\n"
            if latest_choice:
                latest_beer_display_name = beer_names.get(
                    (
                        latest_choice.beer_type.value
                        if isinstance(latest_choice.beer_type, enum.Enum)
                        else latest_choice.beer_type
                    ),
                    str(latest_choice.beer_type),
                )
                profile_text += f"\n⏰ Последний выбор: {latest_beer_display_name} "
                profile_text += (
                    f"({latest_choice.selected_at.strftime('%d.%m.%Y %H:%M')})\n"
                )
            profile_text += "\n🔄 /beer - выбрать пиво\n"
            profile_text += "📊 /stats - статистика\n"
            await message.answer(profile_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in profile handler: {e}")
        await message.answer("Произошла ошибка. Попробуй позже.")
