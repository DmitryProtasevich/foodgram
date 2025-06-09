from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from djoser.serializers import UserSerializer as DjoserUserSerializer

from recipes.constants import Constants
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

User = get_user_model()


class UserDetailSerializer(DjoserUserSerializer):
    """Сериализатор для просмотра пользователей."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta(DjoserUserSerializer.Meta):
        fields = DjoserUserSerializer.Meta.fields+(
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context['request'].user
        return (
            request.is_authenticated and
            obj.author_subscriptions.filter(user=request).exists()
        )


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения ингредиентов рецепта."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ингредиентов рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=Constants.MIN_AMOUNT,
        error_messages={
            'min_value':
                f'Количество не может быть меньше {Constants.MIN_AMOUNT}.'
        }
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для коротких рецептов."""

    image = Base64ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    tags = TagsSerializer(many=True, read_only=True)
    author = UserDetailSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    image = Base64ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и редактирования рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'ingredients', 'image', 'name',
            'text', 'cooking_time',
        )

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Поле не может быть пустым!'
            )
        ingredient_ids = set()
        for item in ingredients:
            ing_id = item.get('id')
            if not Ingredient.objects.filter(id=ing_id).exists():
                raise serializers.ValidationError(
                    f'Ингредиент с id={ing_id} не найден!'
                )
            if ing_id in ingredient_ids:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться!'
                )
            ingredient_ids.add(ing_id)
        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                'Нужно выбрать хотя бы один тег!'
            )
        tag_ids = set()
        for tag_id in tags:
            if tag_id in tag_ids:
                raise serializers.ValidationError(
                    'Теги не должны повторяться!'
                )
            tag_ids.add(tag_id)
        return tags

    def validate_image(self, value):
        if value in ('', None):
            raise serializers.ValidationError(
                'Нужно загрузить изображение!'
            )
        return value

    def create(self, data, **kwargs):
        tags = data.pop('tags')
        ingredients = data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context.get('request').user, **data
        )
        recipe.tags.set(tags)
        for ingredient in ingredients:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=get_object_or_404(Ingredient, pk=ingredient['id']),
                amount=ingredient['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' not in validated_data or 'tags' not in validated_data:
            raise serializers.ValidationError({
                'Это поле обязательно при обновлении рецепта.'
            })
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.set(tags)
        ingredients_data = validated_data.pop('ingredients', None)
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for ingredient in ingredients_data:
                RecipeIngredient.objects.update_or_create(
                    recipe=instance,
                    ingredient=get_object_or_404(Ingredient,
                                                 pk=ingredient['id']),
                    amount=ingredient['amount']
                )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')}
        )
        return serializer.data


class SubscriptionSerializer(UserDetailSerializer):
    """Сериализатор для вывода информации о подписках."""

    recipes_count = serializers.IntegerField(
        read_only=True, default=Constants.RECIPES_COUNT
    )
    recipes = serializers.SerializerMethodField(read_only=True)

    class Meta(UserDetailSerializer.Meta):
        fields = UserDetailSerializer.Meta.fields+(
            'recipes_count',
            'recipes',
        )

    def get_recipes(self, obj):
        try:
            limit = int(
                self.context.get('request').query_params.get('recipes_limit')
            )
        except (TypeError, ValueError):
            limit = None
        return RecipeShortSerializer(
            obj.recipes.all()[:limit], many=True, context=self.context).data


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписок."""

    author = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )

    class Meta:
        model = Follow
        fields = ('author',)
        read_only_fields = ('user',)

    def validate(self, data):
        user = self.context['request'].user
        author = data['author']
        if user == author:
            raise serializers.ValidationError(
                {'detail': 'Нельзя подписаться на самого себя.'}
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                {'detail': 'Подписка уже существует.'}
            )
        return data

    def create(self, validated_data):
        return Follow.objects.create(
            user=self.context['request'].user, **validated_data
        )

    def to_representation(self, instance):
        return SubscriptionSerializer(
            instance.author,
            context=self.context
        ).data
