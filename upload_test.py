import requests

url = "http://127.0.0.1:8000/api/import/upload"

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBhZG1pbi5jb20iLCJ1aWQiOjEsImV4cCI6MTc4MjkzNTc0Mn0.o9chsBDly1RQwG-ISiHZl0UXrYZGNhuCFHupDgT..."

file_path = r"C:\Users\User\Desktop\ml_publisher_enterprise_v5\Cadastro_ML_PRONTO_PUBLICACAO_CORRIGIDO_FINAL_v2.xlsx"

headers = {
    "Authorization": f"Bearer {token}"
}

files = {
    "file": open(file_path, "rb")
}

response = requests.post(url, headers=headers, files=files)

print(response.status_code)
print(response.text)