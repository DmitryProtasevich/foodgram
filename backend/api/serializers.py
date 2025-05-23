from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.constants import Constants
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователей."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(**validated_data, password=password)


class UserDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра пользователей."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(use_url=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )
        read_only_fields = ('id',)

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.subscribers.filter(user=user
                                                                ).exists()


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField(use_url=True, required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Пароль не верен.')
        return value


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = fields = '__all__'


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


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Сериализатор для создания ингредиентов рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=Constants.MIN_AMOUNT,
        error_messages={
            'min_value':
                f'Количество не может быть меньше {Constants.MIN_AMOUNT}.'
        }
    )


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для коротких рецептов."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    author = UserDetailSerializer(read_only=True)
    image = Base64ImageField(use_url=True, read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj in user.favorites.all()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj in user.shopping_list.all()


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и редактирования рецептов."""

    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    image = Base64ImageField(use_url=True)

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

    def validate_image(self, image):
        if not image:
            raise serializers.ValidationError(
                'Нужно загрузить изображение!'
            )
        return image

    def validate(self, attrs):
        attrs['ingredients'
              ] = self.validate_ingredients(attrs.get('ingredients'))
        attrs['tags'] = self.validate_tags(attrs.get('tags'))
        return attrs

    def create(self, data, **kwargs):
        tags = data.pop('tags')
        ingredients_data = data.pop('ingredients')
        recipe = Recipe.objects.create(**data, **kwargs)
        recipe.tags.set(tags)

        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            ) for item in ingredients_data
        ])
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            objs = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=item['id'],
                    amount=item['amount']
                ) for item in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(objs)
        return instance


class SubscriptionSerializer(UserDetailSerializer):
    """Сериализатор для подписок."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta(UserDetailSerializer.Meta):
        fields = UserDetailSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return RecipeShortSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context.get('request'
                                    ).build_absolute_uri(obj.avatar.url)
        return None
