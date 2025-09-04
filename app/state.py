class UserStateManager:
    def __init__(self):
        self.states = {}

    def set(self, chat_id, state):
        self.states[chat_id] = state

    def get(self, chat_id):
        return self.states.get(chat_id)

    def clear(self, chat_id):
        self.states.pop(chat_id, None)
