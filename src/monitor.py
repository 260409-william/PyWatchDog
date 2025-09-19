import os
import time
import yaml
import hashlib
import logging
from pathlib import Path
from datetime import datetime

class FileIntegrityMonitor:
    def __init__(self, config_path="config/config.yaml"):
        self.load_config(config_path)
        self.baseline = {}
        self.setup_logging()
        
    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def setup_logging(self):
        logging.basicConfig(
            filename='pywatchdog.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def calculate_hash(self, file_path):
        """Calcula hash do arquivo usando algoritmo configurado"""
        hash_func = getattr(hashlib, self.config['hash_algorithm'])()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            logging.error(f"Erro ao calcular hash de {file_path}: {e}")
            return None
    
    def create_baseline(self):
        """Cria baseline inicial dos arquivos monitorados"""
        logging.info("Criando baseline inicial...")
        self.baseline = {}
        
        for directory in self.config['monitored_dirs']:
            if not os.path.exists(directory):
                logging.warning(f"Diretório não encontrado: {directory}")
                continue
                
            for file_type in self.config['file_types']:
                for file_path in Path(directory).rglob(f"*{file_type}"):
                    if file_path.is_file():
                        file_hash = self.calculate_hash(file_path)
                        if file_hash:
                            self.baseline[str(file_path)] = {
                                'hash': file_hash,
                                'last_modified': os.path.getmtime(file_path),
                                'size': os.path.getsize(file_path)
                            }
        
        logging.info(f"Baseline criada com {len(self.baseline)} arquivos")
        return self.baseline
    
    def monitor_files(self):
        """Monitora arquivos em busca de alterações"""
        logging.info("Iniciando monitoramento...")
        
        while True:
            for file_path, baseline_info in self.baseline.items():
                if not os.path.exists(file_path):
                    self.alert(f"ARQUIVO REMOVIDO: {file_path}")
                    continue
                
                current_hash = self.calculate_hash(file_path)
                current_mtime = os.path.getmtime(file_path)
                current_size = os.path.getsize(file_path)
                
                if current_hash != baseline_info['hash']:
                    self.alert(f"ARQUIVO MODIFICADO: {file_path}")
                
                elif current_mtime != baseline_info['last_modified']:
                    self.alert(f"METADADO ALTERADO: {file_path}")
                
                elif current_size != baseline_info['size']:
                    self.alert(f"TAMANHO ALTERADO: {file_path}")
            
            time.sleep(self.config['check_interval'])
    
    def alert(self, message):
        """Envia alerta de detecção"""
        logging.warning(message)
        print(f"ALERTA: {message}")

if __name__ == "__main__":
    monitor = FileIntegrityMonitor()
    monitor.create_baseline()
    monitor.monitor_files()
