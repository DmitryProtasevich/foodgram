import re

from django.core.exceptions import ValidationError


def username_validator(value):
    """
    Валидатор для имени пользователя.
    """
    unmatched = re.sub(r'[\w.@+-]', '', value)

    if value.lower() == 'me':
        raise ValidationError('Имя пользователя "me" использовать нельзя!')
    elif unmatched:
        raise ValidationError(
            f'Имя пользователя содержит недопустимые символы: '
            f'{", ".join(set(unmatched))}'
        )
    return value
