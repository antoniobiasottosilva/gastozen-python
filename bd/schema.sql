-- GastoZen: esquema do banco (PostgreSQL)
-- Uso: psql -U postgres -d gastozen -f schema.sql

DROP TABLE IF EXISTS transacoes;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
  id            SERIAL PRIMARY KEY,
  nome          VARCHAR(100) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  senha_hash    VARCHAR(255) NOT NULL,
  data_criacao  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE categorias (
  id            SERIAL PRIMARY KEY,
  usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  nome          VARCHAR(60) NOT NULL,
  tipo          VARCHAR(10) NOT NULL CHECK (tipo IN ('receita', 'despesa')),
  limite_mensal NUMERIC(12,2) CHECK (limite_mensal IS NULL OR limite_mensal >= 0),
  UNIQUE (usuario_id, nome)
);

CREATE TABLE transacoes (
  id            SERIAL PRIMARY KEY,
  usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  categoria_id  INTEGER NOT NULL REFERENCES categorias(id) ON DELETE RESTRICT,
  descricao     VARCHAR(150) NOT NULL,
  valor         NUMERIC(12,2) NOT NULL CHECK (valor > 0),
  data          DATE NOT NULL DEFAULT CURRENT_DATE,
  tipo          VARCHAR(10) NOT NULL CHECK (tipo IN ('receita', 'despesa'))
);

CREATE INDEX idx_transacoes_usuario_data ON transacoes (usuario_id, data);