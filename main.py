import re


def convert_unicode_to_latex(text):
    replacements = {
        "\\": "\\backslash ",
        'φ': '\\varphi ',
        '∂': '\\partial ',
        '∩': '\\cap ',
        'γ': '\\gamma ',
        "'": '\\prime '
    }

    for char, latex in replacements.items():
        text = text.replace(char, latex)

    return text


def process_brackets(text):
    # Обрабатываем сначала подстрочные, потом надстрочные индексы
    for prefix in ['_', '^']:
        pattern = re.compile(re.escape(prefix) + r'\(')
        matches = list(pattern.finditer(text))

        # Обрабатываем с конца, чтобы не сбивались позиции при заменах
        for match in reversed(matches):
            start_pos = match.end() - 1  # позиция открывающей скобки
            depth = 1
            end_pos = None

            # Ищем соответствующую закрывающую скобку
            for i in range(start_pos + 1, len(text)):
                if text[i] == '(':
                    depth += 1
                elif text[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end_pos = i
                        break

            if end_pos is not None:
                # Заменяем скобки
                text = text[:start_pos] + '{' + text[start_pos + 1:end_pos] + '}' + text[end_pos + 1:]

    return text


def word_to_latex(text):
    text = convert_unicode_to_latex(text)
    text = process_brackets(text)
    return text


# "Пусть i(D_1^((1)) )=2,φ(∂D_1^((1))∩γ)=ww и пусть i(D_2^((1)) )=3, φ(∂D_2^((1))∩γ)=ww."
# Пример использования
if __name__ == '__main__':
    while True:
        word_text = input("Enter text copied from word\n\n")
        latex_text = word_to_latex(word_text)
        print('\n'+latex_text, '\n')
