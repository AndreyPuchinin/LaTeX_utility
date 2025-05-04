import re

# Словарь замен Unicode -> LaTeX
replacements = {
    '\\': '\\backslash',
    'φ': '\\varphi',
    '∂': '\\partial',
    '∩': '\\cap',
    'γ': '\\gamma',
    "'": '\\prime'
}

# Регулярные выражения
russian_chars = re.compile(r'[а-яА-ЯёЁ, -]')
formula_delimiters = re.compile(r'(\$[^$]+\$)')
hyphen_before_russian = re.compile(r'\$([^$]+)\$(\s*)-(\s*)([а-яА-ЯёЁ])')


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


def auto_dollar_formulas(text):
    result = []
    i = 0
    n = len(text)

    while i < n:
        if russian_chars.match(text[i]):
            # Русский символ - добавляем как есть
            result.append(text[i])
            i += 1
        else:
            # Нашли начало формулы
            formula_start = i
            while i < n and not russian_chars.match(text[i]):
                i += 1
            formula = text[formula_start:i]

            # Обрабатываем формулу
            formula = convert_unicode_to_latex(formula)
            formula = process_brackets(formula)

            # Добавляем в результат с $
            result.append(f'${formula}$')

    # Собираем результат в строку
    text = ''.join(result)

    # Обрабатываем случай с дефисом после формулы
    text = hyphen_before_russian.sub(r'$\1$-\4', text)

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
        formula = convert_unicode_to_latex(formula)
        formula = process_brackets(formula)
        parts.append(f'${formula}$')

        last_end = match.end()

    # Добавляем оставшийся текст
    parts.append(auto_dollar_formulas(text[last_end:]))

    return ''.join(parts)


# Пример использования
examples = [
    "Рассмотрим D_0 - случай",
    "Пусть i(D_1^((1)) )=2,φ(∂D_1^((1))∩γ)=ww",
    "Функция f(x) - непрерывная",
    "Множество A_1 ∪ B_2 - замкнуто, относительно себя"
]

for example in examples:
    print(f"До: {example}")
    print(f"После: {word_to_latex(example)}\n")