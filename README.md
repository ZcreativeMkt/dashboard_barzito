# BI Barzito na Vercel

## Estrutura

- `app.py` → dashboard Dash
- `api/index.py` → entrypoint WSGI para a Vercel
- `data/BARZITO_DADOS_GERAL.xlsx` → base consolidada
- `requirements.txt` → dependências Python
- `vercel.json` → configuração da Vercel

## Rodar local

```bash
pip install -r requirements.txt
python app.py
```

## Deploy

1. coloque o arquivo `BARZITO_DADOS_GERAL.xlsx` dentro de `data/`
2. suba para o GitHub
3. importe o repositório na Vercel

## Observação

Vercel funciona em serverless. Para dashboards muito pesados ou com planilhas enormes, Render/Railway/EC2 costumam ser mais estáveis.
