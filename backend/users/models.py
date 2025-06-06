from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from users.constants import LIMIT_EMAIL, LIMIT_USERNAME
from users.validators import username_validator


class User(AbstractUser):
    """Модель пользователей."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
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
        blank=True,
        upload_to='users/%Y/%m/%d/',
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
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Подписки'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                name='unique_user_following',
                fields=('user', 'following')
            ),
        )

    def __str__(self):
        return f'{self.user} подписан на {self.following}'

    def clean(self):
        if self.user == self.following:
            raise ValidationError('Нельзя подписаться на самого себя!')
