from rest_framework.response import Response
from rest_framework import filters, viewsets, pagination, status, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action

from django.contrib.auth import get_user_model

# from .permissions import IsAuthorOrReadOnly
from .serializers import (
    UserCreateSerializer,
    UserDetailSerializer,
    AvatarSerializer,
    TagsSerializer,
    IngredientsSerializer,
    RecipeWriteSerializer,
    RecipeReadSerializer
)
from djoser.serializers import SetPasswordSerializer
from recipes.models import Ingredients, Tag, Recipe
from .filters import RecipesFilter

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    search_fields = ('username',)
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'put', 'delete', 'head', 'options')
    pagination_class = pagination.LimitOffsetPagination

    def get_serializer_class(self):
        if self.request.method in ['GET']:
            return UserDetailSerializer
        return UserCreateSerializer

    @action(
        detail=False,
        methods=('get',),
        url_path='me',
        url_name='me',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def get_me_data(self, request):
        return Response(
            UserDetailSerializer(request.user).data,
            status=status.HTTP_200_OK
        )

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
        if not user.avatar:
            return Response(
                {'error': 'Avatar does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )
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


class TagsViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagsSerializer
    http_method_names = ('get',)
    pagination_class = None


class IngredientsViewSet(viewsets.ModelViewSet):
    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    http_method_names = ('get',)
    pagination_class = None


# class RecipesViewSet(viewsets.ModelViewSet):
#     queryset = Recipe.objects.all()
#     pagination_class = pagination.LimitOffsetPagination
#     filter_backends = (DjangoFilterBackend,)
#     filterset_class = RecipesFilter

#     # def perform_create(self, serializer):
#     #     serializer.save(author=self.request.user)

#     def get_serializer_class(self):
#         if self.request.method in ['GET']:
#             return RecipeReadSerializer
#         return RecipeWriteSerializer
class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = pagination.LimitOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        recipe = write_serializer.instance
        read_serializer = RecipeReadSerializer(
            recipe,
            context=self.get_serializer_context()
        )
        headers = self.get_success_headers(read_serializer.data)
        return Response(
            read_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
