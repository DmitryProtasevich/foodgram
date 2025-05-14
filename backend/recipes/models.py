from django.db import models

from recipes.constants import Constants


class Recipe(models.Model):
    """Модель для рецептов."""

    name = models.CharField(
        'Название',
        max_length=Constants.MAX_NAME_LENGHTH,
        db_index=True,
    )
#     year = models.SmallIntegerField(
#         'Год выпуска',
#         db_index=True,
#         validators=(validate_year,)
#     )
#     description = models.TextField(
#         'Описание произведения',
#         blank=True,
#         default=''
#     )
#     genre = models.ManyToManyField(
#         Genre,
#         related_name='titles',
#         verbose_name='Жанр произведения',
#     )
#     category = models.ForeignKey(
#         Category,
#         on_delete=models.CASCADE,
#         related_name='titles',
#         verbose_name='Категория произведения',
#     )

#     class Meta:
#         verbose_name = 'произведение'
#         verbose_name_plural = 'Произведения'
#         ordering = ('-year', 'name')

#     def __str__(self):
#         return (
#             (self.name[:Constants.MAX_TITLE_LENGTH] + '...')
#             if len(self.name) > Constants.MAX_TITLE_LENGTH else self.name
#         )

