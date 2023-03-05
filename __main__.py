from re import search
from custom_tag import CustomTag
from exceptions import FailedAuth
from requests import post, get
from urllib3 import disable_warnings
from bs4 import BeautifulSoup, Tag


class GradeParser:
    def __init__(self, login, password):
        disable_warnings()
        self.__dis_list_names = ("current", "arrears")
        self.login: str = login
        self.password: str = password
        self.url = "https://e.muiv.ru/login/index.php"

    # Get all html data
    def html(self) -> str:
        form = get(self.url, verify=False)
        token = search(r'logintoken" value="\S+"', form.text).group().split('"')[2]
        login_information = {'username': self.login,
                             'password': self.password,
                             'rememberusername': 1,
                             'anchor': None,
                             'logintoken': token}
        return post(self.url, data=login_information, cookies=form.cookies, verify=False).text

    def soup(self):
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

    def dis_lists(self):
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

        # Stage 1
        data['user']['surname'], data['user']['name'], data['user']['patronymic'], *_ = self.student_name().split()

        # Stage 2

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
                                                                           **dis_block.tests}
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


if __name__ == "__main__":
    # From local usage import
    from __init__ import LOGIN, PASSWORD
    # ==================================================================================================================

    user = GradeParser(login=LOGIN, password=PASSWORD)
    print(user.json())
