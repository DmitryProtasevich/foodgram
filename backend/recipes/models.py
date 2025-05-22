from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from recipes.constants import Constants


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
        Ingredients,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes'
    )
    amount = models.PositiveIntegerField(
        'Количество ингридиентов',
        validators=(MinValueValidator(Constants.MIN_AMOUNT),)
    )

    class Meta:
        unique_together = ('recipe', 'ingredient')
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        )


class Recipe(models.Model):
    """Модель для рецептов."""
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги рецепта'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes'
    )
    ingredients = models.ManyToManyField(
        Ingredients,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингридиенты рецепта'
    )
    name = models.CharField(
        'Название',
        max_length=Constants.MAX_NAME_LENGHTH,
        db_index=True,
    )
    image = models.ImageField(
        'Изображение',
        null=False
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


class Follow(models.Model):
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
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                name='unique_user_following',
                fields=['user', 'following']
            ),
            models.CheckConstraint(
                name='prevent_self_follow',
                check=~models.Q(user=models.F('following')),
            ),
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.following}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='cart_items',
        null=True,
        blank=True
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_carts',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('recipe__name',)
        unique_together = ('user', 'recipe')

    def __str__(self):
        return (
            (self.recipe[:Constants.MAX_TITLE_LENGTH] + '...')
            if len(self.recipe) > Constants.MAX_TITLE_LENGTH else self.recipe
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorite_items',
        null=True,
        blank=True
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_favorite',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'покупка в избранном'
        verbose_name_plural = 'Покупки в избранном'
        ordering = ('recipe__name',)
        unique_together = ('user', 'recipe')

    def __str__(self):
        return (
            (self.recipe[:Constants.MAX_TITLE_LENGTH] + '...')
            if len(self.recipe) > Constants.MAX_TITLE_LENGTH else self.recipe
        )
