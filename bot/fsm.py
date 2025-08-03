from aiogram.fsm.state import State, StatesGroup


class Search(StatesGroup):
    waiting_for_entity_name = State()
    waiting_for_url = State()
