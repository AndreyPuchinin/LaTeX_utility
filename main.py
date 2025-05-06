import json
from abc import ABC
import re
from pprint import pprint
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
                if close_pos != -1 and close_pos + 2 < len(text) and \
                        close_pos + 1 < n and text[close_pos + 2] == tilde_char:
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

    def segment_text(self, text):
        """Разбивает текст на сегменты русских и не-русских символов.
           Скобки () считаются русскими символами.
           Возвращает список кортежей (тип, текст), где тип:
           'ru' - русский текст или скобки
           'non_ru' - не-русский текст (формула)"""
        segments = []
        i = 0
        n = len(text)
        russian_re = re.compile(r'[а-яА-ЯёЁ()\s]')  # Скобки считаются русскими

        while i < n:
            current_char = text[i]

            # Определяем тип текущего символа
            if russian_re.match(current_char):
                # Русский сегмент (включая скобки)
                segment = []
                # Пока русские символы
                while i < n and russian_re.match(text[i]):
                    segment.append(text[i])
                    i += 1
                # Русские символы кончились (или конец строки)
                segments.append(('ru', ''.join(segment)))
            else:
                # Не-русский сегмент (формула)
                segment = []
                # Пока формула
                while i < n and (not russian_re.match(text[i]) or text[i].isspace()):
                    segment.append(text[i])
                    i += 1
                # Формула кончилась (или конец строки)
                if segment:  # Игнорируем пробелы между сегментами
                    segments.append(('non_ru', ''.join(segment)))

        return segments

    def process_russian_in_brackets(self, segments, start_index):
        """Обрабатывает русский текст внутри фигурных скобок {}
        Возвращает кортеж (новые_сегменты, новый_индекс)"""
        i = start_index
        n = len(segments)
        new_segments = segments.copy()

        # Ищем открывающую {
        if i >= n or new_segments[i][0] != 'non_ru' or '{' not in new_segments[i][1]:
            return new_segments, i

        # Разделяем текст до { и после
        before, bracket_part = new_segments[i][1].rsplit('{', 1)
        if before:
            new_segments[i] = ('non_ru', before)
            i += 1
            new_segments.insert(i, ('non_ru', '{'))

        i += 1  # Переходим к содержимому скобок

        # Собираем все содержимое внутри {}
        collected = []
        bracket_level = 1  # Учитываем вложенность

        while i < n and bracket_level > 0:
            seg_type, seg_text = new_segments[i]

            # Обрабатываем каждый символ для учета вложенных скобок
            processed_text = []
            for char in seg_text:
                if char == '{':
                    bracket_level += 1
                elif char == '}':
                    bracket_level -= 1
                    if bracket_level == 0:
                        break  # Нашли закрывающую скобку
                processed_text.append(char)

            remaining_text = seg_text[len(processed_text):]

            # Добавляем обработанную часть
            if processed_text:
                collected.append((seg_type, ''.join(processed_text)))

            if bracket_level == 0:
                # Нашли закрывающую }
                if remaining_text.startswith('}'):
                    new_segments[i] = (seg_type, remaining_text[1:])
                break

            i += 1

        # Обрабатываем собранные сегменты
        processed_parts = []
        for seg_type, seg_text in collected:
            if seg_type == 'ru':
                processed_parts.append(f'\\text{{{seg_text.strip()}}}')
            else:
                processed_parts.append(seg_text)

        # Собираем результат
        result_segments = []
        if before:
            result_segments.append(('non_ru', before))
        result_segments.append(('non_ru', '{'))
        result_segments.append(('non_ru', ''.join(processed_parts)))

        # Заменяем обработанные сегменты
        end_index = i + 1 if i < n else i
        new_segments[start_index:end_index] = result_segments

        return new_segments, start_index + len(result_segments)

    def process_segments(self, segments):
        """Обрабатывает сегменты согласно правилам для формул"""
        processed_segments = segments.copy()
        i = 0

        while i < len(processed_segments) and i != -1:
            current_type, current_text = processed_segments[i]

            current_text = current_text

            # Правило 1: русский сегмент перед ^ или _ в английском
            if (current_type == 'ru' and i + 1 < len(processed_segments) and
                    segments[i + 1][0] == 'non_ru' and
                    segments[i + 1][1][0] in ('^', '_')):

                # Оборачиваем русский текст в \text{}
                processed_segments[i] = ('non_ru', f'\\text{{{current_text.strip()}}}')

                # Оставляем ^ или _ как есть
                processed_segments[i + 1] = ('non_ru', segments[i + 1][1])
                i += 1
            # Правило 2: английский сегмент с ^ или _ перед русским
            elif (current_type == 'non_ru' and i + 1 < len(processed_segments) and
                  segments[i + 1][0] == 'ru' and
                  current_text[-1] in ('^', '_')):

                # Добавляем английскую часть с ^ или _
                processed_segments[i] = ('non_ru', current_text)

                # Оборачиваем русский текст в \text{}
                processed_segments[i + 1] = ('non_ru', f'\\text{{{segments[i + 1][1].strip()}}}')
                i += 1

            # Правило 3: русский сегмент внутри {} в английских сегментах
            elif current_type == 'non_ru' and '{' in current_text and \
                    not '^{' in current_text and \
                    not '_{' in current_text and \
                    not '\\text{' in current_text:
                processed_segments, i = self.process_russian_in_brackets(processed_segments, i)

            else:
                # Без изменений
                processed_segments[i] = (current_type, current_text)
                i += 1

        return processed_segments

    def replace_power_brackets(self, text):
        """Заменяет ^(...) на ^{...} и _(...) на _{...} с учетом уровней вложенности"""
        result = []
        i = 0
        n = len(text)

        while i < n:
            if i + 1 < n and text[i] in ('^', '_') and text[i + 1] == '(':
                # Нашли ^( или _(
                operator = text[i]
                result.append(operator + '{')  # Заменяем ( на {
                i += 2

                # Ищем соответствующую закрывающую скобку
                close_pos = self.find_matching_bracket(text, i - 1)  # i-1 потому что скобка на предыдущей позиции
                if close_pos != -1:
                    # Добавляем содержимое
                    result.append(text[i:close_pos])
                    result.append('}')  # Заменяем ) на }
                    i = close_pos + 1
                else:
                    # Закрывающая скобка не найдена - оставляем как есть
                    result.append(text[i - 1:i + 1])
                    i += 1
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def build_text_from_segments(self, segments):
        """Собирает итоговый текст из обработанных сегментов"""
        return ''.join(segment_text for _, segment_text in segments)

    def escape_special_chars(self, text):
        """Заменяет специальные символы с учетом контекста"""
        result = []
        i = 0
        n = len(text)

        while i < n:
            # Обрабатываем обратный слеш
            if text[i] == '\\':
                # Проверяем, не экранирован ли уже этот слеш
                if i > 0 and text[i - 1] == '\\':
                    result.append('\\backslash')
                    i += 1
                else:
                    result.append('\\backslash')
                    i += 1
            # Обрабатываем $
            elif text[i] == '$':
                result.append('\\$')
                i += 1
            # Обрабатываем ^ и _ с учетом контекста
            elif text[i] in ('^', '_'):
                # Проверяем предыдущий символ
                if i + 1 < n and text[i + 1] not in ('(', '{'):
                    if text[i] == '^':
                        result.append('\\textasciicircum ')
                    else:
                        result.append('\\_')
                else:
                    result.append(text[i])
                i += 1
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def replace_symbols(self, text):
        """Заменяет символы в тексте согласно загруженному словарю."""
        if not self.dictionary:
            return text

        # Сначала выполняем все замены
        for unicode_char, latex_cmd in self.dictionary.items():
            text = text.replace(unicode_char, latex_cmd)

        # Затем обрабатываем специальные команды для пробелов
        special_commands = {
            '\\backslash': '\\backslash',
            '\\_': '\\_',
            '\\textasciicircum': '\\textasciicircum'
        }

        # Затем добавляем пробелы где нужно
        result = []
        i = 0
        n = len(text)

        while i < n:
            # Проверяем специальные команды
            cmd_found = False
            for cmd in special_commands.values():
                if text.startswith(cmd, i):
                    result.append(cmd)
                    i += len(cmd)
                    cmd_found = True

                    # Добавляем пробел если нужно
                    if i < n and not text[i].isdigit() and text[i] != '\\':
                        result.append(' ')
                    break

            if cmd_found:
                continue

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

    def wrap_formulas(self, text):
        """Автоматически обрамляет формулы в $...$ с учетом скобок"""
        result = []
        i = 0
        n = len(text)
        russian_re = re.compile(r'[а-яА-ЯёЁ()\-,.?!:;]')

        while i < n:
            # 1. Ищем начало формулы (первый нерусский символ)
            if i == 0 and not russian_re.match(text[i]) and text[i] not in ('$', ' ') or \
                    i > 0 and russian_re.match(text[i - 1]) and not russian_re.match(text[i]) and text[i] not in (
                    '$', ' '):
                result.append('$')
                formula_start = len(result)

                # 2. Собираем формулу до русского символа
                while i < n:
                    # 3. Пропускаем содержимое скобок
                    if text[i] in ('{', '('):
                        bracket_type = text[i]
                        close_pos = self.find_matching_bracket(text, i, "{", "}")
                        if close_pos == -1:
                            close_pos = n - 1

                        # Добавляем всё содержимое скобок
                        result.append(text[i:close_pos + 1])
                        i = close_pos + 1
                        continue

                    # 4. Проверяем на русский символ (конец формулы)
                    if russian_re.match(text[i]):
                        result.append('$')
                        break

                    result.append(text[i])
                    i += 1

                # Если дошли до конца без русского символа
                if i >= n and len(result) > formula_start:
                    result.append('$')
            else:
                result.append(text[i])
                i += 1

        return ''.join(result)

    def convert(self, input_text):
        """Основной метод конвертации.
           Будет пополняться."""

        # 0. Экранируем специальные символы в самом начале
        input_text = self.escape_special_chars(input_text)

        # 1. Обработка widetilde
        input_text = self.process_widetilde(input_text)

        # 2. Обработка специальных скобок
        input_text = self.process_special_brackets(input_text)

        # 3. Обработка ^() и _() -> ^{} и _{} соответственно
        input_text = self.replace_power_brackets(input_text)

        # 4. Добавляем автообрамление $...$ с учетом всех особенностей
        # (перепрыгивает через () и {})
        input_text = self.wrap_formulas(input_text)

        # 5. Разбиение на сегменты и их обработка
        segments = self.segment_text(input_text)
        processed_segments = self.process_segments(segments)

        # 6. Сборка итогового текста
        output_text = self.build_text_from_segments(processed_segments)

        # 7. Замена символов по словарю
        output_text = self.replace_symbols(output_text)

        return output_text


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
