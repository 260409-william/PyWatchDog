"""
PyWatchdog - Sistema de Monitoramento de Integridade de Arquivos
Package inicialização
"""

__version__ = "1.0.0"
__author__ = "Will"
__description__ = "Sistema de monitoramento de integridade de arquivos com Python"


from .monitor import FileIntegrityMonitor
from .hasher import AdvancedHasher
from .alerts import AlertSystem
from .web_dashboard import app, config

__all__ = [
    'FileIntegrityMonitor',
    'AdvancedHasher', 
    'AlertSystem',
    'app',
    'config'
]
