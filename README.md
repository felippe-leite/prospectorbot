# ProspectorBot

Ferramenta de linha de comando que encontra negócios locais, analisa seus sites e
gera um ranking de possíveis oportunidades para serviços de desenvolvimento web.

O ProspectorBot **não envia mensagens nem faz contato automatizado**. O resultado
é uma triagem para análise humana; o score não comprova intenção de contratar.

## Como funciona

1. Busca negócios de um nicho em uma cidade usando a API da [Geoapify](https://www.geoapify.com/).
2. Analisa a página inicial de cada site (HTTPS, título, viewport mobile, CTA,
   agendamento, WhatsApp, redes sociais, links quebrados e tempo de resposta).
3. Aplica regras baseadas em evidências e calcula um score de 0 a 100.
4. Salva tudo em SQLite e mostra o ranking no terminal ou em JSON.

## Instalação

Requer Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Configuração

Crie uma API key gratuita na [Geoapify](https://myprojects.geoapify.com/) e
coloque-a no arquivo `.env`:

```bash
cp .env.example .env
# edite .env e preencha GEOAPIFY_API_KEY
```

O `.env` é lido automaticamente e não é versionado. Outras opções (caminho do
banco, timeout, intervalo entre requests) estão documentadas em `.env.example`.

## Uso

```bash
prospector scan --query "barbearias" --location "Campinas, SP" --limit 30
prospector leads                      # ranking do último scan
prospector show 1                     # detalhes e evidências do 1º colocado
prospector leads --output report.json # exporta o relatório
prospector categories                 # nichos suportados
```

Nichos suportados: barbearias, salão de beleza, restaurantes, cafeterias,
dentistas, academias, hotéis, padarias e pet shops. Também aceita uma
[categoria Geoapify](https://apidocs.geoapify.com/docs/places/) diretamente.

## Score

| Critério | Pontos |
| --- | ---: |
| Sem website (ausência confirmada) | 25 |
| Performance mobile ruim | 20 |
| Agendamento não identificado | 15 |
| CTA não identificado | 10 |
| Viewport mobile ausente | 10 |
| Resposta lenta (> 3 s) | 10 |
| 50+ avaliações | 10 |
| WhatsApp disponível | 5 |
| Presença em redes sociais | 5 |

Classificação: **Low** (0–29), **Moderate** (30–49), **Good** (50–69),
**High** (70–84) e **Gold Nugget** (85–100). Os pesos podem ser alterados via
JSON em `PROSPECTOR_SCORING_CONFIG` (veja `src/prospector/scoring/weights.py`).

## Testes

```bash
python -m pytest -q
```

Os testes não precisam de internet nem de API key.

## Uso responsável

- Respeita `robots.txt`, identifica-se como `ProspectorBot/0.1` e espaça as requests.
- Não contorna CAPTCHA, login ou rate limits, nem coleta dados pessoais.
- Feito para rodar localmente: não exponha como serviço web que aceite URLs arbitrárias.
- Dados © [OpenStreetMap](https://www.openstreetmap.org/copyright) via Geoapify;
  mantenha a atribuição ao compartilhar relatórios.
