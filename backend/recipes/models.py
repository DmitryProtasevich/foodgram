from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from recipes.constants import Constants


class AbstractTitle(models.Model):
    """Абстрактная модель для строкового представления и сортировки."""

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        if len(self.name) > Constants.MAX_TITLE_LENGTH:
            return f'{self.name[:Constants.MAX_TITLE_LENGTH]}...'
        return self.name


class Ingredient(AbstractTitle):
    """Модель для ингредиентов."""

    name = models.CharField(
        'Название',
        max_length=Constants.MAX_INGREDIENT_NAME_LENGTH,
        db_index=True,
    )
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=Constants.MAX_INGREDIENT_MEASUREMENT_LENGTH,
    )

    class Meta(AbstractTitle.Meta):
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_measurement_unit'
            ),
        )


class Tag(AbstractTitle):
    """Модель для тегов."""

    name = models.CharField(
        'Название',
        unique=True,
        max_length=Constants.MAX_TAG_NAME_LENGTH,
        db_index=True,
    )
    slug = models.SlugField(
        'Слаг',
        unique=True,
        max_length=Constants.MAX_TAG_NAME_LENGTH,
        db_index=True,
    )

    class Meta(AbstractTitle.Meta):
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'


class RecipeIngredient(models.Model):
    """Модель для ингредиентов рецепта."""

    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        'Количество ингредиентов',
        validators=(MinValueValidator(Constants.MIN_AMOUNT, message=(
            f'Количество ингредиентов не может быть меньше '
            f'{Constants.MIN_AMOUNT}'
        )),)
    )

    class Meta:
        default_related_name = 'recipe_ingredients'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        )

    def __str__(self):
        return (
            f'{self.ingredient.name} — {self.amount} '
            f'{self.ingredient.measurement_unit}'.strip()
        )


class Recipe(AbstractTitle):
    """Модель для рецептов."""

    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги рецепта'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты рецепта'
    )
    name = models.CharField(
        'Название',
        max_length=Constants.MAX_NAME_LENGTH,
        db_index=True,
    )
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/%Y/%m/%d/',
    )
    text = models.TextField('Описание')
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления (в минутах)',
        validators=(MinValueValidator(Constants.MIN_TIME),
                    MaxValueValidator(Constants.MAX_TIME)),
    )
    pub_date = models.DateTimeField(
        'Дата публикации', auto_now_add=True
    )

    class Meta(AbstractTitle.Meta):
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)


class AbstractUserRecipe(models.Model):
    """Абстрактная модель для пользователя и рецепта."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        ordering = ('recipe__name',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='%(app_label)s_%(class)s_unique_user_recipe'
            ),
        )

    def __str__(self):
        return (
            f'{self._meta.verbose_name}:'
            f' {self.recipe.name[:Constants.MAX_TITLE_LENGTH]}...'
        )


class ShoppingCart(AbstractUserRecipe):
    """Модель для списка покупок."""

    class Meta(AbstractUserRecipe.Meta):
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_carts'


class Favorite(AbstractUserRecipe):
    """Модель для избранного."""

    class Meta(AbstractUserRecipe.Meta):
        verbose_name = 'рецепт в избранном'
        verbose_name_plural = 'Рецепты в избранном'
        default_related_name = 'favorites'
