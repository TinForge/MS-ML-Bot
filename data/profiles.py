
# Profiles for bot characteristics

class Profile():
    def __init__(self):
        self.min_range = None
        self.max_range = None
        self.min_height = None
        self.max_height = None
        # self.jump_attack = False


class WarriorShort(Profile):
    def __init__(self):
        self.min_range = 10
        self.max_range = 100
        self.min_height = -30
        self.max_height = 25


class WarriorLong(Profile):
    def __init__(self):
        self.min_range = 70
        self.max_range = 150
        self.min_height = -30
        self.max_height = 75