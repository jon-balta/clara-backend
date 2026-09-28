"""Regras do acompanhamento comercial, independentes do transporte HTTP."""
from datetime import date

ETAPAS = ('novo', 'em_contato', 'avaliacao_marcada', 'convertido', 'encerrado')
ORIGENS = ('Instagram', 'Indicação', 'Busca online', 'Outro')
ATIVAS = ETAPAS[:3]
CAMPOS = {'nome', 'servico', 'origem', 'etapa', 'proximo_retorno', 'observacao'}


class EntradaInvalida(ValueError):
    """Erros de campos que podem ser apresentados ao usuário."""

    def __init__(self, erros):
        self.erros = erros
        super().__init__('Confira os campos informados.')


def validar(dados):
    """Valida o documento completo usado tanto em POST quanto em PUT."""
    if not isinstance(dados, dict):
        raise EntradaInvalida({'corpo': 'Envie um objeto JSON.'})
    erros, resultado = {}, {}
    if set(dados) - CAMPOS:
        erros['corpo'] = 'Há campos desconhecidos no cadastro.'
    for campo, limite in (('nome', 100), ('servico', 80)):
        valor = dados.get(campo)
        if not isinstance(valor, str) or not 2 <= len(valor.strip()) <= limite:
            erros[campo] = f'Informe entre 2 e {limite} caracteres.'
        else:
            resultado[campo] = valor.strip()
    for campo, opcoes in (('etapa', ETAPAS), ('origem', ORIGENS)):
        valor = dados.get(campo)
        if valor not in opcoes:
            erros[campo] = 'Escolha uma opção válida.'
        else:
            resultado[campo] = valor
    observacao = dados.get('observacao', '')
    if not isinstance(observacao, str) or len(observacao.strip()) > 1000:
        erros['observacao'] = 'Use até 1000 caracteres.'
    else:
        resultado['observacao'] = observacao.strip()
    retorno = dados.get('proximo_retorno')
    if retorno in (None, ''):
        resultado['proximo_retorno'] = None
        if dados.get('etapa') in ATIVAS:
            erros['proximo_retorno'] = 'Defina o próximo retorno para um acompanhamento ativo.'
    else:
        try:
            data = date.fromisoformat(retorno)
            if data.isoformat() != retorno:
                raise ValueError
            resultado['proximo_retorno'] = retorno
        except (TypeError, ValueError):
            erros['proximo_retorno'] = 'Informe uma data válida no formato AAAA-MM-DD.'
    if erros:
        raise EntradaInvalida(erros)
    return resultado
