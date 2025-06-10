
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import base36_to_int

from recipes.models import Recipe


def short_link_redirect(request, short_link_id):
    """Перенаправляет пользователя на рецепт по короткой ссылке."""
    try:
        return redirect('recipes-detail', pk=get_object_or_404(
            Recipe, pk=base36_to_int(short_link_id)
        ).pk)
    except ValueError:
        return HttpResponse('Некорректная ссылка', status=400)
