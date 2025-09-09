import hashlib
import os
import logging
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto import Random
import json
import base64

class AdvancedHasher:
    def __init__(self, algorithm='sha256', private_key_path=None, public_key_path=None):
        self.algorithm = algorithm.lower()
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self.setup_logging()
        
        # Gerar chaves se não existirem
        if private_key_path and not os.path.exists(private_key_path):
            self.generate_keys(private_key_path, public_key_path)
    
    def setup_logging(self):
        logging.basicConfig(
            filename='hasher.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def generate_keys(self, private_key_path, public_key_path):
        """Gera par de chaves RSA para assinatura digital"""
        try:
            random_generator = Random.new().read
            key = RSA.generate(2048, random_generator)
            
            # Salvar chave privada
            with open(private_key_path, 'wb') as priv_file:
                priv_file.write(key.export_key('PEM'))
            
            # Salvar chave pública
            with open(public_key_path, 'wb') as pub_file:
                pub_file.write(key.publickey().export_key('PEM'))
                
            logging.info(f"Chaves RSA geradas: {private_key_path}, {public_key_path}")
        except Exception as e:
            logging.error(f"Erro ao gerar chaves RSA: {e}")
            raise
    
    def calculate_hash(self, file_path, block_size=65536):
        """Calcula hash do arquivo com algoritmo configurado"""
        if not os.path.exists(file_path):
            logging.error(f"Arquivo não encontrado: {file_path}")
            return None
        
        try:
            hash_func = getattr(hashlib, self.algorithm)()
            
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b""):
                    hash_func.update(block)
            
            return hash_func.hexdigest()
        except Exception as e:
            logging.error(f"Erro ao calcular hash de {file_path}: {e}")
            return None
    
    def calculate_multiple_hashes(self, file_path):
        """Calcula múltiplos hashes para o mesmo arquivo"""
        hashes = {}
        algorithms = ['md5', 'sha1', 'sha256', 'sha512']
        
        for algo in algorithms:
            try:
                hash_func = getattr(hashlib, algo)()
                with open(file_path, 'rb') as f:
                    for block in iter(lambda: f.read(65536), b""):
                        hash_func.update(block)
                hashes[algo] = hash_func.hexdigest()
            except Exception as e:
                logging.error(f"Erro ao calcular {algo} para {file_path}: {e}")
                hashes[algo] = None
        
        return hashes
    
    def sign_data(self, data, private_key_path=None):
        """Assina digitalmente os dados"""
        key_path = private_key_path or self.private_key_path
        if not key_path:
            logging.error("Caminho da chave privada não especificado")
            return None
        
        try:
            with open(key_path, 'rb') as key_file:
                private_key = RSA.import_key(key_file.read())
            
            # Se data for dicionário, converter para JSON string
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True)
            else:
                data_str = str(data)
            
            hash_obj = SHA256.new(data_str.encode())
            signature = pkcs1_15.new(private_key).sign(hash_obj)
            return base64.b64encode(signature).decode()
        except Exception as e:
            logging.error(f"Erro ao assinar dados: {e}")
            return None
    
    def verify_signature(self, data, signature, public_key_path=None):
        """Verifica assinatura digital"""
        key_path = public_key_path or self.public_key_path
        if not key_path:
            logging.error("Caminho da chave pública não especificado")
            return False
        
        try:
            with open(key_path, 'rb') as key_file:
                public_key = RSA.import_key(key_file.read())
            
            # Se data for dicionário, converter para JSON string
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True)
            else:
                data_str = str(data)
            
            hash_obj = SHA256.new(data_str.encode())
            signature_bytes = base64.b64decode(signature)
            pkcs1_15.new(public_key).verify(hash_obj, signature_bytes)
            return True
        except (ValueError, TypeError) as e:
            logging.warning(f"Assinatura inválida: {e}")
            return False
        except Exception as e:
            logging.error(f"Erro ao verificar assinatura: {e}")
            return False
    
    def get_file_metadata(self, file_path):
        """Obtém metadados do arquivo"""
        if not os.path.exists(file_path):
            return None
        
        try:
            stat_info = os.stat(file_path)
            return {
                'size': stat_info.st_size,
                'last_modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'last_accessed': datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                'created': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                'mode': stat_info.st_mode,
                'inode': stat_info.st_ino
            }
        except Exception as e:
            logging.error(f"Erro ao obter metadados de {file_path}: {e}")
            return None
    
    def create_file_baseline(self, file_path, include_signature=True):
        """Cria baseline completa para um arquivo"""
        if not os.path.exists(file_path):
            return None
        
        baseline = {
            'file_path': file_path,
            'hashes': self.calculate_multiple_hashes(file_path),
            'metadata': self.get_file_metadata(file_path),
            'timestamp': datetime.now().isoformat(),
            'algorithm': self.algorithm
        }
        
        if include_signature and self.private_key_path:
            baseline['signature'] = self.sign_data(baseline)
        
        return baseline

# Função de utilidade para verificar hashes em lote
def verify_files_against_baseline(files_baseline, hasher_instance):
    """Verifica vários arquivos contra uma baseline"""
    results = {
        'unchanged': [],
        'modified': [],
        'new': [],
        'deleted': [],
        'errors': []
    }
    
    for file_path, baseline_data in files_baseline.items():
        if not os.path.exists(file_path):
            results['deleted'].append(file_path)
            continue
        
        # Verificar assinatura se existir
        if 'signature' in baseline_data:
            data_to_verify = {k: v for k, v in baseline_data.items() if k != 'signature'}
            if not hasher_instance.verify_signature(data_to_verify, baseline_data['signature']):
                results['errors'].append(f"Assinatura inválida para {file_path}")
        
        # Calcular hash atual
        current_hash = hasher_instance.calculate_hash(file_path)
        if current_hash is None:
            results['errors'].append(f"Erro ao calcular hash para {file_path}")
            continue
        
        # Comparar com hash da baseline
        baseline_hash = baseline_data['hashes'].get(hasher_instance.algorithm)
        if baseline_hash and current_hash == baseline_hash:
            results['unchanged'].append(file_path)
        else:
            results['modified'].append({
                'file_path': file_path,
                'expected_hash': baseline_hash,
                'current_hash': current_hash
            })
    
    return results