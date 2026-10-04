# ProspectorBot — MVP v0.1

Ferramenta pessoal de prospecção que encontra negócios e destaca evidências de
possíveis oportunidades para serviços freelance de desenvolvimento web.

**Não envia mensagens, e-mails ou DMs e não realiza contato automatizado.**
O relatório serve para análise humana. O score não comprova intenção de contratar.

## Objetivo

Dado um nicho, uma cidade/região e um limite, descobrir aproximadamente 20–50
negócios quando a fonte tiver cobertura, analisar sua presença web, armazenar as
evidências e apresentar um ranking. O limite é de 1 a 50 negócios por scan.

O MVP funciona sem IA. Não inclui frontend, Docker, Redis, Celery, PostgreSQL ou
microsserviços.

## Instalação

Requer Python 3.12+ com suporte a `venv` e `pip`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
prospector --help
```

Se `.venv` já existe neste projeto, basta ativá-lo e atualizar a instalação
editável. Em Debian/Ubuntu, criar um ambiente pode exigir `python3-venv` do sistema.

Dependências: `httpx` para HTTP; `beautifulsoup4` para HTML; `SQLAlchemy` para
persistência; `pydantic` para validação; `typer` para CLI. `pytest` pertence ao
extra de desenvolvimento. `python-dotenv` lê a configuração local. SQLite vem com
Python. Hatchling é o backend de build.

## Configuração

Crie uma conta/projeto na [Geoapify](https://myprojects.geoapify.com/), obtenha uma
API key e configure-a localmente. Consulte os limites e custos da sua conta; o
ProspectorBot não compra créditos ou contrata planos automaticamente.

Para inserir a chave sem registrá-la no histórico do Bash:

```bash
read -rsp 'Geoapify API key: ' GEOAPIFY_API_KEY
export GEOAPIFY_API_KEY
```

Para guardar a chave localmente, copie `.env.example` para `.env` (se ainda não
existir) e edite o arquivo:

```bash
cp -n .env.example .env
# Edite .env e substitua a chave de exemplo pela sua.
```

O programa **lê `.env` automaticamente do diretório de execução**, sem executar
comandos de shell ou expandir variáveis dentro do arquivo. Variáveis já definidas
no ambiente têm prioridade, inclusive valores vazios. Não é necessário usar
`source .env`. `.env` e o banco local são ignorados pelo Git. Não versione a chave.

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `GEOAPIFY_API_KEY` | obrigatório para scan | Chave da descoberta |
| `PROSPECTOR_DATABASE_PATH` | `data/prospector.db` | Banco SQLite |
| `PROSPECTOR_REQUEST_TIMEOUT` | `10` | Timeout em segundos, máximo 60 |
| `PROSPECTOR_REQUEST_INTERVAL` | `1` | Intervalo entre requests, mínimo 1 segundo |
| `PROSPECTOR_MAX_LINKS` | `5` | Amostra de links internos por site, de 0 a 10 |
| `PROSPECTOR_SCORING_CONFIG` | não definido | JSON com pesos/limiares |

Caminhos relativos usam o diretório em que o comando é executado. Use caminho
absoluto para consultar o mesmo banco de outro diretório. O banco/tabelas são
criados na primeira execução; importar módulos não cria arquivos. O MVP usa
`create_all`, sem migrações de schema.

## Comandos

```bash
prospector scan --query "barbearias" --location "Campinas, SP" --limit 30
prospector leads
prospector show 1
```

`leads` mostra o último scan concluído. O número de `show` é a **posição naquele
ranking**, não uma chave numérica do banco. IDs internos são UUIDs. Para consultar
um histórico específico, use o UUID impresso pelo scan:

```bash
prospector leads --scan "UUID_DO_SCAN"
prospector show 1 --scan "UUID_DO_SCAN"
prospector leads --output data/report.json
prospector scan --query "dentistas" --location "Campinas, SP" --limit 20 --output data/report.json
prospector categories
```

O JSON contém dados comerciais, análises, score, evidências, oportunidades, versão
das regras e atribuição. O arquivo indicado é sobrescrito se já existir; pastas ausentes são criadas.
`leads` e `show` consultam SQLite, sem internet ou API key.

Aliases iniciais: barbearias, salão de beleza, restaurantes, cafeterias,
dentistas, academias, hotéis, padarias e pet shops. `categories` lista os aliases
e singulares suportados. Também é possível usar uma
[categoria Geoapify](https://apidocs.geoapify.com/docs/places/) diretamente.
**Barbearias usa `service.beauty.hairdresser` e pode incluir salões de beleza.**

## Descoberta e enriquecimento

A implementação usa os endpoints oficiais de Geocoding, Places e Place Details:
resolve a região, busca a categoria dentro dessa área e consulta detalhes para
obter website e telefone comercial quando disponíveis. A aplicação depende do
contrato `BusinessProvider.search`, permitindo trocar de fonte posteriormente.

Uma busca faz uma chamada de geocoding, uma de places e até uma de details por
resultado. O consumo de créditos depende do plano e dos endpoints. Requests são
sequenciais e espaçadas. HTTP 401/403/429 interrompe a descoberta, sem retries ou
troca de credenciais. Falha da API produz scan falho, não uma busca vazia concluída.

Dados vêm principalmente do OpenStreetMap. Cobertura e campos variam. Avaliações
não são inventadas: `rating` e `review_count` permanecem desconhecidos quando não
fornecidos. Não coletamos autores de avaliações, comentários, e-mails, dados de
proprietários, fotos ou respostas completas da API.

O website informado pela fonte é um candidato oficial, sujeito a confirmação
humana. URLs, texto e telefone são normalizados. Links de redes sociais e WhatsApp
são canais comerciais, não websites próprios. Não adivinhamos domínios nem
buscamos contatos pessoais.

A [documentação Places](https://apidocs.geoapify.com/docs/places/) permite guardar
resultados. Relatórios preservam atribuição a Geoapify e OpenStreetMap; consulte
os [termos da fonte](https://www.geoapify.com/terms-and-conditions/).

## Análise de websites

O analisador verifica a página inicial e uma pequena amostra de links internos:

- HTTPS final, status HTTP, redirects e tempo de recebimento do HTML;
- title, meta description, viewport com `width=device-width`, headings H1/H2;
- telefone, WhatsApp, CTA, formulário de contato e sinais de agendamento;
- links de redes sociais e links internos com HTTP 404/410.

Esses sinais são heurísticas de HTML, não uma avaliação visual ou prova de que
formulários/agendamento funcionem. Não executamos JavaScript, enviamos formulários
ou abrimos links de WhatsApp/redes sociais. HTML bruto não é salvo.

HTTP usa User-Agent `ProspectorBot/0.1`, verifica `robots.txt`, respeita
`Crawl-delay`/`Request-rate` e mantém intervalo entre requests. Robots
restrito/indisponível causa análise inconclusiva; HTTP 404 em `/robots.txt` indica
ausência do arquivo. Redirects de robots (até 5) são seguidos com a mesma validação
de endereço; redirects em excesso deixam a análise inconclusiva.
Delays acima do orçamento de 60 segundos impedem a coleta.

Há limites de tamanho da resposta (2 MB por padrão), timeout, redirects e links.
URLs locais/privadas/reservadas são rejeitadas após resolução DNS, inclusive nos
redirects. A resolução não é fixada ao socket: execute localmente com fontes
confiáveis; o MVP não deve ser exposto como serviço para URLs arbitrárias.

HTTP 401/403/429 bloqueia novas requests à origem no scan. CAPTCHA identificado,
HTML escasso, resposta não HTML, falha de TLS e timeout deixam sinais desconhecidos.
Uma página com reCAPTCHA/hCaptcha embutido (ex.: formulário de contato) não é
tratada como bloqueio; apenas telas de desafio. Não tentamos contornar bloqueios. Timeout em um link não é link quebrado. Links
externos não são percorridos. Páginas dependentes de JavaScript podem produzir
análises parciais ou deixar sinais indisponíveis.
Uma falha inesperada na análise de um site fica registrada como análise falha,
sem interromper o restante do scan.

## Oportunidades e score

Regras de oportunidade e scoring compartilham condições. Cada regra pontua no
máximo uma vez por negócio/scan e exige evidências. O total é limitado a 100,
sem participação de IA.

| Critério | Peso | Condição padrão |
| --- | ---: | --- |
| Sem website | 25 | Ausência confirmada e evidência `website_absent_confirmed` |
| Performance mobile ruim | 20 | Métrica específica abaixo de 50/100, com fonte |
| CTA não identificado | 10 | Não detectado no HTML inicial suficientemente completo |
| Agendamento não identificado | 15 | Sinal de negócio por agendamento e acesso não detectado no HTML inicial |
| WhatsApp disponível | 5 | Link/canal comercial informado |
| Presença por avaliações | 10 | Pelo menos 50 avaliações fornecidas pela fonte |
| Presença social | 5 | Link/canal social identificado |
| Resposta lenta | 10 | HTML, incluindo redirects, acima de 3000 ms |
| Viewport ausente/inadequado | 10 | `width=device-width` não identificado no HTML completo |

Falta de HTTPS, title, meta description e links com 404/410 podem gerar
oportunidades, mas não pontuam por padrão. É válido concluir que não existe
oportunidade relevante. Um canal de WhatsApp sozinho não prova um problema;
avaliações não comprovam orçamento ou intenção de contratar.

Cuidados essenciais:

1. `not_found` significa **não informado/encontrado na fonte**, não “sem website”.
   A Geoapify nunca confirma ausência; esse critério não pontua automaticamente.
2. Ausência no HTML inicial tem escopo limitado: o recurso pode estar em outra
   página ou aparecer via JavaScript. Evidências e oportunidades explicam isso.
3. Agendamento habitual por categoria é uma **inferência explícita** para
   cabeleireiros, dentistas e alguns serviços de beleza. Uma indicação explícita
   de negócio sem agendamento impede essa regra. Confirme antes da proposta.

Tempo de resposta é uma única medição de rede/servidor, não tempo completo de
carregamento ou PageSpeed. Viewport ausente não equivale a performance mobile
ruim. O contrato de métricas está preparado, mas **PageSpeed/Lighthouse não estão
integrados**: a análise HTML não atribui os 20 pontos de performance mobile.
Dados ausentes podem produzir scores baixos ou zero; não inventamos problemas
para preencher a escala.

| Score | Classificação |
| --- | --- |
| 0–29 | Low |
| 30–49 | Moderate |
| 50–69 | Good |
| 70–84 | High |
| 85–100 | Gold Nugget |

Pesos/limiares estão centralizados em `scoring/weights.py`. Para gerar um JSON
editável com a configuração completa:

```bash
python -c 'from pathlib import Path; from prospector.scoring.weights import ScoringConfig; Path("data/scoring.json").write_text(ScoringConfig().model_dump_json(indent=2), encoding="utf-8")'
export PROSPECTOR_SCORING_CONFIG=data/scoring.json
```

Também pode conter somente os valores alterados:

```json
{"weights": {"no_cta": 5}, "slow_response_ms": 4000}
```

Pesos negativos e chaves desconhecidas são rejeitados. A versão do score inclui
um hash da configuração. Mudanças aplicam-se a novos scans e não reescrevem o
histórico. Para evidências/configuração iguais, a pontuação e as contribuições
são iguais.

## Arquitetura e histórico

```text
src/prospector/
├── models.py                 # Modelos Pydantic
├── config.py                 # Configuração do ambiente
├── main.py                   # CLI Typer
├── service.py                # Orquestração do scan
├── discovery/                # Contrato e adaptador Geoapify
├── enrichment/               # Normalização de URLs, texto e telefone
├── analyzers/                # HTTP público, HTML e contrato de métricas futuras
├── opportunities/            # Regras e oportunidades
├── scoring/                  # Pesos, limiares e cálculo determinístico
├── database/                 # Tabelas, transações e repository
├── reports/                  # Ranking, detalhes e JSON
└── diagnostics/              # Contrato futuro de diagnóstico por evidências
```

SQLite contém Business, Scan, ScanBusiness, WebsiteAnalysis, Opportunity e Score.
IDs/vínculos são relacionais; detalhes validados/evidências ficam em JSON, mantendo
o MVP simples.

Negócios são deduplicados pelo par confiável `source` + `source_id`. Sem esse par,
não juntamos registros por nomes ou telefones parecidos. Cada scan mantém um
snapshot comercial; análises, oportunidades e scores ficam ligados a ele. Chaves
estrangeiras são ativadas e transações fazem rollback em caso de erro. Um scan
falho mantém o que já foi salvo, mas não é selecionado automaticamente por `leads`.

## Testes

```bash
python -m pytest -q -W error
```

Testes não precisam de chave ou internet. Cobrem scoring, oportunidades,
normalização, HTML, robots, redirects, bloqueios, limites de coleta, falhas da
API, persistência, duplicatas, histórico e CLI. Um teste de integração percorre
o fluxo inteiro com **30 negócios simulados**, exporta o relatório e repete o
scan para verificar histórico e deduplicação.

Uma execução real depende de chave, conectividade, créditos e cobertura da fonte.
O teste simulado não comprova que haverá 30 resultados em qualquer cidade.

## Uso responsável e limitações

Use APIs autorizadas e informações comerciais públicas, coletando apenas o
necessário. Preserve a atribuição nos relatórios e revise os dados/termos da fonte
antes de compartilhar o banco com contatos.

Não há contato automatizado, automação de DMs, scraping do Instagram, coleta
massiva de dados pessoais, bypass de CAPTCHA/autenticação/rate limits ou disfarce
de automação.

A análise é uma triagem. Confirme vínculo do domínio, atualidade dos dados,
conteúdo renderizado, fluxos externos e relevância da oportunidade antes de uma
abordagem humana.

`diagnostics/base.py` define somente uma interface futura: fatos com evidências,
inferências separadas, sugestões de serviços e possibilidade de concluir que não
há oportunidade. Não há implementação de LLM ou dependência de IA. Esse contrato
não altera o score.
