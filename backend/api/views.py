from rest_framework.response import Response
from rest_framework import filters, viewsets, pagination, status, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action

from django.contrib.auth import get_user_model
from .serializers import UserCreateSerializer, UserDetailSerializer, AvatarSerializer
from djoser.serializers import SetPasswordSerializer

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
        """Позволяет получить информацию о себе и редактировать её."""
        serializer = UserDetailSerializer(request.user)
        return Response(
            serializer.data,
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
                {"error": "Avatar does not exist"},
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