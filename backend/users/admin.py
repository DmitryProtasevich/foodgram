from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.safestring import mark_safe

from users.models import Follow, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Административный интерфейс для управления пользователями."""

    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'avatar_preview',
        'recipes_count',
        'followers_count'
    )
    empty_value_display = 'значение отсутствует'
    list_filter = ('username',)
    search_fields = ('username', 'email')

    @admin.display(description='Аватар')
    def avatar_preview(self, obj):
        if obj.avatar:
            return mark_safe(
                f'<img src="{obj.avatar.url}" width="80" height="60">'
            )
        return ''

    @admin.display(description='Кол-во рецептов у пользователя')
    def recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Кол-во подписчиков у пользователя')
    def followers_count(self, obj):
        return obj.subscriptions_to_author.count()


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Административный интерфейс для управления подписками."""

    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')
    list_filter = ('user', 'author')
