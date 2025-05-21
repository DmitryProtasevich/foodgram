from django.contrib.auth.models import AbstractUser
from django.db import models

from recipes.models import Recipe
from users.constants import LIMIT_EMAIL, LIMIT_USERNAME
from users.validators import username_validator


class User(AbstractUser):
    """Модель пользователей."""
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    USER = 'user'
    ROLE_CHOICES = (
        (USER, 'Пользователь'),
        (MODERATOR, 'Модератор'),
        (ADMIN, 'Администратор'),
    )
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
    role = models.CharField(
        'Роль',
        max_length=max(len(role) for role, _ in ROLE_CHOICES),
        choices=ROLE_CHOICES,
        default=USER,
    )
    first_name = models.CharField(
        'Имя',
        max_length=LIMIT_USERNAME,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=LIMIT_USERNAME,
    )
    is_subscribed = models.BooleanField(
        'Подписка',
        default=False
    )
    favorites = models.ManyToManyField(
        Recipe,
        verbose_name='Избранное',
        through='recipes.Favorite',
        related_name='favorited_by',
        blank=True
    )
    shopping_list = models.ManyToManyField(
        Recipe,
        verbose_name='Список покупок',
        through='recipes.ShoppingCart',
        related_name='shopping_list_users',
        blank=True
    )
    avatar = models.ImageField(
        'Аватар',
        blank=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    @property
    def is_moderator(self):
        return self.role == self.MODERATOR

    @property
    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser or self.is_staff

    def __str__(self):
        return self.username
