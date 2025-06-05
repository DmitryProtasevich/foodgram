from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import int_to_base36
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (Follow, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)

from .filters import RecipesFilter
from .permissions import IsAuthorOrAdminOrModeratorOrReadOnly
from .serializers import (AvatarSerializer, IngredientsSerializer,
                          RecipeReadSerializer, RecipeShortSerializer,
                          RecipeWriteSerializer, SubscriptionSerializer,
                          TagsSerializer, UserCreateSerializer,
                          UserDetailSerializer)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет для объектов пользователя."""

    queryset = User.objects.all().prefetch_related('recipes')
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    search_fields = ('username',)
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'put', 'delete', 'head', 'options')

    def get_serializer_class(self):
        if self.action in ('subscriptions', 'subscribe'):
            return SubscriptionSerializer
        if self.action == 'avatar':
            return AvatarSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action in ('list', 'retrieve', 'me'):
            return UserDetailSerializer
        return UserCreateSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.user.is_authenticated:
            followed_ids = set(Follow.objects.filter(
                user=request.user).values_list('following_id', flat=True))
            for user in qs:
                user.is_subscribed = user.id in followed_ids
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_subscribed = (
            request.user.is_authenticated and Follow.objects.filter(
                user=request.user, following=obj
            ).exists()
        )
        return super().retrieve(request, *args, **kwargs)

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
        methods=['put', 'delete'],
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
        if request.user.avatar:
            request.user.avatar.delete(save=False)
            request.user.avatar = None
            request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        url_path='subscribe',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(
            User.objects.prefetch_related('recipes'), pk=id
        )
        if request.method == 'POST':
            if request.user == author:
                return Response(
                    {'detail': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                Follow.objects.create(user=request.user, following=author)
            except IntegrityError:
                return Response(
                    {'detail': 'Подписка уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                limit = int(request.query_params.get('recipes_limit'))
            except (TypeError, ValueError):
                limit = None
            recipes = list(
                author.recipes.all()[:limit]
            ) if limit else list(author.recipes.all())
            author.recipes_count = len(recipes)
            author.recipes_list = recipes
            return Response(SubscriptionSerializer(
                author, context={'request': request}
            ).data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted, _ = Follow.objects.filter(
                user=request.user,
                following=author
            ).delete()
            if not deleted:
                return Response(
                    {'detail': 'Подписка не существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SubscriptionSerializer,
    )
    def subscriptions(self, request):
        authors = User.objects.filter(
            subscribers__user=request.user
        ).prefetch_related('recipes')

        page = self.paginate_queryset(authors)
        authors = list(page) if page is not None else list(authors)
        try:
            limit = int(request.query_params.get('recipes_limit'))
        except (TypeError, ValueError):
            limit = None

        for author in authors:
            author.is_subscribed = True
            recipes = list(
                author.recipes.all()[:limit] if limit else author.recipes.all()
            )
            author.recipes_count, author.recipes_list = len(recipes), recipes

        data = SubscriptionSerializer(
            authors, many=True, context={'request': request}
        ).data
        return (self.get_paginated_response(data)
                if page is not None else Response(data))


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
    filterset_fields = ('name',)


class RecipesViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter
    permission_classes = (IsAuthorOrAdminOrModeratorOrReadOnly,)

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
                f'/s/{int_to_base36(self.get_object().id)}'
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

    def handle_relation(self, request, name, detail, detail_not_exists):
        recipe = self.get_object()
        relation = getattr(request.user, name)
        if request.method == 'POST':
            if relation.filter(id=recipe.id).exists():
                return Response({'detail': detail},
                                status=status.HTTP_400_BAD_REQUEST)
            relation.add(recipe)
            return Response(RecipeShortSerializer(
                recipe, context={'request': request}
            ).data, status=status.HTTP_201_CREATED)
        if not relation.filter(id=recipe.id).exists():
            return Response({'detail': detail_not_exists},
                            status=status.HTTP_400_BAD_REQUEST)
        relation.remove(recipe)
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
            name='shopping_list',
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
            name='favorites',
            detail='Рецепт уже в избранном',
            detail_not_exists='Рецепта нет в избранном')
