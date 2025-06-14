from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, F, OuterRef, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import int_to_base36
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserViewSet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import RecipesFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (AvatarSerializer, FavoriteSerializer,
                             IngredientsSerializer, RecipeReadSerializer,
                             RecipeWriteSerializer, ShoppingCartSerializer,
                             SubscriptionCreateSerializer,
                             SubscriptionSerializer, TagsSerializer,
                             UserDetailSerializer)
from api.services import generate_shoping_list
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

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
        serializer.save(user=self.request.user)
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
        subscribed_authors_qs = (
            User.objects.filter(subscriptions_to_author__user=request.user)
            .annotate(recipes_count=Count('recipes'))
            .order_by('username').prefetch_related('recipes')
        )
        page = self.paginate_queryset(subscribed_authors_qs)
        serializer = self.get_serializer(
            page if page is not None else subscribed_authors_qs, many=True
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

    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter
    permission_classes = (IsAuthorOrReadOnly,)

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Recipe.objects.select_related('author')
            .prefetch_related('tags', 'ingredients')
        )
        if user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(Favorite.objects.filter(
                    recipe=OuterRef('pk'), user=user
                )),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    recipe=OuterRef('pk'), user=user
                )),
            ).order_by('-is_favorited', '-is_in_shopping_cart')
        return queryset

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link'
    )
    def get_short_link(self, request, pk=None):
        return Response({
            'short-link': request.build_absolute_uri(
                reverse('short_link-redirect',
                        args=[int_to_base36(self.get_object().id)]))
        })

    @action(
        detail=False,
        methods=('get',),
        url_path='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated,),
        pagination_class=None
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_carts__user=request.user)
            .values(name=F('ingredient__name'),
                    measurement_unit=F('ingredient__measurement_unit'))
            .annotate(total_amount=Sum('amount')).order_by('name')
        )
        text_content = generate_shoping_list(ingredients)
        return FileResponse(
            text_content, as_attachment=True, filename='shopping_list.txt',
            content_type='text/plain; charset=utf-8'
        )

    def create_relation(self, request, serializer_cls, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        data = {'user': request.user.id, 'recipe': recipe.id}
        serializer = serializer_cls(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_relation(self, request, model, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        return Response(
            status=status.HTTP_204_NO_CONTENT
            if deleted else status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=('post',),
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        return self.create_relation(request, ShoppingCartSerializer, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.delete_relation(request, ShoppingCart, pk)

    @action(
        detail=True,
        methods=('post',),
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        return self.create_relation(request, FavoriteSerializer, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.delete_relation(request, Favorite, pk)
