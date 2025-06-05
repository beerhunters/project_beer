# bot/handlers/beer_selection.py
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.beer_repo import BeerRepository
from bot.core.schemas import BeerChoiceCreate
from bot.core.models import BeerTypeEnum

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("beer"))
async def beer_selection_handler(message: types.Message):
    """Обработчик команды выбора пива"""
    try:
        async for session in get_async_session():
            # Проверяем, зарегистрирован ли пользователь
            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )

            if not user:
                await message.answer(
                    "❌ Ты не зарегистрирован!\n"
                    "Используй команду /start для регистрации."
                )
                return

            # Создаем клавиатуру выбора пива
            builder = InlineKeyboardBuilder()
            builder.add(
                types.InlineKeyboardButton(text="🍺 Lager", callback_data="beer_lager")
            )
            builder.add(
                types.InlineKeyboardButton(
                    text="🍻 Hand of God", callback_data="beer_hand_of_god"
                )
            )
            builder.adjust(2)

            await message.answer(
                f"🍺 Привет, {user.name}!\n" "Какое пиво предпочитаешь сегодня?",
                reply_markup=builder.as_markup(),
            )

    except Exception as e:
        logger.error(f"Error in beer selection handler: {e}")
        await message.answer("Произошла ошибка. Попробуй позже.")


@router.callback_query(lambda c: c.data.startswith("beer_"))
async def beer_choice_callback(callback_query: types.CallbackQuery):
    """Обработчик выбора типа пива"""
    try:
        await callback_query.answer()

        # Определяем тип пива
        beer_type_map = {
            "beer_lager": BeerTypeEnum.LAGER,
            "beer_hand_of_god": BeerTypeEnum.HAND_OF_GOD,
        }

        beer_type = beer_type_map.get(callback_query.data)
        if not beer_type:
            await callback_query.message.edit_text("❌ Неизвестный тип пива!")
            return

        async for session in get_async_session():
            # Получаем пользователя
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )

            if not user:
                await callback_query.message.edit_text(
                    "❌ Пользователь не найден!\n"
                    "Используй команду /start для регистрации."
                )
                return

            # Создаем выбор пива
            choice_data = BeerChoiceCreate(user_id=user.id, beer_type=beer_type)

            choice = await BeerRepository.create_choice(session, choice_data)

            # Получаем статистику пользователя
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)

            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }

            selected_beer = beer_names[beer_type.value]

            stats_text = "📊 Твоя статистика:\n"
            for beer_name, count in user_stats.items():
                stats_text += f"{beer_names.get(beer_name, beer_name)}: {count}\n"

            await callback_query.message.edit_text(
                f"✅ Отличный выбор! Ты выбрал {selected_beer}\n\n"
                f"{stats_text}\n"
                "🔄 /beer - выбрать еще раз\n"
                "📊 /stats - общая статистика\n"
                "👤 /profile - мой профиль"
            )

    except Exception as e:
        logger.error(f"Error in beer choice callback: {e}")
        await callback_query.message.edit_text("Произошла ошибка. Попробуй позже.")
