from datetime import date
from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, FormView, ListView, TemplateView, UpdateView

from main.forms import CategoryForm, EntryForm, GoalForm, RegistrationForm
from main.models import Category, Entry, Goal
from main.services.goal_allocation_service import (
    delete_entry_with_goal_allocation,
    save_entry_with_goal_allocation,
)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        try:
            selected_period = self.request.GET.get('period', '')
            if selected_period:
                year, month = (int(part) for part in selected_period.split('-', maxsplit=1))
            else:
                year = int(self.request.GET.get('year', today.year))
                month = int(self.request.GET.get('month', today.month))
            if not 1 <= month <= 12 or not 2000 <= year <= 2100:
                raise ValueError
        except (TypeError, ValueError):
            year, month = today.year, today.month

        selected_kind = self.request.GET.get('kind', '')
        if selected_kind not in Entry.Kind.values:
            selected_kind = ''
        selected_category_id = self.request.GET.get('category', '')
        selected_category = None
        if selected_category_id.isdigit():
            selected_category = Category.objects.filter(
                owner=self.request.user, pk=selected_category_id,
            ).first()
        if selected_category is None:
            selected_category_id = ''

        monthly_entries = Entry.objects.filter(
            owner=self.request.user,
            occurred_on__year=year,
            occurred_on__month=month,
        )
        if selected_kind:
            monthly_entries = monthly_entries.filter(kind=selected_kind)
        if selected_category:
            monthly_entries = monthly_entries.filter(category=selected_category)
        entries = monthly_entries.select_related('category')
        totals = entries.aggregate(
            income=Sum('amount', filter=Q(kind=Entry.Kind.INCOME)),
            expense=Sum('amount', filter=Q(kind=Entry.Kind.EXPENSE)),
        )
        income = totals['income'] or Decimal('0.00')
        expense = totals['expense'] or Decimal('0.00')
        savings_rate = ((income - expense) * 100 / income) if income else None
        current_month = date(year, month, 1)
        previous_month = date(year - (month == 1), month - 1 if month > 1 else 12, 1)
        next_month = date(year + (month == 12), month + 1 if month < 12 else 1, 1)

        month_indexes = [year * 12 + month - 1 - offset for offset in range(5, -1, -1)]
        chart_months = [date(index // 12, index % 12 + 1, 1) for index in month_indexes]
        chart_queryset = Entry.objects.filter(
            owner=self.request.user,
            occurred_on__gte=chart_months[0],
            occurred_on__lt=next_month,
        )
        if selected_kind:
            chart_queryset = chart_queryset.filter(kind=selected_kind)
        if selected_category:
            chart_queryset = chart_queryset.filter(category=selected_category)
        monthly_totals = {
            (item['occurred_on__year'], item['occurred_on__month']): item
            for item in chart_queryset.values(
                'occurred_on__year', 'occurred_on__month',
            ).annotate(
                income=Sum('amount', filter=Q(kind=Entry.Kind.INCOME)),
                expense=Sum('amount', filter=Q(kind=Entry.Kind.EXPENSE)),
            )
        }
        chart_data = []
        chart_maximum = Decimal('0.00')
        for chart_month in chart_months:
            values = monthly_totals.get((chart_month.year, chart_month.month), {})
            month_income = values.get('income') or Decimal('0.00')
            month_expense = values.get('expense') or Decimal('0.00')
            chart_maximum = max(chart_maximum, month_income, month_expense)
            chart_data.append({
                'month': chart_month,
                'income': month_income,
                'expense': month_expense,
            })
        for item in chart_data:
            item['income_height'] = int(item['income'] * 100 / chart_maximum) if chart_maximum else 0
            item['expense_height'] = int(item['expense'] * 100 / chart_maximum) if chart_maximum else 0

        distribution_kind = selected_kind or Entry.Kind.EXPENSE
        category_totals = list(
            entries.filter(kind=distribution_kind)
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')[:6]
        )
        category_maximum = max((item['total'] for item in category_totals), default=Decimal('0.00'))
        category_chart = [
            {
                'name': item['category__name'] or 'Sem categoria',
                'total': item['total'],
                'width': int(item['total'] * 100 / category_maximum) if category_maximum else 0,
            }
            for item in category_totals
        ]
        context.update({
            'entries': entries[:12],
            'income': income,
            'expense': expense,
            'balance': income - expense,
            'savings_rate': savings_rate,
            'has_income': income > 0,
            'month_label': current_month,
            'previous_month': previous_month,
            'next_month': next_month,
            'period_value': current_month.strftime('%Y-%m'),
            'selected_kind': selected_kind,
            'selected_category_id': selected_category_id,
            'selected_category': selected_category,
            'category_choices': Category.objects.filter(owner=self.request.user),
            'entry_count': entries.count(),
            'chart_data': chart_data,
            'category_chart': category_chart,
            'distribution_label': 'receitas' if distribution_kind == Entry.Kind.INCOME else 'despesas',
            'categories_count': Category.objects.filter(owner=self.request.user).count(),
        })
        return context


class RegisterView(FormView):
    template_name = 'main/register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class EntryCreateView(LoginRequiredMixin, CreateView):
    model = Entry
    form_class = EntryForm
    template_name = 'main/entry_form.html'
    success_url = reverse_lazy('dashboard')

    def get_initial(self):
        initial = super().get_initial()
        goal_id = self.request.GET.get('goal')
        if goal_id:
            goal = Goal.objects.filter(owner=self.request.user, pk=goal_id).first()
            if goal:
                initial['goal'] = goal
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        try:
            self.object = save_entry_with_goal_allocation(form.instance)
        except ValidationError as error:
            if hasattr(error, 'error_dict'):
                for field, errors in error.error_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                form.add_error(None, error)
            return self.form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())


class EntryUpdateView(LoginRequiredMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = 'main/entry_form.html'
    success_url = reverse_lazy('dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        try:
            self.object = save_entry_with_goal_allocation(form.instance)
        except ValidationError as error:
            if hasattr(error, 'error_dict'):
                for field, errors in error.error_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                form.add_error(None, error)
            return self.form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())

    def get_queryset(self):
        return Entry.objects.filter(owner=self.request.user)


class EntryDeleteView(LoginRequiredMixin, DeleteView):
    model = Entry
    template_name = 'main/entry_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def get_queryset(self):
        return Entry.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        try:
            delete_entry_with_goal_allocation(self.object)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'main/category_form.html'
    success_url = reverse_lazy('dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = 'main/goals.html'
    context_object_name = 'goals'

    def get_queryset(self):
        return Goal.objects.filter(owner=self.request.user)


class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'main/goal_form.html'
    success_url = reverse_lazy('goal-list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class GoalUpdateView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = 'main/goal_form.html'
    success_url = reverse_lazy('goal-list')

    def get_queryset(self):
        return Goal.objects.filter(owner=self.request.user)


class GoalDeleteView(LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = 'main/goal_confirm_delete.html'
    success_url = reverse_lazy('goal-list')

    def get_queryset(self):
        return Goal.objects.filter(owner=self.request.user)
