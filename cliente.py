import socket, json, sys, os, base64

def mostrar_ajuda():
    print("\n🛠 FTPPlus - Cliente de Gerenciamento de Arquivos")
    print("──────────────────────────────────────────────")
    
    print("\n📋 Comandos disponíveis:")
    print("  listar               - Lista arquivos no servidor")
    print("  enviar <arquivo>     - Envia arquivo para o servidor")
    print("  excluir <arquivo>    - Remove arquivo do servidor")
    print("  baixar <arquivo>     - Baixa arquivo do servidor")
    print("  baixartodos          - Baixa todos arquivos enviados (se < 50 arquivos)")
    
    print("\n💻 Exemplos de uso:")
    print("Windows:")
    print('   .\ ftpplus 127.0.0.1 "listar"')
    print('   .\ ftpplus 127.0.0.1 "enviar C:\Fotos\ foto.jpg"')
    print("Linux/Mac:")
    print('   ./ftpplus 127.0.0.1 "listar"')
    print('   ./ftpplus 127.0.0.1 "enviar /home/user/foto.jpg"')
    print()
    
"""
Prompt é dividido em 4 argumentos;
sys.argv[0]: nome do próprio script
sys.argv[1]: primeiro argumento (IP ou comando)
sys.argv[2]: segundo argumento (comando e caminho do arquivo)
"""

if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
    mostrar_ajuda()
    sys.exit(0)

# Em vez de usar somente sys.argv[1], junta todos os argumentos passados
raw_command = " ".join(arg for arg in sys.argv[1:] if arg).strip('"')

parts = raw_command.split(None, 1)  # Separa no primeiro espaço
if len(parts) < 1 or parts[0] == "":
    print("Argumentos insuficientes.")
    mostrar_ajuda()
    sys.exit(1)

command = parts[0].lower()
server_ip = "127.0.0.1"  # Sempre usa localhost no modo simplificado
payload = {"command": command}

if command in ["enviar", "excluir", "baixar"]:
    if len(parts) < 2:
        print("Nome do arquivo não fornecido.")
        mostrar_ajuda()
        sys.exit(1)
    filename = parts[1].strip()
    payload["filename"] = filename

ALLOWED_EXTENSIONS = {'.zip', '.pdf', '.jpg', '.png', '.sql', '.txt', '.doc', '.gif', '.xlsx', '.jpeg', '.docx', '.htm', '.html', '.potx', '.ppsx', '.ppt', '.pptx', '.xls'}

if command == "enviar":
    if not os.path.exists(filename): 
        print("Arquivo não encontrado no cliente.") 
        sys.exit(1)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        print("Extensão de arquivo não permitida.")
        sys.exit(1)
    try:
        with open(filename, 'rb') as f:  #read in binary mode
            file_bytes = f.read()  
            
        file_data = base64.b64encode(file_bytes).decode('utf-8')  
        
        payload["file_data"] = file_data  
    except Exception as e:
        print(f"Erro ao ler o arquivo: {str(e)}")
        sys.exit(1)

# Cria a pasta "baixados" se não existir
pasta_baixados = os.path.join(os.getcwd(), 'baixados')
if not os.path.exists(pasta_baixados):
    os.makedirs(pasta_baixados)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
PORT = 9000 

try:
    client_socket.connect((server_ip, PORT))  
    message = json.dumps(payload) + "\n"  # Acrescenta o delimitador de nova linha
    client_socket.sendall(message.encode('utf-8'))  # Envia a mensagem com newline

    response_data = ""
    while True:
        parte = client_socket.recv(4096).decode('utf-8')
        if not parte:
            break
        response_data += parte
        if "\n" in response_data:
            response_data = response_data.strip()
            break

    response = json.loads(response_data)  # Decodifica e converte a resposta para dicionário

    print("\n📡 Resposta do servidor:")
    print("──────────────────────")

    # Formata a resposta de acordo com o comando
    if response.get("status") == "sucesso":
        if command == "listar":
            print("\n📂 Arquivos disponíveis:")
            if not response.get("dados"):
                print("   📭 Nenhum arquivo encontrado")
            else:
                for arquivo in response.get("dados", []):
                    print(f"   📄 {arquivo}")
        
        elif command == "enviar":
            print(f"✅ Arquivo enviado com sucesso:")
            print(f"   📄 {response.get('mensagem')}")
        
        elif command == "excluir":
            print(f"✅ Arquivo excluído com sucesso:")
            print(f"   🗑️ {response.get('mensagem')}")
        
        elif command == "baixar":
            print(f"✅ Download concluído:")
            print(f"   💾 {response.get('mensagem')}")
            if "file_data" in response:
                try:
                    file_bytes = base64.b64decode(response["file_data"].encode('utf-8')) # Decodifica de base64 para bytes
                    caminho_arquivo = os.path.join(pasta_baixados, filename)
                    with open(caminho_arquivo, 'wb') as f:# write in binary mode
                        f.write(file_bytes) 
                    print(f"   📥 Arquivo salvo: {caminho_arquivo}")
                except Exception as e:
                    print(f"   ❌ Erro ao salvar arquivo: {str(e)}")
        
        elif command == "baixartodos":
            print(f"✅ Download múltiplo iniciado")
            if "files" in response:
                for file_name, file_data in response["files"].items():
                    try:
                        file_bytes = base64.b64decode(file_data.encode('utf-8'))
                        # Decodifica de base64 para bytes
                        caminho_arquivo = os.path.join(pasta_baixados, file_name)
                        with open(caminho_arquivo, 'wb') as f:
                            f.write(file_bytes) # write in binary mode
                        print(f"   📥 Arquivo salvo: {caminho_arquivo}")
                    except Exception as e:
                        print(f"   ❌ Erro ao salvar {file_name}: {str(e)}")
            print("   ✅ Download múltiplo concluído")
    else:
        print(f"❌ Erro: {response.get('mensagem', 'Erro desconhecido')}")

except Exception as e:
    print("\n❌ Erro de conexão:")
    print(f"   {str(e)}")
finally:
    client_socket.close()
