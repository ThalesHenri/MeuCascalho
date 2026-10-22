from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from main.models import Category, Entry, Goal


class FinanceWebTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ana', password='strong-pass-123')
        self.client.login(username='ana', password='strong-pass-123')

    def test_dashboard_sums_only_current_user_month(self):
        category = Category.objects.create(owner=self.user, name='Salário', kind=Category.Kind.INCOME)
        Entry.objects.create(
            owner=self.user, category=category, kind=Entry.Kind.INCOME,
            description='Pagamento', amount=Decimal('3500.00'), occurred_on=date.today(),
        )
        other = User.objects.create_user(username='bia', password='strong-pass-123')
        Entry.objects.create(
            owner=other, kind=Entry.Kind.INCOME, description='Privado',
            amount=Decimal('9000.00'), occurred_on=date.today(),
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['income'], Decimal('3500.00'))
        self.assertNotContains(response, 'Privado')

    def test_dashboard_filters_by_period_kind_and_category(self):
        today = date.today()
        expense_category = Category.objects.create(
            owner=self.user, name='Moradia', kind=Category.Kind.EXPENSE,
        )
        income_category = Category.objects.create(
            owner=self.user, name='Salário', kind=Category.Kind.INCOME,
        )
        Entry.objects.create(
            owner=self.user, category=expense_category, kind=Entry.Kind.EXPENSE,
            description='Aluguel', amount=Decimal('900.00'), occurred_on=today,
        )
        Entry.objects.create(
            owner=self.user, category=income_category, kind=Entry.Kind.INCOME,
            description='Pagamento', amount=Decimal('3000.00'), occurred_on=today,
        )
        Entry.objects.create(
            owner=self.user, category=expense_category, kind=Entry.Kind.EXPENSE,
            description='Outro mês', amount=Decimal('99.00'),
            occurred_on=today.replace(day=1) - date.resolution,
        )

        response = self.client.get(reverse('dashboard'), {
            'period': today.strftime('%Y-%m'),
            'kind': 'expense',
            'category': expense_category.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['income'], Decimal('0.00'))
        self.assertEqual(response.context['expense'], Decimal('900.00'))
        self.assertEqual(response.context['balance'], Decimal('-900.00'))
        self.assertEqual(response.context['entry_count'], 1)
        self.assertIsNone(response.context['savings_rate'])
        self.assertEqual(response.context['category_chart'][0]['name'], 'Moradia')
        self.assertEqual(len(response.context['chart_data']), 6)
        self.assertContains(response, 'Evolução dos últimos 6 meses')

    def test_create_expense_from_web_form(self):
        response = self.client.post(reverse('entry-create'), {
            'kind': 'expense', 'description': 'Mercado', 'amount': '120.50',
            'occurred_on': date.today().isoformat(), 'note': '',
        })
        self.assertRedirects(response, reverse('dashboard'))
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.amount, Decimal('120.50'))
        self.assertEqual(entry.kind, Entry.Kind.EXPENSE)

    def test_entry_can_deposit_or_withdraw_from_a_goal(self):
        goal = Goal.objects.create(
            owner=self.user, name='Notebook', target_amount=Decimal('3000.00'),
            current_amount=Decimal('500.00'),
        )
        deposit = self.client.post(reverse('entry-create'), {
            'kind': 'expense', 'description': 'Aporte notebook', 'amount': '250.00',
            'occurred_on': date.today().isoformat(), 'goal': goal.pk,
            'goal_action': 'deposit',
        })
        self.assertRedirects(deposit, reverse('dashboard'))
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('750.00'))

        withdrawal = self.client.post(reverse('entry-create'), {
            'kind': 'income', 'description': 'Retirada notebook', 'amount': '125.00',
            'occurred_on': date.today().isoformat(), 'goal': goal.pk,
            'goal_action': 'withdraw',
        })
        self.assertRedirects(withdrawal, reverse('dashboard'))
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('625.00'))

        too_much = self.client.post(reverse('entry-create'), {
            'kind': 'income', 'description': 'Retirada maior que o saldo', 'amount': '700.00',
            'occurred_on': date.today().isoformat(), 'goal': goal.pk,
            'goal_action': 'withdraw',
        })
        self.assertEqual(too_much.status_code, 200)
        self.assertEqual(Entry.objects.filter(owner=self.user).count(), 2)

        deposit_entry = Entry.objects.get(description='Aporte notebook')
        self.client.post(reverse('entry-delete', args=[deposit_entry.pk]))
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('375.00'))

    def test_user_can_register_and_is_logged_in(self):
        self.client.logout()
        response = self.client.post(reverse('register'), {
            'username': 'novo', 'email': 'novo@example.com',
            'password1': 'MudarSenha!234', 'password2': 'MudarSenha!234',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='novo').exists())


class FinanceApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api-user', password='strong-pass-123')
        self.other = User.objects.create_user(username='other-user', password='strong-pass-123')
        self.client = APIClient()

    def test_entries_require_authentication(self):
        response = self.client.get('/api/entries/')
        self.assertEqual(response.status_code, 401)

    def test_api_entry_create_and_month_summary(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/entries/', {
            'kind': 'income', 'description': 'Freelance', 'amount': '800.00',
            'occurred_on': date.today().isoformat(), 'note': '',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        summary = self.client.get('/api/entries/summary/')
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data['income'], Decimal('800.00'))
        self.assertEqual(summary.data['balance'], Decimal('800.00'))

    def test_api_prevents_using_another_users_category(self):
        category = Category.objects.create(owner=self.other, name='Privada', kind=Category.Kind.EXPENSE)
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/entries/', {
            'kind': 'expense', 'description': 'Tentativa', 'amount': '20.00',
            'category': category.pk, 'occurred_on': date.today().isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Entry.objects.exists())

    def test_api_list_is_scoped_to_authenticated_user(self):
        Entry.objects.create(
            owner=self.user, kind=Entry.Kind.EXPENSE, description='Meu lançamento',
            amount=Decimal('10.00'), occurred_on=date.today(),
        )
        Entry.objects.create(
            owner=self.other, kind=Entry.Kind.EXPENSE, description='Lançamento alheio',
            amount=Decimal('99.00'), occurred_on=date.today(),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/entries/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['description'], 'Meu lançamento')

    def test_api_entry_allocation_updates_goal_and_delete_reverses_it(self):
        goal = Goal.objects.create(
            owner=self.user, name='Fundo', target_amount=Decimal('1000.00'),
            current_amount=Decimal('300.00'),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/entries/', {
            'kind': 'expense', 'description': 'Aporte', 'amount': '200.00',
            'occurred_on': date.today().isoformat(), 'goal': goal.pk,
            'goal_action': 'deposit',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('500.00'))
        response = self.client.delete(f"/api/entries/{response.data['id']}/")
        self.assertEqual(response.status_code, 204)
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('300.00'))

    def test_api_rejects_withdrawal_over_goal_balance(self):
        goal = Goal.objects.create(
            owner=self.user, name='Fundo limitado', target_amount=Decimal('500.00'),
            current_amount=Decimal('25.00'),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/entries/', {
            'kind': 'income', 'description': 'Retirada', 'amount': '30.00',
            'occurred_on': date.today().isoformat(), 'goal': goal.pk,
            'goal_action': 'withdraw',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Entry.objects.filter(description='Retirada').exists())
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('25.00'))


class GoalWebTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='meta-user', password='strong-pass-123')
        self.other = User.objects.create_user(username='other-meta-user', password='strong-pass-123')
        self.client.login(username='meta-user', password='strong-pass-123')

    def test_create_goal_and_show_progress(self):
        response = self.client.post(reverse('goal-create'), {
            'name': 'Viagem', 'target_amount': '5000.00', 'current_amount': '1250.00',
            'target_date': '', 'note': 'Férias de verão',
        })
        self.assertRedirects(response, reverse('goal-list'))
        goal = Goal.objects.get(owner=self.user)
        self.assertEqual(goal.progress_percentage, 25)
        self.assertEqual(goal.amount_remaining, Decimal('3750.00'))
        self.assertContains(self.client.get(reverse('goal-list')), 'Viagem')

    def test_goal_list_and_update_are_scoped_to_user(self):
        private_goal = Goal.objects.create(
            owner=self.other, name='Meta privada', target_amount=Decimal('100.00'),
        )
        response = self.client.get(reverse('goal-list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Meta privada')
        response = self.client.get(reverse('goal-update', args=[private_goal.pk]))
        self.assertEqual(response.status_code, 404)

    def test_invalid_goal_amount_is_rejected(self):
        response = self.client.post(reverse('goal-create'), {
            'name': 'Valor inválido', 'target_amount': '0', 'current_amount': '0',
            'target_date': '', 'note': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Goal.objects.filter(owner=self.user).exists())


class GoalApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='goal-api-user', password='strong-pass-123')
        self.other = User.objects.create_user(username='goal-api-other', password='strong-pass-123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_goal_and_calculate_progress(self):
        response = self.client.post('/api/goals/', {
            'name': 'Reserva', 'target_amount': '2000.00', 'current_amount': '500.00',
            'target_date': None, 'note': '',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['progress_percentage'], 25)
        self.assertFalse(response.data['is_completed'])
        self.assertEqual(Goal.objects.get(owner=self.user).owner, self.user)

    def test_goal_api_only_lists_authenticated_users_goals(self):
        Goal.objects.create(owner=self.user, name='Minha reserva', target_amount=Decimal('100.00'))
        Goal.objects.create(owner=self.other, name='Reserva alheia', target_amount=Decimal('100.00'))
        response = self.client.get('/api/goals/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Minha reserva')


class DemoDataCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_command_is_idempotent(self):
        output = StringIO()
        call_command('seed_demo_data', username='demo-test', months=3, stdout=output)
        demo_user = User.objects.get(username='demo-test')
        self.assertTrue(demo_user.check_password('DemoCascalho2026!'))
        self.assertEqual(Category.objects.filter(owner=demo_user).count(), 7)
        self.assertEqual(Goal.objects.filter(owner=demo_user).count(), 2)
        self.assertEqual(Entry.objects.filter(owner=demo_user).count(), 27)

        call_command('seed_demo_data', username='demo-test', months=3, stdout=StringIO())
        self.assertEqual(Entry.objects.filter(owner=demo_user).count(), 27)
        self.assertEqual(Category.objects.filter(owner=demo_user).count(), 7)
        self.assertEqual(Goal.objects.filter(owner=demo_user).count(), 2)

    @override_settings(DEBUG=False)
    def test_seed_command_refuses_non_debug_environment(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo_data', username='not-created')
        self.assertFalse(User.objects.filter(username='not-created').exists())
