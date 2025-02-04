#!/usr/bin/env bash

# Função para instalar o Python em distribuições Linux
install_python() {
    # Verifica se o arquivo /etc/os-release existe para identificar a distribuição
    if [ -f /etc/os-release ]; then
        . /etc/os-release  # Carrega informações da distribuição
        case $ID in
            ubuntu|debian)
                # Atualiza repositórios e instala python3 e pip3
                sudo apt-get update && sudo apt-get install -y python3 python3-pip
                ;;
            fedora)
                sudo dnf install -y python3 python3-pip
                ;;
            *)
                echo "❌ Sistema não suportado. Instale Python 3.6+ manualmente"
                exit 1
                ;;
        esac
    fi
}

# Verifica se o comando python3 está disponível
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Tentando instalar..."
    install_python   # Chama a função para instalar o Python
fi

# Verifica a versão do Python (precisa ser 3.6 ou superior)
VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$VER < 3.6" | bc -l) )); then
    echo "❌ Requer Python 3.6 ou superior"
    exit 1
fi

# Verifica a existência do pip3; se não existir, baixa e instala
if ! command -v pip3 &> /dev/null; then
    echo "📥 Instalando pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py --user
    rm get-pip.py
fi

# Verifica se o módulo cryptography está instalado; instala, se necessário
if ! python3 -c "import cryptography" &> /dev/null; then
    echo "📥 Instalando biblioteca cryptography..."
    python3 -m pip install --user cryptography
fi

# Executa o cliente passando os argumentos fornecidos na linha de comando
python3 cliente.py "$@"
