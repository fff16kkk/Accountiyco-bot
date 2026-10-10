from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛒 خرید سرویس")
    builder.button(text="📦 سفارش‌های من")
    builder.button(text="💳 اطلاعات پرداخت")
    builder.button(text="📞 پشتیبانی")
    if is_admin:
        builder.button(text="🛠 پنل ادمین")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def plans_kb(plans: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.button(
            text=f"{plan['title']} - {plan['price']:,} تومان",
            callback_data=f"plan_{plan['id']}"
        )
    builder.button(text="🔙 بازگشت", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def plan_detail_kb(plan_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ خرید این پلن", callback_data=f"buy_{plan_id}")
    builder.button(text="🔙 بازگشت به پلن‌ها", callback_data="show_plans")
    builder.adjust(1)
    return builder.as_markup()


def payment_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 ارسال رسید پرداخت", callback_data=f"send_receipt_{order_id}")
    builder.button(text="❌ انصراف", callback_data=f"cancel_order_{order_id}")
    builder.adjust(1)
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 مدیریت پلن‌ها", callback_data="admin_plans")
    builder.button(text="🔗 مدیریت لینک ساب", callback_data="admin_subs")
    builder.button(text="📦 سفارش‌های در انتظار", callback_data="admin_pending")
    builder.button(text="💳 تغییر کارت", callback_data="admin_card")
    builder.button(text="📊 آمار", callback_data="admin_stats")
    builder.button(text="🔙 منوی اصلی", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def admin_plans_kb(plans: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        status = "✅" if plan["is_active"] else "❌"
        builder.button(
            text=f"{status} {plan['title']} | {plan['price']:,} ت",
            callback_data=f"admin_plan_{plan['id']}"
        )
    builder.button(text="➕ افزودن پلن جدید", callback_data="admin_add_plan")
    builder.button(text="🔙 بازگشت", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def admin_plan_actions_kb(plan_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 تغییر قیمت", callback_data=f"edit_price_{plan_id}")
    builder.button(text="✏️ ویرایش کامل", callback_data=f"edit_plan_{plan_id}")
    builder.button(text="🔄 فعال/غیرفعال", callback_data=f"toggle_plan_{plan_id}")
    builder.button(text="🗑 حذف پلن", callback_data=f"delete_plan_{plan_id}")
    builder.button(text="🔙 بازگشت", callback_data="admin_plans")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def admin_subs_plans_kb(plans: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.button(
            text=f"{plan['title']}",
            callback_data=f"admin_sub_plan_{plan['id']}"
        )
    builder.button(text="🔙 بازگشت", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def admin_sub_actions_kb(plan_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ افزودن لینک (تکی)", callback_data=f"add_sub_one_{plan_id}")
    builder.button(text="📥 افزودن گروهی لینک", callback_data=f"add_sub_bulk_{plan_id}")
    builder.button(text="📊 موجودی لینک‌ها", callback_data=f"sub_stats_{plan_id}")
    builder.button(text="🔙 بازگشت", callback_data="admin_subs")
    builder.adjust(1)
    return builder.as_markup()


def pending_order_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ تأیید و ارسال لینک", callback_data=f"approve_{order_id}")
    builder.button(text="❌ رد کردن", callback_data=f"reject_{order_id}")
    builder.button(text="🔙 بازگشت", callback_data="admin_pending")
    builder.adjust(1)
    return builder.as_markup()


def back_to_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 بازگشت به پنل ادمین", callback_data="admin_panel")
    return builder.as_markup()


def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ انصراف")
    return builder.as_markup(resize_keyboard=True)
