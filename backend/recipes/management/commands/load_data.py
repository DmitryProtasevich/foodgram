import csv
from enum import unique
import os

from django.conf import settings
from django.core.management import BaseCommand

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
            if file_name == 'tags':
                unique_field = 'slug'
            else:
                unique_field = 'name'
            existing_values = set(
                model.objects.values_list(unique_field, flat=True).distinct()
            )
            with open(path, encoding='utf-8') as f:
                objects = []
                if file_name == 'ingredients':
                    reader = csv.DictReader(
                        f, fieldnames=['name', 'measurement_unit']
                    )
                else:
                    reader = csv.DictReader(f)
                for row in reader:
                    unique_val = row.get(unique_field)
                    if unique_val in existing_values:
                        continue
                    data = {}
                    for field, value in row.items():
                        if field.endswith('_id') and field != 'id':
                            rel = model._meta.get_field(field[:-3]
                                                        ).related_model
                            data[field[:-3]] = rel.objects.get(pk=value)
                        else:
                            data[field] = value
                    objects.append(model(**data))
                    existing_values.add(unique_val)
                model.objects.bulk_create(objects, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(
                f'Загрузка {file_name}.csv завершена'
            ))
