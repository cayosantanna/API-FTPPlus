# API-FTPPlus

## Objetivo da API FTPPlus

A API FTPPlus foi desenvolvida para realizar o gerenciamento de arquivos entre um cliente e um servidor utilizando sockets. As operações disponíveis incluem:

- **listar:** Listar todos os arquivos disponíveis no diretório do servidor.
- **enviar <arquivo>:** Enviar um arquivo do cliente para o servidor.
- **excluir <arquivo>:** Excluir um arquivo existente no servidor.
- **baixar <arquivo>:** Baixar um arquivo do servidor para o cliente.

API segura para transferência de arquivos via sockets com validação rigorosa e protocolo JSON.

Fornecer uma solução segura para transferência de arquivos entre clientes e servidores com:
- Protocolo de comunicação simples via JSON
- Validação rigorosa de entradas
- Operações básicas de gerenciamento de arquivos

---

## ⚙️ Funcionalidades

| Comando          | Descrição                          | Exemplo de Uso               |
|------------------|------------------------------------|-------------------------------|
| `listar`         | Lista arquivos do servidor         | `python client.py 127.0.0.1 "listar"` |
| `enviar <arquivo>`| Envia arquivo para o servidor      | `python client.py 127.0.0.1 "enviar foto.jpg"` |
| `baixar <arquivo>`| Baixa arquivo do servidor         | `python client.py 127.0.0.1 "baixar relatorio.pdf"` |
| `excluir <arquivo>`| Remove arquivo do servidor       | `python client.py 127.0.0.1 "excluir temp.txt"` |

---

## Funcionamento da Comunicação

### Formato de Mensagem

A comunicação entre cliente e servidor é realizada por meio de mensagens JSON. Cada mensagem possui pelo menos o campo `"command"`, e, para comandos que envolvem arquivos, também contém `"filename"`. No caso do comando **enviar**, o campo `"filedata"` (conteúdo do arquivo codificado em base64) também é enviado.

### Fluxo de Execução

#### Servidor

1. **Inicialização:**
   - Cria o diretório `server_files` (caso não exista) para armazenar os arquivos.
   - Cria um socket que escuta conexões na porta `5000`.

2. **Processamento de Conexões:**
   - Ao aceitar uma conexão, o servidor recebe os dados enviados pelo cliente.
   - Converte a mensagem recebida para JSON e valida o comando.
   - Realiza a operação correspondente (listar, enviar, excluir ou baixar) com as devidas sanitizações.
   - Envia uma resposta JSON ao cliente.

#### Cliente

1. **Recepção de Argumentos:**
   - Recebe argumentos da linha de comando para definir o IP do servidor e o comando a ser executado.
   
2. **Manipulação de Arquivos:**
   - Para comandos que exigem manipulação de arquivos (como **enviar** e **baixar**), o cliente realiza a leitura ou gravação do arquivo no sistema local.

3. **Comunicação:**
   - Conecta-se ao servidor e envia a mensagem JSON com o comando.
   - Aguarda e exibe a resposta do servidor.
   - Se o comando for **baixar**, salva o arquivo recebido.

---

## Sanitização e Boas Práticas

### Sanitização de Nomes de Arquivos

- O servidor utiliza uma expressão regular (`^[\w\-.]+$`) para validar os nomes dos arquivos.
- Essa validação garante que não sejam enviados nomes contendo caracteres especiais ou sequências que possam levar a acesso indevido a outras pastas (por exemplo, `../../`).

### Validação de Comandos

- Apenas os comandos `"listar"`, `"enviar"`, `"excluir"` e `"baixar"` são reconhecidos.
- Caso o comando não seja um destes, o servidor retorna uma mensagem de erro clara.

### Tratamento de Erros

- Em todos os pontos críticos (leitura, escrita de arquivos, comunicação via socket), são utilizados blocos `try/except` para capturar e informar erros.
- Essa abordagem garante maior robustez e confiabilidade na aplicação.
