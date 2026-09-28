# Clara API — Acompanhamento de interessados

MVP de Desenvolvimento Full Stack Básico:  Software desenvolvido para que uma recepção de uma clínica fictícia possa registrar clientes interessados, acompanha etapas e definir o próximo retorno. Marca e exemplos fictícios, inspirados em necessidades de atendimento de um negócio de bem-estar.

## Executar localmente

Ambiente verificado: Python 3.14.4, Linux. Dependências diretas com versões fixadas em `requirements.txt`. Os comandos abaixo devem ser executados na pasta que contém `app.py`.

### Com uv (fluxo de desenvolvimento)

O `uv` é uma ferramenta instalada na máquina para criar ambientes e instalar dependências. Não é uma biblioteca importada pelo Flask. Confira a instalação com `uv --version`; se necessário, siga a [instalação oficial](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv venv --python 3.14 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python -m flask --app app run --host 127.0.0.1 --port 5001
```

`uv venv` cria a pasta `.venv`; `source` faz o terminal usar o Python desse ambiente; `uv pip install` instala nele as bibliotecas listadas. Para sair, use `deactivate`. No Windows/PowerShell, a ativação é `.venv\Scripts\Activate.ps1`.

Este projeto mantém `requirements.txt` como lista de dependências. Não exige `uv init`, `uv add`, `uv sync`, `pyproject.toml` ou `uv.lock` para esse fluxo. A pasta `.venv` é local, está ignorada pelo Git e deve ser recriada em cada máquina. Ela isola as bibliotecas Python; não é uma máquina virtual nem um contêiner.

### Alternativa com Python e pip (sem uv)

Em uma cópia sem ambiente criado:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --host 127.0.0.1 --port 5001
```

No Windows, use `py -m venv .venv` e `.venv\Scripts\Activate.ps1` no PowerShell. As duas opções executam o mesmo código. Um ambiente criado pelo uv não inclui necessariamente o pip: ao seguir o primeiro fluxo, use `uv pip install`.

- Swagger interativo: **http://127.0.0.1:5001/docs/**
- Contrato OpenAPI: http://127.0.0.1:5001/openapi.json
- Listagem: http://127.0.0.1:5001/interessados

O Swagger e seus arquivos JS/CSS são servidos pela própria API. Após instalar as dependências, não há necessidade de CDN para utilizá-lo. Não é necessário instalar SQLite separadamente: o módulo `sqlite3` acompanha Python.

## Dados de demonstração

Com o ambiente ativado, antes ou depois de iniciar o servidor:

```bash
python -m flask --app app seed-demo
```

Adiciona seis cadastros fictícios, incluindo retornos para dias anteriores, hoje e próximos dias, calculados no dia da carga. Só funciona com banco vazio: caso existam registros, recusa a operação e preserva os dados. Não é executado automaticamente.

O banco é criado em `instance/clara.sqlite3` na primeira execução. Os dados permanecem após reiniciar a API. Para iniciar outra demonstração vazia, pare a API e **mova** esse arquivo para uma pasta de backup; na próxima execução será criado um novo banco. A pasta `instance/` está no `.gitignore`.

## Operações

| Método | Rota | Resultado |
|---|---|---|
| POST | `/interessados` | Cria cadastro; retorna objeto e status 201 |
| GET | `/interessados` | Lista todos, inclusive lista vazia; status 200 |
| GET | `/interessados/{identificador}` | Consulta detalhes; 200 ou 404 |
| PUT | `/interessados/{identificador}` | Substitui campos editáveis; 200, 400 ou 404 |
| DELETE | `/interessados/{identificador}` | Exclui; 204 sem corpo, ou 404 |

POST e PUT recebem JSON. Exemplo:

```json
{
  "nome": "Ana Exemplo",
  "servico": "Avaliação inicial",
  "origem": "Instagram",
  "etapa": "novo",
  "proximo_retorno": "2026-09-26",
  "observacao": "Prefere retorno à tarde."
}
```

### Regras

- Nome: 2–100 caracteres; serviço: 2–80; ambos removem espaços das extremidades.
- Origem: `Instagram`, `Indicação`, `Busca online` ou `Outro`.
- Etapas ativas: `novo`, `em_contato`, `avaliacao_marcada`. Exigem data de retorno válida (`AAAA-MM-DD`).
- Etapas finalizadas: `convertido`, `encerrado`. Data opcional; não entram nos indicadores de pendências da interface.
- Datas passadas são permitidas para registrar retornos atrasados.
- Observação comercial opcional, até 1000 caracteres.
- Homônimos são permitidos; o ID identifica cada cadastro.
- PUT exige o documento completo dos campos obrigatórios; campos opcionais omitidos são limpos. Campos desconhecidos são rejeitados.
- `criado_em` e `atualizado_em` são gerados pela API em UTC. A data de retorno representa um dia civil, sem conversão de fuso.
- “Avaliação marcada” é uma etapa comercial; este MVP não reserva horários nem controla conflitos de agenda.

## Organização

- `app.py`: Flask, rotas, persistência SQLite e carga fictícia.
- `domain.py`: validação e opções do domínio.
- `openapi.py`: contrato usado pelo Swagger.
- `tests/test_api.py`: testes com arquivos SQLite temporários.

SQL usa parâmetros, transações fazem commit/rollback pelo gerenciador de contexto e conexões são fechadas ao fim do contexto Flask. O frontend consome JSON e recebe CORS para abertura por `file://`.

## Testar

```bash
uv pip install -r requirements-dev.txt
python -m pytest -q
```

Se criou o ambiente pela alternativa sem uv, use `python -m pip install -r requirements-dev.txt` para instalar as dependências de teste.

Os testes usam banco temporário e não alteram a demonstração. Cobrem CRUD, persistência entre instâncias, entradas inválidas, atualização rejeitada, registro inexistente, CORS, documentação e proteção contra carga duplicada.
