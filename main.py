import re

# Словарь замен Unicode -> LaTeX
replacements = {
    '\\': '\\backslash ',
    'φ': '\\varphi ',
    '∂': '\\partial ',
    '∩': '\\cap ',
    'γ': '\\gamma ',
    "'": '\\prime ',
    '∪': '\\cup ',
    '∈': '\\in ',
    '⊂': '\\subset '
}

# Регулярные выражения
russian_chars = re.compile(r'[а-яА-ЯёЁ]')
russian_with_spaces = re.compile(r'[а-яА-ЯёЁ,\s]')  # Добавлена запятая
formula_delimiters = re.compile(r'(\$[^$]+\$)')
hyphen_after_formula = re.compile(r'\$([^-]+)-\s*\$(\s*)([а-яА-ЯёЁ])')


def convert_unicode_to_latex(text):
    for char, latex in replacements.items():
        text = text.replace(char, latex)
    return text


def process_brackets(text):
    for prefix in ['_', '^']:
        pattern = re.compile(re.escape(prefix) + r'\(')
        matches = list(pattern.finditer(text))

        for match in reversed(matches):
            start_pos = match.end() - 1
            depth = 1
            end_pos = None

            for i in range(start_pos + 1, len(text)):
                if text[i] == '(':
                    depth += 1
                elif text[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end_pos = i
                        break

            if end_pos is not None:
                text = text[:start_pos] + '{' + text[start_pos + 1:end_pos] + '}' + text[end_pos + 1:]

    return text


def process_hyphen_after_formula(text):
    # Обрабатываем случай с дефисом после формулы
    def replacer(match):
        formula = match.group(1).strip()
        spaces = match.group(2)
        next_char = match.group(3)
        return f'${formula}$-{next_char}'

    text = hyphen_after_formula.sub(replacer, text)
    return text


def auto_dollar_formulas(text):
    result = []
    i = 0
    n = len(text)

    while i < n:
        if russian_with_spaces.match(text[i]):
            # Русский символ или пробел/запятая - добавляем как есть
            result.append(text[i])
            i += 1
        else:
            # Нашли начало формулы
            formula_start = i

            # Собираем всю формулу до следующего русского символа
            while i < n and not russian_chars.match(text[i]):
                i += 1

            formula = text[formula_start:i]

            # Проверяем, заканчивается ли формула на "-"
            if formula.rstrip().endswith('-'):
                # Разделяем формулу и дефис
                formula_part = formula[:formula.rfind('-')].rstrip()
                hyphen_part = '-'

                # Обрабатываем основную часть формулы
                if formula_part:
                    formula_part = convert_unicode_to_latex(formula_part)
                    formula_part = process_brackets(formula_part)
                    # Добавляем пробел перед формулой, если нужно
                    if result and result[-1].strip() and not result[-1].isspace():
                        result.append(' ')
                    result.append(f'${formula_part}$')

                # Добавляем дефис
                result.append(hyphen_part)
            else:
                # Обычная формула без дефиса в конце
                if formula.strip():
                    formula = convert_unicode_to_latex(formula)
                    formula = process_brackets(formula)
                    # Добавляем пробел перед формулой, если нужно
                    if result and result[-1].strip() and not result[-1].isspace():
                        result.append(' ')
                    result.append(f'${formula.strip()}$ ')

    # Собираем результат в строку
    text = ''.join(result)

    # Дополнительная обработка дефисов после формул
    text = process_hyphen_after_formula(text)

    return text


def word_to_latex(text):
    # Сначала обрабатываем формулы в долларах, если они есть
    parts = []
    last_end = 0
    for match in formula_delimiters.finditer(text):
        # Текст до формулы
        before = text[last_end:match.start()]
        parts.append(auto_dollar_formulas(before))

        # Сама формула (уже в долларах)
        formula = match.group(1)[1:-1]  # убираем $

        # Обрабатываем случай с дефисом в конце формулы
        if formula.rstrip().endswith('-'):
            formula_part = formula[:formula.rfind('-')].rstrip()
            if formula_part:
                formula_part = convert_unicode_to_latex(formula_part)
                formula_part = process_brackets(formula_part)
                parts.append(f'${formula_part}$')
            parts.append('-')
        else:
            formula = convert_unicode_to_latex(formula)
            formula = process_brackets(formula)
            parts.append(f'${formula}$')

        last_end = match.end()

    # Добавляем оставшийся текст
    remaining_text = auto_dollar_formulas(text[last_end:])
    if remaining_text:
        parts.append(remaining_text)

    return ''.join(parts)


# Пример использования
examples = [
    "Рассмотрим D_0 - случай",
    "Пусть i(D_1^((1)) )=2,φ(∂D_1^((1))∩γ)=ww",
    "Функция f(x) - непрерывная",
    "Множество A_1 ∪ B_2 - замкнуто, относительно себя",
    "Элемент x∈X называется предельной точкой",
    "Множество A⊂B называется подмножеством",
    "Теорема 1 - важный результат"
]

for example in examples:
    print(f"До: {example}")
    print(f"После: {word_to_latex(example)}\n")