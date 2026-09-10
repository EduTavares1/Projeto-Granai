import urllib.request
import json
import base64
import os

# Configuração da chave de API padrão da Evolution API v2 local
headers = {
    "apikey": "trill-bot-api-key-segura-2024"
}

# 1. Verifica o estado atual da conexão da instância
try:
    url_state = "http://localhost:8080/instance/connectionState/trill-bot"
    req_state = urllib.request.Request(url_state, headers=headers, method="GET")
    with urllib.request.urlopen(req_state) as response:
        res_data = response.read().decode('utf-8')
        print("Estado atual da conexão:")
        print(res_data)
except Exception as e:
    print(f"Erro ao obter estado de conexão: {e}")

# 2. Solicita um novo QR Code da Evolution API
url_connect = "http://localhost:8080/instance/connect/trill-bot"
req_connect = urllib.request.Request(url_connect, headers=headers, method="GET")

try:
    with urllib.request.urlopen(req_connect) as response:
        res_data = response.read().decode('utf-8')
        json_data = json.loads(res_data)
        
        base64_data = json_data.get("base64")
        if base64_data:
            # Remove o prefixo do cabeçalho base64 caso exista
            if base64_data.startswith("data:image/png;base64,"):
                base64_data = base64_data.replace("data:image/png;base64,", "")
            
            # Decodifica os bytes da imagem
            image_bytes = base64.b64decode(base64_data)
            
            # Salva o arquivo no diretório local do projeto
            out_path = "qrcode.png"
            with open(out_path, "wb") as f:
                f.write(image_bytes)
                
            print(f"\n✅ QR Code gerado e salvo com sucesso em: {os.path.abspath(out_path)}")
            print("Você pode abrir esta imagem e escaneá-la com seu WhatsApp.")
        else:
            print("\nA Evolution API não retornou uma imagem de QR Code. Verifique se o aparelho já está conectado.")
            
except urllib.error.HTTPError as e:
    print(f"Erro HTTP da Evolution API: {e.code}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Erro ao gerar QR Code: {e}")
