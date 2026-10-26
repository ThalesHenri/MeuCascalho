from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Goal(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField('nome da meta', max_length=100)
    target_amount = models.DecimalField(
        'valor desejado', max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    current_amount = models.DecimalField(
        'valor guardado', max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    target_date = models.DateField('data desejada', null=True, blank=True)
    note = models.CharField('observação', max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['target_date', 'name']
        constraints = [
            models.CheckConstraint(check=Q(target_amount__gt=0), name='goal_target_must_be_positive'),
            models.CheckConstraint(check=Q(current_amount__gte=0), name='goal_current_must_be_nonnegative'),
        ]
        verbose_name = 'meta financeira'
        verbose_name_plural = 'metas financeiras'

    @property
    def progress_percentage(self):
        if not self.target_amount:
            return 0
        return min(int(self.current_amount * 100 / self.target_amount), 100)

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount

    @property
    def amount_remaining(self):
        return max(self.target_amount - self.current_amount, 0)

    def __str__(self):
        return self.name
