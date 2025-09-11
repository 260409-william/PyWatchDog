#!/usr/bin/env python3
"""
PyWatchdog - Sistema de Monitoramento de Integridade de Arquivos
Arquivo principal de execução
"""

import os
import sys
import logging
from flask import Flask

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pywatchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)

class Config:
    host = '127.0.0.1'
    port = 5000
    debug = True

config = Config()

def setup_directories():
    """Cria todos os diretórios necessários"""
    directories = [
        'data',
        'keys', 
        'exports',
        'static/css',
        'static/js',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Diretório criado/verificado: {directory}")

def check_dependencies():
    """Verifica se todas as dependências estão instaladas"""
    try:
        import flask
        import yaml
        from Crypto.PublicKey import RSA
        import watchdog
        logger.info("Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        logger.error(f"Dependência missing: {e}")
        print(f"Erro: {e}")
        print("Instale as dependências com: pip install -r requirements.txt")
        return False

def load_monitoring_data():
    """Carrega dados de monitoramento"""
    return {
        'total_files': 0,
        'unchanged_files': 0,
        'modified_files': 0,
        'deleted_files': 0,
        'critical_alerts': 0,
        'total_alerts': 0
    }

def start_monitoring():
    """Inicia monitoramento em background"""
    logger.info("Monitoramento em background iniciado")
    # Implementação real virá depois

# Rotas básicas
@app.route('/')
def index():
    return "PyWatchdog - Sistema de Monitoramento"

@app.route('/dashboard')
def dashboard():
    stats = load_monitoring_data()
    return f"Dashboard - Arquivos: {stats['total_files']}"

@app.route('/api/verify', methods=['POST'])
def api_verify():
    return {'success': True, 'message': 'Verificação iniciada'}

@app.route('/api/export')
def api_export():
    return {'success': True, 'data': []}

def main():
    """Função principal"""
    print("=" * 50)
    print("🐕 PyWatchdog - Monitor de Integridade")
    print("=" * 50)
    
    # Setup inicial
    setup_directories()
    
    if not check_dependencies():
        sys.exit(1)
    
    # Iniciar monitoramento em background
    try:
        start_monitoring()
        logger.info("Monitoramento em background iniciado")
    except Exception as e:
        logger.error(f"Erro ao iniciar monitoramento: {e}")
        print(f"Aviso: Monitoramento em background não iniciado: {e}")
    
    # Executar aplicação web
    print(f"🚀 Servidor web iniciado em http://{config.host}:{config.port}")
    print("📊 Acesse o dashboard no seu navegador")
    print("⏹️  Pressione Ctrl+C para parar o servidor")
    print("=" * 50)
    
    try:
        app.run(
            host=config.host, 
            port=config.port, 
            debug=config.debug,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Servidor parado pelo usuário")
        logger.info("Servidor parado pelo usuário")
    except Exception as e:
        logger.error(f"Erro no servidor: {e}")
        print(f"Erro: {e}")

if __name__ == '__main__':
    main()