from django.conf import settings
from django.db import models


class Category(models.Model):
    class Kind(models.TextChoices):
        INCOME = 'income', 'Receita'
        EXPENSE = 'expense', 'Despesa'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField('nome', max_length=60)
    kind = models.CharField('tipo', max_length=10, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['kind', 'name']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name', 'kind'], name='unique_owner_category_name_kind'),
        ]
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'

    def __str__(self):
        return f'{self.name} ({self.get_kind_display()})'
