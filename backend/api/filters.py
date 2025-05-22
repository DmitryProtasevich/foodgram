from django_filters import rest_framework

from recipes.models import Recipe, Tag


class RecipesFilter(rest_framework.FilterSet):
    tags = rest_framework.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = rest_framework.NumberFilter(
        field_name='author',
    )
    is_favorited = rest_framework.BooleanFilter(method='filter_by_favorites')
    is_in_shopping_cart = rest_framework.BooleanFilter(method='filter_by_shopping_list')

    class Meta:
        model = Recipe
        fields = ()

    def _filter_by_user_relation(self, queryset, value, relation):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        
        ids = getattr(user, relation).values_list('id', flat=True)
        return queryset.filter(id__in=ids) if value else queryset.exclude(id__in=ids)

    def filter_by_favorites(self, queryset, name, value):
        return self._filter_by_user_relation(queryset, value, 'favorites')

    def filter_by_shopping_list(self, queryset, name, value):
        return self._filter_by_user_relation(queryset, value, 'shopping_list')
