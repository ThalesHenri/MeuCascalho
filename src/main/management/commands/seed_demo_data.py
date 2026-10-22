import random
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from main.models import Category, Entry, Goal
from main.services.goal_allocation_service import save_entry_with_goal_allocation


class Command(BaseCommand):
    help = 'Cria dados demonstrativos para testar o Meu Cascalho localmente.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo', help='Usuário que receberá os dados (padrão: demo).')
        parser.add_argument(
            '--password', default='DemoCascalho2026!',
            help='Senha usada somente se a conta demo precisar ser criada.',
        )
        parser.add_argument(
            '--months', type=int, default=6,
            help='Quantidade de meses de lançamentos a gerar (de 1 a 24; padrão: 6).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Por segurança, este comando só pode ser executado com DEBUG=True.')

        months_count = options['months']
        if not 1 <= months_count <= 24:
            raise CommandError('--months deve ser um número entre 1 e 24.')

        user_model = get_user_model()
        username = options['username'].strip()
        if not username:
            raise CommandError('--username não pode ficar vazio.')
        user, user_created = user_model.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.test'},
        )
        if user_created:
            user.set_password(options['password'])
            user.save(update_fields=['password'])

        categories = self._create_categories(user)
        self._create_goals(user)
        created_entries = 0
        updated_entries = 0
        today = date.today()
        current_month_index = today.year * 12 + today.month - 1

        for offset in range(months_count - 1, -1, -1):
            month_index = current_month_index - offset
            year, month = divmod(month_index, 12)
            month += 1
            days_in_month = monthrange(year, month)[1]
            rng = random.Random(f'meu-cascalho-demo-{username}-{year}-{month}')
            entries = self._month_entries(year, month, days_in_month, rng, categories)

            for description, kind, amount, category, day in entries:
                entry, created = Entry.objects.get_or_create(
                    owner=user,
                    description=description,
                    occurred_on=date(year, month, day),
                    defaults={
                        'kind': kind,
                        'amount': amount,
                        'category': category,
                        'note': 'Dado demonstrativo',
                    },
                )
                entry.kind = kind
                entry.amount = amount
                entry.category = category
                entry.note = 'Dado demonstrativo'
                entry.goal = None
                entry.goal_action = ''
                # Go through the same balance service as real goal-linked entries,
                # so rerunning the command safely reverses any previous allocation.
                save_entry_with_goal_allocation(entry)
                if created:
                    created_entries += 1
                else:
                    updated_entries += 1

        if user_created:
            self.stdout.write(self.style.WARNING(
                f'Conta criada: {username} / {options["password"]} (somente desenvolvimento).'
            ))
        self.stdout.write(self.style.SUCCESS(
            f'Dados prontos para {username}: {len(categories)} categorias, '
            f'{Goal.objects.filter(owner=user).count()} metas, '
            f'{created_entries} lançamentos novos e {updated_entries} atualizados.'
        ))
        self.stdout.write('Acesse o dashboard para conferir KPIs, filtros e gráficos.')

    def _create_categories(self, user):
        definitions = [
            ('Salário', Category.Kind.INCOME),
            ('Freelance', Category.Kind.INCOME),
            ('Moradia', Category.Kind.EXPENSE),
            ('Alimentação', Category.Kind.EXPENSE),
            ('Transporte', Category.Kind.EXPENSE),
            ('Saúde', Category.Kind.EXPENSE),
            ('Lazer', Category.Kind.EXPENSE),
        ]
        categories = {}
        for name, kind in definitions:
            category, _ = Category.objects.get_or_create(owner=user, name=name, kind=kind)
            categories[name] = category
        return categories

    def _create_goals(self, user):
        next_year = date.today().year + 1
        definitions = [
            ('Reserva de emergência', Decimal('20000.00'), Decimal('6800.00'), date(next_year, 12, 31)),
            ('Viagem de férias', Decimal('8500.00'), Decimal('3250.00'), date(next_year, 7, 1)),
        ]
        for name, target, saved, target_date in definitions:
            Goal.objects.get_or_create(
                owner=user,
                name=name,
                defaults={
                    'target_amount': target,
                    'current_amount': saved,
                    'target_date': target_date,
                    'note': 'Meta demonstrativa',
                },
            )

    def _month_entries(self, year, month, days_in_month, rng, categories):
        salary = Decimal('5200.00') + Decimal((month % 3) * 100)
        freelance = Decimal(rng.randrange(35000, 90100, 100)) / 100
        entries = [
            (f'[DEMO] Salário {year}-{month:02d}', Entry.Kind.INCOME, salary, categories['Salário'], min(5, days_in_month)),
            (f'[DEMO] Projeto freelance {year}-{month:02d}', Entry.Kind.INCOME, freelance, categories['Freelance'], min(20, days_in_month)),
        ]
        expenses = [
            ('Aluguel', 'Moradia', 145000, 165000, 3),
            ('Supermercado', 'Alimentação', 35000, 68000, 7),
            ('Conta de luz e água', 'Moradia', 12000, 26000, 10),
            ('Transporte', 'Transporte', 8000, 19000, 13),
            ('Farmácia', 'Saúde', 5000, 22000, 16),
            ('Restaurante', 'Alimentação', 7000, 18000, 21),
            ('Cinema e lazer', 'Lazer', 5000, 16000, 25),
        ]
        for label, category_name, minimum, maximum, day in expenses:
            amount = Decimal(rng.randrange(minimum, maximum + 1, 100)) / 100
            description = f'[DEMO] {label} {year}-{month:02d}'
            entries.append((
                description,
                Entry.Kind.EXPENSE,
                amount,
                categories[category_name],
                min(day, days_in_month),
            ))
        return entries
