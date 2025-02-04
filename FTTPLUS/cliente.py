import socket, json, sys, os, base64, logging
from pathlib import Path

# === CONFIGURAÇÃO DO CLIENTE ===
CONFIG = {
    'BUFFER_SIZE': 4096,    # Tamanho dos pacotes trocados entre cliente e servidor
    'PORT': 5000,           # Porta padrão para conexão com o servidor
    'MAX_RETRIES': 3,       # Número máximo de tentativas de conexão
    'TIMEOUT': 30           # Timeout em segundos para a conexão
}

# Nomes de arquivos para salvar configurações locais
FIRST_RUN_FILE = '.ftpplus_initialized'  # Indica se o programa já foi iniciado
CONFIG_FILE = '.ftpplus_config.json'       # Armazena o último IP utilizado

# Configura logging para o cliente (opcional)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FTPClient:
    """
    Cliente FTP com funcionalidades:
      - Conexão com retry (várias tentativas)
      - Barra de progresso durante upload/download
      - Validação local de arquivos
      - Interface via terminal com mensagens amigáveis
    """
    
    @staticmethod
    def mostrar_boas_vindas():
        """Exibe uma mensagem de boas-vindas e introdução ao usuário."""
        print("""
╔════════════════════════════════════════╗
║          Bem-vindo ao FTPPlus!         ║
╠════════════════════════════════════════╣
║ • Seus arquivos são criptografados     ║
║ • Cada usuário tem sua pasta privada   ║
║ • Suporta arquivos até 100MB           ║
╚════════════════════════════════════════╝
""")

    def __init__(self, servidor):
        """Inicializa o objeto com o IP do servidor e tenta conectar."""
        self.servidor = servidor  # IP ou hostname do servidor
        self.socket = None        # Será definido ao conectar
        self._conectar()          # Tenta estabelecer conexão imediatamente

    def _conectar(self):
        """Realiza a tentativa de conexão com o servidor, com retry."""
        for tentativa in range(CONFIG['MAX_RETRIES']):
            try:
                self.socket = socket.socket()  # Cria um novo socket TCP
                self.socket.settimeout(CONFIG['TIMEOUT'])  # Define o tempo máximo de espera
                self.socket.connect((self.servidor, CONFIG['PORT']))  # Conecta ao servidor
                print(f"✅ Conectado a {self.servidor}")
                return  # Conexão realizada, sai do loop
            except Exception as e:
                print(f"⚠️ Tentativa {tentativa + 1}: {e}")
        print("❌ Não foi possível conectar")
        sys.exit(1)  # Finaliza o programa se não conseguir conectar

    def verificar_servidor(self):
        """
        Tenta estabelecer uma breve conexão para confirmar que o servidor está disponível.
        Retorna True se disponível, False caso contrário.
        """
        try:
            with socket.create_connection((self.servidor, CONFIG['PORT']), timeout=5):
                return True
        except:
            return False

    def mostrar_progresso(self, enviado, total):
        """
        Exibe uma barra de progresso no terminal.
        - Calcula a porcentagem de dados enviados.
        - Gera e exibe uma barra baseada nessa porcentagem.
        """
        porcentagem = (enviado / total) * 100
        barra = '=' * int(porcentagem / 2)  # Escala simplificada (2% por '=')
        print(f"\r[{barra:-<50}] {porcentagem:.1f}%", end='')

    def executar(self, comando):
        """
        Processa o comando do usuário:
         - Valida se o servidor está online.
         - Separa a ação e os parâmetros.
         - Prepara o payload para envio.
         - Para upload, lê e codifica o arquivo em base64.
         - Envia o comando e processa a resposta.
         - Fecha a conexão ao final.
        """
        try:
            if not self.verificar_servidor():
                print("❌ Servidor não está respondendo")
                return

            partes = comando.strip().split()
            if not partes:
                return self.mostrar_ajuda()

            acao = partes[0].lower()  # Ação: listar, enviar, excluir ou baixar
            arquivo = ' '.join(partes[1:]) if len(partes) > 1 else None

            if acao not in ['listar', 'enviar', 'excluir', 'baixar']:
                print("❌ Comando desconhecido")
                self.mostrar_ajuda()
                return

            print(f"\n🔄 Executando: {acao}")
            # Cria o dicionário que será enviado ao servidor
            payload = {"comando": acao, "arquivo": arquivo}

            if acao == 'enviar':
                if not self._validar_arquivo_local(arquivo):
                    return
                print("\nEnviando arquivo...")
                tamanho = os.path.getsize(arquivo)  # Obtém o tamanho do arquivo em bytes
                with open(arquivo, 'rb') as f:
                    dados = f.read()  # Lê os dados do arquivo
                    self.mostrar_progresso(len(dados), tamanho)  # Mostra a barra de progresso
                    tamanho_mb = len(dados) / (1024 * 1024)
                    print(f"Tamanho: {tamanho_mb:.2f}MB")
                    # Converte os dados para base64 para envio seguro via JSON
                    payload["dados"] = base64.b64encode(dados).decode()
                print("\nEnvio concluído!")

            # Envia o payload e recebe a resposta com retry interno
            resposta = self._enviar_com_retry(payload)

            # Se for baixar um arquivo, salva-o localmente após decodificação
            if acao == 'baixar' and resposta.get("status") == "sucesso":
                self._salvar_arquivo(arquivo, resposta["dados"])
            else:
                print(json.dumps(resposta, indent=2))

            print("✨ Comando concluído!")
        except Exception as e:
            logging.error(f"Erro ao executar comando: {e}")
            print(f"❌ Erro: {str(e)}")
        finally:
            if self.socket:
                self.socket.close()  # Garante o fechamento do socket

    def _validar_arquivo_local(self, arquivo):
        """
        Realiza validação local do arquivo:
         1. Verifica se o nome foi informado.
         2. Checa se o arquivo existe.
         3. Garante que seu tamanho não exceda 100MB.
        """
        if not arquivo:
            print("❌ Nome do arquivo não informado")
            return False
        if not os.path.exists(arquivo):
            print("❌ Arquivo não encontrado")
            return False
        if os.path.getsize(arquivo) > 100 * 1024 * 1024:
            print("❌ Arquivo muito grande")
            return False
        return True

    def _receber_resposta(self):
        """
        Aguarda a resposta do servidor e a converte de JSON para um dicionário.
        Em caso de erro, retorna um dicionário com status de erro.
        """
        try:
            dados = self.socket.recv(CONFIG['BUFFER_SIZE'])
            return json.loads(dados.decode())
        except Exception as e:
            print(f"❌ Erro ao receber resposta: {e}")
            return {"status": "erro", "mensagem": str(e)}

    def _salvar_arquivo(self, nome, dados):
        """
        Salva o arquivo baixado:
         - Decodifica os dados de base64.
         - Escreve os dados no arquivo local.
        """
        try:
            with open(nome, 'wb') as f:
                f.write(base64.b64decode(dados))
            print(f"✅ Arquivo '{nome}' salvo com sucesso")
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")

    def _enviar_com_retry(self, payload, max_tentativas=3):
        """
        Tenta enviar os dados para o servidor com até max_tentativas.
        Se ocorrer erro em todas as tentativas, lança a exceção.
        """
        import time  # Importa o módulo time para utilizar sleep
        for tentativa in range(max_tentativas):
            try:
                self.socket.send(json.dumps(payload).encode())
                return self._receber_resposta()
            except Exception as e:
                if tentativa == max_tentativas - 1:
                    raise e
                print(f"Erro ao enviar. Tentando novamente ({tentativa + 1}/{max_tentativas})")
                time.sleep(1)

    @staticmethod
    def mostrar_ajuda():
        """Exibe instruções de uso e exemplos de comandos possíveis."""
        print("\n🛠 FTPPlus - Cliente de Gerenciamento de Arquivos")
        print("──────────────────────────────────────────────")
        print("\n📌 Primeiro Uso:")
        print("Na primeira vez, você DEVE informar o IP do servidor:")
        print('   ftpplus 127.0.0.1 "listar"')
        print("Depois, pode usar o modo simplificado:")
        print('   ftpplus "listar"')
        print('   ftpplus "enviar arquivo.txt"')
        print("\n📋 Comandos disponíveis:")
        print("  listar               - Lista arquivos no servidor")
        print("  enviar <arquivo>     - Envia arquivo para o servidor")
        print("  excluir <arquivo>    - Remove arquivo do servidor")
        print("  baixar <arquivo>     - Baixa arquivo do servidor")
        print("\n💻 Exemplos de uso:")
        print("Windows:")
        print('   ftpplus 127.0.0.1 "listar"')
        print('   ftpplus 127.0.0.1 "enviar C:\\Fotos\\foto.jpg"')
        print("Linux/Mac:")
        print('   ./ftpplus 127.0.0.1 "listar"')
        print('   ./ftpplus 127.0.0.1 "enviar /home/user/foto.jpg"')

    @staticmethod
    def is_first_run():
        """Retorna True se o arquivo indicador não existir, sinalizando primeira execução."""
        return not os.path.exists(FIRST_RUN_FILE)
    
    @staticmethod
    def mark_initialized():
        """Cria o arquivo indicador de inicialização."""
        with open(FIRST_RUN_FILE, 'w') as f:
            f.write('initialized')

    @staticmethod
    def salvar_ultimo_servidor(ip):
        """Salva o IP do último servidor usado em um arquivo de configuração."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'ultimo_servidor': ip}, f)
        except Exception:
            pass

    @staticmethod
    def obter_ultimo_servidor():
        """Recupera o último IP usado do arquivo de configuração."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('ultimo_servidor')
        except Exception:
            return None

# Execução principal: leitura de argumentos e inicia o cliente
if __name__ == "__main__":
    # Se for a primeira execução, exibe as instruções iniciais
    if FTPClient.is_first_run():
        print("\n🎉 Bem-vindo ao FTPPlus!")
        FTPClient.mostrar_boas_vindas()
        FTPClient.mostrar_ajuda()
        FTPClient.mark_initialized()
        if len(sys.argv) < 3:
            sys.exit(1)
    
    if len(sys.argv) == 1:
        FTPClient.mostrar_ajuda()
        sys.exit(1)

    # Se receber três ou mais argumentos, considera o primeiro como IP e o segundo como comando
    if len(sys.argv) >= 3:
        server_ip = sys.argv[1]
        command = sys.argv[2]
    else:
        # Se não for fornecido o IP, utiliza o último salvo
        server_ip = FTPClient.obter_ultimo_servidor()
        if not server_ip:
            print("❌ Primeiro uso: informe o IP do servidor")
            print('Exemplo: ftpplus 127.0.0.1 "listar"')
            sys.exit(1)
        command = sys.argv[1]

    FTPClient.salvar_ultimo_servidor(server_ip)
    cliente = FTPClient(server_ip)
    cliente.executar(command)
