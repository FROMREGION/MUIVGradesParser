from re import search
from custom_tag import CustomTag
from exceptions import FailedAuth
from requests import post, get
from urllib3 import disable_warnings
from bs4 import BeautifulSoup, Tag
from os.path import exists


class GradeParser:
    def __init__(self, login, password):
        disable_warnings()
        self.__dis_list_names = ("current", "arrears")
        self.login: str = login
        self.password: str = password
        self.url: str = "https://e.muiv.ru/login/index.php"
        self.DEBUG: int = 1 if exists("cabinet.html") else 0

    # Get all html data
    def html(self) -> str:
        """
        Return RAW html
        """
        form = get(self.url, verify=False)
        token = search(r'logintoken" value="\S+"', form.text).group().split('"')[2]
        login_information = {'username': self.login,
                             'password': self.password,
                             'rememberusername': 1,
                             'anchor': None,
                             'logintoken': token}
        return post(self.url, data=login_information, cookies=form.cookies, verify=False).text

    def soup(self) -> BeautifulSoup:
        if self.DEBUG:
            with open('cabinet.html', 'r', encoding="UTF-8") as file:
                debug_file_data = file.read()
            return BeautifulSoup(debug_file_data, 'lxml', element_classes={Tag: CustomTag})

        return BeautifulSoup(self.html(), 'lxml', element_classes={Tag: CustomTag})

    def student_name(self) -> str:
        """
        Returns the student name
        """
        try:
            return self.soup().find("span", class_="usertext").text.rstrip('0123456789')\
                .removesuffix('Неудачных попыток авторизации после Вашего последнего входа: ')
        except AttributeError:
            raise FailedAuth("Invalid username or password, please try again.")

    def dis_lists(self) -> list:
        """
        Returns a list 0: Current courses 1: Arrears courses
        """
        try:
            return self.soup().find_all('div', class_='dis_list')
        except AttributeError:
            raise FailedAuth("Invalid username or password, please try again.")

    def json(self) -> dict:
        """
        Returns a Python-like dictionary object
        """

        data = {'user': {}}

        data['user']['surname'], data['user']['name'], data['user']['patronymic'], *_ = self.student_name().split()
        for dis_list_name, dis_list in zip(self.__dis_list_names, self.dis_lists()):
            data[f'{dis_list_name}_courses'] = {}
            data[f'{dis_list_name}_progress'] = {"course_count": 0,
                                                 "course_done": 0,
                                                 "course_remained": 0,
                                                 "test_count": 0,
                                                 "test_done": 0,
                                                 "test_remained": 0,
                                                 "test_percentage_done": 0}
            for dis_block in dis_list:
                data[f'{dis_list_name}_courses'][dis_block.course_name] = {"type": dis_block.type,
                                                                           "teacher": dis_block.teacher,
                                                                           "middle": dis_block.middle,
                                                                           "until_complete": dis_block.until_complete,
                                                                           "tests": dis_block.tests,
                                                                           }
                data[f'{dis_list_name}_progress']['course_count'] += 1
                data[f'{dis_list_name}_progress']['course_done'] += 1 if dis_block.until_complete is None else 0

                data[f'{dis_list_name}_progress']['test_count'] += len(dis_block.tests)
                data[f'{dis_list_name}_progress']['test_done'] += len(tuple(filter(lambda v: v != 0,
                                                                                   map(lambda td: td['grade'],
                                                                                       dis_block.tests.values()))))

            data[f'{dis_list_name}_progress']['course_remained'] = data[f'{dis_list_name}_progress']['course_count'] - \
                data[f'{dis_list_name}_progress']['course_done']
            data[f'{dis_list_name}_progress']['test_remained'] = data[f'{dis_list_name}_progress']['test_count'] - \
                data[f'{dis_list_name}_progress']['test_done']
            data[f'{dis_list_name}_progress']['test_percentage_done'] = \
                int(data[f'{dis_list_name}_progress']['test_done'] /
                    data[f'{dis_list_name}_progress']['test_count'] * 100)
        return data

    def prettify_print(self) -> str:
        """
        Function for easy viewing when running locally in the console
        """
        data = self.json()
        current_course = data.get("current_courses")
        arrears = data.get("arrears")
        message = f'| ФИО: {data["user"]["surname"]} {data["user"]["name"]} {data["user"]["patronymic"]}\n'
        if current_course:
            message += f'|-- Активные предметы:\n'
            for course in current_course:
                course_obj = current_course[course]
                message += f'|  |- {course} | {course_obj["type"]}\n'
                for test in course_obj["tests"]:
                    test_obj = course_obj["tests"][test]
                    message += f'|  |  |-- {test} - {test_obj["grade"]} ' \
                               f'[{test_obj["availability"]} | Осталось попыток: {test_obj["attempts"]}]\n'

                message += f'|  |  |- Средний балл: {course_obj["middle"]}\n'
                message += f'|  |  |- Преподаватель: {course_obj["teacher"]}\n'
                message += "| \n"
        if arrears:
            message += f'|- Активные предметы:\n'
            for course in arrears:
                course_obj = arrears[course]
                message += f'|  |- {course} | {course_obj["type"]}\n'
                for test in course_obj["tests"]:
                    test_obj = course_obj["tests"][test]
                    message += f'|  |  |- {test} - {test_obj["grade"]} [{test_obj["availability"]} | ' \
                               f'Осталось попыток: {test_obj["attempts"]}]\n'

                message += f'|  |  |- Средний балл: {course_obj["middle"]}\n'
                message += f'|  |  |- Преподаватель: {course_obj["teacher"]}\n'

        message += '|- Прогресс: \n'
        message += '|  |- по дисциплинам:\n'
        message += f'|  |  |- Кол-во дисциплин: {data["current_progress"]["course_count"]}\n'
        message += f'|  |  |- Кол-во решенных дисциплин: {data["current_progress"]["course_done"]}\n'
        message += f'|  |  |- Кол-во оставшихся дисциплин: {data["current_progress"]["course_remained"]}\n'

        message += '|  |- по тестам:\n'
        message += f'|  |  |- Кол-во тестов: {data["current_progress"]["test_count"]}\n'
        message += f'|  |  |- Кол-во решенных тестов: {data["current_progress"]["test_done"]}\n'
        message += f'|  |  |- Кол-во оставшихся тестов: {data["current_progress"]["test_remained"]}\n'

        message += f'|- Процент выполнения: {data["current_progress"]["test_percentage_done"]}%'

        return message


if __name__ == "__main__":
    # From local usage import
    from __init__ import LOGIN, PASSWORD
    # ==================================================================================================================

    user = GradeParser(login=LOGIN, password=PASSWORD)
    print(user.prettify_print())
