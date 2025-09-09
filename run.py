#!/usr/bin/env python3
"""
PyWatchdog - Sistema de Monitoramento de Integridade de Arquivos
Arquivo principal de execução
"""

import os
import sys
import logging
from src.web_dashboard import app, config, load_monitoring_data, start_monitoring

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pywatchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def setup_directories():
    """Cria todos os diretórios necessários"""
    directories = [
        'data',
        'keys', 
        'exports',
        'templates',
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
        logger.info("Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        logger.error(f"Dependência missing: {e}")
        print(f"Erro: {e}")
        print("Instale as dependências com: pip install -r requirements.txt")
        return False

def main():
    """Função principal"""
    print("=" * 50)
    print("🐕 PyWatchdog - Monitor de Integridade")
    print("=" * 50)
    
    # Setup inicial
    setup_directories()
    
    if not check_dependencies():
        sys.exit(1)
    
    # Carregar dados de monitoramento
    global monitoring_data
    monitoring_data = load_monitoring_data()
    
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