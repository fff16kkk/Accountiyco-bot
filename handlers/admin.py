from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS
from keyboards import (
    admin_menu_kb, admin_plans_kb, admin_plan_actions_kb,
    admin_subs_plans_kb, admin_sub_actions_kb, pending_order_kb,
    back_to_admin_kb, main_menu_kb, cancel_kb
)

admin_router = Router()


class AdminStates(StatesGroup):
    add_plan_title = State()
    add_plan_desc = State()
    add_plan_price = State()
    add_plan_days = State()
    edit_price = State()
    edit_card_number = State()
    edit_card_name = State()
    add_sub_one = State()
    add_sub_bulk = State()
    reject_reason = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ----------------- ورود به پنل -----------------

@admin_router.message(F.text == "🛠 پنل ادمین")
async def admin_panel_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 <b>پنل مدیریت</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")


@admin_router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی نداری.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("🛠 <b>پنل مدیریت</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ----------------- مدیریت پلن‌ها -----------------

@admin_router.callback_query(F.data == "admin_plans")
async def admin_plans(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plans = await db.get_all_plans()
    text = "📋 <b>مدیریت پلن‌ها</b>\n\nروی هر پلن کلیک کنید:"
    await callback.message.edit_text(text, reply_markup=admin_plans_kb(plans), parse_mode="HTML")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_add_plan")
async def start_add_plan(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.add_plan_title)
    await callback.message.answer("📝 عنوان پلن را وارد کنید:", reply_markup=cancel_kb())
    await callback.answer()


@admin_router.message(AdminStates.add_plan_title)
async def add_plan_title(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return
    await state.update_data(title=message.text)
    await state.set_state(AdminStates.add_plan_desc)
    await message.answer("📝 توضیحات پلن را وارد کنید (یا - برای خالی):")


@admin_router.message(AdminStates.add_plan_desc)
async def add_plan_desc(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return
    desc = None if message.text.strip() == "-" else message.text
    await state.update_data(description=desc)
    await state.set_state(AdminStates.add_plan_price)
    await message.answer("💰 قیمت پلن را به تومان وارد کنید (فقط عدد):")


@admin_router.message(AdminStates.add_plan_price)
async def add_plan_price(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return
    try:
        price = int(message.text.replace(",", "").replace("،", "").strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("قیمت نامعتبر است. فقط عدد وارد کنید:")
        return

    await state.update_data(price=price)
    await state.set_state(AdminStates.add_plan_days)
    await message.answer("⏱ مدت پلن را به روز وارد کنید (فقط عدد):")


@admin_router.message(AdminStates.add_plan_days)
async def add_plan_days(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
    except ValueError:
        await message.answer("تعداد روز نامعتبر است. فقط عدد وارد کنید:")
        return

    data = await state.get_data()
    plan_id = await db.add_plan(
        title=data["title"],
        description=data.get("description"),
        price=data["price"],
        duration_days=days
    )
    await state.clear()
    await message.answer(
        f"✅ پلن با موفقیت اضافه شد.\n🆔 پلن: {plan_id}",
        reply_markup=main_menu_kb(True)
    )


@admin_router.callback_query(F.data.startswith("admin_plan_"))
async def admin_plan_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[2])
    plan = await db.get_plan(plan_id)
    if not plan:
        await callback.answer("پلن یافت نشد.", show_alert=True)
        return

    stats = await db.get_sub_links_stats(plan_id)
    status = "فعال ✅" if plan["is_active"] else "غیرفعال ❌"

    text = (
        f"📦 <b>{plan['title']}</b>\n\n"
        f"📝 {plan['description'] or '—'}\n"
        f"💰 قیمت: {plan['price']:,} تومان\n"
        f"⏱ مدت: {plan['duration_days']} روز\n"
        f"وضعیت: {status}\n"
        f"🔗 لینک موجود: {stats['available']} از {stats['total']}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_plan_actions_kb(plan_id),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("edit_price_"))
async def start_edit_price(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[2])
    await state.set_state(AdminStates.edit_price)
    await state.update_data(plan_id=plan_id)
    await callback.message.answer("💰 قیمت جدید را به تومان وارد کنید:", reply_markup=cancel_kb())
    await callback.answer()


@admin_router.message(AdminStates.edit_price)
async def process_edit_price(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return
    try:
        price = int(message.text.replace(",", "").replace("،", "").strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("قیمت نامعتبر است:")
        return

    data = await state.get_data()
    await db.update_plan_price(data["plan_id"], price)
    await state.clear()
    await message.answer(f"✅ قیمت پلن به {price:,} تومان تغییر کرد.", reply_markup=main_menu_kb(True))


@admin_router.callback_query(F.data.startswith("toggle_plan_"))
async def toggle_plan(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[2])
    plan = await db.get_plan(plan_id)
    if not plan:
        await callback.answer("پلن یافت نشد.", show_alert=True)
        return

    new_status = 0 if plan["is_active"] else 1
    await db.update_plan(plan_id, is_active=new_status)
    status_text = "فعال" if new_status else "غیرفعال"
    await callback.answer(f"پلن {status_text} شد.", show_alert=True)

    # رفرش صفحه
    plan = await db.get_plan(plan_id)
    stats = await db.get_sub_links_stats(plan_id)
    status = "فعال ✅" if plan["is_active"] else "غیرفعال ❌"
    text = (
        f"📦 <b>{plan['title']}</b>\n\n"
        f"📝 {plan['description'] or '—'}\n"
        f"💰 قیمت: {plan['price']:,} تومان\n"
        f"⏱ مدت: {plan['duration_days']} روز\n"
        f"وضعیت: {status}\n"
        f"🔗 لینک موجود: {stats['available']} از {stats['total']}"
    )
    await callback.message.edit_text(text, reply_markup=admin_plan_actions_kb(plan_id), parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("delete_plan_"))
async def delete_plan(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[2])
    await db.delete_plan(plan_id)
    await callback.answer("پلن حذف شد.", show_alert=True)
    plans = await db.get_all_plans()
    await callback.message.edit_text(
        "📋 <b>مدیریت پلن‌ها</b>",
        reply_markup=admin_plans_kb(plans),
        parse_mode="HTML"
    )


# ----------------- مدیریت لینک ساب -----------------

@admin_router.callback_query(F.data == "admin_subs")
async def admin_subs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plans = await db.get_all_plans()
    if not plans:
        await callback.answer("اول باید پلن بسازی.", show_alert=True)
        return
    await callback.message.edit_text(
        "🔗 <b>مدیریت لینک‌های ساب</b>\n\nپلن مورد نظر را انتخاب کنید:",
        reply_markup=admin_subs_plans_kb(plans),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_sub_plan_"))
async def admin_sub_plan(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[3])
    plan = await db.get_plan(plan_id)
    stats = await db.get_sub_links_stats(plan_id)

    text = (
        f"🔗 مدیریت لینک‌های پلن: <b>{plan['title']}</b>\n\n"
        f"کل لینک‌ها: {stats['total']}\n"
        f"موجود: {stats['available']}\n"
        f"استفاده‌شده: {stats['used']}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_sub_actions_kb(plan_id),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("add_sub_one_"))
async def start_add_sub_one(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[3])
    await state.set_state(AdminStates.add_sub_one)
    await state.update_data(plan_id=plan_id)
    await callback.message.answer(
        "🔗 لینک ساب را ارسال کنید:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@admin_router.message(AdminStates.add_sub_one)
async def process_add_sub_one(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return

    data = await state.get_data()
    await db.add_sub_link(data["plan_id"], message.text.strip())
    await state.clear()
    await message.answer("✅ لینک با موفقیت اضافه شد.", reply_markup=main_menu_kb(True))


@admin_router.callback_query(F.data.startswith("add_sub_bulk_"))
async def start_add_sub_bulk(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[3])
    await state.set_state(AdminStates.add_sub_bulk)
    await state.update_data(plan_id=plan_id)
    await callback.message.answer(
        "📥 لینک‌ها را ارسال کنید (هر خط یک لینک):\n\n"
        "مثال:\n"
        "https://sub1.example.com/...\n"
        "https://sub2.example.com/...\n"
        "https://sub3.example.com/...",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@admin_router.message(AdminStates.add_sub_bulk)
async def process_add_sub_bulk(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return

    links = [line.strip() for line in message.text.strip().splitlines() if line.strip()]
    if not links:
        await message.answer("هیچ لینک معتبری پیدا نشد.")
        return

    data = await state.get_data()
    await db.add_sub_links_bulk(data["plan_id"], links)
    await state.clear()
    await message.answer(
        f"✅ {len(links)} لینک با موفقیت اضافه شد.",
        reply_markup=main_menu_kb(True)
    )


@admin_router.callback_query(F.data.startswith("sub_stats_"))
async def sub_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    plan_id = int(callback.data.split("_")[2])
    plan = await db.get_plan(plan_id)
    stats = await db.get_sub_links_stats(plan_id)

    text = (
        f"📊 موجودی لینک‌های <b>{plan['title']}</b>\n\n"
        f"کل: {stats['total']}\n"
        f"موجود: {stats['available']}\n"
        f"استفاده‌شده: {stats['used']}"
    )
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML")


# ----------------- سفارش‌های در انتظار -----------------

@admin_router.callback_query(F.data == "admin_pending")
async def admin_pending(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    orders = await db.get_pending_orders()
    if not orders:
        await callback.message.edit_text(
            "✅ هیچ سفارش در انتظار تأییدی وجود ندارد.",
            reply_markup=back_to_admin_kb()
        )
        await callback.answer()
        return

    text = f"📦 <b>سفارش‌های در انتظار تأیید</b> ({len(orders)} عدد)\n\n"
    for o in orders[:20]:
        text += (
            f"🆔 <code>{o['id']}</code> | {o['plan_title']}\n"
            f"👤 {o['full_name']} | {o['amount']:,} ت\n"
            f"────────────\n"
        )

    await callback.message.edit_text(text, reply_markup=back_to_admin_kb(), parse_mode="HTML")

    # ارسال دکمه‌های جداگانه برای هر سفارش
    for o in orders[:10]:
        await callback.message.answer(
            f"سفارش <code>{o['id']}</code> - {o['plan_title']}\n"
            f"کاربر: {o['full_name']}",
            reply_markup=pending_order_kb(o["id"]),
            parse_mode="HTML"
        )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("approve_"))
async def approve_order(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[1])
    order = await db.get_order(order_id)

    if not order:
        await callback.answer("سفارش یافت نشد.", show_alert=True)
        return

    if order["status"] != "waiting_approval":
        await callback.answer("این سفارش دیگر در انتظار تأیید نیست.", show_alert=True)
        return

    # گرفتن لینک آزاد
    sub = await db.get_available_sub_link(order["plan_id"])
    if not sub:
        await callback.answer(
            "⚠️ لینک موجود برای این پلن وجود ندارد! اول لینک اضافه کنید.",
            show_alert=True
        )
        return

    # علامت‌گذاری لینک و آپدیت سفارش
    await db.mark_sub_link_used(sub["id"], order_id)
    await db.update_order_status(order_id, "delivered", sub_link=sub["link"])

    plan = await db.get_plan(order["plan_id"])

    # ارسال به کاربر
    user_text = (
        f"✅ <b>سفارش شما تأیید شد</b>\n\n"
        f"🆔 شماره سفارش: <code>{order_id}</code>\n"
        f"📦 پلن: {plan['title'] if plan else '—'}\n"
        f"⏱ مدت: {plan['duration_days']} روز\n\n"
        f"🔗 <b>لینک ساب شما:</b>\n"
        f"<code>{sub['link']}</code>\n\n"
        f"این لینک را در اپلیکیشن خود وارد کنید."
    )

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=user_text,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n✅ توسط ادمین تأیید شد و لینک ارسال گردید.",
        parse_mode="HTML"
    ) if callback.message.photo else await callback.message.edit_text(
        f"✅ سفارش {order_id} تأیید و لینک ارسال شد."
    )

    await callback.answer("تأیید شد و لینک برای کاربر ارسال گردید.", show_alert=True)


@admin_router.callback_query(F.data.startswith("reject_"))
async def start_reject(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    order_id = int(callback.data.split("_")[1])
    await state.set_state(AdminStates.reject_reason)
    await state.update_data(order_id=order_id)
    await callback.message.answer(
        "دلیل رد کردن را بنویسید (برای کاربر ارسال می‌شود):",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@admin_router.message(AdminStates.reject_reason)
async def process_reject(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return

    data = await state.get_data()
    order_id = data["order_id"]
    order = await db.get_order(order_id)

    if not order:
        await message.answer("سفارش یافت نشد.")
        await state.clear()
        return

    reason = message.text
    await db.update_order_status(order_id, "rejected", admin_note=reason)

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"❌ <b>سفارش شما رد شد</b>\n\n"
                f"🆔 شماره سفارش: <code>{order_id}</code>\n"
                f"📝 دلیل: {reason}\n\n"
                f"در صورت نیاز با پشتیبانی در ارتباط باشید."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()
    await message.answer(f"✅ سفارش {order_id} رد شد و به کاربر اطلاع داده شد.", reply_markup=main_menu_kb(True))


# ----------------- تغییر کارت -----------------

@admin_router.callback_query(F.data == "admin_card")
async def admin_card(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    card_number = await db.get_setting("card_number") or "تنظیم نشده"
    card_name = await db.get_setting("card_name") or "تنظیم نشده"

    text = (
        f"💳 <b>اطلاعات کارت فعلی</b>\n\n"
        f"شماره کارت:\n<code>{card_number}</code>\n"
        f"نام صاحب کارت: <b>{card_name}</b>\n\n"
        f"چه چیزی را می‌خواهید تغییر دهید؟"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🔢 تغییر شماره کارت", callback_data="edit_card_number")
    builder.button(text="👤 تغییر نام صاحب کارت", callback_data="edit_card_name")
    builder.button(text="🔙 بازگشت", callback_data="admin_panel")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@admin_router.callback_query(F.data == "edit_card_number")
async def start_edit_card_number(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.edit_card_number)
    await callback.message.answer(
        "🔢 شماره کارت جدید را وارد کنید:\n(مثال: 6037-XXXX-XXXX-XXXX)",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@admin_router.message(AdminStates.edit_card_number)
async def process_edit_card_number(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return

    await db.set_setting("card_number", message.text.strip())
    await state.clear()
    await message.answer("✅ شماره کارت با موفقیت تغییر کرد.", reply_markup=main_menu_kb(True))


@admin_router.callback_query(F.data == "edit_card_name")
async def start_edit_card_name(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.edit_card_name)
    await callback.message.answer(
        "👤 نام صاحب کارت را وارد کنید:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@admin_router.message(AdminStates.edit_card_name)
async def process_edit_card_name(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("لغو شد.", reply_markup=main_menu_kb(True))
        return

    await db.set_setting("card_name", message.text.strip())
    await state.clear()
    await message.answer("✅ نام صاحب کارت با موفقیت تغییر کرد.", reply_markup=main_menu_kb(True))


# ----------------- آمار -----------------

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    pending = await db.get_orders_count_by_status("waiting_approval")
    delivered = await db.get_orders_count_by_status("delivered")
    rejected = await db.get_orders_count_by_status("rejected")

    plans = await db.get_all_plans()
    total_available_subs = 0
    for p in plans:
        stats = await db.get_sub_links_stats(p["id"])
        total_available_subs += stats["available"]

    text = (
        f"📊 <b>آمار ربات</b>\n\n"
        f"🕐 سفارش در انتظار تأیید: <b>{pending}</b>\n"
        f"✅ سفارش تحویل‌شده: <b>{delivered}</b>\n"
        f"❌ سفارش رد‌شده: <b>{rejected}</b>\n"
        f"🔗 کل لینک موجود: <b>{total_available_subs}</b>\n"
        f"📦 تعداد پلن‌ها: <b>{len(plans)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_admin_kb(), parse_mode="HTML")
    await callback.answer()
