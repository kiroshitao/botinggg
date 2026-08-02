from aiogram.fsm.state import State, StatesGroup


class AddMentorStates(StatesGroup):
    name = State()
    photo = State()
    description = State()
    experience = State()
    specialization = State()
    price = State()
    tg_username = State()
    tg_user_id = State()
    category = State()


class EditMentorStates(StatesGroup):
    choose_field = State()
    enter_value = State()
    enter_photo = State()


class AddCategoryStates(StatesGroup):
    name = State()
    parent = State()


class EditCategoryStates(StatesGroup):
    name = State()
