# -*- coding: utf-8 -*-
import csv
from decimal import Decimal, ROUND_HALF_UP
from json import load
from re import findall
from time import strftime, gmtime

mob_pattern = r'\b(Mob)|\b(Boss)'
exp_pattern = r'exp(\d+)'
time_pattern = r'tm(\d+)'
hatch_pattern = r'\b(Hatch)'
location_pattern = r'\b(Location)'


class DungeonExceptions(Exception):
    def __init__(self):
        self.summary = ''


class NotEnoughExperience(DungeonExceptions):
    def __init__(self):
        self.summary = 'У Вас недостаточно опыта, что выбраться из подземелья, нужно 280!'


class Character:
    def __init__(self, location=None, experience=0, date=Decimal("0.000000000000")):
        self.location = location
        self.previous_location = ''
        self.experience = Decimal(experience)
        self.date = date
        self.is_it_end = False
        self.start_new_game = False
        self.available_actions = []

    def __str__(self):
        return f'\nместонахождение: {self.location.name}\n' \
               f'опыт: {self.experience}\n' \
               f'времени в пути {strftime("%H часа, %M минуты,  %S секунд", gmtime(int(self.date)))}\n' \
               f'времени осталось: {strftime("%H часа, %M минуты, %S секунд", gmtime(int(remaining_time)))}\n'

    def get_stats(self):
        stats = [self.location.name, str(self.experience), strftime("%H:%M:%S", gmtime(int(self.date)))]

        return stats

    def fight(self, mob):
        global remaining_time
        self.experience += Decimal(mob.experience)
        print(f'\nВы победили {mob.name} \n ')
        self.time_in_journey(mob.time_to_spend)
        remaining_time = time_controller(remaining_time, mob.time_to_spend)

    def move_on(self, location):
        global remaining_time
        self.location = location
        self.time_in_journey(location.time_to_spend)
        remaining_time = time_controller(remaining_time, location.time_to_spend)

    def give_up(self):
        self.is_it_end = True
        print('\n Вы решили сдаться \n ')

    def time_in_journey(self, time):
        time = Decimal(time)
        self.date += time

    def get_actions_list(self):
        """
        формируем список тюплов из доступных действий
        :return: список тюполов (counter, Action_obj)
        """
        actions_list = []
        counter = 1
        for action in self.available_actions:
            action.init_action()
            action.number = counter
            actions_list.append((counter, action))

            counter += 1
        return actions_list

    def print_actions(self, action_list):
        """
        печатаем доступные действия в консоли
        :param action_list: список тюплов из доступных действий
        :return: None
        """
        print(f'{self}')
        print('доступные действия:')

        for action_tuple in action_list:
            print(f'{action_tuple[0]} - {action_tuple[1].summary} - {action_tuple[1].action_object_name}')
        self.previous_location = self.location

    def fight_case(self, action_tuple):
        """
        обработка сценария "Драка"
        :param action_tuple: тьюпл с нашим Action_obj
        :return: None
        """
        self.fight(action_tuple[1].action_object)
        self.available_actions.pop(action_tuple[1].number - 1)

    def move_case(self, action_tuple):
        """
        обработка сценария "перейти в локацию"
        :param action_tuple: тьюпл с нашим Action_obj
        :return: None
        """
        new_abs_path = self.location.absolute_path[action_tuple[1].index][
            action_tuple[1].action_object_name]
        self.move_on(
            location=Location(name=action_tuple[1].action_object_name, absolute_path=new_abs_path,
                              character=self))
        print(f'\n\nВы перешли в локацию: {self.location.name}')

    def get_case(self, action_list, user_action):
        for action_tuple in action_list:
            if user_action == action_tuple[0]:
                if action_tuple[1].action_type == 'move':
                    self.move_case(action_tuple)
                    break
                elif action_tuple[1].action_type == 'fight':
                    self.fight_case(action_tuple)
                    break
                elif action_tuple[1].action_type == 'give_up':
                    self.give_up()
                    break
                elif action_tuple[1].action_type == 'open_the_hatch':
                    try:
                        action_tuple[1].action_object.enough_exp(self)
                    except NotEnoughExperience as error:
                        print(f'\n{error.summary}\n')
                        break
                    else:
                        self.move_case(action_tuple)
                    break
                else:
                    print('что то не так')

    def actions(self):
        """
        главный метод класса - обработка ввод от пользователя
        :return:
        """

        # чтоб не писать отдельный метод на проверку времени осталось и время на прохождение локации, первой делаем
        # проверку времени, если персонаж войдет в Люк и окажется там с отрицательным значением времени, он проиграет
        global remaining_time
        if remaining_time <= 0:
            print('Время вышло\n')
            self.start_new_game = True
            remaining_time = restart_timer()
            print('\n\nПерезапускаем игру:\n\n')
            return

        if findall(hatch_pattern, self.location.name):
            self.is_it_end = True
            print('Вы выбрались!')
            return

        action_list = self.get_actions_list()
        self.print_actions(action_list)
        user_action = int(input("Введите номер действия: "))

        self.get_case(action_list, user_action)


class Mob:
    def __init__(self, name, mob_string):
        self.name = name
        self.experience = int((findall(exp_pattern, mob_string))[0])
        self.time_to_spend = (findall(time_pattern, mob_string))[0]

    def __str__(self):
        return f'имя {self.name}\n' \
               f'опыт {self.experience}\n' \
               f'время на победу {self.time_to_spend}'


class GiveUp:
    def __init__(self):
        self.name = ''


class Hatch:

    def __init__(self, name, absolute_path):
        self.name = name
        self.absolute_path = absolute_path

    @staticmethod
    def enough_exp(character):
        if character.experience < 280:
            raise NotEnoughExperience


class Action:
    def __init__(self, index, action_object):
        self.index = index
        self.number = 0
        self.action_type = None
        self.action_object = action_object
        self.action_object_name = action_object.name
        self.summary = ''

    def __str__(self):
        return f'номер - {self.index}\n' \
               f'тип действия - {self.action_type}\n' \
               f'объект - {self.action_object}\n' \
               f'описание - {self.summary}\n'

    def init_action(self):

        """
        дополняем экземпляр класса по шаблону
        :return:
        """

        if isinstance(self.action_object, Location):
            self.action_type = 'move'
            self.summary = 'Перейти в локацию'
        elif isinstance(self.action_object, Mob):
            self.action_type = 'fight'
            self.summary = 'Победить монстра'
        elif isinstance(self.action_object, GiveUp):
            self.action_type = 'give_up'
            self.summary = 'Сдаться'
        elif isinstance(self.action_object, Hatch):
            self.action_type = 'open_the_hatch'
            self.summary = 'Выбраться из подземелья'
        else:
            print('что то не так')


class Location:
    def __init__(self, name, ways_to_another_rooms=None, mobs='', absolute_path=None, character=None):
        self.name = name
        self.ways_to_another_rooms = ways_to_another_rooms
        self.mobs = mobs
        self.time_to_spend = None
        self.absolute_path = absolute_path
        self.available_actions = []
        self.character_in_location = character
        self.time_to_spend = (findall(time_pattern, name))[0]

    @staticmethod
    def get_location_name(path_to_location):
        for key in path_to_location:
            return key

    def check_mobs(self):
        """
        проверяем объект, моб ли это, моб является строкой
        апдейтим список мобов у экземпляра класса
        :return: None
        """

        self.mobs = []
        i = 0  # считаем индекс для посторения пути в карте
        for item in self.absolute_path:
            if isinstance(item, str):
                if findall(mob_pattern, item):
                    mob = Mob(name=item, mob_string=item)
                    self.mobs.append(mob)
                    self.available_actions.append(Action(i, mob))
            i += 1

    def check_locations(self):
        """
        проверяем, есть ли пути в другие комнаты, комната - dict объект
        если в списке есть словари инициализируем их как новые комнаты
        :return: None
        """
        self.ways_to_another_rooms = []
        i = 0  # считаем индекс для посторения пути в карте
        for item in self.absolute_path:
            if isinstance(item, dict):
                location = self.get_location_name(self.absolute_path[i])

                if findall(location_pattern, location):
                    new_room = Location(name=self.get_location_name(self.absolute_path[i]),
                                        absolute_path=self.absolute_path[i])

                    self.ways_to_another_rooms.append(new_room)
                    self.available_actions.append(Action(i, new_room))

                elif findall(hatch_pattern, location):
                    new_room = Hatch(name=self.get_location_name(self.absolute_path[i]),
                                     absolute_path=self.absolute_path[i])
                    self.ways_to_another_rooms.append(new_room)
                    self.available_actions.append(Action(i, new_room))
            i += 1

    def scan(self):
        """
        проверяем контент локации
        :return: все записываем в экземпляр класса
        """
        self.available_actions = []
        self.time_to_spend = (findall(time_pattern, self.name))[0]
        self.check_mobs()
        self.check_locations()

        give_up = GiveUp()
        self.available_actions.append(Action(len(self.available_actions), give_up))

        return self.available_actions


class Dungeon:
    def __init__(self):
        self.map = None

    def set_map_json(self, file_json):
        with open(file_json, 'r') as dungeon_map:
            self.map = load(dungeon_map)


remaining_time = '123456.0987654321'
# если изначально не писать число в виде строки - теряется точность!
field_names = ['current_location', 'current_experience', 'current_date']

remaining_time = Decimal(remaining_time)


def restart_timer():
    return Decimal('123456.0987654321')


def time_controller(time_left, time_delta):
    time_left = Decimal(time_left)
    time_delta = Decimal(time_delta)
    return (time_left - time_delta).quantize(Decimal("0.000000000000"), ROUND_HALF_UP)


def init_new_game():
    char = Character()
    dungeon = Dungeon()
    dungeon.set_map_json(file_json='rpg.json')
    char.location = Location(name='Location_0_tm0', absolute_path=dungeon.map['Location_0_tm0'], character=char)

    return char, dungeon


def print_docs():
    docs = f'Начата новая игра\n' \
           f'Выбирайте номер действия и нажимайте Enter\n' \
           f'Нужно успеть найти выход пока не выйдет время!\n'
    print(docs)


def write_stats(statistic):
    with open('dungeon.csv', 'a', newline='')as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(statistic)


def main():
    print_docs()
    char, dungeon = init_new_game()
    while char.is_it_end is False:
        with open('dungeon.csv', 'a', newline='')as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(char.get_stats())
            if char.start_new_game:
                char, dungeon = init_new_game()
            if char.location is not char.previous_location:
                char.available_actions = char.location.scan()
            char.actions()


if __name__ == '__main__':
    main()
