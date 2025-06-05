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
    try:
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )
            if not user:
                await message.answer(
                    "❌ Ты не зарегистрирован!\n"
                    "Используй команду /start для регистрации."
                )
                return
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
    try:
        await callback_query.answer()  # Подтверждаем получение колбэка
        beer_type_map = {
            "beer_lager": BeerTypeEnum.LAGER,
            "beer_hand_of_god": BeerTypeEnum.HAND_OF_GOD,
        }
        beer_type = beer_type_map.get(callback_query.data)
        if not beer_type:
            await callback_query.message.edit_text("❌ Неизвестный тип пива!")
            return
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if not user:
                await callback_query.message.edit_text(
                    "❌ Пользователь не найден!\n"
                    "Используй команду /start для регистрации."
                )
                return
            choice_data = BeerChoiceCreate(user_id=user.id, beer_type=beer_type)
            await BeerRepository.create_choice(session, choice_data)  # Создаем выбор
            user_stats = await BeerRepository.get_user_beer_stats(
                session, user.id
            )  # Получаем обновленную статистику
            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }
            selected_beer_display_name = beer_names.get(
                beer_type.value, beer_type.value
            )
            message_text = (
                f"✅ Отличный выбор! Ты выбрал {selected_beer_display_name}\n\n"
            )
            if user_stats:
                stats_lines = ["📊 Твоя статистика:"]
                for db_beer_type_value, count in user_stats.items():
                    display_name = beer_names.get(
                        db_beer_type_value, db_beer_type_value
                    )
                    stats_lines.append(f"{display_name}: {count}")
                message_text += "\n".join(stats_lines) + "\n"
            else:
                # Этот случай маловероятен, если выбор только что был сделан, но для полноты:
                message_text += "📊 У тебя пока нет статистики по выбору пива.\n"
            message_text += (
                "\n🔄 /beer - выбрать еще раз\n"
                "📊 /stats - общая статистика\n"
                "👤 /profile - мой профиль"
            )
            await callback_query.message.edit_text(message_text)
    except Exception as e:
        logger.error(f"Error in beer choice callback: {e}")
        await callback_query.message.edit_text("Произошла ошибка. Попробуй позже.")
