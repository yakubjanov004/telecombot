from aiogram.fsm.state import State, StatesGroup


class AuthState(StatesGroup):
    waiting_lang = State()


class OperatorAuthState(StatesGroup):
    waiting_operator_password = State()
    waiting_navi_username = State()
    waiting_operator_type = State()
    waiting_branch = State()


class ManagerAuthState(StatesGroup):
    waiting_manager_password = State()
