"""Contrato OpenAPI servido localmente e usado pelo Swagger UI."""
from domain import ETAPAS, ORIGENS


def specification():
    entrada = {
        'type': 'object', 'additionalProperties': False,
        'required': ['nome', 'servico', 'origem', 'etapa'],
        'properties': {
            'nome': {'type': 'string', 'minLength': 2, 'maxLength': 100, 'example': 'Ana Exemplo'},
            'servico': {'type': 'string', 'minLength': 2, 'maxLength': 80, 'example': 'Avaliação inicial'},
            'origem': {'type': 'string', 'enum': list(ORIGENS), 'example': 'Instagram'},
            'etapa': {'type': 'string', 'enum': list(ETAPAS), 'example': 'novo'},
            'proximo_retorno': {'type': 'string', 'format': 'date', 'nullable': True,
                'description': 'Obrigatório nas etapas novo, em_contato e avaliacao_marcada. Datas passadas são permitidas para sinalizar pendências.', 'example': '2026-09-26'},
            'observacao': {'type': 'string', 'maxLength': 1000, 'default': '', 'example': 'Prefere retorno à tarde.'},
        },
    }
    saida = {'type': 'object', 'properties': {**entrada['properties'],
        'id': {'type': 'integer', 'example': 1},
        'criado_em': {'type': 'string', 'format': 'date-time'},
        'atualizado_em': {'type': 'string', 'format': 'date-time'}}}
    def response(descricao, schema=None):
        resultado = {'description': descricao}
        if schema:
            resultado['content'] = {'application/json': {'schema': schema}}
        return resultado
    ref = lambda nome: {'$ref': f'#/components/schemas/{nome}'}
    erros = {'400': response('Entrada inválida', ref('Erro')),
             '404': response('Interessado não encontrado', ref('Erro')),
             '500': response('Falha de persistência', ref('Erro'))}
    corpo = {'required': True, 'content': {'application/json': {'schema': ref('Cadastro')}}}
    def op(resumo, respostas, body=False):
        obj = {'tags': ['Interessados'], 'summary': resumo, 'responses': respostas}
        if body:
            obj['requestBody'] = corpo
        return obj
    return {
        'openapi': '3.0.3', 'info': {'title': 'Clara — API de acompanhamento', 'version': '1.0.0',
            'description': 'MVP acadêmico com dados fictícios. PUT substitui os campos editáveis; nomes repetidos são permitidos. Etapa de avaliação não reserva horário em uma agenda.'},
        'servers': [{'url': '/', 'description': 'API local'}],
        'paths': {
            '/interessados': {
                'get': op('Listar interessados', {'200': response('Lista, inclusive vazia', {'type': 'object', 'properties': {'interessados': {'type': 'array', 'items': ref('Interessado')}}}), '500': erros['500']}),
                'post': op('Cadastrar interessado', {'201': response('Cadastro criado', ref('Interessado')), '400': erros['400'], '500': erros['500']}, True),
            },
            '/interessados/{identificador}': {
                'parameters': [{'name': 'identificador', 'in': 'path', 'required': True, 'schema': {'type': 'integer', 'minimum': 1}, 'description': 'ID retornado no cadastro ou listagem.'}],
                'get': op('Consultar detalhes', {'200': response('Interessado', ref('Interessado')), '404': erros['404'], '500': erros['500']}),
                'put': op('Editar acompanhamento', {'200': response('Cadastro atualizado', ref('Interessado')), **erros}, True),
                'delete': op('Excluir interessado', {'204': response('Excluído, sem corpo'), '404': erros['404'], '500': erros['500']}),
            },
        },
        'components': {'schemas': {'Cadastro': entrada, 'Interessado': saida, 'Erro': {
            'type': 'object', 'properties': {'mensagem': {'type': 'string'}, 'campos': {'type': 'object', 'additionalProperties': {'type': 'string'}}}}}},
    }
