from django.db import models
from django.core.validators import MinValueValidator

from recipes.constants import Constants
from django.conf import settings


class Ingredients(models.Model):
    """Модель для ингридиентов."""
    name = models.CharField(
        'Название',
        max_length=Constants.MAX_INGREDIENT_NAME_LENGHTH,
        db_index=True,
        blank=True
    )
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=Constants.MAX_INGREDIENT_MEASUREMENT_LENGHTH,
        db_index=True,
        blank=True
    )

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)

    def __str__(self):
        return (
            (self.name[:Constants.MAX_TITLE_LENGTH] + '...')
            if len(self.name) > Constants.MAX_TITLE_LENGTH else self.name
        )


class Tag(models.Model):
    """Модель для тегов."""
    name = models.CharField(
        'Название',
        unique=True,
        max_length=Constants.MAX_TAG_NAME_LENGHTH,
        db_index=True,
        blank=True
    )
    slug = models.SlugField(
        'Слаг',
        unique=True,
        max_length=Constants.MAX_TAG_NAME_LENGHTH,
        db_index=True,
        blank=True
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return (
            (self.name[:Constants.MAX_TITLE_LENGTH] + '...')
            if len(self.name) > Constants.MAX_TITLE_LENGTH else self.name
        )


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredients, on_delete=models.CASCADE, related_name='ingredient_recipes'
    )
    amount = models.PositiveIntegerField()

    class Meta:
        unique_together = ('recipe', 'ingredient')


class Recipe(models.Model):
    """Модель для рецептов."""
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги рецепта'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    ingredients = models.ManyToManyField(
        Ingredients,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингридиенты рецепта'
    )
    is_favorited = models.BooleanField(
        'Находится в избранном',
        default=False
    )
    is_in_shopping_cart = models.BooleanField(
        'Находится в избранном корзине',
        default=False
    )
    name = models.CharField(
        'Название',
        max_length=Constants.MAX_NAME_LENGHTH,
        db_index=True,
    )
    image = models.ImageField(
        'Изображение',
    )
    text = models.TextField('Описание')
    cooking_time = models.IntegerField(
        'Время приготовления (в минутах)',
        validators=[MinValueValidator(Constants.MIN_TIME)],
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('name',)

    def __str__(self):
        return (
            (self.name[:Constants.MAX_TITLE_LENGTH] + '...')
            if len(self.name) > Constants.MAX_TITLE_LENGTH else self.name
        )
