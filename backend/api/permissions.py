from rest_framework import permissions


class IsAuthorOrAdminOrModeratorOrReadOnly(permissions.BasePermission):
    """
    Разрешает чтение всем, изменение/удаление - автору, модератору или админу.
    """

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or (
            request.user.is_admin
            or request.user.is_moderator
            or obj.author == request.user
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешает чтение всем, запись - только администраторам и персоналу.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or (
            request.user.is_authenticated and request.user.is_admin
        )


class IsSuperUserOrIsAdminOnly(permissions.BasePermission):
    """
    Разрешает доступ только администраторам и суперпользователям.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin