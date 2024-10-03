from aiogram.fsm.state import State, StatesGroup

class AddChannel(StatesGroup):
    link = State()

class Refactoring(StatesGroup):
    original_post = State()
    array_of_refactors = State()
    original_message_id = State()
    generic_msg_id = State()
    current_index = State()

class ThirdPartyPost(StatesGroup):
    post_text = State()
    msg_id = State()

class AddPostChannel(StatesGroup):
    link = State()