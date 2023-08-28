import pymongo


class Training():
    def __init__(self, type, date, time, lasts, held, trainer, max_people=None, people_atm=None, city=None, address=None):
        self.type = type
        self.date = date
        self.time = time
        self.lasts = lasts
        self.held = held
        self.trainer = trainer
        self.max_people = max_people
        self.people_atm = people_atm
        self.city = city
        self.address = address        

    def save(self):
