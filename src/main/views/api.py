from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, Sum
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from main.models import Category, Entry, Goal
from main.serializers import CategorySerializer, EntrySerializer, GoalSerializer
from main.services.goal_allocation_service import delete_entry_with_goal_allocation


class OwnedQuerySetMixin:
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CategoryViewSet(OwnedQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)


class GoalViewSet(OwnedQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = GoalSerializer

    def get_queryset(self):
        return Goal.objects.filter(owner=self.request.user)


class EntryViewSet(OwnedQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = EntrySerializer

    def get_queryset(self):
        queryset = Entry.objects.filter(owner=self.request.user).select_related('category')
        kind = self.request.query_params.get('kind')
        if kind in Entry.Kind.values:
            queryset = queryset.filter(kind=kind)
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        try:
            if year:
                queryset = queryset.filter(occurred_on__year=int(year))
            if month:
                month_number = int(month)
                if 1 <= month_number <= 12:
                    queryset = queryset.filter(occurred_on__month=month_number)
        except ValueError:
            pass
        return queryset

    def perform_destroy(self, instance):
        try:
            delete_entry_with_goal_allocation(instance)
        except DjangoValidationError as error:
            raise ValidationError(getattr(error, 'message_dict', error.messages)) from error

    @action(detail=False, methods=['get'])
    def summary(self, request):
        today = date.today()
        year = request.query_params.get('year', today.year)
        month = request.query_params.get('month', today.month)
        try:
            year, month = int(year), int(month)
            if month < 1 or month > 12:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'detail': 'Informe mês (1–12) e ano válidos.'}, status=400)
        entries = Entry.objects.filter(owner=request.user, occurred_on__year=year, occurred_on__month=month)
        totals = entries.aggregate(
            income=Sum('amount', filter=Q(kind=Entry.Kind.INCOME)),
            expense=Sum('amount', filter=Q(kind=Entry.Kind.EXPENSE)),
        )
        income = totals['income'] or Decimal('0.00')
        expense = totals['expense'] or Decimal('0.00')
        return Response({
            'year': year,
            'month': month,
            'income': income,
            'expense': expense,
            'balance': income - expense,
        })
