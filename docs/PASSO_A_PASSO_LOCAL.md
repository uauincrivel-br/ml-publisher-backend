# Passo a passo local — ML Publisher Enterprise V4

## 1. Entrar na pasta
```powershell
cd "C:\Users\User\Desktop\ml_publisher_enterprise_v4"
```

## 2. Subir backend seguro
```powershell
docker compose up --build -d
```

## 3. Validar API
Abra no navegador:
```text
http://localhost:8090/api/health
```

## 4. Abrir frontend local
Abra o arquivo:
```text
frontend\index.html
```

## 5. Criar usuário
Use:
- e-mail: admin@mlpublisher.local
- senha: admin123

## 6. Salvar credenciais Mercado Livre
Preencha Seller ID, Client ID, Client Secret e Access Token apenas para teste local.

## 7. Importar planilha
Anexe o XLSX/CSV. O backend salva o histórico no banco.

## 8. Descobrir próximo SKU seguro
Clique em "Descobrir próximo SKU seguro".

## 9. Simular antes de publicar
Clique em "Simular 1 SKU".

## 10. Publicação real
Só clique em "Publicar real pausado" após validar token/seller e confirmar que o próximo SKU está correto.
