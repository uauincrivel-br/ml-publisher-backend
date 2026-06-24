# ML Publisher Enterprise V5

Versão SaaS comercial com:

- Interface moderna estilo ERP/SaaS.
- Upload inteligente de planilha Excel/CSV.
- Mapeamento automático de colunas brasileiras do Mercado Livre.
- Validação de SKU duplicado na planilha.
- Bloqueio de SKU e offset já publicados no histórico.
- Continuidade real usando `published_items`.
- Publicação segura sempre pausada.
- Simulação antes da publicação real.
- Auditoria e logs no painel.

## Rodar local

```powershell
cd "C:\Users\User\Desktop\ml_publisher_enterprise_v5"
docker compose up --build -d
```

API: http://localhost:8090/docs

Frontend local: abra `frontend/index.html` no navegador ou hospede a pasta `frontend` no Netlify.

## Atualização a partir da V4

1. Faça backup da V4.
2. Extraia esta V5 em pasta separada.
3. Copie, se necessário, o banco `backend/data/mlp_enterprise.db` da V4 para a V5 para manter histórico.
4. Rode `docker compose up --build -d`.
5. Abra o painel e faça upload da planilha.

## Segurança

A publicação real exige token salvo no backend. Não publique direto pelo frontend estático sem backend seguro.
