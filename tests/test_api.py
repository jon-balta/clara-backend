"""Testes do contrato e das regras com banco temporário, sem dados reais."""
import pytest
from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'teste.sqlite3')})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cadastro():
    return {'nome': 'Ana Exemplo', 'servico': 'Avaliação inicial', 'origem': 'Indicação',
            'etapa': 'novo', 'proximo_retorno': '2026-09-26', 'observacao': 'Retornar à tarde.'}


def test_ciclo_completo_e_persistencia(client, app, cadastro):
    assert client.get('/interessados').json == {'interessados': []}
    criada = client.post('/interessados', json=cadastro)
    assert criada.status_code == 201
    caminho = criada.headers['Location']
    assert client.get(caminho).json['nome'] == cadastro['nome']
    # Outra instância lê o mesmo arquivo; prova persistência fora da aplicação original.
    outra = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert len(outra.get('/interessados').json['interessados']) == 1
    alterada = outra.put(caminho, json={**cadastro, 'etapa': 'convertido', 'proximo_retorno': None})
    assert alterada.status_code == 200
    assert alterada.json['etapa'] == 'convertido'
    assert alterada.json['criado_em'] == criada.json['criado_em']
    assert alterada.json['atualizado_em'] != criada.json['atualizado_em']
    assert client.delete(caminho).status_code == 204
    assert client.get(caminho).status_code == 404
    assert client.get('/interessados').json['interessados'] == []


@pytest.mark.parametrize('campo,valor', [
    ('nome', ' '), ('nome', 99), ('nome', 'a'*101), ('servico', ''),
    ('origem', 'desconhecida'), ('etapa', 'inexistente'), ('etapa', []),
    ('proximo_retorno', None), ('proximo_retorno', '2026-02-30'),
    ('proximo_retorno', '20260926'), ('proximo_retorno', 123),
    ('observacao', 'x'*1001), ('observacao', None),
])
def test_entrada_invalida_nao_persiste(client, cadastro, campo, valor):
    resposta = client.post('/interessados', json={**cadastro, campo: valor})
    assert resposta.status_code == 400
    assert campo in resposta.json['campos']
    assert client.get('/interessados').json['interessados'] == []


def test_edicao_invalida_preserva_registro(client, cadastro):
    criado = client.post('/interessados', json=cadastro)
    caminho = criado.headers['Location']
    assert client.put(caminho, json={**cadastro, 'nome': ''}).status_code == 400
    assert client.get(caminho).json == criado.json


@pytest.mark.parametrize('metodo', ['get', 'put', 'delete'])
def test_id_inexistente(client, metodo):
    resposta = getattr(client, metodo)('/interessados/999')
    assert resposta.status_code == 404
    assert resposta.json['mensagem']


def test_json_invalido_e_campos_extras(client, cadastro):
    assert client.post('/interessados', data='{}').status_code == 400
    assert client.post('/interessados', data='{', content_type='application/json').status_code == 400
    assert client.post('/interessados', json=[]).status_code == 400
    assert client.post('/interessados', json={**cadastro, 'id': 1}).status_code == 400


def test_nomes_repetidos_e_texto_literal(client, cadastro):
    dados = {**cadastro, 'nome': "D'Ávila <script>exemplo</script>"}
    primeiro = client.post('/interessados', json=dados).json
    segundo = client.post('/interessados', json=dados).json
    assert primeiro['id'] != segundo['id']
    assert primeiro['nome'] == dados['nome']


def test_cors_file_e_preflight(client):
    resposta = client.get('/interessados', headers={'Origin': 'null'})
    assert resposta.headers['Access-Control-Allow-Origin'] in ('null', '*')
    preflight = client.options('/interessados/1', headers={'Origin': 'null',
        'Access-Control-Request-Method': 'PUT', 'Access-Control-Request-Headers': 'content-type'})
    assert 'PUT' in preflight.headers['Access-Control-Allow-Methods']
    assert 'content-type' in preflight.headers['Access-Control-Allow-Headers'].lower()


def test_documentacao_local(client):
    assert client.get('/docs/').status_code == 200
    assert client.get('/docs/swagger-ui-bundle.js').status_code == 200
    spec = client.get('/openapi.json').json
    assert spec['openapi'] == '3.0.3'
    assert set(spec['paths']['/interessados']) == {'get', 'post'}
    assert set(spec['paths']['/interessados/{identificador}']) == {'get', 'put', 'delete', 'parameters'}


def test_seed_nao_duplica_ou_sobrescreve(app, client):
    runner = app.test_cli_runner()
    assert runner.invoke(args=['seed-demo']).exit_code == 0
    registros = client.get('/interessados').json
    assert len(registros['interessados']) == 6
    assert runner.invoke(args=['seed-demo']).exit_code != 0
    assert client.get('/interessados').json == registros
