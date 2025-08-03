from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold

from bot.keyboards import start_kb, search_type_kb
from db.repository import UserRepo

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user_repo: UserRepo):
    await user_repo.get_or_create_user(message.from_user.id, message.from_user.username)

    user_name = hbold(message.from_user.full_name)

    welcome_text = (
        f"Привет, {user_name}! 👋🏻\n\n"
        "Ну что, проверим, является ли искомый ресурс «нежелательной организацией», "
        "экстремистским, террористическим или доступ к нему ограничен по решению суда "
        "(сайты иноагентов, пиратские и т.д.)!"
    )

    await message.answer(welcome_text, reply_markup=start_kb, parse_mode="HTML")


@router.callback_query(F.data == "go_to_check")
async def cb_go_to_check(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Выберите, что вы хотите проверить:", reply_markup=search_type_kb
    )


@router.message(Command("check"))
async def cmd_check(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Выберите, что вы хотите проверить:", reply_markup=search_type_kb
    )
