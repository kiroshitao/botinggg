from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

import database as db
import keyboards as kb
from config import ADMIN_IDS, ADMIN_GROUP_ID

router = Router()


def _now() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name or "Пользователь"
    if _is_admin(message.from_user.id):
        await message.answer(
            f"👋 Привет, {name}!\n\nВы вошли как <b>администратор</b>.",
            reply_markup=kb.admin_main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"👋 Привет, {name}!\n\nДобро пожаловать в каталог менторов.\n"
            "Здесь вы можете найти подходящего специалиста и записаться на консультацию.",
            reply_markup=kb.main_menu_kb()
        )


# ─── Main menu callback ───────────────────────────────────────────────────────

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    name = call.from_user.first_name or "Пользователь"
    if _is_admin(call.from_user.id):
        await call.message.edit_text(
            f"👋 Привет, {name}!\n\nВы вошли как <b>администратор</b>.",
            reply_markup=kb.admin_main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await call.message.edit_text(
            f"👋 Привет, {name}!\n\nДобро пожаловать в каталог менторов.",
            reply_markup=kb.main_menu_kb()
        )
    await call.answer()


# ─── Catalog root ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "catalog")
async def cb_catalog(call: CallbackQuery):
    categories = await db.get_root_categories()
    if not categories:
        await call.message.edit_text(
            "📭 Каталог пока пуст. Скоро здесь появятся менторы!",
            reply_markup=kb.main_menu_kb()
        )
        await call.answer()
        return
    await call.message.edit_text(
        "📚 <b>Каталог менторов</b>\n\nВыберите направление:",
        reply_markup=kb.categories_kb(categories),
        parse_mode="HTML"
    )
    await call.answer()


# ─── Category navigation ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_") & ~F.data.startswith("cat_back_"))
async def cb_category(call: CallbackQuery):
    cat_id = int(call.data.split("_")[1])
    category = await db.get_category(cat_id)
    if not category:
        await call.answer("Категория не найдена", show_alert=True)
        return

    # Check if has subcategories
    has_subs = await db.has_subcategories(cat_id)
    if has_subs:
        subcats = await db.get_subcategories(cat_id)
        path = await db.get_category_path(cat_id)
        breadcrumb = " › ".join(path)
        await call.message.edit_text(
            f"📂 <b>{breadcrumb}</b>\n\nВыберите специализацию:",
            reply_markup=kb.categories_kb(subcats, parent_id=cat_id),
            parse_mode="HTML"
        )
    else:
        # Show mentors in this category
        mentors = await db.get_mentors_in_category(cat_id)
        path = await db.get_category_path(cat_id)
        breadcrumb = " › ".join(path)
        if not mentors:
            await call.message.edit_text(
                f"📂 <b>{breadcrumb}</b>\n\n😔 В этой категории пока нет менторов.",
                reply_markup=kb.categories_kb([], parent_id=cat_id),
                parse_mode="HTML"
            )
        else:
            await call.message.edit_text(
                f"📂 <b>{breadcrumb}</b>\n\nВыберите ментора:",
                reply_markup=kb.mentors_list_kb(mentors, cat_id),
                parse_mode="HTML"
            )
    await call.answer()


@router.callback_query(F.data.startswith("cat_back_"))
async def cb_cat_back(call: CallbackQuery):
    # Go to parent category
    child_id = int(call.data.split("_")[2])
    child = await db.get_category(child_id)
    if not child or not child["parent_id"]:
        # Go to root
        categories = await db.get_root_categories()
        await call.message.edit_text(
            "📚 <b>Каталог менторов</b>\n\nВыберите направление:",
            reply_markup=kb.categories_kb(categories),
            parse_mode="HTML"
        )
    else:
        parent_id = child["parent_id"]
        parent = await db.get_category(parent_id)
        has_subs = await db.has_subcategories(parent_id)
        if has_subs:
            subcats = await db.get_subcategories(parent_id)
            path = await db.get_category_path(parent_id)
            breadcrumb = " › ".join(path)
            await call.message.edit_text(
                f"📂 <b>{breadcrumb}</b>\n\nВыберите специализацию:",
                reply_markup=kb.categories_kb(subcats, parent_id=parent_id),
                parse_mode="HTML"
            )
        else:
            mentors = await db.get_mentors_in_category(parent_id)
            path = await db.get_category_path(parent_id)
            breadcrumb = " › ".join(path)
            await call.message.edit_text(
                f"📂 <b>{breadcrumb}</b>\n\nВыберите ментора:",
                reply_markup=kb.mentors_list_kb(mentors, parent_id),
                parse_mode="HTML"
            )
    await call.answer()


# ─── Mentor card ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mentor_") & ~F.data.startswith("mentor_back_"))
async def cb_mentor_card(call: CallbackQuery):
    mentor_id = int(call.data.split("_")[1])
    mentor = await db.get_mentor(mentor_id)
    if not mentor:
        await call.answer("Ментор не найден", show_alert=True)
        return

    status_text = "✅ Принимает заявки" if mentor["is_active"] else "🔴 Временно не принимает заявки"
    username_text = f"@{mentor['tg_username'].lstrip('@')}" if mentor["tg_username"] else "не указан"

    card_text = (
        f"👤 <b>{mentor['name']}</b>\n\n"
        f"📝 <b>Описание:</b>\n{mentor['description'] or '—'}\n\n"
        f"💼 <b>Опыт:</b> {mentor['experience'] or '—'}\n"
        f"🎯 <b>Специализация:</b> {mentor['specialization'] or '—'}\n"
        f"💰 <b>Стоимость:</b> {mentor['price'] or '—'}\n"
        f"📱 <b>Telegram:</b> {username_text}\n\n"
        f"{status_text}"
    )

    markup = kb.mentor_card_kb(mentor_id, bool(mentor["is_active"]), mentor["tg_username"] or "")

    if mentor["photo_file_id"]:
        try:
            await call.message.delete()
            await call.message.answer_photo(
                photo=mentor["photo_file_id"],
                caption=card_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        except Exception:
            await call.message.edit_text(card_text, reply_markup=markup, parse_mode="HTML")
    else:
        await call.message.edit_text(card_text, reply_markup=markup, parse_mode="HTML")

    await call.answer()


@router.callback_query(F.data.startswith("mentor_back_"))
async def cb_mentor_back(call: CallbackQuery):
    mentor_id = int(call.data.split("_")[2])
    mentor = await db.get_mentor(mentor_id)
    if not mentor or not mentor["category_id"]:
        categories = await db.get_root_categories()
        await call.message.edit_text(
            "📚 <b>Каталог менторов</b>\n\nВыберите направление:",
            reply_markup=kb.categories_kb(categories),
            parse_mode="HTML"
        )
        await call.answer()
        return

    cat_id = mentor["category_id"]
    mentors = await db.get_mentors_in_category(cat_id)
    path = await db.get_category_path(cat_id)
    breadcrumb = " › ".join(path)

    try:
        await call.message.edit_text(
            f"📂 <b>{breadcrumb}</b>\n\nВыберите ментора:",
            reply_markup=kb.mentors_list_kb(mentors, cat_id),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            f"📂 <b>{breadcrumb}</b>\n\nВыберите ментора:",
            reply_markup=kb.mentors_list_kb(mentors, cat_id),
            parse_mode="HTML"
        )
    await call.answer()


# ─── Apply (contact mentor) ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("apply_"))
async def cb_apply(call: CallbackQuery, bot: Bot):
    mentor_id = int(call.data.split("_")[1])
    mentor = await db.get_mentor(mentor_id)
    if not mentor:
        await call.answer("Ментор не найден", show_alert=True)
        return

    if not mentor["is_active"]:
        await call.answer("Этот ментор временно не принимает заявки.", show_alert=True)
        return

    user = call.from_user
    student_username = user.username or ""
    student_name = user.full_name or user.first_name or "Не указано"
    now = _now()

    # Get category path for direction/specialization
    path = []
    if mentor["category_id"]:
        path = await db.get_category_path(mentor["category_id"])

    direction = path[0] if len(path) > 0 else "—"
    specialization = " › ".join(path[1:]) if len(path) > 1 else path[0] if path else "—"

    # Create application
    app_id = await db.create_application(
        student_tg_id=user.id,
        student_username=student_username,
        student_name=student_name,
        mentor_id=mentor_id,
        direction=direction,
        specialization=specialization,
        created_at=now,
    )

    # Confirm to user
    username_display = f"@{student_username}" if student_username else f"ID: {user.id}"
    try:
        await call.message.edit_text(
            f"✅ <b>С Вами свяжутся :)</b>\n\n"
            f"Заявка <b>#{app_id}</b> успешно создана!\n"
            f"Ментор <b>{mentor['name']}</b> скоро свяжется с вами.",
            reply_markup=kb.after_apply_kb(mentor["tg_username"] or ""),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            f"✅ <b>С Вами свяжутся :)</b>\n\n"
            f"Заявка <b>#{app_id}</b> успешно создана!\n"
            f"Ментор <b>{mentor['name']}</b> скоро свяжется с вами.",
            reply_markup=kb.after_apply_kb(mentor["tg_username"] or ""),
            parse_mode="HTML"
        )

    # Notify mentor (if has tg_user_id)
    mentor_notification = (
        f"🔔 <b>Новая заявка #{app_id}</b>\n\n"
        f"👤 <b>Ученик:</b>\n{student_name}\n\n"
        f"📱 <b>Telegram:</b>\n{username_display}\n\n"
        f"🆔 <b>ID:</b> {user.id}\n\n"
        f"📂 <b>Направление:</b>\n{direction}\n\n"
        f"🎯 <b>Специализация:</b>\n{specialization}\n\n"
        f"📅 <b>Дата:</b>\n{now}\n\n"
        f"📌 <b>Статус:</b> Новая заявка"
    )

    if mentor["tg_user_id"]:
        try:
            await bot.send_message(
                chat_id=mentor["tg_user_id"],
                text=mentor_notification,
                reply_markup=kb.application_actions_kb(app_id),
                parse_mode="HTML"
            )
        except Exception:
            pass  # Mentor hasn't started the bot

    # Notify admin group (topic per mentor)
    admin_msg_text = (
        f"📋 <b>Заявка #{app_id}</b>\n\n"
        f"👨‍🏫 <b>Ментор:</b>\n{mentor['name']}\n\n"
        f"👤 <b>Ученик:</b>\n{student_name}\n\n"
        f"📱 <b>Telegram:</b>\n{username_display}\n\n"
        f"🆔 <b>ID:</b> {user.id}\n\n"
        f"📂 <b>Направление:</b>\n{direction}\n\n"
        f"🎯 <b>Специализация:</b>\n{specialization}\n\n"
        f"📅 <b>Дата:</b>\n{now}\n\n"
        f"📌 <b>Статус:</b> Новая заявка"
    )

    if ADMIN_GROUP_ID:
        try:
            send_kwargs = dict(
                chat_id=ADMIN_GROUP_ID,
                text=admin_msg_text,
                reply_markup=kb.admin_app_actions_kb(app_id),
                parse_mode="HTML"
            )
            # Use topic if mentor has one
            if mentor["topic_id"]:
                send_kwargs["message_thread_id"] = mentor["topic_id"]

            sent = await bot.send_message(**send_kwargs)
            await db.update_application_admin_message(app_id, sent.message_id)
        except Exception:
            pass

    await call.answer()
