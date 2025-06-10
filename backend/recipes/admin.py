from django.contrib import admin
from django.utils.safestring import mark_safe

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)


class RecipeNameMixin:
    """Миксин для имени рецепта."""

    @admin.display(description='Рецепт')
    def display_recipe(self, obj):
        return obj.recipe.name


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для добавления ингредиентов к рецепту."""

    model = RecipeIngredient
    fields = ('ingredient', 'amount')
    extra = 0
    min_num = 1
    validate_min = True


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Административный интерфейс для управления рецептами."""

    list_display = ('id', 'author', 'name', 'get_tags', 'favorites_count',
                    'get_ingredients', 'image_preview', 'cooking_time',
                    'pub_date')
    search_fields = ('author__username', 'name', 'text')
    list_filter = ('tags', 'author')
    inlines = (RecipeIngredientInline, )

    @admin.display(description='Изображение')
    def image_preview(self, obj):
        return mark_safe(
            f'<img src="{obj.image.url}" width="80" height="60">'
        )

    @admin.display(description='Теги')
    def get_tags(self, obj):
        return ', '.join(tag.name for tag in obj.tags.all())

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ', '.join(
            f'{ri.ingredient.name} ({ri.amount})'
            for ri in obj.recipe_ingredients.all()
        )

    @admin.display(description='Количество добавлений в избранное')
    def favorites_count(self, obj):
        return obj.favorites.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Административный интерфейс для управления ингредиентами."""

    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Административный интерфейс для управления тегами."""

    list_display = ('id', 'name', 'slug')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Favorite)
class FavoriteAdmin(RecipeNameMixin, admin.ModelAdmin):
    """Административный интерфейс для управления избранным."""

    list_display = ('id', 'user', 'display_recipe')
    list_filter = ('user',)
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(RecipeNameMixin, admin.ModelAdmin):
    """Административный интерфейс для управления покупками."""

    list_display = ('id', 'user', 'display_recipe')
    list_filter = ('user',)
    search_fields = ('user__username', 'recipe__name')
