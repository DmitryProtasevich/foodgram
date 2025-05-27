from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import int_to_base36
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from rest_framework import filters, pagination, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError

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
    queryset = User.objects.all().prefetch_related('recipes')
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    search_fields = ('username',)
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'put', 'delete', 'head', 'options')
    pagination_class = pagination.LimitOffsetPagination

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
            request.user.is_authenticated and
            Follow.objects.filter(user=request.user, following=obj).exists()
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
    queryset = Tag.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientsSerializer
    pagination_class = None
    filterset_fields = ('name',)


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = pagination.LimitOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter
    permission_classes = (IsAuthorOrAdminOrModeratorOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        params = self.request.query_params
        fav = params.get('is_favorited')
        if fav is not None and user.is_authenticated:
            ids = user.favorites.values_list('id', flat=True)
            qs = qs.filter(id__in=ids) if fav in ['1', 'true', 'True'] \
                else qs.exclude(id__in=ids)
        cart = params.get('is_in_shopping_cart')
        if cart is not None and user.is_authenticated:
            ids = user.shopping_list.values_list('id', flat=True)
            qs = qs.filter(id__in=ids) if cart in ['1', 'true', 'True'] \
                else qs.exclude(id__in=ids)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        data = RecipeReadSerializer(page, many=True, context={
                                    'request': request}).data
        if request.user.is_authenticated:
            fav_ids = set(request.user.favorites.values_list('id', flat=True))
            cart_ids = set(
                request.user.shopping_list.values_list('id', flat=True))
        else:
            fav_ids = cart_ids = set()
        for item in data:
            item['is_favorited'] = item['id'] in fav_ids
            item['is_in_shopping_cart'] = item['id'] in cart_ids
        return self.get_paginated_response(data)

    def retrieve(self, request, *args, **kwargs):
        inst = self.get_object()
        data = RecipeReadSerializer(inst, context={'request': request}).data
        if request.user.is_authenticated:
            fav_ids = set(request.user.favorites.values_list('id', flat=True))
            cart_ids = set(
                request.user.shopping_list.values_list('id', flat=True))
        else:
            fav_ids = cart_ids = set()
        data['is_favorited'] = inst.id in fav_ids
        data['is_in_shopping_cart'] = inst.id in cart_ids
        return Response(data)

    def create(self, request, *args, **kwargs):
        ws = self.get_serializer(data=request.data)
        ws.is_valid(raise_exception=True)
        recipe = ws.save(author=request.user)
        data = RecipeReadSerializer(recipe, context={'request': request}).data
        data['is_favorited'] = False
        data['is_in_shopping_cart'] = False
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        inst = self.get_object()
        ws = self.get_serializer(inst, data=request.data, partial=True)
        ws.is_valid(raise_exception=True)
        ws.save()

        data = RecipeReadSerializer(inst, context={'request': request}).data
        if request.user.is_authenticated:
            fav_ids = set(request.user.favorites.values_list('id', flat=True))
            cart_ids = set(
                request.user.shopping_list.values_list('id', flat=True))
        else:
            fav_ids = cart_ids = set()

        data['is_favorited'] = inst.id in fav_ids
        data['is_in_shopping_cart'] = inst.id in cart_ids
        return Response(data, status=status.HTTP_200_OK)

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
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=RecipeShortSerializer,
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if user.shopping_list.filter(id=recipe.id).exists():
                return Response(
                    {'detail': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.shopping_list.add(recipe)
            serializer = RecipeShortSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if not user.shopping_list.filter(id=recipe.id).exists():
            return Response(
                {'detail': 'Рецепта нет в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.shopping_list.remove(recipe)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated,),
        pagination_class=None
    )
    def download_shopping_cart(self, request):
        cart_recipes = ShoppingCart.objects.filter(
            user=request.user
        ).values_list('recipe', flat=True)
        all_ings = RecipeIngredient.objects.filter(recipe__in=cart_recipes)
        summary = {}
        for ing in all_ings:
            key = (ing.ingredient.name, ing.ingredient.measurement_unit)
            summary[key] = summary.get(key, 0) + ing.amount
        lines = ['Список покупок:\n']
        for (name, unit), total in summary.items():
            lines.append(f"{name} ({unit}) — {total}")
        content = "\n".join(lines)
        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=RecipeShortSerializer,
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if user.favorites.filter(id=recipe.id).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.favorites.add(recipe)
            serializer = RecipeShortSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not user.favorites.filter(id=recipe.id).exists():
                return Response(
                    {'detail': 'Рецепта нет в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.favorites.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
