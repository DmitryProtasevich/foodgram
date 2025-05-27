from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.http import int_to_base36
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from rest_framework import filters, pagination, permissions, status, viewsets
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
    queryset = User.objects.all()
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    search_fields = ('username',)
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'put', 'delete', 'head', 'options')
    pagination_class = pagination.LimitOffsetPagination

    def get_serializer_class(self):
        if self.action == 'subscriptions':
            return SubscriptionSerializer
        if self.request.method == 'GET':
            return UserDetailSerializer
        return UserCreateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        subscribed_ids = set()
        if user.is_authenticated:
            subscribed_ids = set(
                Follow.objects.filter(user=user)
                .values_list('following_id', flat=True)
            )
        for u in queryset:
            u.is_subscribed = u.id in subscribed_ids

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        instance.is_subscribed = (
            user.is_authenticated and 
            Follow.objects.filter(user=user, following=instance).exists()
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('get',),
        url_path='me',
        url_name='me',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def get_me_data(self, request):
        return Response(UserDetailSerializer(
            request.user,
            context={'request': request}
        ).data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        url_name='me-avatar',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def update_or_delete_avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password',
        url_name='set_password',
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=SetPasswordSerializer
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        url_path='subscribe',
        serializer_class=SubscriptionSerializer,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscription_handler(self, request, *args, **kwargs):
        author = self.get_object()
        user = request.user
        if request.method == 'POST':
            return self.create_subscription(user, author)
        return self.delete_subscription(user, author)

    def create_subscription(self, user, author):
        if user == author:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Follow.objects.filter(user=user, following=author).exists():
            return Response(
                {'detail': 'Подписка уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Follow.objects.create(user=user, following=author)
        author.is_subscribed = True
        author.recipes_count = author.recipes.count()
        limit = self.request.query_params.get('recipes_limit')
        try:
            rl = int(limit) if limit is not None else None
        except ValueError:
            rl = None
        qs = author.recipes.all()
        if rl is not None:
            qs = qs[:rl]
        author.recipes_list = list(qs)
        serializer = SubscriptionSerializer(
            author,
            context={'request': self.request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_subscription(self, user, author):
        deleted_count, _ = Follow.objects.filter(
            user=user, following=author).delete()
        if deleted_count == 0:
            return Response(
                {'detail': 'Подписка не существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=(permissions.IsAuthenticated,),
        pagination_class=pagination.LimitOffsetPagination,
        serializer_class=SubscriptionSerializer,
    )
    def subscriptions(self, request):
        qs = User.objects.filter(subscribers__user=request.user) \
                         .prefetch_related('recipes')
        page = self.paginate_queryset(qs)
        authors = list(page) if page is not None else list(qs)
        limit = request.query_params.get('recipes_limit')
        try:
            rl = int(limit) if limit is not None else None
        except ValueError:
            rl = None

        for author in authors:
            author.is_subscribed = True
            author.recipes_count = author.recipes.count()
            qs = author.recipes.all()
            if rl is not None:
                qs = qs[:rl]
            author.recipes_list = list(qs)
        serializer = SubscriptionSerializer(
            authors,
            many=True,
            context={'request': request}
        )
        return (self.get_paginated_response(serializer.data)
                if page is not None else Response(serializer.data))


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
        data = RecipeReadSerializer(page, many=True, context={'request': request}).data
        if request.user.is_authenticated:
            fav_ids = set(request.user.favorites.values_list('id', flat=True))
            cart_ids = set(request.user.shopping_list.values_list('id', flat=True))
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
            cart_ids = set(request.user.shopping_list.values_list('id', flat=True))
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
            cart_ids = set(request.user.shopping_list.values_list('id', flat=True))
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
