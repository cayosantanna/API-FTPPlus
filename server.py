import socket, json, base64, re, os, logging, tempfile, subprocess, shutil  # Adicionado para verificar o clamscan
#base64 garante transferência confiável e evita que dados sejam corrompidos

ALLOWED_EXTENSIONS = {'.zip', '.pdf', '.jpg', '.png', '.sql', '.txt', '.doc', '.gif', '.xlsx', '.jpeg', '.docx', '.htm', '.html', '.potx', '.ppsx', '.ppt', '.pptx', '.xls'}

PASTA_ARQUIVOS = 'arquivos_servidor'
PORTA = 9000
TAMANHO_MAXIMO = 25 * 1024 * 1024  #1024 tamanho em bytes

logging.basicConfig( 
    level=logging.DEBUG,  
    format='[%(asctime)s] %(levelname)s: %(message)s', 
    handlers=[logging.StreamHandler()]  
)


def validar_nome_arquivo(nome):
    # Valida o padrão e a extensão aceita
    if re.match(r'^[\w\-. ]+$', nome):
        ext = os.path.splitext(nome)[1].lower()
        return nome if ext in ALLOWED_EXTENSIONS else None
    return None
# Começar obrigatoriamente com string,pode ter caracteres alfanuméricos e underline,hífen, ponto e espaço, pelo menos um caractere válido, não pode ter caracteres inválidos no meio ou no final.


def processar_comando(comandoRecebido, dadosRequisicao):
    try:
        if comandoRecebido == "listar":
            listaArquivos = os.listdir(PASTA_ARQUIVOS)
            return {"status": "sucesso", "dados": listaArquivos}

        # Extrai e valida o nome do arquivo enviado utilizando apenas o nome base
        nomeArquivo = validar_nome_arquivo(os.path.basename(dadosRequisicao.get('filename')))
        if not nomeArquivo:
            return {"status": "erro", "mensagem": "Nome de arquivo inválido"}

        # monta o caminho completo para o arquivo
        caminhoCompleto = os.path.join(PASTA_ARQUIVOS, nomeArquivo)

        if comandoRecebido == "excluir":  
            if os.path.exists(caminhoCompleto):  
                os.remove(caminhoCompleto)  
                logging.info(f"Arquivo {nomeArquivo} excluído com sucesso.")  
                # Informa a exclusão
                return {"status": "sucesso", "mensagem": f"{nomeArquivo} excluído"} 
            return {"status": "erro", "mensagem": "Arquivo não encontrado"}  # Se não existir, erro
        

        elif comandoRecebido == "enviar": 
            dadosArquivo = dadosRequisicao.get('file_data')  # Obtém os dados do arquivo (base64)
            
            if not dadosArquivo:  
                return {"status": "erro", "mensagem": "Nenhum dado de arquivo recebido"}
            try:
                conteudo_bytes = base64.b64decode(dadosArquivo.encode('utf-8'))  
                # Decodifica a string base64 em bytes

                if len(conteudo_bytes) > TAMANHO_MAXIMO:  
                    return {"status": "erro", "mensagem": "Arquivo excede 25MB"}
                # Cria arquivo temporário para verificação de vírus
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(conteudo_bytes)
                    tmp_path = tmp.name
                if os.name != 'nt':
                    clamscan_exe = shutil.which("clamscan")
                    if clamscan_exe:
                        resultado = subprocess.run([clamscan_exe, tmp_path], capture_output=True)
                        if resultado.returncode != 0:
                            os.remove(tmp_path)
                            return {"status": "erro", "mensagem": "Arquivo suspeito ou vírus detectado"}
                    else:
                        logging.warning("clamscan não encontrado, verificação de vírus ignorada.")
                else:
                    defender_path = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
                    if os.path.exists(defender_path):
                        resultado = subprocess.run([defender_path, "-Scan", "-ScanType", "3", "-File", tmp_path], capture_output=True)
                        if resultado.returncode != 0:
                            os.remove(tmp_path)
                            return {"status": "erro", "mensagem": "Arquivo suspeito ou vírus detectado"}
                    else:
                        logging.warning("Windows Defender não encontrado, verificação de vírus ignorada.")
                os.remove(tmp_path)
                
                # Re-codifica os bytes em base64 para armazenamento
                conteudo_cod = base64.b64encode(conteudo_bytes)
                with open(caminhoCompleto, 'wb') as arquivo: #write in binary mod
                    arquivo.write(conteudo_cod)  # Salva o conteúdo codificado
                logging.info(f"Arquivo {nomeArquivo} recebido e salvo.")  
                return {"status": "sucesso", "mensagem": f"{nomeArquivo} salvo"}  
            
            except Exception as erro:
                logging.error(f"Erro ao processar arquivo: {erro}")
                return {"status": "erro", "mensagem": f"Erro ao processar: {erro}"}

        elif comandoRecebido == "baixar":
            if not os.path.exists(caminhoCompleto):
                return {"status": "erro", "mensagem": "Arquivo não encontrado"}
            
            with open(caminhoCompleto, 'rb') as arquivo:  # read in binary mode
                conteudo_cod = arquivo.read()  # Lê o conteúdo codificado (base64)
            conteudo_bytes = base64.b64decode(conteudo_cod)  # Decodifica para os bytes originais
            conteudo_envio = base64.b64encode(conteudo_bytes).decode('utf-8')  # Re-codifica para envio
            logging.info(f"Arquivo {nomeArquivo} pronto para download.") 
            return {"status": "sucesso", "mensagem": f"{nomeArquivo} enviado", "file_data": conteudo_envio}

        elif comandoRecebido == "baixartodos":
            arquivos = os.listdir(PASTA_ARQUIVOS)
            if len(arquivos) >= 50:
                return {"status": "erro", "mensagem": "Quantidade de arquivos excede o limite para download simultâneo."}
            files = {}
            for nome in arquivos:
                caminho = os.path.join(PASTA_ARQUIVOS, nome)
                with open(caminho, 'rb') as arq:
                    conteudo_cod = arq.read()
                conteudo_bytes = base64.b64decode(conteudo_cod)
                conteudo_envio = base64.b64encode(conteudo_bytes).decode('utf-8')
                files[nome] = conteudo_envio
            logging.info("Comando baixartodos: todos os arquivos enviados.")
            return {"status": "sucesso", "mensagem": "Arquivos enviados", "files": files}

        return {"status": "erro", "mensagem": "Comando desconhecido"}
    except Exception as erro:
        logging.error(f"Erro ao processar comando: {erro}")
        return {"status": "erro", "mensagem": f"Erro ao processar: {erro}"}
        

def iniciar_servidor():
    socketServidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
    socketServidor.settimeout(60)  # Define o tempo limite operações do socket
    socketServidor.bind(('', PORTA))  # Liga o socket à porta 
    socketServidor.listen(5)  #socket escuta até 5 conexões
    logging.info(f"Servidor iniciado na porta {PORTA}")  

    while True:  
        try:
            conexao, enderecoCliente = socketServidor.accept()  
        except socket.timeout:  #tempo limite for excedido
            continue  # Continua aguardando novas conexões
        logging.info(f"Conexão estabelecida com {enderecoCliente}")  

        try:
            mensagem = ""
            while True:  # Loop para ler dados da conexão
                parte = conexao.recv(4096).decode('utf-8')  # Lê os dados da conexão em blocos de 4096 bytes e decodifica.
                
                if not parte:
                    break  
                mensagem = mensagem + parte
                
                if "\n" in mensagem:  # se nova linha
                    mensagem = mensagem.strip() # Remove espaços em branco 
                    break
                
            dadosRecebidos = json.loads(mensagem)  # Converte a mensagem JSON para um objeto (Desserialização)
            comandoRecebido = dadosRecebidos.get('command', '').lower()  # pega o comando da mensagem
            logging.debug(f"Comando recebido: {comandoRecebido}")
            resposta = processar_comando(comandoRecebido, dadosRecebidos) 
            
            conexao.sendall((json.dumps(resposta) + "\n").encode('utf-8'))  # Converte a resposta em JSON com delimitador e envia
            
        except Exception as erro:
            logging.error(f"Erro na conexão: {str(erro)}")  
        finally:
            conexao.close()  

if __name__ == '__main__':
    iniciar_servidor()
