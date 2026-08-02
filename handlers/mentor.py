from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import database as db
import keyboards as kb
from config import ADMIN_GROUP_ID

router = Router()


def _now() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def _build_admin_text(app, mentor_name: str, new_status: str) -> str:
    username_display = f"@{app['student_username']}" if app["student_username"] else f"ID: {app['student_tg_id']}"
    return (
        f"📋 <b>Заявка #{app['id']}</b>\n\n"
        f"👨‍🏫 <b>Ментор:</b>\n{mentor_name}\n\n"
        f"👤 <b>Ученик:</b>\n{app['student_name']}\n\n"
        f"📱 <b>Telegram:</b>\n{username_display}\n\n"
        f"🆔 <b>ID:</b> {app['student_tg_id']}\n\n"
        f"📂 <b>Направление:</b>\n{app['direction']}\n\n"
        f"🎯 <b>Специализация:</b>\n{app['specialization']}\n\n"
        f"📅 <b>Дата:</b>\n{app['created_at']}\n\n"
        f"📌 <b>Статус:</b> {new_status}"
    )


# ─── Accept application ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("app_accept_"))
async def cb_app_accept(call: CallbackQuery, bot: Bot):
    app_id = int(call.data.split("_")[2])
    app = await db.get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    now = _now()
    await db.update_application_status(app_id, "Подтверждена", now)
    mentor = await db.get_mentor(app["mentor_id"])
    mentor_name = mentor["name"] if mentor else "—"

    # Edit mentor's notification message
    await call.message.edit_text(
        f"✅ <b>Заявка #{app_id} принята</b>\n\n"
        f"👤 Ученик: {app['student_name']}\n"
        f"📱 @{app['student_username'] or '—'}\n"
        f"📅 {app['created_at']}\n\n"
        f"📌 Статус: <b>Подтверждена</b>",
        parse_mode="HTML"
    )

    # Update admin group message
    if ADMIN_GROUP_ID and app["admin_message_id"] and mentor:
        try:
            new_text = _build_admin_text(app, mentor_name, "Подтверждена")
            await bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=app["admin_message_id"],
                text=new_text,
                reply_markup=kb.admin_app_actions_kb(app_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await call.answer("✅ Заявка принята!", show_alert=True)


# ─── Reject application ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("app_reject_"))
async def cb_app_reject(call: CallbackQuery, bot: Bot):
    app_id = int(call.data.split("_")[2])
    app = await db.get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    now = _now()
    await db.update_application_status(app_id, "Отклонена", now)
    mentor = await db.get_mentor(app["mentor_id"])
    mentor_name = mentor["name"] if mentor else "—"

    # Edit mentor's notification message
    await call.message.edit_text(
        f"❌ <b>Заявка #{app_id} отклонена</b>\n\n"
        f"👤 Ученик: {app['student_name']}\n"
        f"📱 @{app['student_username'] or '—'}\n"
        f"📅 {app['created_at']}\n\n"
        f"📌 Статус: <b>Отклонена</b>",
        parse_mode="HTML"
    )

    # Update admin group message
    if ADMIN_GROUP_ID and app["admin_message_id"] and mentor:
        try:
            new_text = _build_admin_text(app, mentor_name, "Отклонена")
            await bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=app["admin_message_id"],
                text=new_text,
                reply_markup=kb.admin_app_actions_kb(app_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await call.answer("❌ Заявка отклонена", show_alert=True)


# ─── CRM actions (from admin group) ──────────────────────────────────────────

@router.callback_query(F.data.startswith("crm_contacted_"))
async def cb_crm_contacted(call: CallbackQuery):
    app_id = int(call.data.split("_")[2])
    app = await db.get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    await db.update_application_field(app_id, "contacted", 1)
    mentor = await db.get_mentor(app["mentor_id"])
    mentor_name = mentor["name"] if mentor else "—"

    # Refresh admin message
    app = await db.get_application(app_id)
    new_text = _build_admin_text(app, mentor_name, app["status"]) + "\n\n🤝 <b>Связь состоялась</b>"
    try:
        await call.message.edit_text(
            new_text,
            reply_markup=kb.admin_app_actions_kb(app_id),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer("🤝 Отмечено: связь состоялась", show_alert=True)


@router.callback_query(F.data.startswith("crm_deal_"))
async def cb_crm_deal(call: CallbackQuery):
    app_id = int(call.data.split("_")[2])
    app = await db.get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    await db.update_application_field(app_id, "deal_closed", 1)
    mentor = await db.get_mentor(app["mentor_id"])
    mentor_name = mentor["name"] if mentor else "—"

    app = await db.get_application(app_id)
    new_text = _build_admin_text(app, mentor_name, app["status"]) + "\n\n💰 <b>Сделка закрыта</b>"
    try:
        await call.message.edit_text(
            new_text,
            reply_markup=kb.admin_app_actions_kb(app_id),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer("💰 Отмечено: сделка закрыта", show_alert=True)


@router.callback_query(F.data.startswith("crm_commission_"))
async def cb_crm_commission(call: CallbackQuery):
    app_id = int(call.data.split("_")[2])
    app = await db.get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    await db.update_application_field(app_id, "commission_paid", 1)
    mentor = await db.get_mentor(app["mentor_id"])
    mentor_name = mentor["name"] if mentor else "—"

    app = await db.get_application(app_id)
    new_text = _build_admin_text(app, mentor_name, app["status"]) + "\n\n💵 <b>Комиссия получена</b>"
    try:
        await call.message.edit_text(
            new_text,
            reply_markup=kb.admin_app_actions_kb(app_id),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer("💵 Отмечено: комиссия получена", show_alert=True)
