from django_filters import rest_framework

from recipes.models import Recipe, Tag


class RecipesFilter(rest_framework.FilterSet):
    tags = rest_framework.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = rest_framework.NumberFilter(
        field_name='author__id',
    )
    is_favorited = rest_framework.BooleanFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = rest_framework.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ()

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(
                id__in=user.favorites.values_list('id', flat=True)
            )
        return queryset.exclude(
            id__in=user.favorites.values_list('id', flat=True)
        )

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(
                id__in=user.shopping_list.values_list('id', flat=True)
            )
        return queryset.exclude(
            id__in=user.shopping_list.values_list('id', flat=True)
        )
