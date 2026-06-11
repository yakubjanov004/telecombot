from aiogram.fsm.state import State, StatesGroup

class OperatorInternetState(StatesGroup):
    choosing_branch = State()
    entering_department = State()
    entering_msisdn = State()
    choosing_rate_plan = State()

class OperatorMobileState(StatesGroup):
    choosing_dealer = State()
    choosing_branch = State()
    entering_msisdn = State()
    choosing_rate_plan = State()
    confirm = State()

class ManagerStatsState(StatesGroup):
    choosing_period = State()

class ManagerExportState(StatesGroup):
    choosing_period = State()

class ManagerCompareState(StatesGroup):
    choosing_first_period = State()
    choosing_second_period = State()
