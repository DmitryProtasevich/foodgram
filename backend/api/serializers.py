from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.constants import Constants
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователей."""

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

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
        return User.objects.create_user(**validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра пользователей."""

    is_subscribed = serializers.BooleanField(read_only=True)
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


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField(use_url=True, required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля."""

    new_password = serializers.CharField(validators=[validate_password])
    current_password = serializers.CharField(required=True)


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
    image = Base64ImageField(use_url=True, read_only=True)
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )


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


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""

    email = serializers.EmailField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    avatar = serializers.ImageField(use_url=True, read_only=True,
                                    required=False, allow_null=True)
    is_subscribed = serializers.BooleanField(read_only=True)
    recipes_count = serializers.IntegerField(read_only=True)
    recipes = RecipeShortSerializer(
        many=True,
        read_only=True,
        source='recipes_list'
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
            'recipes_count',
            'recipes',
        )
