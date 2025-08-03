from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime

from db.repository import UserRepo
from bot.keyboards import profile_kb
from bot.handlers.search import send_subscription_invoice

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message, user_repo: UserRepo):
    user = await user_repo.get_or_create_user(
        message.from_user.id, message.from_user.username
    )

    expires_at = user.subscription_expires_at
    if expires_at and expires_at > datetime.now():
        sub_status = f"✅ Активна до {expires_at.strftime('%d.%m.%Y %H:%M')}"
        sub_details = "Вам доступны безлимитные проверки по реестрам и проверка URL раз в 30 минут."
    else:
        sub_status = "❌ Не активна"
        sub_details = "Приобретите подписку для снятия ограничений."

    profile_text = (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"<b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Статус подписки:</b> {sub_status}\n\n"
        f"<i>{sub_details}</i>"
    )

    await message.answer(profile_text, parse_mode="HTML", reply_markup=profile_kb)


@router.callback_query(F.data == "buy_subscription")
async def cb_buy_subscription(callback: CallbackQuery):
    await send_subscription_invoice(callback.from_user.id, callback.bot)
    await callback.answer()
