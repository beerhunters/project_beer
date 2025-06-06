from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.beer_repo import BeerRepository
from bot.core.schemas import BeerChoiceCreate
from bot.core.models import BeerTypeEnum
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


def get_command_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="cmd_stats")
    )
    builder.add(
        types.InlineKeyboardButton(text="👤 Профиль", callback_data="cmd_profile")
    )
    builder.add(
        types.InlineKeyboardButton(text="🏠 В начало", callback_data="cmd_start")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("beer"))
async def beer_selection_handler(message: types.Message, bot: Bot):
    try:
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )
            if not user:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Ты не зарегистрирован!\nИспользуй команду /start для регистрации.",
                    reply_markup=get_command_keyboard(),
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
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"🍺 Привет, {user.name}!\nКакое пиво предпочитаешь сегодня?",
                reply_markup=builder.as_markup(),
            )
    except Exception as e:
        logger.error(f"Error in beer selection handler: {e}")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )


# @router.callback_query(lambda c: c.data.startswith("beer_"))
# async def beer_choice_callback(callback_query: types.CallbackQuery, bot: Bot):
#     try:
#         await callback_query.answer()
#         beer_type_map = {
#             "beer_lager": BeerTypeEnum.LAGER,
#             "beer_hand_of_god": BeerTypeEnum.HAND_OF_GOD,
#         }
#         beer_type = beer_type_map.get(callback_query.data)
#         if not beer_type:
#             await bot.edit_message_text(
#                 chat_id=callback_query.message.chat.id,
#                 message_id=callback_query.message.message_id,
#                 text="❌ Неизвестный тип пива!",
#                 reply_markup=get_command_keyboard(),
#             )
#             return
#         async for session in get_async_session():
#             user = await UserRepository.get_user_by_telegram_id(
#                 session, callback_query.from_user.id
#             )
#             if not user:
#                 await bot.edit_message_text(
#                     text="❌ Пользователь не найден!\n"
#                     f"Используй команду /start для регистрации.",
#                     chat_id=callback_query.message.chat.id,
#                     message_id=callback_query.message.message_id,
#                     reply_markup=get_command_keyboard(),
#                 )
#                 return
#             choice_data = BeerChoiceCreate(user_id=user.id, beer_type=beer_type)
#             await BeerRepository.create_choice(session, choice_data)
#             user_stats = await BeerRepository.get_user_beer_stats(session, user.id)
#             beer_names = {
#                 BeerTypeEnum.LAGER.value: "🍺 Lager",
#                 BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
#             }
#             selected_beer_display_name = beer_names.get(
#                 beer_type.value, beer_type.value
#             )
#             message_text = (
#                 f"✅ Отличный выбор! Ты выбрал {selected_beer_display_name}\n\n"
#             )
#             if user_stats:
#                 stats_lines = ["📊 Твоя статистика:"]
#                 for db_beer_type_value, count in user_stats.items():
#                     display_name = beer_names.get(
#                         db_beer_type_value, db_beer_type_value
#                     )
#                     stats_lines.append(f"{display_name}: {count}")
#                 message_text += "\n".join(stats_lines) + "\n"
#             else:
#                 message_text += "📊 У тебя пока нет статистики по выбору пива.\n"
#             message_text += "\n"
#             message_text += "\nВыбери действие:"
#             await bot.edit_message_text(
#                 message_id=callback_query.message_id,
#                 text=message_text,
#                 chat_id=callback_query.message.chat_id,
#                 reply_markup=get_command_keyboard(),
#             )
#     except Exception as e:
#         logger.error(f"Error in beer choice callback: {e}")
#         await bot.edit_message_text(
#             text="Произошла ошибка. Попробуй позже.",
#             chat_id=callback_query.message.chat.id,
#             message_id=callback_query.message.message_id,
#             reply_markup=get_command_keyboard(),
#         )
@router.callback_query(lambda c: c.data.startswith("beer_"))
async def beer_choice_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        await callback_query.answer()
        beer_type_map = {
            "beer_lager": BeerTypeEnum.LAGER,
            "beer_hand_of_god": BeerTypeEnum.HAND_OF_GOD,
        }
        beer_type = beer_type_map.get(callback_query.data)
        if not beer_type:
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="❌ Неизвестный тип пива!",
                reply_markup=get_command_keyboard(),
            )
            return
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if not user:
                await bot.edit_message_text(
                    text="❌ Пользователь не найден!\n"
                    f"Используй команду /start для регистрации.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(),
                )
                return
            choice_data = BeerChoiceCreate(user_id=user.id, beer_type=beer_type)
            await BeerRepository.create_choice(session, choice_data)
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)
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
                message_text += "📊 У тебя пока нет статистики по выбору пива.\n"
            message_text += "\n"
            message_text += "\nВыбери действие:"
            await bot.edit_message_text(
                message_id=callback_query.message.message_id,
                text=message_text,
                chat_id=callback_query.message.chat_id,
                reply_markup=get_command_keyboard(),
            )
    except Exception as e:
        logger.error(f"Error in beer choice callback: {e}")
        await bot.edit_message_text(
            text="Произошла ошибка. Попробуй позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data == "cmd_beer")
async def cmd_beer_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        await callback_query.answer()
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if not user:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text="❌ Ты не зарегистрирован!\nИспользуй команду /start для регистрации.",
                    reply_markup=get_command_keyboard(),
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
            builder.add(
                types.InlineKeyboardButton(
                    text="🏠 В начало", callback_data="cmd_start"
                )
            )
            builder.adjust(2)
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=f"🍺 Привет, {user.name}!\nКакое пиво предпочитаешь сегодня?",
                reply_markup=builder.as_markup(),
            )
    except Exception as e:
        logger.error(f"Error in cmd_beer callback: {e}")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )
