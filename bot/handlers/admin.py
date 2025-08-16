from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.services import UserService

router = Router()

router.message.filter(F.from_user.id == settings.ADMIN_ID)


@router.message(Command("delsub"))
async def cmd_delsub(message: Message, user_service: UserService):
    """
    Удаляет подписку у пользователя.
    Использование: /delsub <telegram_id>
    """
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неверный формат. Используйте: <code>/delsub &lt;ID пользователя&gt;</code>"
        )
        return

    try:
        user_id_to_revoke = int(args[1])
    except ValueError:
        await message.answer(
            "❌ ID пользователя должен быть числом. Используйте: <code>/delsub &lt;ID пользователя&gt;</code>"
        )
        return

    was_revoked = await user_service.revoke_subscription(user_id_to_revoke)

    if was_revoked:
        await message.answer(
            f"✅ Подписка для пользователя с ID <code>{user_id_to_revoke}</code> успешно отозвана."
        )
    else:
        await message.answer(
            f"⚠️ Не удалось отозвать подписку для ID <code>{user_id_to_revoke}</code>. "
            f"Возможно, у пользователя нет активной подписки или такой ID не найден."
        )
