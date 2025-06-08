import json
import os

from django.conf import settings
from django.core.management import BaseCommand

from recipes.models import Ingredient, Tag

MODEL_MAP = {
    'tags': Tag,
    'ingredients': Ingredient,
}


class Command(BaseCommand):
    """Класс загрузки тестовой базы данных."""

    def handle(self, *args, **options):
        for file_name, model in MODEL_MAP.items():
            path = os.path.join(settings.JSON_FILES_DIR, f'{file_name}.json')
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(
                    f'Файл {file_name}.json не найден.'
                ))
                return
            self.stdout.write(f'Началась загрузка файла: {file_name}.json')
            objects = []
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
                for row in data:
                    objects.append(model(**row))
            model.objects.bulk_create(objects, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(
                f'Загрузка {file_name}.json завершена'
            ))
