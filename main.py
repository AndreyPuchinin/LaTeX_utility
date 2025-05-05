import json
from abc import ABC
import re
from pathlib import Path


class Logger(ABC):
    def __init__(self, logger_name: str):
        self.logger_name = logger_name
        self._notes = []
        self._errors = []
        self._warnings = []
        self._pos_msgs = []

    def errors(self) -> None:
        for one_err in self._errors:
            self._errors += [one_err]

    def warnings(self) -> None:
        for one_warning in self._warnings:
            self._warnings += [one_warning]

    def notes(self) -> None:
        for one_note in self._notes:
            self._notes += [one_note]

    def pos_msgs(self) -> None:
        for one_pos_msgs in self._pos_msgs:
            self._pos_msgs += [one_pos_msgs]

    def print_one(self, _msgs: list):
        if _msgs:
            for one_msg in _msgs:
                print(one_msg)

    def print_all(self) -> None:
        print(self.logger_name + ':')
        self.print_one(self._errors)
        self.print_one(self._warnings)
        self.print_one(self._notes)
        if not self._errors:
            self.print_one(self._pos_msgs)
        if not self._errors and \
                not self._warnings and \
                not self._notes:
            print('success!\n')

    def __del__(self):
        self.print_all()


class WordToLatexLogger(Logger):
    def replacements_not_found(self, path: str) -> None:
        self._errors += [f"Ошибка: файл словаря '{path}' не найден."]

    def invalid_replacements(self, path: str) -> None:
        self._errors += [f"Ошибка: файл '{path}' не является валидным JSON."]

    def empty_replacements(self, path: str) -> None:
        self._warnings += [f"Предупреждение: файл JSON {path} пуст."]

    def check_remaining_tildes(self, text):
        """Проверяет наличие непрочитанных символов тильды"""
        matches = re.finditer(chr(771), text)
        indices = [match.start() for match in matches]

        tilde_pos = text.find(chr(771))
        if tilde_pos != -1:
            self._warnings += [f"Обнаружен непрочитанный символ тильды в позициях: {indices}"]


class MainLogger(Logger):
    def no_inp_file(self, input_path: str) -> None:
        self._errors += [f"Ошибка: входной файл '{input_path}' не найден."]

    def success(self, output_path: str) -> None:
        self._pos_msgs += [f"Конвертация завершена. Результат сохранен в '{output_path}'"]


class WordToLatexConverter:
    def __init__(self, dictionary_path):
        self.logger = WordToLatexLogger('word_to_latex_logger')
        self.dictionary = self.load_dictionary(dictionary_path)
        self.no_space_after_chars = re.compile(r'[\d\\]')  # Цифры или обратный слеш для проверки после замены

    def validate_dictionary_structure(self, dictionary):
        """Проверяет, что словарь содержит только строковые ключи и значения."""
        if not isinstance(dictionary, dict):
            return False

        for key, value in dictionary.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return False

        return True

    def load_dictionary(self, path):
        """Загружает словарь замен из JSON-файла."""
        result = None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                # Проверяем, что словарь не пустой и содержит хотя бы одну замену
                result = json.load(f)
                if not self.validate_dictionary_structure(result):
                    self.logger.empty_replacements(path)
                    return {}
                else:
                    return result
        except FileNotFoundError:
            self.logger.replacements_not_found(path)
            return {}
        except json.JSONDecodeError:
            self.logger.invalid_replacements(path)
            return {}

    def find_matching_bracket(self, text, start_pos, open_bracket='(', close_bracket=')'):
        """
        Находит позицию закрывающей скобки того же уровня вложенности.
        Возвращает позицию закрывающей скобки или -1 если не найдено.
        """
        if start_pos >= len(text) or text[start_pos] != open_bracket:
            return -1

        level = 1
        pos = start_pos + 1

        while pos < len(text):
            if text[pos] == open_bracket:
                level += 1
            elif text[pos] == close_bracket:
                level -= 1
                if level == 0:
                    return pos
            pos += 1

        return -1  # Не найдена закрывающая скобка

    def process_special_brackets(self, text):
        """
        Обрабатывает специальные скобки: ^( -> ^{ }, _( -> _{ }
        """
        result = []
        i = 0
        n = len(text)

        while i < n:
            if i + 1 < n and text[i] in ('^', '_') and text[i + 1] == '(':
                # Нашли специальную скобку
                close_pos = self.find_matching_bracket(text, i + 1)
                if close_pos != -1:
                    # Заменяем скобки
                    result.append(f"{text[i]}{{{text[i + 2:close_pos]}}}")
                    i = close_pos + 1
                else:
                    # Нет закрывающей скобки - оставляем как есть
                    result.append(text[i])
                    i += 1
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def process_widetilde(self, text):
        """
        Обрабатывает "(text)<символ 771>" -> "\widetild{text}"
        Удаляет только те символы 771, которые участвуют в преобразовании
        """
        tilde_char = chr(771)  # Символ тильды-акцента
        result = []
        i = 0
        n = len(text)

        while i < n:
            if text[i] == '(':
                close_pos = self.find_matching_bracket(text, i)
                if close_pos != -1 and close_pos + 1 < n and text[close_pos + 2] == tilde_char:
                    # Нашли конструкцию (text)<тильда>
                    result.append(f"\\widetilde{{{text[i + 1:close_pos]}}}")
                    i = close_pos + 3  # Пропускаем и закрывающую скобку и тильду
                else:
                    result.append(text[i])
                    i += 1
            else:
                # Оставляем символ, если это не обрабатываемая тильда
                if text[i] != tilde_char or (i > 0 and text[i - 1] != ')'):
                    result.append(text[i])
                i += 1

        result = ''.join(result)

        if chr(771) in result:
            self.logger.check_remaining_tildes(result)

        return result

    def replace_symbols(self, text):
        """Заменяет символы в тексте согласно загруженному словарю."""
        if not self.dictionary:
            return text

        # Сначала выполняем все замены
        for unicode_char, latex_cmd in self.dictionary.items():
            text = text.replace(unicode_char, latex_cmd)

        # Затем добавляем пробелы где нужно
        result = []
        i = 0
        n = len(text)

        while i < n:
            # Проверяем, является ли текущая позиция началом какой-либо latex команды
            found = False
            for latex_cmd in self.dictionary.values():
                if text.startswith(latex_cmd, i):
                    # Добавляем команду в результат
                    result.append(latex_cmd)
                    i += len(latex_cmd)
                    found = True

                    # Проверяем следующий символ
                    if i < n and not text[i].isdigit() and text[i] != '\\':
                        result.append(' ')
                    break

            if not found:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def convert(self, input_text):
        """Основной метод конвертации.
           Будет пополняться."""
        input_text = self.replace_symbols(input_text)  # Сперва выполним замены, чтобы не \ -> \backslash
        input_text = self.process_widetilde(input_text)
        input_text = self.process_special_brackets(input_text)
        return input_text


def main():
    # Настройки путей
    dictionary_path = 'replacements.json'  # JSON-словарь замен
    input_path = 'input.txt'  # Входной текстовый файл
    output_path = 'output.tex'  # Выходной LaTeX-файл

    main_logger = MainLogger('main_logger')

    # Читаем входной файл
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            input_text = f.read()
    except FileNotFoundError:
        main_logger.no_inp_file(input_path)
        return

    # Конвертируем
    converter = WordToLatexConverter(dictionary_path)
    output_text = converter.convert(input_text)

    # Сохраняем результат
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)

    main_logger.success(output_path)


if __name__ == "__main__":
    main()
