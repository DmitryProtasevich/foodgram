from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag


class RecipesFilter(filters.FilterSet):
    """Фильтр выборки рецептов."""

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(method='check_auth')
    is_in_shopping_cart = filters.BooleanFilter(method='check_auth')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_in_shopping_cart', 'is_favorited')

    def check_auth(self, queryset, name, value):
        if self.request.user.is_anonymous:
            return queryset
        return queryset.filter(**{name: value})
