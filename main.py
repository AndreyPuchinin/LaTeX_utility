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
        return self.replace_symbols(input_text)


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
