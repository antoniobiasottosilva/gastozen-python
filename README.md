# GastoZen

Sistema web de controle de gastos para estudantes. Projeto Integrador (Recuperação do 1º Momento, 3º Trimestre).

**Autor:** Antonio Carlos Biasotto da Silva · 3º C · https://github.com/antoniobiasottosilva

## O que o sistema faz
Cadastro e login, registro de receitas e despesas, categorias com limite mensal e resumo do mês com alerta quando o limite é ultrapassado.

## Tecnologias
- **Front-end:** HTML, CSS e JavaScript (pasta `frontend`)
- **Back-end:** Python + Flask, API REST com JWT (pasta `backend`)
- **Banco de dados:** PostgreSQL (pasta `bd`)

## Estrutura
```
bd/         der.png (diagrama) e schema.sql (criação das tabelas)
backend/    app.py e requirements.txt
frontend/   index.html, style.css e app.js
```

## Como rodar
Requisitos: Python 3.10+ e PostgreSQL.

1. Crie o banco e as tabelas:
   ```
   psql -U postgres -c "CREATE DATABASE gastozen;"
   psql -U postgres -d gastozen -f bd/schema.sql
   ```
2. Configure e rode o servidor:
   ```
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env     (edite a senha do PostgreSQL no .env)
   python app.py
   ```
3. Abra http://localhost:5000

## Documentação das rotas (Endpoints)
As rotas marcadas com 🔒 precisam do cabeçalho `Authorization: Bearer <token>` (o token vem do login).

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/status` | Verifica se o servidor está no ar |
| POST | `/api/cadastro` | Cria conta |
| POST | `/api/login` | Entra e recebe o token |
| GET 🔒 | `/api/transacoes?mes=2026-11` | Lista as transações do mês |
| POST 🔒 | `/api/transacoes` | Cadastra transação |
| PUT 🔒 | `/api/transacoes/<id>` | Atualiza transação |
| DELETE 🔒 | `/api/transacoes/<id>` | Exclui transação |
| GET 🔒 | `/api/categorias` | Lista categorias |
| POST 🔒 | `/api/categorias` | Cria categoria |
| PUT 🔒 | `/api/categorias/<id>` | Atualiza categoria |
| DELETE 🔒 | `/api/categorias/<id>` | Exclui categoria |
| GET 🔒 | `/api/dashboard?mes=2026-11` | Saldo, receitas, despesas e gasto por categoria |

### Exemplos de JSON
**POST /api/cadastro**
```json
{ "nome": "Antonio", "email": "antonio@email.com", "senha": "123456" }
```
Resposta: `{ "token": "eyJ...", "nome": "Antonio" }`

**POST /api/login**
```json
{ "email": "antonio@email.com", "senha": "123456" }
```

**POST /api/transacoes** (resposta 201: `{ "id": 1 }`)
```json
{ "descricao": "Lanche", "valor": 15.5, "data": "2026-11-18", "categoria_id": 1 }
```

**GET /api/transacoes** (resposta)
```json
[{ "id": 1, "descricao": "Lanche", "valor": 15.5, "tipo": "despesa",
   "data": "2026-11-18", "categoria_id": 1, "categoria": "Alimentação" }]
```

**PUT /api/transacoes/1**
```json
{ "descricao": "Lanche da tarde", "valor": 18, "data": "2026-11-18", "categoria_id": 1 }
```

**DELETE /api/transacoes/1** → `{ "ok": true }`
