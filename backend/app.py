"""GastoZen - API em Python (Flask) + PostgreSQL."""
import os
import datetime
from functools import wraps

import jwt
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE, "..", "frontend"), static_url_path="")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET = os.getenv("JWT_SECRET", "dev-secret")


# ---------- Conexão com o banco ----------
def executar(sql, params=(), um=False):
    """Abre conexão, executa o SQL e devolve as linhas (dicionários)."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        cur = conn.execute(sql, params)
        if cur.description is None:
            return None
        return cur.fetchone() if um else cur.fetchall()


def numero(valor):
    """Converte texto vazio em None e o resto em float."""
    if valor in (None, ""):
        return None
    return float(valor)


# ---------- Autenticação (JWT) ----------
def gerar_token(user_id):
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    return jwt.encode({"id": user_id, "exp": exp}, SECRET, algorithm="HS256")


def login_obrigatorio(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            request.user_id = jwt.decode(token, SECRET, algorithms=["HS256"])["id"]
        except Exception:
            return jsonify(erro="Sessão expirada. Entre novamente."), 401
        return f(*args, **kwargs)
    return wrapper


@app.errorhandler(Exception)
def erro_geral(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception(e)
    return jsonify(erro="Erro no servidor."), 500


# ---------- Rota inicial ----------
@app.get("/")
def inicio():
    return app.send_static_file("index.html")


@app.get("/api/status")
def status():
    return jsonify(status="ok", app="GastoZen")


# ---------- Cadastro e login ----------
@app.post("/api/cadastro")
def cadastro():
    d = request.get_json(silent=True) or {}
    nome, email, senha = d.get("nome"), d.get("email"), d.get("senha") or ""
    if not nome or not email or len(senha) < 6:
        return jsonify(erro="Preencha nome, e-mail e senha (mínimo 6 caracteres)."), 400
    try:
        u = executar(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (%s,%s,%s) RETURNING id, nome",
            (nome, email.lower(), generate_password_hash(senha)), um=True)
    except psycopg.errors.UniqueViolation:
        return jsonify(erro="Este e-mail já está cadastrado."), 409
    # categorias iniciais para o usuário já poder usar o app
    executar(
        """INSERT INTO categorias (usuario_id, nome, tipo, limite_mensal) VALUES
           (%s,'Alimentação','despesa',600), (%s,'Transporte','despesa',200),
           (%s,'Lazer','despesa',150), (%s,'Mesada/Bolsa','receita',NULL)""",
        (u["id"],) * 4)
    return jsonify(token=gerar_token(u["id"]), nome=u["nome"])


@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    u = executar("SELECT * FROM usuarios WHERE email=%s", ((d.get("email") or "").lower(),), um=True)
    if not u or not check_password_hash(u["senha_hash"], d.get("senha") or ""):
        return jsonify(erro="E-mail ou senha incorretos."), 401
    return jsonify(token=gerar_token(u["id"]), nome=u["nome"])


# ---------- CRUD de categorias ----------
CAMPOS_CAT = "id, usuario_id, nome, tipo, limite_mensal::float8 AS limite_mensal"


@app.get("/api/categorias")
@login_obrigatorio
def listar_categorias():
    return jsonify(executar(f"SELECT {CAMPOS_CAT} FROM categorias WHERE usuario_id=%s ORDER BY nome",
                            (request.user_id,)))


@app.post("/api/categorias")
@login_obrigatorio
def criar_categoria():
    d = request.get_json(silent=True) or {}
    if not d.get("nome") or d.get("tipo") not in ("receita", "despesa"):
        return jsonify(erro="Informe nome e tipo da categoria."), 400
    try:
        c = executar(f"INSERT INTO categorias (usuario_id, nome, tipo, limite_mensal) "
                     f"VALUES (%s,%s,%s,%s) RETURNING {CAMPOS_CAT}",
                     (request.user_id, d["nome"], d["tipo"], numero(d.get("limite_mensal"))), um=True)
    except psycopg.errors.UniqueViolation:
        return jsonify(erro="Você já tem uma categoria com esse nome."), 409
    return jsonify(c), 201


@app.put("/api/categorias/<int:cid>")
@login_obrigatorio
def atualizar_categoria(cid):
    d = request.get_json(silent=True) or {}
    c = executar(f"UPDATE categorias SET nome=%s, tipo=%s, limite_mensal=%s "
                 f"WHERE id=%s AND usuario_id=%s RETURNING {CAMPOS_CAT}",
                 (d.get("nome"), d.get("tipo"), numero(d.get("limite_mensal")), cid, request.user_id), um=True)
    return jsonify(c) if c else (jsonify(erro="Categoria não encontrada."), 404)


@app.delete("/api/categorias/<int:cid>")
@login_obrigatorio
def excluir_categoria(cid):
    try:
        executar("DELETE FROM categorias WHERE id=%s AND usuario_id=%s", (cid, request.user_id))
    except psycopg.errors.ForeignKeyViolation:
        return jsonify(erro="Esta categoria tem transações. Exclua-as antes."), 409
    return jsonify(ok=True)


# ---------- CRUD de transações ----------
def mes_da_requisicao():
    return request.args.get("mes") or datetime.date.today().strftime("%Y-%m")


@app.get("/api/transacoes")
@login_obrigatorio
def listar_transacoes():
    return jsonify(executar(
        """SELECT t.id, t.descricao, t.valor::float8 AS valor, t.tipo,
                  to_char(t.data,'YYYY-MM-DD') AS data, t.categoria_id, c.nome AS categoria
           FROM transacoes t JOIN categorias c ON c.id = t.categoria_id
           WHERE t.usuario_id=%s AND to_char(t.data,'YYYY-MM')=%s
           ORDER BY t.data DESC, t.id DESC""",
        (request.user_id, mes_da_requisicao())))


def categoria_do_usuario(cat_id):
    return executar("SELECT tipo FROM categorias WHERE id=%s AND usuario_id=%s",
                    (cat_id, request.user_id), um=True)


@app.post("/api/transacoes")
@login_obrigatorio
def criar_transacao():
    d = request.get_json(silent=True) or {}
    try:
        valor = float(d.get("valor"))
    except (TypeError, ValueError):
        valor = 0
    if not d.get("descricao") or valor <= 0 or not d.get("categoria_id"):
        return jsonify(erro="Informe descrição, valor maior que zero e categoria."), 400
    cat = categoria_do_usuario(d["categoria_id"])
    if not cat:
        return jsonify(erro="Categoria inválida."), 400
    t = executar(
        """INSERT INTO transacoes (usuario_id, categoria_id, descricao, valor, data, tipo)
           VALUES (%s,%s,%s,%s,COALESCE(%s::date, CURRENT_DATE),%s) RETURNING id""",
        (request.user_id, d["categoria_id"], d["descricao"], valor, d.get("data") or None, cat["tipo"]), um=True)
    return jsonify(t), 201


@app.put("/api/transacoes/<int:tid>")
@login_obrigatorio
def atualizar_transacao(tid):
    d = request.get_json(silent=True) or {}
    cat = categoria_do_usuario(d.get("categoria_id"))
    if not cat:
        return jsonify(erro="Categoria inválida."), 400
    t = executar(
        """UPDATE transacoes SET descricao=%s, valor=%s, data=%s::date, categoria_id=%s, tipo=%s
           WHERE id=%s AND usuario_id=%s RETURNING id""",
        (d.get("descricao"), numero(d.get("valor")), d.get("data"), d["categoria_id"], cat["tipo"],
         tid, request.user_id), um=True)
    return jsonify(t) if t else (jsonify(erro="Transação não encontrada."), 404)


@app.delete("/api/transacoes/<int:tid>")
@login_obrigatorio
def excluir_transacao(tid):
    executar("DELETE FROM transacoes WHERE id=%s AND usuario_id=%s", (tid, request.user_id))
    return jsonify(ok=True)


# ---------- Resumo do mês ----------
@app.get("/api/dashboard")
@login_obrigatorio
def dashboard():
    mes = mes_da_requisicao()
    tot = executar(
        """SELECT COALESCE(SUM(valor) FILTER (WHERE tipo='receita'),0)::float8 AS receitas,
                  COALESCE(SUM(valor) FILTER (WHERE tipo='despesa'),0)::float8 AS despesas
           FROM transacoes WHERE usuario_id=%s AND to_char(data,'YYYY-MM')=%s""",
        (request.user_id, mes), um=True)
    cats = executar(
        """SELECT c.id, c.nome, c.limite_mensal::float8 AS limite_mensal,
                  COALESCE(SUM(t.valor),0)::float8 AS gasto
           FROM categorias c
           LEFT JOIN transacoes t ON t.categoria_id=c.id AND to_char(t.data,'YYYY-MM')=%s
           WHERE c.usuario_id=%s AND c.tipo='despesa'
           GROUP BY c.id ORDER BY gasto DESC""",
        (mes, request.user_id))
    for c in cats:
        c["estourou"] = c["limite_mensal"] is not None and c["gasto"] > c["limite_mensal"]
    return jsonify(receitas=tot["receitas"], despesas=tot["despesas"],
                   saldo=tot["receitas"] - tot["despesas"], categorias=cats)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
