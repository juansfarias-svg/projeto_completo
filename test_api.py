import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Chave carregada: {api_key[:30]}..." if api_key else "Nenhuma chave encontrada")

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Teste de conexão"
        )
        print("✅ API válida e funcionando!")
        print(f"Resposta: {response.text[:100]}")
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
else:
    print("❌ GEMINI_API_KEY não encontrada no .env")
