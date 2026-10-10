from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS, SUPPORT_USERNAME
from keyboards import (
    main_menu_kb, plans_kb, plan_detail_kb, payment_kb, cancel_kb
)

user_router = Router()


class BuyState(StatesGroup):
    waiting_receipt = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ----------------- Start -----------------

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    welcome = await db.get_setting("welcome_text") or "به ربات فروش فیلترشکن خوش آمدید 🌟"
    text = (
        f"{welcome}\n\n"
        f"از منوی زیر می‌تونی سرویس مورد نظرت رو انتخاب کنی."
    )
    await message.answer(text, reply_markup=main_menu_kb(is_admin(message.from_user.id)))


@user_router.message(F.text == "🔙 منوی اصلی")
@user_router.callback_query(F.data == "back_main")
async def back_to_main(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    text = "منوی اصلی:"
    kb = main_menu_kb(is_admin(event.from_user.id))

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text)
        await event.message.answer("از منوی زیر انتخاب کن:", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)


# ----------------- نمایش پلن‌ها -----------------

@user_router.message(F.text == "🛒 خرید سرویس")
@user_router.callback_query(F.data == "show_plans")
async def show_plans(event: Message | CallbackQuery):
    plans = await db.get_active_plans()

    if not plans:
        text = "⚠️ در حال حاضر پلنی برای فروش وجود ندارد."
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    text = "🛒 لطفاً یکی از پلن‌های زیر را انتخاب کنید:"
    kb = plans_kb(plans)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)


@user_router.callback_query(F.data.startswith("plan_"))
async def show_plan_detail(callback: CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    plan = await db.get_plan(plan_id)

    if not plan or not plan["is_active"]:
        await callback.answer("این پلن دیگر موجود نیست.", show_alert=True)
        return

    available = await db.get_available_sub_count(plan_id)

    text = (
        f"📦 <b>{plan['title']}</b>\n\n"
        f"📝 توضیحات:\n{plan['description'] or '—'}\n\n"
        f"⏱ مدت: <b>{plan['duration_days']} روز</b>\n"
        f"💰 قیمت: <b>{plan['price']:,} تومان</b>\n"
        f"🔗 موجودی لینک: <b>{available}</b> عدد\n"
    )

    if available == 0:
        text += "\n⚠️ موجودی این پلن تمام شده است."

    await callback.message.edit_text(
        text,
        reply_markup=plan_detail_kb(plan_id),
        parse_mode="HTML"
    )
    await callback.answer()


# ----------------- خرید -----------------

@user_router.callback_query(F.data.startswith("buy_"))
async def start_buy(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split("_")[1])
    plan = await db.get_plan(plan_id)

    if not plan or not plan["is_active"]:
        await callback.answer("این پلن دیگر موجود نیست.", show_alert=True)
        return

    available = await db.get_available_sub_count(plan_id)
    if available == 0:
        await callback.answer("موجودی این پلن تمام شده. لطفاً بعداً دوباره تلاش کنید.", show_alert=True)
        return

    order_id = await db.create_order(
        user_id=callback.from_user.id,
        plan_id=plan_id,
        amount=plan["price"]
    )

    card_number = await db.get_setting("card_number") or "تنظیم نشده"
    card_name = await db.get_setting("card_name") or "تنظیم نشده"

    text = (
        f"✅ سفارش شما ثبت شد.\n\n"
        f"🆔 شماره سفارش: <code>{order_id}</code>\n"
        f"📦 پلن: <b>{plan['title']}</b>\n"
        f"💰 مبلغ قابل پرداخت: <b>{plan['price']:,} تومان</b>\n\n"
        f"💳 لطفاً مبلغ را به کارت زیر واریز کنید:\n\n"
        f"شماره کارت:\n<code>{card_number}</code>\n"
        f"به نام: <b>{card_name}</b>\n\n"
        f"پس از واریز، روی دکمه «ارسال رسید پرداخت» بزنید و عکس فیش را ارسال کنید."
    )

    await callback.message.edit_text(text, reply_markup=payment_kb(order_id), parse_mode="HTML")
    await callback.answer()


@user_router.callback_query(F.data.startswith("send_receipt_"))
async def ask_receipt(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)

    if not order or order["user_id"] != callback.from_user.id:
        await callback.answer("سفارش یافت نشد.", show_alert=True)
        return

    if order["status"] not in ("pending", "waiting_approval"):
        await callback.answer("وضعیت این سفارش قابل تغییر نیست.", show_alert=True)
        return

    await state.set_state(BuyState.waiting_receipt)
    await state.update_data(order_id=order_id)

    await callback.message.answer(
        "📤 لطفاً عکس رسید پرداخت را ارسال کنید:\n\n"
        "(فقط عکس بفرستید)",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@user_router.message(BuyState.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await message.answer("خطا در پردازش. دوباره تلاش کنید.")
        await state.clear()
        return

    order = await db.get_order(order_id)
    if not order or order["user_id"] != message.from_user.id:
        await message.answer("سفارش یافت نشد.")
        await state.clear()
        return

    file_id = message.photo[-1].file_id
    await db.set_order_receipt(order_id, file_id)

    await state.clear()
    await message.answer(
        "✅ رسید شما دریافت شد و برای بررسی به ادمین ارسال گردید.\n"
        "پس از تأیید، لینک ساب برای شما ارسال می‌شود.",
        reply_markup=main_menu_kb(is_admin(message.from_user.id))
    )

    # اطلاع به ادمین‌ها
    plan = await db.get_plan(order["plan_id"])
    user = message.from_user

    admin_text = (
        f"🔔 <b>رسید جدید دریافت شد</b>\n\n"
        f"🆔 سفارش: <code>{order_id}</code>\n"
        f"👤 کاربر: {user.full_name}"
        f"{' (@' + user.username + ')' if user.username else ''}\n"
        f"🆔 آیدی: <code>{user.id}</code>\n"
        f"📦 پلن: {plan['title'] if plan else '—'}\n"
        f"💰 مبلغ: {order['amount']:,} تومان"
    )

    from keyboards import pending_order_kb

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=admin_text,
                parse_mode="HTML",
                reply_markup=pending_order_kb(order_id)
            )
        except Exception:
            pass


@user_router.message(BuyState.waiting_receipt)
async def invalid_receipt(message: Message):
    if message.text == "❌ انصراف":
        await message.answer(
            "عملیات لغو شد.",
            reply_markup=main_menu_kb(is_admin(message.from_user.id))
        )
        await message.answer("منوی اصلی:")
        return

    await message.answer("لطفاً فقط <b>عکس</b> رسید را ارسال کنید.", parse_mode="HTML")


@user_router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)

    if not order or order["user_id"] != callback.from_user.id:
        await callback.answer("سفارش یافت نشد.", show_alert=True)
        return

    if order["status"] in ("delivered", "rejected"):
        await callback.answer("این سفارش دیگر قابل لغو نیست.", show_alert=True)
        return

    await db.update_order_status(order_id, "cancelled")
    await state.clear()
    await callback.message.edit_text("❌ سفارش شما لغو شد.")
    await callback.answer()


# ----------------- سفارش‌های من -----------------

@user_router.message(F.text == "📦 سفارش‌های من")
async def my_orders(message: Message):
    orders = await db.get_user_orders(message.from_user.id)

    if not orders:
        await message.answer("شما هنوز سفارشی ثبت نکرده‌اید.")
        return

    status_map = {
        "pending": "⏳ در انتظار پرداخت",
        "waiting_approval": "🕐 در انتظار تأیید ادمین",
        "delivered": "✅ تحویل شده",
        "rejected": "❌ رد شده",
        "cancelled": "🚫 لغو شده"
    }

    text = "📦 <b>سفارش‌های شما:</b>\n\n"
    for o in orders[:15]:
        status = status_map.get(o["status"], o["status"])
        text += (
            f"🆔 <code>{o['id']}</code> | {o['plan_title']}\n"
            f"💰 {o['amount']:,} تومان | {status}\n"
        )
        if o["status"] == "delivered" and o["sub_link"]:
            text += f"🔗 لینک: <code>{o['sub_link']}</code>\n"
        text += "────────────\n"

    await message.answer(text, parse_mode="HTML")


# ----------------- اطلاعات پرداخت -----------------

@user_router.message(F.text == "💳 اطلاعات پرداخت")
async def payment_info(message: Message):
    card_number = await db.get_setting("card_number") or "تنظیم نشده"
    card_name = await db.get_setting("card_name") or "تنظیم نشده"

    text = (
        "💳 <b>اطلاعات پرداخت کارت به کارت</b>\n\n"
        f"شماره کارت:\n<code>{card_number}</code>\n\n"
        f"به نام: <b>{card_name}</b>\n\n"
        "پس از خرید پلن، رسید را از طریق ربات ارسال کنید."
    )
    await message.answer(text, parse_mode="HTML")


# ----------------- پشتیبانی -----------------

@user_router.message(F.text == "📞 پشتیبانی")
async def support(message: Message):
    text = (
        f"📞 برای ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n\n"
        f"👤 @{SUPPORT_USERNAME}"
    )
    await message.answer(text)
