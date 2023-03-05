from bs4 import Tag
from re import findall, search


class CustomTag(Tag):
    """
    Methods write down may be called only for html tag with class 'dis_block'!!!
    """

    @property
    def _raw_tests(self) -> list:
        return self.find_all('div', class_='mod_quiz')

    @property
    def _raw_tests_without_finally(self) -> list:
        return list(filter(lambda tst: "Итоговое тестирование" not in tst.text, self._raw_tests))

    @property
    def course_name(self) -> str:
        data = self.find('span', class_='dis_name').text
        if data is None:
            return 'Unknown course name'
        else:
            return data

    @property
    def teacher_name(self) -> str:
        data = self.find('span', class_='teachers').text
        if data is None:
            return 'Unknown teacher'
        else:
            return data

    @property
    def type(self) -> str:
        data = self.find('span', class_='reports').text
        if data is None:
            return 'Unknown type'
        else:
            return data

    @property
    def tests(self) -> dict:
        data = {}
        for test in self._raw_tests:
            test_sliced_data = (findall(r"(Тест \d|Итоговое тестирование|"
                                        r"доступно до \d{2}.\d{2}.\d{4}|"
                                        r"доступно c \d{2}.\d{2}.\d{4} по \d{2}.\d{2}.\d{4}|"
                                        r"не выполнено|"
                                        r"доступ закрыт \d{2}.\d{2}.\d{4}|"
                                        r"\d{1,3})", test.text))
            grade = 0
            attempts = 2
            if len(test_sliced_data) == 3:
                test_name, availability, *_ = test_sliced_data
            elif len(test_sliced_data) == 4:
                test_sliced_data[-1] = int(test_sliced_data[-1])
                test_sliced_data[-2] = int(test_sliced_data[-2])
                test_name, availability, attempts, grade = test_sliced_data
            else:
                test_name, availability, attempts, grade = "Invalid test name", "Invalid availability", \
                                                           len(test_sliced_data), len(test_sliced_data)
            data[test_name] = {"availability": availability, "attempts": attempts, "grade": grade}
        if data is None:
            return {'Unknown tests': 'Unknown tests data'}
        else:
            return data

    @property
    def _grades_sum(self) -> int:
        points = 0
        for test in self._raw_tests_without_finally:
            match = search(r"((?!Оценка: )\d{1,3})$", test.text)
            points += int(match.group()) if match is not None else 0
        return points

    @property
    def middle(self) -> int:
        return self._grades_sum / len(self._raw_tests) if len(self._raw_tests) else 0

    @property
    def until_complete(self) -> int:
        target_points = 75 if self.type == "Зачет" else 85
        until_complete = (target_points * len(self._raw_tests_without_finally)) - self._grades_sum
        return until_complete if len(self._raw_tests) and self.middle < target_points else None
