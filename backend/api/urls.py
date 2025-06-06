from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientsViewSet, RecipesViewSet, TagsViewSet,
                    UserViewSet, short_link_redirect)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='users')
router.register('tags', TagsViewSet, basename='tags')
router.register('ingredients', IngredientsViewSet, basename='ingredients')
router.register('recipes', RecipesViewSet, basename='recipes')

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('s/<str:short_link_id>/', short_link_redirect),
    path('', include(router.urls)),
]
