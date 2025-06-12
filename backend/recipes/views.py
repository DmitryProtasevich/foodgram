from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.utils.http import base36_to_int

from recipes.models import Recipe


def short_link_redirect(request, short_link_id):
    """Перенаправляет пользователя на рецепт по короткой ссылке."""
    try:
        recipe_id = base36_to_int(short_link_id)
    except ValueError:
        return HttpResponse('Некорректная ссылка', status=400)
    return HttpResponsePermanentRedirect(request.build_absolute_uri(
        f'/recipes/{get_object_or_404(Recipe, pk=recipe_id).id}'
    ))
