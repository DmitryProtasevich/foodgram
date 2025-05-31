import csv
import os

from django.core.management import BaseCommand
from django.conf import settings

from recipes.models import Ingredient, Tag

CSV_MODEL_MAP = {
    'tags': Tag,
    'ingredients': Ingredient,
}


class Command(BaseCommand):
    """Класс загрузки тестовой базы данных."""

    def handle(self, *args, **options):
        for file_name, model in CSV_MODEL_MAP.items():
            path = os.path.join(settings.CSV_FILES_DIR, f'{file_name}.csv')
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(
                    f'Файл {file_name}.csv не найден.'
                ))
                return
            self.stdout.write(f'Началась загрузка файла: {file_name}.csv')
            with open(path, encoding='utf-8') as f:
                objects = []
                if file_name == 'ingredients':
                    reader = csv.DictReader(
                        f, fieldnames=['name', 'measurement_unit']
                    )
                else:
                    reader = csv.DictReader(f)
                for row in reader:
                    data = {}
                    for field, value in row.items():
                        if field.endswith('_id') and field != 'id':
                            rel = model._meta.get_field(field[:-3]
                                                        ).related_model
                            data[field[:-3]] = rel.objects.get(pk=value)
                        else:
                            data[field] = value
                    objects.append(model(**data))
                model.objects.bulk_create(objects, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(
                f'Загрузка {file_name}.csv завершена'
            ))
