import socket              # Módulo para comunicação em rede
import json                # Serialização para troca de dados em JSON
import os                  # Manipulação de sistema de arquivos
import re                  # Validações com expressões regulares
import base64              # Conversão de dados para base64 
import hashlib             # Geração de hash (usado para criar pastas únicas)
import logging             # Registro de eventos e erros
from datetime import datetime  # Obtenção da data/hora para logs
from cryptography.fernet import Fernet   # Criptografia simétrica
from pathlib import Path   # Operações seguras com caminhos

# ========================== CONFIGURAÇÃO UNIFICADA ==========================
class Config:
    """Centraliza configurações, logging e criptografia do servidor."""
    BUFFER_SIZE = 4096                    # Tamanho do buffer para recebimento de dados
    HOST = '0.0.0.0'                      # Escuta em todas as interfaces de rede
    PORT = 5000                           # Porta de escuta do servidor
    STORAGE_DIR = 'FTPPLUS/Armazenamento'  # Diretório onde os arquivos serão armazenados
    MAX_FILE_SIZE = 100 * 1024 * 1024     # Tamanho máximo permitido para um arquivo (100MB)
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.jpg', '.png'}  # Extensões de arquivos permitidas
    MAX_CONNECTIONS = 5                   # Máximo de conexões pendentes aceitas
    LOG_FILE = 'ftpplus_server.log'        # Nome do arquivo de log

    @classmethod
    def setup(cls):
        """Configura logging, cria o diretório base e inicializa a criptografia."""
        logging.basicConfig(
            filename=cls.LOG_FILE,        # Registra logs neste arquivo
            level=logging.INFO,           # Nível de log: informações e superiores
            format='%(asctime)s - %(levelname)s - %(message)s'  # Formato padrão do log
        )
        os.makedirs(cls.STORAGE_DIR, exist_ok=True)  # Cria o diretório se não existir
        cls.CRYPTO_KEY = Fernet.generate_key()         # Gera uma chave de criptografia
        cls.cipher = Fernet(cls.CRYPTO_KEY)              # Cria o objeto para criptografar e descriptografar

# Inicializa configurações ao carregar o módulo
Config.setup()

# ========================== FUNÇÕES IMPORTANTES ==========================
def get_pasta_usuario(ip):
    """
    Cria uma pasta exclusiva para o usuário usando o hash do IP.
    O hash garante que IPs diferentes usem pastas diferentes.

    Exemplo:
    IP: 192.168.1.100 -> Pasta: a1b2c3d4...
    IP: 192.168.1.101 -> Pasta: e5f6g7h8...
    """
    # Gera um hash MD5 a partir do IP
    pasta_hash = hashlib.md5(ip.encode()).hexdigest()
    # Concatena o diretório base com o hash
    pasta_usuario = os.path.join(Config.STORAGE_DIR, pasta_hash)
    os.makedirs(pasta_usuario, exist_ok=True)  # Cria a pasta se ela não existir
    return pasta_usuario

def validar_arquivo(nome, dados=None):
    """
    Valida o nome do arquivo e (opcionalmente) o tamanho dos dados.
    Garante que não haja tentativas de acessar diretórios superiores e que a extensão seja permitida.
    """
    if not nome or '..' in nome:
        return False, "Nome inválido"
    if not re.match(r'^[\w\-.]+$', nome):
        return False, "Nome contém caracteres não permitidos"
    if Path(nome).suffix.lower() not in Config.ALLOWED_EXTENSIONS:
        return False, "Tipo de arquivo não permitido"
    if dados and len(dados) > Config.MAX_FILE_SIZE:
        return False, "Arquivo muito grande"
    return True, ""

def salvar_arquivo_criptografado(pasta, nome, dados):
    """
    Criptografa os dados usando Config.cipher e os salva em um arquivo com extensão '.enc'.
    """
    caminho = os.path.join(pasta, nome + '.enc')    # Define o caminho completo do arquivo
    dados_criptografados = Config.cipher.encrypt(dados)  # Criptografa os dados
    with open(caminho, 'wb') as f:
        f.write(dados_criptografados)  # Salva os dados criptografados

def ler_arquivo_criptografado(pasta, nome):
    """
    Lê o arquivo criptografado e o descriptografa utilizando Config.cipher.
    """
    caminho = os.path.join(pasta, nome + '.enc')  # Define o caminho do arquivo
    with open(caminho, 'rb') as f:
        dados = f.read()
    return Config.cipher.decrypt(dados)  # Retorna o conteúdo descriptografado

def processar_comando(conn, addr, dados):
    """
    Processa comandos enviados pelo cliente: listar, enviar, baixar e excluir.
    Cada comando tem validação e operação específica.
    """
    try:
        # Extrai informações do payload recebido
        comando = dados.get("comando", "").lower()
        arquivo = dados.get("arquivo")
        # Cria ou acessa a pasta do usuário com base no IP
        pasta_usuario = get_pasta_usuario(addr[0])
        print(f"📁 Usuário {addr[0]} usando pasta: {os.path.basename(pasta_usuario)}")
        print(f"📝 Usuário {addr[0]} solicitou: {comando}")

        if comando == "listar":
            # Lista os arquivos removendo a extensão .enc
            arquivos = [f.replace('.enc', '') for f in os.listdir(pasta_usuario) if f.endswith('.enc')]
            return {"status": "sucesso", "dados": arquivos}

        if comando == "enviar" and arquivo:
            # Decodifica os dados enviados em base64
            conteudo = base64.b64decode(dados["dados"])
            # Verifica se o tamanho excede o máximo definido
            if len(conteudo) > Config.MAX_FILE_SIZE:
                return {"status": "erro", "mensagem": "Arquivo muito grande"}
            # Valida o nome e o conteúdo do arquivo
            valido, msg = validar_arquivo(arquivo, dados=conteudo)
            if not valido:
                return {"status": "erro", "mensagem": msg}
            # Salva o arquivo criptografado
            salvar_arquivo_criptografado(pasta_usuario, arquivo, conteudo)
            return {"status": "sucesso", "mensagem": f"✅ Arquivo {arquivo} salvo com sucesso"}

        if comando == "baixar" and arquivo:
            caminho = os.path.join(pasta_usuario, arquivo + '.enc')
            if not os.path.exists(caminho):
                return {"status": "erro", "mensagem": "❌ Arquivo não encontrado"}
            # Lê e descriptografa o conteúdo
            conteudo = ler_arquivo_criptografado(pasta_usuario, arquivo)
            # Codifica o conteúdo em base64 para envio
            return {
                "status": "sucesso",
                "dados": base64.b64encode(conteudo).decode(),
                "mensagem": f"✅ Arquivo {arquivo} enviado"
            }

        if comando == "excluir" and arquivo:
            # Valida o nome do arquivo
            valido, msg = validar_arquivo(arquivo)
            if not valido:
                return {"status": "erro", "mensagem": msg}
            caminho = os.path.join(pasta_usuario, arquivo + '.enc')
            if os.path.exists(caminho):
                os.remove(caminho)  # Remove o arquivo
                return {"status": "sucesso", "mensagem": "Arquivo excluído"}
            else:
                return {"status": "erro", "mensagem": "Arquivo não encontrado"}

        # Se o comando não for reconhecido, retorna erro
        return {"status": "erro", "mensagem": "Comando não reconhecido"}
    except Exception as e:
        logging.error(f"Erro no processamento do comando de {addr[0]}: {str(e)}")
        return {"status": "erro", "mensagem": f"❌ Erro: {str(e)}"}

def main():
    """
    Função principal: configura o diretório de armazenamento, inicia o socket
    e fica aguardando conexões de clientes. Para cada conexão, processa o comando.
    """
    os.makedirs(Config.STORAGE_DIR, exist_ok=True)  # Garante a existência do diretório base
    
    print("\n=== 🚀 FTPPlus Server ===")
    print("• Armazenamento seguro de arquivos")
    print("• Criptografia automática")
    print("• Pastas isoladas por usuário")
    
    # Cria o socket do servidor
    with socket.socket() as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reuso do endereço de forma imediata
        # Liga o socket ao HOST e PORT definidos na configuração
        servidor.bind((Config.HOST, Config.PORT))
        servidor.listen(Config.MAX_CONNECTIONS)  # Define o número máximo de conexões pendentes
        print(f"\n🌍 Servidor FTP rodando em {Config.HOST}:{Config.PORT}")
        
        while True:
            conn, addr = servidor.accept()  # Aceita uma nova conexão
            logging.info(f"Conexão estabelecida com {addr[0]}")
            print(f"\n📡 Conexão de {addr[0]}")
            with conn:
                try:
                    # Recebe dados com o tamanho definido e converte de JSON
                    dados = json.loads(conn.recv(Config.BUFFER_SIZE).decode())
                    resposta = processar_comando(conn, addr, dados)
                    # Envia a resposta de volta ao cliente
                    conn.send(json.dumps(resposta).encode())
                except Exception as e:
                    logging.error(f"Erro durante a conexão com {addr[0]}: {e}")

if __name__ == "__main__":
    main()

