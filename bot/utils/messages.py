# Текстовые сообщения для всех модулей бота

# --- Модуль hero_of_the_day ---
HERO_COMMAND_SUCCESS_MESSAGE = "🏆 Герой дня: @{username}!"
HERO_COMMAND_NO_HERO_MESSAGE = "❌ Герой дня ещё не выбран. Ждите выборов в 10:00!"
HERO_COMMAND_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."
HERO_COMMAND_GROUP_ALREADY_REGISTERED = "✅ Группа уже зарегистрирована!"
HERO_COMMAND_GROUP_ADDED_MESSAGE = (
    "👋 Группа зарегистрирована! Теперь я буду выбирать Героя Дня каждый день в 10:00!\n"
    "Пользователи могут зарегистрироваться как кандидаты с помощью /become_hero."
)
HERO_TODAY_NO_HERO_MESSAGE = "❌ Герой дня ещё не выбран. Ждите выборов в 10:00!"
HERO_TODAY_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."
BECOME_HERO_GROUP_NOT_REGISTERED = (
    "❌ Группа не зарегистрирована. Сначала выполните /hero."
)
BECOME_HERO_USER_NOT_FOUND_MESSAGE = (
    "❌ Вы не зарегистрированы в системе. Нажмите кнопку ниже, чтобы начать!"
)
BECOME_HERO_BUTTON_TEXT = "Начать с ботом"
BECOME_HERO_USER_REGISTERED_MESSAGE = (
    "✅ Вы зарегистрированы как кандидат на Героя Дня! Ждите своего звездного часа!"
)
BECOME_HERO_USER_ALREADY_CANDIDATE_MESSAGE = (
    "ℹ️ Вы уже зарегистрированы как кандидат на Героя Дня!"
)
BECOME_HERO_ERROR_MESSAGE = "❌ Ошибка при регистрации. Попробуйте позже."
HERO_TOP_MESSAGE = "🏆 Топ-10 героев дня в группе:\n\n{top_list}"
HERO_TOP_NO_HEROES_MESSAGE = "❌ Пока нет героев дня в этой группе."
HERO_TOP_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."

# --- Модуль start ---
START_WELCOME_MESSAGE = (
    "👋 Привет! Я твой бот для управления событиями и выбора героев дня!"
)
START_ALREADY_REGISTERED_MESSAGE = (
    "ℹ️ Вы уже зарегистрированы! Используйте /profile для просмотра профиля."
)
START_REQUEST_NAME_MESSAGE = "✍️ Пожалуйста, введите ваше имя:"
START_INVALID_NAME_MESSAGE = "❌ Имя должно быть от 1 до 50 символов. Попробуйте снова:"
START_REQUEST_BIRTH_DATE_MESSAGE = "🎂 Пожалуйста, введите дату рождения (ДД.ММ.ГГГГ):"
START_INVALID_BIRTH_DATE_MESSAGE = "❌ Неверный формат даты или возраст меньше 18 лет. Введите дату в формате ДД.ММ.ГГГГ:"
START_REGISTRATION_COMPLETE_MESSAGE = "✅ Регистрация завершена! Теперь вы можете участвовать в событиях и стать Героем Дня!"
START_GROUP_CANDIDATE_MESSAGE = (
    "✅ Вы зарегистрированы как кандидат на Героя Дня в группе {chat_title}!\n"
    "Используйте /profile для просмотра профиля."
)
START_ERROR_MESSAGE = "❌ Произошла ошибка при регистрации. Попробуйте позже."

# --- Модуль profile ---
PROFILE_HEADER = "👤 **Твой профиль**\n\n"
PROFILE_INFO = (
    "🆔 ID: {telegram_id}\n"
    "📛 Имя: {name}\n"
    "🎂 День рождения: {birth_date}\n"
    "👤 Username: {username}\n"
    "📅 Возраст: {age}\n"
    "📊 Статистика пивных предпочтений:\n{stats}\n"
    "🍺 Последний выбор: {latest_choice}\n"
)
PROFILE_NO_STATS = "📊 Пока нет статистики по пивным предпочтениям."
PROFILE_NO_LATEST_CHOICE = "🍺 Вы ещё не выбирали пиво."
PROFILE_NOT_REGISTERED_MESSAGE = (
    "❌ Вы не зарегистрированы. Отправьте /start для регистрации."
)
PROFILE_BUTTON_PROFILE_TEXT = "👤 Профиль"
PROFILE_BUTTON_EVENTS_TEXT = "📅 События"
PROFILE_BUTTON_BEER_TEXT = "🍺 Выбор пива"
PROFILE_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."

# --- Модуль beer_selection ---
BEER_WELCOME_MESSAGE = "🍺 Выберите событие для выбора пива:"
BEER_NO_UPCOMING_EVENTS_MESSAGE = "❌ Нет предстоящих событий. Попробуйте позже."
BEER_NOT_REGISTERED_MESSAGE = (
    "❌ Вы не зарегистрированы. Отправьте /start для регистрации."
)
BEER_EVENT_NOT_FOUND_MESSAGE = "❌ Событие не найдено."
BEER_SELECTION_NOT_AVAILABLE_MESSAGE = (
    "❌ Выбор пива ещё не доступен. Он откроется за 30 минут до начала события.\n"
    "⏰ Осталось: {time_str}"
)
BEER_ALREADY_CHOSEN_MESSAGE = "ℹ️ Вы уже выбрали пиво для этого события."
BEER_REQUEST_LOCATION_MESSAGE = (
    "📍 Отправьте свою геолокацию, чтобы подтвердить, что вы рядом с местом события:"
)
BEER_INVALID_LOCATION_MESSAGE = "❌ Пожалуйста, отправьте геолокацию, а не текст."
BEER_TOO_FAR_MESSAGE = (
    "❌ Вы слишком далеко от места события ({distance:.1f} км). Подойдите ближе!"
)
BEER_NO_LOCATION_MESSAGE = "ℹ️ Для этого события не требуется геолокация."
BEER_CHOICE_MESSAGE = "🍺 Выберите пиво для события {event_name}:"
BEER_SUCCESS_MESSAGE = (
    "✅ Отличный выбор! Ты выбрал 🍺 {beer_choice}\n\n"
    "📊 Твоя статистика:\n{stats_lines}"
)
BEER_BUTTON_CANCEL_TEXT = "❌ Отмена"
BEER_BUTTON_LOCATION_TEXT = "📍 Отправить геолокацию"
BEER_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."

# --- Модуль event_creation ---
CREATE_EVENT_NOT_ADMIN_MESSAGE = "❌ Вы не являетесь администратором этой группы."
CREATE_EVENT_REQUEST_NAME_MESSAGE = "✍️ Введите название события:"
CREATE_EVENT_INVALID_NAME_MESSAGE = (
    "❌ Название должно быть от 1 до 200 символов. Попробуйте снова:"
)
CREATE_EVENT_REQUEST_DATE_MESSAGE = "📅 Введите дату события (ДД.ММ.ГГГГ):"
CREATE_EVENT_INVALID_DATE_MESSAGE = (
    "❌ Неверный формат даты или дата в прошлом. Введите в формате ДД.ММ.ГГГГ:"
)
CREATE_EVENT_REQUEST_TIME_MESSAGE = "⏰ Введите время события (ЧЧ:ММ):"
CREATE_EVENT_INVALID_TIME_MESSAGE = (
    "❌ Неверный формат времени. Введите в формате ЧЧ:ММ:"
)
CREATE_EVENT_REQUEST_LOCATION_MESSAGE = (
    "📍 Отправьте геолокацию или введите название места (или нажмите 'Пропустить'):"
)
CREATE_EVENT_BUTTON_SKIP_TEXT = "➡️ Пропустить"
CREATE_EVENT_INVALID_LOCATION_MESSAGE = (
    "❌ Неверный формат. Отправьте геолокацию или текст."
)
CREATE_EVENT_REQUEST_LOCATION_NAME_MESSAGE = (
    "📍 Введите название места (или нажмите 'Пропустить'):"
)
CREATE_EVENT_REQUEST_DESCRIPTION_MESSAGE = (
    "📝 Введите описание события (или нажмите 'Пропустить'):"
)
CREATE_EVENT_REQUEST_IMAGE_MESSAGE = (
    "🖼️ Отправьте изображение события (или нажмите 'Пропустить'):"
)
CREATE_EVENT_INVALID_IMAGE_MESSAGE = (
    "❌ Пожалуйста, отправьте изображение, а не другой тип файла."
)
CREATE_EVENT_REQUEST_BEER_CHOICE_MESSAGE = "🍺 Добавить выбор пива для события?"
CREATE_EVENT_BUTTON_YES_TEXT = "✅ Да"
CREATE_EVENT_BUTTON_NO_TEXT = "❌ Нет"
CREATE_EVENT_REQUEST_BEER_OPTIONS_MESSAGE = (
    "🍺 Введите варианты пива через запятую (например, Лагер, IPA):"
)
CREATE_EVENT_INVALID_BEER_OPTIONS_MESSAGE = "❌ Введите хотя бы один вариант пива."
CREATE_EVENT_SUMMARY_MESSAGE = (
    "🎉 Событие создано!\n\n"
    "📅 Название: {name}\n"
    "🗓 Дата: {date}\n"
    "⏰ Время: {time}\n"
    "📍 Место: {location}\n"
    "📝 Описание: {description}\n"
    "🖼️ Изображение: {image}\n"
    "🍺 Выбор пива: {beer_choice}\n"
    "🍺 Варианты пива: {beer_options}\n"
)
CREATE_EVENT_NOTIFICATION_MESSAGE = (
    "🎉 Новое событие!\n\n"
    "📅 Название: {name}\n"
    "🗓 Дата: {date}\n"
    "⏰ Время: {time}\n"
    "📍 Место: {location}\n"
    "📝 Описание: {description}\n"
    "🍺 Выбор пива: {beer_choice}\n"
)
CREATE_EVENT_BUTTON_NOTIFY_TEXT = "🔔 Уведомить всех"
CREATE_EVENT_BUTTON_NO_NOTIFY_TEXT = "🔕 Без уведомления"
CREATE_EVENT_BUTTON_CANCEL_TEXT = "❌ Отмена"
CREATE_EVENT_ERROR_MESSAGE = (
    "❌ Произошла ошибка при создании события. Попробуйте позже."
)

# --- Модуль events_list ---
EVENTS_LIST_HEADER = (
    "📅 Список предстоящих событий в группе (страница {page} из {total_pages}):\n\n"
)
EVENTS_LIST_NO_EVENTS_MESSAGE = "❌ Нет предстоящих событий в этой группе."
EVENTS_LIST_EVENT_INFO = (
    "📅 {name}\n"
    "🗓 Дата: {date}\n"
    "⏰ Время: {time}\n"
    "📍 Место: {location}\n"
    "🍺 Выбор пива: {beer_choice}\n\n"
)
EVENTS_LIST_BUTTON_PREV_TEXT = "⬅️ Назад"
EVENTS_LIST_BUTTON_NEXT_TEXT = "➡️ Вперед"
EVENTS_LIST_BUTTON_DETAILS_TEXT = "ℹ️ Подробности"
EVENTS_LIST_EVENT_DETAILS = (
    "📅 Событие: {name}\n"
    "🗓 Дата: {date}\n"
    "⏰ Время: {time}\n"
    "📍 Место: {location}\n"
    "📝 Описание: {description}\n"
    "🍺 Выбор пива: {beer_choice}\n"
    "🍺 Варианты пива: {beer_options}\n"
)
EVENTS_LIST_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."

# --- Модуль delete_event ---
DELETE_EVENT_NOT_ADMIN_MESSAGE = "❌ Эта команда доступна только администратору."
DELETE_EVENT_REQUEST_ID_MESSAGE = "✍️ Введите ID события для удаления:"
DELETE_EVENT_INVALID_ID_MESSAGE = "❌ Неверный формат ID. Введите число."
DELETE_EVENT_NOT_FOUND_MESSAGE = "❌ Событие с ID {event_id} не найдено."
DELETE_EVENT_SUCCESS_MESSAGE = "✅ Событие с ID {event_id} удалено."
DELETE_EVENT_ERROR_MESSAGE = (
    "❌ Произошла ошибка при удалении события. Попробуйте позже."
)

# --- Модуль admin_management ---
CREATE_ADMIN_INVALID_FORMAT_MESSAGE = (
    "❌ Неверный формат. Используйте: /create_admin <admin_id> <group_id>"
)
CREATE_ADMIN_NOT_SUPERADMIN_MESSAGE = "❌ Эта команда доступна только суперадмину."
CREATE_ADMIN_USER_NOT_FOUND_MESSAGE = "❌ Пользователь с ID {admin_id} не найден."
CREATE_ADMIN_GROUP_NOT_FOUND_MESSAGE = "❌ Группа с ID {group_id} не найдена."
CREATE_ADMIN_ALREADY_ADMIN_MESSAGE = (
    "ℹ️ Пользователь с ID {admin_id} уже является администратором группы {group_id}."
)
CREATE_ADMIN_SUCCESS_MESSAGE = (
    "✅ Пользователь с ID {admin_id} назначен администратором группы {group_id}."
)
CREATE_ADMIN_ERROR_MESSAGE = (
    "❌ Произошла ошибка при назначении администратора. Попробуйте позже."
)

# --- Модуль hero_notification ---
HERO_NOTIFICATION_INTRO_MESSAGES = [
    "🌟 Настало время выбрать нового Героя Дня!",
    "🎉 Кто станет героем сегодня?",
    "🏆 Ищем нового героя дня!",
]
HERO_NOTIFICATION_SEARCH_MESSAGE = "⏳ Идет поиск героя..."
HERO_NOTIFICATION_SUCCESS_MESSAGE = "🏆 Герой дня в группе: @{username}!"
HERO_NOTIFICATION_ERROR_MESSAGE = "❌ Ошибка при выборе героя дня. Попробуйте позже."

# --- Модуль birthday_notification ---
BIRTHDAY_MESSAGE = "🎉 Сегодня день рождения у {mentions}! Поздравляем с праздником! 🥳"
NO_BIRTHDAY_MESSAGE = "Сегодня нет именинников. 😊"

# --- Модуль bartender_notification ---
BARTENDER_NOTIFICATION_MESSAGE = (
    "🍺 Событие: {event_name}\n"
    "⏰ Начало: {event_time}\n"
    "📍 Место: {location}\n"
    "👥 Участников: {participant_count}\n"
    "🍺 Выборы пива:\n{beer_counts}\n"
)
