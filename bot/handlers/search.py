from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery

from bot.fsm import Search
from bot.keyboards import get_payment_kb
from bot.services import UserService, SearchService
from bot.config import settings
from bot.utils import normalize_url_for_search

router = Router()


async def send_subscription_invoice(user_id: int, bot: Bot):
    await bot.send_invoice(
        chat_id=user_id,
        title="Подписка на 30 дней",
        description="Полный доступ ко всем функциям It_brother_bot на 30 дней.",
        payload="subscription_payload",
        provider_token=settings.PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка на 30 дней", amount=1900 * 100)],
        need_email=True,
    )


async def send_single_check_invoice(user_id: int, bot: Bot, payload: str):
    await bot.send_invoice(
        chat_id=user_id,
        title="Разовая проверка",
        description="Одна полная проверка по выбранному реестру.",
        payload=payload,
        provider_token=settings.PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Разовая проверка", amount=200 * 100)],
        need_email=True,
    )


@router.callback_query(F.data == "search_entity")
async def start_entity_search(
    callback: CallbackQuery, state: FSMContext, user_service: UserService
):
    user_id = callback.from_user.id
    credits = await user_service.get_credits(user_id)

    if await user_service.has_active_subscription(user_id) or credits > 0:
        await callback.message.answer("Введите название организации:")
        await state.set_state(Search.waiting_for_entity_name)
    else:
        await callback.message.answer(
            "Эта проверка платная. Выберите действие:",
            reply_markup=get_payment_kb("payload_entity_check"),
        )
    await callback.answer()


@router.message(Search.waiting_for_entity_name)
async def process_entity_search(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    search_service: SearchService,
):
    user_id = message.from_user.id
    query = message.text
    await state.clear()

    msg = await message.answer(f"Проверяю '<i>{query}</i>'...", parse_mode="HTML")
    verdict = await search_service.get_entity_verdict(query)

    if not await user_service.has_active_subscription(user_id):
        await user_service.spend_credit(user_id)

    await msg.edit_text(verdict, parse_mode="Markdown")


@router.callback_query(F.data == "search_url")
async def start_url_search(
    callback: CallbackQuery, state: FSMContext, user_service: UserService
):
    user_id = callback.from_user.id
    credits = await user_service.get_credits(user_id)

    if await user_service.has_active_subscription(user_id) or credits > 0:
        if await user_service.can_check_url(user_id):
            await callback.message.answer("Введите URL сайта:")
            await state.set_state(Search.waiting_for_url)
        else:
            await callback.answer(
                "Вы уже выполняли проверку URL менее 30 минут назад.", show_alert=True
            )
    else:
        await callback.message.answer(
            "Эта проверка платная...", reply_markup=get_payment_kb("payload_url_check")
        )
    await callback.answer()


@router.message(Search.waiting_for_url)
async def process_url_search(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    search_service: SearchService,
):
    user_id = message.from_user.id
    url = message.text.strip()
    await state.clear()

    normalized_url = normalize_url_for_search(url)
    waiting_msg = await message.answer(
        f"Проверяю <code>{normalized_url}</code>...", parse_mode="HTML"
    )

    verdict = await search_service.check_url(normalized_url)

    if verdict == "CAPTCHA_SERVICE_FAILED":
        await waiting_msg.edit_text(
            "❗️ **Проверка не удалась.**\n\n"
            "Сервис временно перегружен или недоступен. Пожалуйста, попробуйте позже.\n\n"
            "Ваш платеж **не был списан**."
        )
        return

    if not await user_service.has_active_subscription(user_id):
        await user_service.spend_credit(user_id)
    await user_service.update_user_url_check_time(user_id)

    await waiting_msg.edit_text(verdict, parse_mode="Markdown")


@router.callback_query(F.data.startswith("payload_"))
async def process_single_payment_cb(callback: CallbackQuery, bot: Bot):
    payload = callback.data
    await send_single_check_invoice(callback.from_user.id, bot, payload)
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message, state: FSMContext, user_service: UserService
):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload

    if payload == "subscription_payload":
        await user_service.grant_subscription(user_id)
        await message.answer("✅ Подписка успешно оформлена!")
        return

    if "single" in payload:
        await user_service.add_credit(user_id)
        await message.answer(
            "✅ Оплата прошла успешно!\n\n" "Теперь введите ваш запрос:"
        )
        if payload == "payload_entity_check:single":
            await state.set_state(Search.waiting_for_entity_name)
        elif payload == "payload_url_check:single":
            await state.set_state(Search.waiting_for_url)
