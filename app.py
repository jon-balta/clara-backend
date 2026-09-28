"""API local do Clara: acompanhamento de interessados com SQLite."""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import click
from flask import Flask, g, jsonify, redirect, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.exceptions import BadRequest, HTTPException

from domain import EntradaInvalida, validar
from openapi import specification


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=str(Path(app.instance_path) / 'clara.sqlite3'))
    if config:
        app.config.update(config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    # file:// envia origem null. Sem credenciais; aplicação acadêmica local.
    CORS(app, resources={r'/interessados.*': {'origins': '*'}}, supports_credentials=False)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def fechar_db(_erro):
        conexao = g.pop('db', None)
        if conexao is not None:
            conexao.close()

    with app.app_context():
        db().execute('''CREATE TABLE IF NOT EXISTS interessados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL, servico TEXT NOT NULL, origem TEXT NOT NULL,
            etapa TEXT NOT NULL, proximo_retorno TEXT, observacao TEXT NOT NULL,
            criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
        )''')
        db().commit()

    def encontrar(identificador):
        return db().execute('SELECT * FROM interessados WHERE id = ?', (identificador,)).fetchone()

    def entrada():
        if not request.is_json:
            raise EntradaInvalida({'corpo': 'Use Content-Type application/json.'})
        try:
            return validar(request.get_json())
        except BadRequest:
            raise EntradaInvalida({'corpo': 'O JSON enviado não é válido.'}) from None

    def agora():
        return datetime.now(timezone.utc).isoformat(timespec='microseconds')

    @app.errorhandler(EntradaInvalida)
    def erro_validacao(erro):
        return jsonify(mensagem=str(erro), campos=erro.erros), 400

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        return jsonify(mensagem=erro.description), erro.code

    @app.errorhandler(sqlite3.Error)
    def erro_banco(erro):
        app.logger.exception('Falha de persistência')
        return jsonify(mensagem='Não foi possível salvar ou consultar os dados. Tente novamente.'), 500

    @app.get('/')
    def inicio():
        return redirect('/docs/')

    @app.get('/openapi.json')
    def openapi():
        return jsonify(specification())

    app.register_blueprint(get_swaggerui_blueprint('/docs', '/openapi.json', config={'app_name': 'Clara API'}))

    @app.get('/interessados')
    def listar():
        registros = db().execute('SELECT * FROM interessados ORDER BY id DESC').fetchall()
        return jsonify(interessados=[dict(item) for item in registros])

    @app.post('/interessados')
    def cadastrar():
        dados = entrada()
        momento = agora()
        with db():
            cursor = db().execute('''INSERT INTO interessados
                (nome, servico, origem, etapa, proximo_retorno, observacao, criado_em, atualizado_em)
                VALUES (:nome, :servico, :origem, :etapa, :proximo_retorno, :observacao, :criado_em, :atualizado_em)''',
                {**dados, 'criado_em': momento, 'atualizado_em': momento})
        resposta = jsonify(dict(encontrar(cursor.lastrowid)))
        resposta.status_code = 201
        resposta.headers['Location'] = f'/interessados/{cursor.lastrowid}'
        return resposta

    @app.get('/interessados/<int:identificador>')
    def consultar(identificador):
        registro = encontrar(identificador)
        if registro is None:
            return jsonify(mensagem='Interessado não encontrado.'), 404
        return jsonify(dict(registro))

    @app.put('/interessados/<int:identificador>')
    def editar(identificador):
        if encontrar(identificador) is None:
            return jsonify(mensagem='Interessado não encontrado.'), 404
        dados = entrada()
        with db():
            db().execute('''UPDATE interessados SET nome=:nome, servico=:servico,
                origem=:origem, etapa=:etapa, proximo_retorno=:proximo_retorno,
                observacao=:observacao, atualizado_em=:atualizado_em WHERE id=:id''',
                {**dados, 'atualizado_em': agora(), 'id': identificador})
        return jsonify(dict(encontrar(identificador)))

    @app.delete('/interessados/<int:identificador>')
    def excluir(identificador):
        with db():
            cursor = db().execute('DELETE FROM interessados WHERE id=?', (identificador,))
        if cursor.rowcount == 0:
            return jsonify(mensagem='Interessado não encontrado.'), 404
        return '', 204

    @app.cli.command('seed-demo')
    def seed_demo():
        """Insere seis exemplos fictícios somente se o banco estiver vazio."""
        with db():
            # Impede que outro escritor ocupe o banco entre a checagem e a carga.
            db().execute('BEGIN IMMEDIATE')
            if db().execute('SELECT COUNT(*) FROM interessados').fetchone()[0]:
                raise click.ClickException('O banco já possui registros. Nenhum dado foi alterado.')
            exemplos = [
                ('Marina Exemplo', 'Avaliação inicial', 'Instagram', 'novo', -2),
                ('Caio Exemplo', 'Programa de bem-estar', 'Indicação', 'em_contato', 0),
                ('Luiza Exemplo', 'Acompanhamento', 'Busca online', 'avaliacao_marcada', 1),
                ('Rafael Exemplo', 'Avaliação inicial', 'Outro', 'novo', 3),
                ('Bia Exemplo', 'Programa de bem-estar', 'Instagram', 'convertido', None),
                ('Pedro Exemplo', 'Avaliação inicial', 'Indicação', 'encerrado', None),
            ]
            for nome, servico, origem, etapa, dias in exemplos:
                retorno = (date.today() + timedelta(days=dias)).isoformat() if dias is not None else None
                db().execute('''INSERT INTO interessados
                    (nome,servico,origem,etapa,proximo_retorno,observacao,criado_em,atualizado_em)
                    VALUES (?,?,?,?,?,?,?,?)''',
                    (nome, servico, origem, etapa, retorno, 'Cadastro fictício para demonstração acadêmica.', agora(), agora()))
        click.echo('Seis cadastros fictícios adicionados.')

    return app
