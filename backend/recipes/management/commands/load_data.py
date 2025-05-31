import csv
import os

from django.core.management import BaseCommand
from django.conf import settings

from recipes.models import Ingredient


class Command(BaseCommand):
    """Класс загрузки тестовой базы данных ингредиентов."""

    def handle(self, *args, **options):
        path = os.path.join(settings.CSV_FILES_DIR, 'ingredients.csv')
        if not os.path.exists(path):
            self.stdout.write(self.style.WARNING(
                'Файл ingredients.csv не найден.'
            ))
            return

        self.stdout.write('Началась загрузка файла: ingredients.csv')
        objects = []
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(
                f, fieldnames=('name', 'measurement_unit')
            ):
                objects.append(Ingredient(
                    name=row['name'],
                    measurement_unit=row['measurement_unit']
                ))
        Ingredient.objects.bulk_create(objects, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            'Загрузка ingredients.csv завершена'
        ))
