# ProspectorBot

Ferramenta (CLI e interface web) que encontra negócios locais, analisa seus sites e
gera um ranking de possíveis oportunidades para serviços de desenvolvimento web.

O ProspectorBot **não envia mensagens nem faz contato automatizado**. O resultado
é uma triagem para análise humana; o score não comprova intenção de contratar.

## Como funciona

1. Busca negócios de um nicho em uma cidade usando a API da [Geoapify](https://www.geoapify.com/).
2. Analisa a página inicial de cada site (HTTPS, título, viewport mobile, CTA,
   agendamento, WhatsApp, redes sociais, links quebrados e tempo de resposta) e,
   quando habilitado, mede a performance mobile com o Google PageSpeed Insights.
3. Aplica regras baseadas em evidências e calcula um score de 0 a 100.
4. Salva tudo em SQLite e mostra o ranking no terminal ou em JSON.

Cada oportunidade apontada vem acompanhada das evidências que a sustentam. Quando
um dado não pode ser verificado, ele fica como desconhecido em vez de virar um
problema inventado.

## Interface web

Além da CLI, o ProspectorBot tem um dashboard web para iniciar prospecções,
acompanhar o progresso em tempo real, filtrar leads por score e oportunidade e
consultar as evidências de cada negócio. Status e notas pessoais ajudam a
organizar a triagem.

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
**High** (70–84) e **Gold Nugget** (85–100).

## Uso responsável

- Respeita `robots.txt`, identifica-se como `ProspectorBot/0.1` e espaça as requests.
- Não contorna CAPTCHA, login ou rate limits, nem coleta dados pessoais.
- Dados © [OpenStreetMap](https://www.openstreetmap.org/copyright) via Geoapify.
