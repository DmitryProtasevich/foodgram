from django.db.models import Count
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import base36_to_int, int_to_base36
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserViewSet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow
from .filters import RecipesFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, IngredientsSerializer,
                          RecipeReadSerializer, RecipeShortSerializer,
                          RecipeWriteSerializer,
                          TagsSerializer, SubscriptionSerializer,
                          UserDetailSerializer, SubscriptionCreateSerializer)

User = get_user_model()


class UserViewSet(DjoserViewSet):
    """Вьюсет для объектов пользователя."""

    queryset = User.objects.all().prefetch_related('recipes')
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    search_fields = ('username',)
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'put', 'delete', 'head', 'options')

    @action(
        detail=False,
        methods=('get',),
        url_path='me',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def me(self, request):
        return Response(UserDetailSerializer(
            request.user,
            context={'request': request}
        ).data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=('put',),
        url_path='me/avatar',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def avatar(self, request):
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                request.user, data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=('post',),
        detail=True,
        url_path='subscribe',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SubscriptionCreateSerializer
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(
            User.objects.prefetch_related('recipes'), pk=id
        )
        serializer = SubscriptionCreateSerializer(
            data={'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        deleted, _ = Follow.objects.filter(
            user=request.user,
            author=author
        ).delete()
        return Response(
            status=status.HTTP_400_BAD_REQUEST
            if not deleted else status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=False,
        methods=('get',),
        url_path='subscriptions',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SubscriptionSerializer
    )
    def subscriptions(self, request):
        subscribed_authors_qs = User.objects.filter(
            author_subscriptions__user=request.user
        ).annotate(recipes_count=Count('recipes')).prefetch_related('recipes')
        page = self.paginate_queryset(subscribed_authors_qs)
        serializer = self.get_serializer(
            page if page is not None else subscribed_authors_qs,
            many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для тегов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientsSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class RecipesViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter
    permission_classes = (IsAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_short_link(self, request, pk=None):
        return Response(
            {'short-link': request.build_absolute_uri(
                f'/s/{int_to_base36(self.get_object().id)}/'
            )}
        )

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated,),
        pagination_class=None
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=ShoppingCart.objects.filter(
                user=request.user
            ).values_list('recipe', flat=True)
        ).select_related('ingredient')
        totals = {}
        for item in ingredients:
            key = (item.ingredient.name, item.ingredient.measurement_unit)
            totals[key] = totals.get(key, 0) + item.amount
        response = HttpResponse('\n'.join(['Список покупок:\n'] + [
            f'{name} ({unit}) — {amount}'
            for (name, unit), amount in totals.items()
        ]), content_type='text/plain; charset=utf-8')
        response['Content-Disposition'
                 ] = 'attachment; filename="shopping_list.txt"'
        return response

    def handle_relation(self, request, model, detail, detail_not_exists):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response({'detail': detail},
                                status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=user, recipe=recipe)
            return Response(RecipeShortSerializer(
                recipe, context={'request': request}
            ).data, status=status.HTTP_201_CREATED)
        deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if not deleted:
            return Response({'detail': detail_not_exists},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=RecipeShortSerializer,
    )
    def shopping_cart(self, request, pk=None):
        return self.handle_relation(
            request,
            model=ShoppingCart,
            detail='Рецепт уже в списке покупок',
            detail_not_exists='Рецепта нет в списке покупок')

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=RecipeShortSerializer,
    )
    def favorite(self, request, pk=None):
        return self.handle_relation(
            request,
            model=Favorite,
            detail='Рецепт уже в избранном',
            detail_not_exists='Рецепта нет в избранном')


def short_link_redirect(request, short_link_id):
    """Перенаправляет пользователя на рецепт по короткой ссылке."""
    try:
        recipe_id = base36_to_int(short_link_id)
    except ValueError:
        return HttpResponse('Некорректная ссылка', status=400)
    return redirect(f'/recipes/{recipe_id}')
