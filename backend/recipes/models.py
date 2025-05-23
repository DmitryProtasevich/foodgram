from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from recipes.constants import Constants


class AbstractUserRecipe(models.Model):
    """Абстрактная модель для пользователя и рецепта."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        ordering = ('recipe__name',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='%(app_label)s_%(class)s_unique_user_recipe'
            )
        ]

    def __str__(self):
        if self.recipe and len(self.recipe.name) > Constants.MAX_TITLE_LENGTH:
            return f'{self.recipe.name[:Constants.MAX_TITLE_LENGTH]}...'
        return self.recipe.name if self.recipe else ''


class AbstractTitle(models.Model):
    """Абстрактная модель для строкового представления и сортировки."""

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        if len(self.name) > Constants.MAX_TITLE_LENGTH:
            return f'{self.name[:Constants.MAX_TITLE_LENGTH]}...'
        return self.name


class Ingredients(AbstractTitle):
    """Модель для ингредиентов."""

    name = models.CharField(
        'Название',
        max_length=Constants.MAX_INGREDIENT_NAME_LENGHTH,
        db_index=True,
    )
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=Constants.MAX_INGREDIENT_MEASUREMENT_LENGHTH,
        blank=True
    )

    class Meta(AbstractTitle.Meta):
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        default_related_name = 'ingredient'


class Tag(AbstractTitle):
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

    class Meta(AbstractTitle.Meta):
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        default_related_name = 'tag'


class RecipeIngredient(models.Model):
    """Модель для ингредиентов рецепта."""

    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredients,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        'Количество ингредиентов',
        validators=(MinValueValidator(Constants.MIN_AMOUNT),)
    )

    class Meta:
        default_related_name = 'recipe_ingredients'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        )


class Recipe(AbstractTitle):
    """Модель для рецептов."""

    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги рецепта'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    ingredients = models.ManyToManyField(
        Ingredients,
        through='RecipeIngredient',
        verbose_name='Ингредиенты рецепта'
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

    class Meta(AbstractTitle.Meta):
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'


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


class ShoppingCart(AbstractUserRecipe):
    """Модель для списка покупок."""

    class Meta(AbstractUserRecipe.Meta):
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_cart'


class Favorite(AbstractUserRecipe):
    """Модель для избранного."""

    class Meta(AbstractUserRecipe.Meta):
        verbose_name = 'рецепт в избранном'
        verbose_name_plural = 'Рецепты в избранном'
        default_related_name = 'favorite'
