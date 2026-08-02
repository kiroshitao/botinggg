from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Filter

import database as db
import keyboards as kb
from config import ADMIN_IDS
from states import AddMentorStates, EditMentorStates, AddCategoryStates, EditCategoryStates

router = Router()


# ─── Admin filter ─────────────────────────────────────────────────────────────

class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        if hasattr(event, "from_user"):
            return event.from_user.id in ADMIN_IDS
        return False


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ─── Admin back ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(call: CallbackQuery):
    name = call.from_user.first_name or "Администратор"
    await call.message.edit_text(
        f"👋 Привет, {name}!\n\nВы вошли как <b>администратор</b>.",
        reply_markup=kb.admin_main_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()


# ─── Statistics ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    stats = await db.get_statistics()
    per_mentor_lines = "\n".join(
        f"  • {row['name']}: {row['cnt']}" for row in stats["per_mentor"]
    ) or "  нет данных"

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📋 Всего заявок: <b>{stats['total']}</b>\n"
        f"✅ Подтверждено: <b>{stats['confirmed']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected']}</b>\n"
        f"📈 Конверсия: <b>{stats['conversion']}%</b>\n\n"
        f"👨‍🏫 Активных менторов: <b>{stats['active_mentors']}</b>\n"
        f"🤝 Связь состоялась: <b>{stats['contacted']}</b>\n"
        f"💰 Сделок закрыто: <b>{stats['deals_closed']}</b>\n"
        f"💵 Комиссий получено: <b>{stats['commission']:.2f}</b>\n\n"
        f"<b>По менторам:</b>\n{per_mentor_lines}"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin_back")
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# MENTOR MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_mentors")
async def cb_admin_mentors(call: CallbackQuery):
    mentors = await db.get_all_mentors()
    await call.message.edit_text(
        "⚙️ <b>Управление менторами</b>\n\nВыберите ментора или добавьте нового:",
        reply_markup=kb.admin_mentors_kb(mentors),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_mentor_") & ~F.data.startswith("admin_mentor_actions"))
async def cb_admin_mentor_detail(call: CallbackQuery):
    parts = call.data.split("_")
    mentor_id = int(parts[2])
    mentor = await db.get_mentor(mentor_id)
    if not mentor:
        await call.answer("Ментор не найден", show_alert=True)
        return

    status = "🟢 Принимает заявки" if mentor["is_active"] else "🔴 Не принимает заявки"
    username = f"@{mentor['tg_username'].lstrip('@')}" if mentor["tg_username"] else "не указан"
    text = (
        f"👤 <b>{mentor['name']}</b>\n\n"
        f"📝 {mentor['description'] or '—'}\n"
        f"💼 Опыт: {mentor['experience'] or '—'}\n"
        f"🎯 Специализация: {mentor['specialization'] or '—'}\n"
        f"💰 Стоимость: {mentor['price'] or '—'}\n"
        f"📱 TG: {username}\n"
        f"🆔 TG ID: {mentor['tg_user_id'] or 'не указан'}\n\n"
        f"{status}"
    )
    await call.message.edit_text(
        text,
        reply_markup=kb.admin_mentor_actions_kb(mentor_id, bool(mentor["is_active"])),
        parse_mode="HTML"
    )
    await call.answer()


# ─── Toggle active ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_toggle_"))
async def cb_admin_toggle(call: CallbackQuery):
    mentor_id = int(call.data.split("_")[2])
    new_status = await db.toggle_mentor_active(mentor_id)
    status_text = "🟢 Приём заявок включён" if new_status else "🔴 Приём заявок отключён"
    await call.answer(status_text, show_alert=True)

    mentor = await db.get_mentor(mentor_id)
    if mentor:
        status = "🟢 Принимает заявки" if mentor["is_active"] else "🔴 Не принимает заявки"
        username = f"@{mentor['tg_username'].lstrip('@')}" if mentor["tg_username"] else "не указан"
        text = (
            f"👤 <b>{mentor['name']}</b>\n\n"
            f"📝 {mentor['description'] or '—'}\n"
            f"💼 Опыт: {mentor['experience'] or '—'}\n"
            f"🎯 Специализация: {mentor['specialization'] or '—'}\n"
            f"💰 Стоимость: {mentor['price'] or '—'}\n"
            f"📱 TG: {username}\n"
            f"🆔 TG ID: {mentor['tg_user_id'] or 'не указан'}\n\n"
            f"{status}"
        )
        await call.message.edit_text(
            text,
            reply_markup=kb.admin_mentor_actions_kb(mentor_id, bool(mentor["is_active"])),
            parse_mode="HTML"
        )


# ─── Delete mentor ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_delete_") & ~F.data.startswith("admin_delete_cat_") & ~F.data.startswith("admin_confirm_delete_"))
async def cb_admin_delete_mentor(call: CallbackQuery):
    mentor_id = int(call.data.split("_")[2])
    mentor = await db.get_mentor(mentor_id)
    if not mentor:
        await call.answer("Ментор не найден", show_alert=True)
        return
    await call.message.edit_text(
        f"🗑 Вы уверены, что хотите удалить ментора <b>{mentor['name']}</b>?\n\n"
        "Все заявки этого ментора также будут удалены.",
        reply_markup=kb.confirm_delete_kb(mentor_id),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_") & ~F.data.startswith("admin_confirm_delete_cat_"))
async def cb_admin_confirm_delete_mentor(call: CallbackQuery):
    mentor_id = int(call.data.split("_")[3])
    await db.delete_mentor(mentor_id)
    mentors = await db.get_all_mentors()
    await call.message.edit_text(
        "✅ Ментор удалён.\n\n⚙️ <b>Управление менторами</b>",
        reply_markup=kb.admin_mentors_kb(mentors),
        parse_mode="HTML"
    )
    await call.answer("Ментор удалён", show_alert=True)


# ─── Edit mentor ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_edit_") & ~F.data.startswith("admin_edit_field_"))
async def cb_admin_edit_mentor(call: CallbackQuery):
    mentor_id = int(call.data.split("_")[2])
    mentor = await db.get_mentor(mentor_id)
    if not mentor:
        await call.answer("Ментор не найден", show_alert=True)
        return
    await call.message.edit_text(
        f"✏️ <b>Редактирование: {mentor['name']}</b>\n\nВыберите поле для изменения:",
        reply_markup=kb.admin_edit_mentor_kb(mentor_id),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_edit_field_"))
async def cb_admin_edit_field(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_")
    # admin_edit_field_{mentor_id}_{field}
    mentor_id = int(parts[3])
    field = "_".join(parts[4:])

    await state.update_data(mentor_id=mentor_id, field=field)

    if field == "photo":
        await state.set_state(EditMentorStates.enter_photo)
        await call.message.edit_text(
            "📸 Отправьте новое фото ментора:",
            reply_markup=None
        )
        await call.message.answer("Отправьте фото:", reply_markup=kb.cancel_kb())
    elif field == "category_id":
        await state.set_state(EditMentorStates.enter_value)
        categories = await db.get_root_categories()
        cats_text = "\n".join(f"  {c['id']}. {c['name']}" for c in categories)
        await call.message.edit_text(
            f"📂 Введите ID новой категории:\n\n{cats_text}",
            reply_markup=None
        )
        await call.message.answer("Введите ID категории:", reply_markup=kb.cancel_kb())
    else:
        field_names = {
            "name": "имя",
            "description": "описание",
            "experience": "опыт",
            "specialization": "специализацию",
            "price": "стоимость",
            "tg_username": "Telegram username",
            "tg_user_id": "Telegram ID",
        }
        fname = field_names.get(field, field)
        await state.set_state(EditMentorStates.enter_value)
        await call.message.edit_text(
            f"✏️ Введите новое значение для поля <b>{fname}</b>:",
            reply_markup=None,
            parse_mode="HTML"
        )
        await call.message.answer("Введите значение:", reply_markup=kb.cancel_kb())
    await call.answer()


@router.message(EditMentorStates.enter_value)
async def process_edit_value(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return

    data = await state.get_data()
    mentor_id = data["mentor_id"]
    field = data["field"]

    value = message.text.strip()
    if field == "tg_user_id":
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Введите числовой Telegram ID.")
            return
    elif field == "category_id":
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Введите числовой ID категории.")
            return

    await db.update_mentor_field(mentor_id, field, value)
    await state.clear()

    mentor = await db.get_mentor(mentor_id)
    await message.answer(
        f"✅ Поле обновлено!\n\n👤 <b>{mentor['name']}</b>",
        reply_markup=kb.admin_mentor_actions_kb(mentor_id, bool(mentor["is_active"])),
        parse_mode="HTML"
    )


@router.message(EditMentorStates.enter_photo)
async def process_edit_photo(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return

    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте фотографию.")
        return

    data = await state.get_data()
    mentor_id = data["mentor_id"]
    photo_id = message.photo[-1].file_id

    await db.update_mentor_field(mentor_id, "photo_file_id", photo_id)
    await state.clear()

    mentor = await db.get_mentor(mentor_id)
    await message.answer(
        f"✅ Фото обновлено!\n\n👤 <b>{mentor['name']}</b>",
        reply_markup=kb.admin_mentor_actions_kb(mentor_id, bool(mentor["is_active"])),
        parse_mode="HTML"
    )


# ─── Add mentor (FSM) ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_mentor")
async def cb_admin_add_mentor(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddMentorStates.name)
    await call.message.edit_text(
        "➕ <b>Добавление нового ментора</b>\n\nШаг 1/9: Введите имя ментора:",
        parse_mode="HTML"
    )
    await call.message.answer("Введите имя:", reply_markup=kb.cancel_kb())
    await call.answer()


@router.message(AddMentorStates.name)
async def add_mentor_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddMentorStates.photo)
    await message.answer(
        "Шаг 2/9: Отправьте фото ментора (или нажмите «Пропустить»):",
        reply_markup=kb.skip_kb()
    )


@router.message(AddMentorStates.photo)
async def add_mentor_photo(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    if message.text == "⏭ Пропустить":
        await state.update_data(photo_file_id=None)
    elif message.photo:
        await state.update_data(photo_file_id=message.photo[-1].file_id)
    else:
        await message.answer("Пожалуйста, отправьте фото или нажмите «Пропустить».")
        return
    await state.set_state(AddMentorStates.description)
    await message.answer("Шаг 3/9: Введите описание ментора:", reply_markup=kb.skip_kb())


@router.message(AddMentorStates.description)
async def add_mentor_description(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    val = "" if message.text == "⏭ Пропустить" else message.text.strip()
    await state.update_data(description=val)
    await state.set_state(AddMentorStates.experience)
    await message.answer("Шаг 4/9: Введите опыт работы:", reply_markup=kb.skip_kb())


@router.message(AddMentorStates.experience)
async def add_mentor_experience(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    val = "" if message.text == "⏭ Пропустить" else message.text.strip()
    await state.update_data(experience=val)
    await state.set_state(AddMentorStates.specialization)
    await message.answer("Шаг 5/9: Введите специализацию:", reply_markup=kb.skip_kb())


@router.message(AddMentorStates.specialization)
async def add_mentor_specialization(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    val = "" if message.text == "⏭ Пропустить" else message.text.strip()
    await state.update_data(specialization=val)
    await state.set_state(AddMentorStates.price)
    await message.answer("Шаг 6/9: Введите стоимость обучения/консультации:", reply_markup=kb.skip_kb())


@router.message(AddMentorStates.price)
async def add_mentor_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    val = "" if message.text == "⏭ Пропустить" else message.text.strip()
    await state.update_data(price=val)
    await state.set_state(AddMentorStates.tg_username)
    await message.answer("Шаг 7/9: Введите Telegram username ментора (например: @username):", reply_markup=kb.skip_kb())


@router.message(AddMentorStates.tg_username)
async def add_mentor_tg_username(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    val = "" if message.text == "⏭ Пропустить" else message.text.strip().lstrip("@")
    await state.update_data(tg_username=val)
    await state.set_state(AddMentorStates.tg_user_id)
    await message.answer(
        "Шаг 8/9: Введите Telegram ID ментора (числовой ID для уведомлений):\n"
        "Узнать ID можно через @userinfobot",
        reply_markup=kb.skip_kb()
    )


@router.message(AddMentorStates.tg_user_id)
async def add_mentor_tg_user_id(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    if message.text == "⏭ Пропустить":
        await state.update_data(tg_user_id=None)
    else:
        try:
            await state.update_data(tg_user_id=int(message.text.strip()))
        except ValueError:
            await message.answer("❌ Введите числовой Telegram ID или нажмите «Пропустить».")
            return

    # Show categories
    categories = await db.get_root_categories()
    if not categories:
        await state.update_data(category_id=None)
        await _finish_add_mentor(message, state)
        return

    cats_text = "\n".join(f"  {c['id']}. {c['name']}" for c in categories)
    await state.set_state(AddMentorStates.category)
    await message.answer(
        f"Шаг 9/9: Введите ID категории для ментора:\n\n{cats_text}\n\n"
        "Или нажмите «Пропустить».",
        reply_markup=kb.skip_kb()
    )


@router.message(AddMentorStates.category)
async def add_mentor_category(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    if message.text == "⏭ Пропустить":
        await state.update_data(category_id=None)
    else:
        try:
            await state.update_data(category_id=int(message.text.strip()))
        except ValueError:
            await message.answer("❌ Введите числовой ID категории или нажмите «Пропустить».")
            return
    await _finish_add_mentor(message, state)


async def _finish_add_mentor(message: Message, state: FSMContext):
    data = await state.get_data()
    mentor_id = await db.add_mentor(
        name=data.get("name", ""),
        photo_file_id=data.get("photo_file_id"),
        description=data.get("description", ""),
        experience=data.get("experience", ""),
        specialization=data.get("specialization", ""),
        price=data.get("price", ""),
        tg_username=data.get("tg_username", ""),
        tg_user_id=data.get("tg_user_id"),
        category_id=data.get("category_id"),
    )
    await state.clear()
    mentor = await db.get_mentor(mentor_id)
    await message.answer(
        f"✅ Ментор <b>{mentor['name']}</b> успешно добавлен! (ID: {mentor_id})",
        reply_markup=kb.admin_mentor_actions_kb(mentor_id, True),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_categories")
async def cb_admin_categories(call: CallbackQuery):
    categories = await db.get_root_categories()
    await call.message.edit_text(
        "🗂 <b>Управление категориями</b>\n\nКорневые категории:",
        reply_markup=kb.admin_categories_kb(categories),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cat_") & ~F.data.startswith("admin_cat_subs_") & ~F.data.startswith("admin_cat_back_"))
async def cb_admin_cat_detail(call: CallbackQuery):
    cat_id = int(call.data.split("_")[2])
    cat = await db.get_category(cat_id)
    if not cat:
        await call.answer("Категория не найдена", show_alert=True)
        return
    path = await db.get_category_path(cat_id)
    breadcrumb = " › ".join(path)
    await call.message.edit_text(
        f"📂 <b>{breadcrumb}</b>\n\nВыберите действие:",
        reply_markup=kb.admin_category_actions_kb(cat_id, cat["parent_id"]),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cat_subs_"))
async def cb_admin_cat_subs(call: CallbackQuery):
    cat_id = int(call.data.split("_")[3])
    subcats = await db.get_subcategories(cat_id)
    path = await db.get_category_path(cat_id)
    breadcrumb = " › ".join(path)
    await call.message.edit_text(
        f"📂 <b>{breadcrumb}</b> — подкатегории:",
        reply_markup=kb.admin_categories_kb(subcats, parent_id=cat_id),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_cat_back_"))
async def cb_admin_cat_back(call: CallbackQuery):
    child_id = int(call.data.split("_")[3])
    child = await db.get_category(child_id)
    if not child or not child["parent_id"]:
        categories = await db.get_root_categories()
        await call.message.edit_text(
            "🗂 <b>Управление категориями</b>\n\nКорневые категории:",
            reply_markup=kb.admin_categories_kb(categories),
            parse_mode="HTML"
        )
    else:
        parent_id = child["parent_id"]
        subcats = await db.get_subcategories(parent_id)
        path = await db.get_category_path(parent_id)
        breadcrumb = " › ".join(path)
        await call.message.edit_text(
            f"📂 <b>{breadcrumb}</b> — подкатегории:",
            reply_markup=kb.admin_categories_kb(subcats, parent_id=parent_id),
            parse_mode="HTML"
        )
    await call.answer()


# ─── Add category ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_add_cat_"))
async def cb_admin_add_cat(call: CallbackQuery, state: FSMContext):
    parent_id_str = call.data.split("_")[3]
    parent_id = int(parent_id_str) if parent_id_str != "0" else None
    await state.update_data(parent_id=parent_id)
    await state.set_state(AddCategoryStates.name)

    if parent_id:
        path = await db.get_category_path(parent_id)
        breadcrumb = " › ".join(path)
        await call.message.edit_text(
            f"➕ Добавление подкатегории в <b>{breadcrumb}</b>\n\nВведите название:",
            parse_mode="HTML"
        )
    else:
        await call.message.edit_text("➕ Добавление корневой категории\n\nВведите название:")
    await call.message.answer("Введите название:", reply_markup=kb.cancel_kb())
    await call.answer()


@router.message(AddCategoryStates.name)
async def add_category_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    data = await state.get_data()
    parent_id = data.get("parent_id")
    name = message.text.strip()
    cat_id = await db.add_category(name, parent_id)
    await state.clear()
    await message.answer(
        f"✅ Категория <b>{name}</b> добавлена! (ID: {cat_id})",
        reply_markup=kb.admin_main_menu_kb(),
        parse_mode="HTML"
    )


# ─── Rename category ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_rename_cat_"))
async def cb_admin_rename_cat(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split("_")[3])
    await state.update_data(cat_id=cat_id)
    await state.set_state(EditCategoryStates.name)
    cat = await db.get_category(cat_id)
    await call.message.edit_text(
        f"✏️ Переименование категории <b>{cat['name'] if cat else ''}</b>\n\nВведите новое название:",
        parse_mode="HTML"
    )
    await call.message.answer("Введите новое название:", reply_markup=kb.cancel_kb())
    await call.answer()


@router.message(EditCategoryStates.name)
async def edit_category_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_main_menu_kb())
        return
    data = await state.get_data()
    cat_id = data["cat_id"]
    name = message.text.strip()
    await db.update_category(cat_id, name)
    await state.clear()
    await message.answer(
        f"✅ Категория переименована в <b>{name}</b>",
        reply_markup=kb.admin_main_menu_kb(),
        parse_mode="HTML"
    )


# ─── Delete category ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_delete_cat_") & ~F.data.startswith("admin_confirm_delete_cat_"))
async def cb_admin_delete_cat(call: CallbackQuery):
    cat_id = int(call.data.split("_")[3])
    cat = await db.get_category(cat_id)
    if not cat:
        await call.answer("Категория не найдена", show_alert=True)
        return
    await call.message.edit_text(
        f"🗑 Вы уверены, что хотите удалить категорию <b>{cat['name']}</b>?\n\n"
        "⚠️ Все подкатегории и менторы в ней будут отвязаны.",
        reply_markup=kb.confirm_delete_cat_kb(cat_id),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_cat_"))
async def cb_admin_confirm_delete_cat(call: CallbackQuery):
    cat_id = int(call.data.split("_")[4])
    await db.delete_category(cat_id)
    categories = await db.get_root_categories()
    await call.message.edit_text(
        "✅ Категория удалена.\n\n🗂 <b>Управление категориями</b>",
        reply_markup=kb.admin_categories_kb(categories),
        parse_mode="HTML"
    )
    await call.answer("Категория удалена", show_alert=True)
