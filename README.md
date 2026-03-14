# 🌡️ Polymarket Weather Tracker

Dashboard que cruza previsão do tempo com odds do Polymarket para os mercados de temperatura diária.

## O que o app faz

- Busca previsão do tempo das 14 cidades via **Open-Meteo** (gratuito, sem chave)
- Busca mercados ativos via **Polymarket Gamma API** (gratuito, sem chave)
- Gera análise automática comparando previsão vs odds do mercado
- Mostra mini previsão de 5 dias por cidade

## Como colocar no ar (100% gratuito)

### 1. Criar conta no GitHub
Acesse https://github.com e crie uma conta gratuita.

### 2. Criar repositório
- Clique em "New repository"
- Nome: `polymarket-weather` (ou qualquer nome)
- Deixe público
- Clique em "Create repository"

### 3. Subir os arquivos
Faça upload dos dois arquivos:
- `polymarket_weather.py`
- `requirements.txt`

### 4. Deploy no Streamlit Community Cloud
- Acesse https://share.streamlit.io
- Faça login com sua conta GitHub
- Clique em "New app"
- Selecione o repositório e o arquivo `polymarket_weather.py`
- Clique em "Deploy"

Pronto! Em ~2 minutos o app estará em:
`https://[seu-usuario]-polymarket-weather-[hash].streamlit.app`

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run polymarket_weather.py
```

## APIs utilizadas (todas gratuitas)

| API | Uso | Limite gratuito |
|-----|-----|----------------|
| Open-Meteo | Previsão do tempo | Ilimitado |
| Polymarket Gamma API | Odds dos mercados | 60 req/min |

## Aviso
Este app é apenas para fins informativos. Não é conselho financeiro.
