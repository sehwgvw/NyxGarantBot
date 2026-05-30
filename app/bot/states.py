from aiogram.fsm.state import State, StatesGroup


class CreateDeal(StatesGroup):
    amount = State()
    subject = State()
    method = State()
    side = State()
    guarantor = State()
    confirm = State()


class ReviewState(StatesGroup):
    text = State()


class SupportState(StatesGroup):
    text = State()


class AdminSettingState(StatesGroup):
    key = State()
    value = State()
