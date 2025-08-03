from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ПОГНАЛИ", callback_data="go_to_check")]
    ]
)

search_type_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🏢 Поиск по юр. лицу / ИП", callback_data="search_entity"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌐 Проверить URL/домен", callback_data="search_url"
            )
        ],
    ]
)

profile_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⭐ Купить/Продлить подписку (1900 RUB)",
                callback_data="buy_subscription",
            )
        ]
    ]
)


def get_payment_kb(payload_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Разовая проверка (200 RUB)",
                    callback_data=f"{payload_prefix}:single",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Оформить подписку (1900 RUB)",
                    callback_data="buy_subscription",
                )
            ],
        ]
    )


def get_pagination_kb(
    current_page: int, total_pages: int
) -> InlineKeyboardMarkup | None:
    if total_pages <= 1:
        return None

    buttons = []

    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"paginate:{current_page - 1}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page} / {total_pages}", callback_data="noop"
        )
    )

    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="Вперёд ▶️", callback_data=f"paginate:{current_page + 1}"
            )
        )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])
