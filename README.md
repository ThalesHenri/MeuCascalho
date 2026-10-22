# Meu Cascalho

Organizador individual de finanças com Django, interface web inicial e API REST preparada para um cliente Flutter.

## Requisitos e execução local

- Python 3.10 ou superior.
- Ambiente virtual na raiz do repositório.

Com o ambiente virtual ativado, instale as dependências e inicialize o banco:

```sh
pip install -r requirements.txt
python src/manage.py migrate
python src/manage.py runserver
```

Acesse `http://127.0.0.1:8000/`; crie uma conta pela tela inicial de login. Para administrar usuários e dados, crie um administrador com `python src/manage.py createsuperuser` e acesse `/admin/`.

### Dados demonstrativos

Com `DEBUG=True`, gere um conjunto repetível de dados para testar os gráficos:

```sh
python src/manage.py seed_demo_data
```

O comando cria a conta `demo` com senha `DemoCascalho2026!` se ela ainda não existir, sete categorias, duas metas e lançamentos dos últimos seis meses. A execução é idempotente: atualiza os lançamentos de demonstração sem duplicá-los e não apaga dados. Personalize com `--username nome --months 12`; o comando se recusa a executar quando `DEBUG=False`. Use a conta/senha padrão somente no ambiente local.

## MVP implementado

- Cadastro e login de usuário.
- Lançamentos pessoais de receita e despesa com descrição, valor positivo, data, categoria opcional e observação.
- Edição e exclusão de lançamentos; categorias individuais por tipo.
- Metas financeiras pessoais com valor desejado, valor já guardado, prazo opcional e progresso automático; criação, edição e exclusão pela interface.
- Em Novo lançamento, vincule uma meta para guardar (despesa) ou retirar (receita); o saldo da meta é atualizado junto e retiradas acima do disponível são bloqueadas.
- Resumo mensal de receitas, despesas e saldo, com navegação entre meses.
- Dashboard com filtros por período, tipo e categoria, KPIs de saldo e taxa poupada, gráfico semestral de receitas/despesas e distribuição por categoria.
- API REST autenticada por JWT; os dados são sempre limitados ao usuário autenticado.
- SQLite para desenvolvimento.

## API

- `POST /api/token/` recebe `username` e `password` e retorna tokens `access` e `refresh`.
- `POST /api/token/refresh/` renova o token de acesso.
- `/api/entries/` lista, cria, atualiza e remove lançamentos. Aceita filtros `kind`, `year` e `month`; os campos opcionais `goal` e `goal_action` atualizam o saldo da meta.
- `GET /api/entries/summary/?year=2026&month=9` retorna receitas, despesas e saldo do mês.
- `/api/categories/` lista, cria, atualiza e remove categorias.
- `/api/goals/` lista, cria, atualiza e remove metas; a resposta inclui `progress_percentage` e `is_completed`.

Para usar os recursos protegidos, envie `Authorization: Bearer <access>`.

## Verificações

```sh
python src/manage.py check
python src/manage.py test
```

Antes de publicar, defina `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` e `DJANGO_DEBUG=false`; o valor padrão da chave é apenas para desenvolvimento.