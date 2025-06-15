from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag


class RecipesFilter(filters.FilterSet):
    """Фильтр выборки рецептов."""

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(method='filter_user_relation')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_user_relation')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_in_shopping_cart', 'is_favorited')

    def filter_user_relation(self, queryset, name, value):
        if not self.request.user.id:
            return queryset
        return queryset.filter(**{name: value})
