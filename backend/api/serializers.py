from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField

from recipes.models import Ingredients, Recipe, Tag, RecipeIngredient
from recipes.constants import Constants
User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
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
        user = User.objects.create_user(**validated_data, password=password)
        return user


class UserDetailSerializer(serializers.ModelSerializer):
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
    avatar = Base64ImageField(use_url=True, required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Текущий пароль неверен")
        return value


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredients
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def to_representation(self, instance):
        return {
            'id': instance.ingredient.id,
            'name': instance.ingredient.name,
            'measurement_unit': instance.ingredient.measurement_unit,
            'amount': instance.amount,
        }


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
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


class RecipeIngredientWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=Constants.MIN_AMOUNT,
        error_messages={
            'min_value':
                f"Количество не может быть меньше {Constants.MIN_AMOUNT}."
        }
    )


class RecipeWriteSerializer(serializers.ModelSerializer):
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

    def validate(self, attrs):
        ingredient_ids = set()
        tag_ids = set()
        ingredients = attrs.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Поле не может быть пустым!'})
        for item in ingredients:
            ing_id = item.get('id')
            if not Ingredients.objects.filter(id=ing_id).exists():
                raise serializers.ValidationError(
                    {'ingredients': f'Ингредиент с id={ing_id} не найден!'})
            if ing_id in ingredient_ids:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться!'})
            ingredient_ids.add(ing_id)
        tags = attrs.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужно выбрать хотя бы один тег!'})
        for tag_id in tags:
            if tag_id in tag_ids:
                raise serializers.ValidationError(
                    {'tags': 'Теги не должны повторяться!'})
            tag_ids.add(tag_id)
        if not attrs.get('image'):
            raise serializers.ValidationError(
                {'image': 'Нужно загрузить изображение!'})
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
