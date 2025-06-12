from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from users.constants import LIMIT_EMAIL, LIMIT_USERNAME
from users.validators import username_validator


class User(AbstractUser):
    """Модель пользователей."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')
    username = models.CharField(
        'Имя пользователя',
        max_length=LIMIT_USERNAME,
        unique=True,
        validators=(username_validator,),
        error_messages={
            'unique': 'Пользователь с таким именем уже существует!',
        },
    )
    email = models.EmailField(
        'Электронная почта',
        max_length=LIMIT_EMAIL,
        unique=True,
        error_messages={
            'unique': 'Пользователь с таким e-mail уже существует!',
        },
    )
    first_name = models.CharField(
        'Имя',
        max_length=LIMIT_USERNAME,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=LIMIT_USERNAME,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/%Y/%m/%d/',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Модель для подписок."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions_to_author',
        verbose_name='Подписки'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                name='unique_user_author',
                fields=('user', 'author')
            ),
        )

    def __str__(self):
        return f'{self.user} подписан на {self.author}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на самого себя!')
