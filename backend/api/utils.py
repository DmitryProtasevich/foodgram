def generate_shoping_list(ingredients_queryset):
    """Генерирует текст для списка покупок."""
    lines = ['Список покупок:\n']
    for item in ingredients_queryset:
        lines.append(
            f"{item['ingredient__name']} "
            f"{item['ingredient__measurement_unit']} - "
            f"{item['total_amount']}\n"
        )
    return ''.join(lines)
