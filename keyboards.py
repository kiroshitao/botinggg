from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Каталог менторов", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Каталог менторов", callback_data="catalog")
    builder.button(text="⚙️ Управление менторами", callback_data="admin_mentors")
    builder.button(text="🗂 Управление категориями", callback_data="admin_categories")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(1)
    return builder.as_markup()


# ─── Catalog navigation ───────────────────────────────────────────────────────

def categories_kb(categories, parent_id=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=cat["name"],
            callback_data=f"cat_{cat['id']}"
        )
    if parent_id is not None:
        builder.button(text="◀️ Назад", callback_data=f"cat_back_{parent_id}")
    else:
        builder.button(text="◀️ Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def mentors_list_kb(mentors, category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mentor in mentors:
        status = "" if mentor["is_active"] else " 🔴"
        builder.button(
            text=f"{mentor['name']}{status}",
            callback_data=f"mentor_{mentor['id']}"
        )
    builder.button(text="◀️ Назад", callback_data=f"cat_back_{category_id}")
    builder.adjust(1)
    return builder.as_markup()


def mentor_card_kb(mentor_id: int, is_active: bool, tg_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.button(
            text="📩 Связаться с ментором",
            callback_data=f"apply_{mentor_id}"
        )
    builder.button(text="◀️ Назад", callback_data=f"mentor_back_{mentor_id}")
    builder.adjust(1)
    return builder.as_markup()


def after_apply_kb(tg_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if tg_username:
        username = tg_username.lstrip("@")
        builder.button(
            text="✉️ Написать ментору",
            url=f"https://t.me/{username}"
        )
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


# ─── Mentor status actions (for mentor's private chat) ────────────────────────

def application_actions_kb(app_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"app_accept_{app_id}")
    builder.button(text="❌ Отклонить", callback_data=f"app_reject_{app_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── Admin: mentor management ─────────────────────────────────────────────────

def admin_mentors_kb(mentors) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in mentors:
        status = "🟢" if m["is_active"] else "🔴"
        builder.button(
            text=f"{status} {m['name']}",
            callback_data=f"admin_mentor_{m['id']}"
        )
    builder.button(text="➕ Добавить ментора", callback_data="admin_add_mentor")
    builder.button(text="◀️ Назад", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def admin_mentor_actions_kb(mentor_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = "🔴 Отключить приём заявок" if is_active else "🟢 Включить приём заявок"
    builder.button(text=toggle_text, callback_data=f"admin_toggle_{mentor_id}")
    builder.button(text="✏️ Редактировать", callback_data=f"admin_edit_{mentor_id}")
    builder.button(text="🗑 Удалить ментора", callback_data=f"admin_delete_{mentor_id}")
    builder.button(text="◀️ Назад", callback_data="admin_mentors")
    builder.adjust(1)
    return builder.as_markup()


def admin_edit_mentor_kb(mentor_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fields = [
        ("Имя", "name"),
        ("Фото", "photo"),
        ("Описание", "description"),
        ("Опыт", "experience"),
        ("Специализация", "specialization"),
        ("Стоимость", "price"),
        ("TG Username", "tg_username"),
        ("TG User ID", "tg_user_id"),
        ("Категория", "category_id"),
    ]
    for label, field in fields:
        builder.button(
            text=f"✏️ {label}",
            callback_data=f"admin_edit_field_{mentor_id}_{field}"
        )
    builder.button(text="◀️ Назад", callback_data=f"admin_mentor_{mentor_id}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_delete_kb(mentor_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"admin_confirm_delete_{mentor_id}")
    builder.button(text="❌ Отмена", callback_data=f"admin_mentor_{mentor_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── Admin: category management ───────────────────────────────────────────────

def admin_categories_kb(categories, parent_id=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=cat["name"],
            callback_data=f"admin_cat_{cat['id']}"
        )
    builder.button(text="➕ Добавить категорию", callback_data=f"admin_add_cat_{parent_id or 0}")
    if parent_id:
        builder.button(text="◀️ Назад", callback_data=f"admin_cat_back_{parent_id}")
    else:
        builder.button(text="◀️ Назад", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def admin_category_actions_kb(cat_id: int, parent_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 Подкатегории", callback_data=f"admin_cat_subs_{cat_id}")
    builder.button(text="✏️ Переименовать", callback_data=f"admin_rename_cat_{cat_id}")
    builder.button(text="🗑 Удалить", callback_data=f"admin_delete_cat_{cat_id}")
    back_cb = f"admin_cat_back_{parent_id}" if parent_id else "admin_categories"
    builder.button(text="◀️ Назад", callback_data=back_cb)
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_cat_kb(cat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"admin_confirm_delete_cat_{cat_id}")
    builder.button(text="❌ Отмена", callback_data=f"admin_cat_{cat_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── Admin: application CRM actions ──────────────────────────────────────────

def admin_app_actions_kb(app_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🤝 Связь состоялась", callback_data=f"crm_contacted_{app_id}")
    builder.button(text="💰 Сделка закрыта", callback_data=f"crm_deal_{app_id}")
    builder.button(text="💵 Комиссия получена", callback_data=f"crm_commission_{app_id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── Cancel keyboard ──────────────────────────────────────────────────────────

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ Пропустить")], [KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
