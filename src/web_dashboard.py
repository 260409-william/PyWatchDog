from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import json
import os
import logging
from datetime import datetime
from threading import Thread
import time
from pathlib import Path
import yaml

# Importações internas
from .monitor import FileIntegrityMonitor
from .hasher import AdvancedHasher, verify_files_against_baseline
from .alerts import AlertSystem

# Configuração da aplicação Flask
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = 'pywatchdog-secret-key-2024-change-in-production'

# Configuração
class DashboardConfig:
    def __init__(self):
        self.host = '0.0.0.0'
        self.port = 5000
        self.debug = True
        self.monitor = None
        self.hasher = None
        self.data_file = 'data/monitoring_data.json'
        self.config_file = 'config/config.yaml'

# Carregar configuração YAML
def load_config():
    config_path = 'config/config.yaml'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {
        'monitored_dirs': ['/etc', '/usr/bin'],
        'file_types': ['.conf', '.sh', '.py'],
        'hash_algorithm': 'sha256',
        'check_interval': 300,
        'alert_methods': {
            'console': {'enabled': True},
            'email': {'enabled': False},
            'telegram': {'enabled': False}
        }
    }

# Carregar dados de monitoramento
def load_monitoring_data():
    if os.path.exists('data/monitoring_data.json'):
        try:
            with open('data/monitoring_data.json', 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error("Erro ao carregar dados de monitoramento. Criando novo arquivo.")
    
    return {
        'files_baseline': {},
        'alerts': [],
        'scan_history': [],
        'settings': {},
        'statistics': {
            'total_scans': 0,
            'total_files_monitored': 0,
            'total_alerts_generated': 0,
            'last_scan_duration': 0
        }
    }

# Salvar dados
def save_monitoring_data(data):
    os.makedirs('data', exist_ok=True)
    with open('data/monitoring_data.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)

# Inicializar aplicação
config = DashboardConfig()
monitoring_data = load_monitoring_data()
app_config = load_config()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pywatchdog.log'),
        logging.StreamHandler()
    ]
)

# Rotas da aplicação
@app.route('/')
def index():
    return render_template('index.html', 
                         files_count=len(monitoring_data.get('files_baseline', {})),
                         alerts_count=len(monitoring_data.get('alerts', [])),
                         last_scan=monitoring_data.get('scan_history', [])[-1]['timestamp'] 
                         if monitoring_data.get('scan_history') else 'Nunca')

@app.route('/dashboard')
def dashboard():
    stats = {
        'total_files': len(monitoring_data.get('files_baseline', {})),
        'unchanged_files': len([f for f in monitoring_data.get('files_baseline', {}).values() 
                              if f.get('status') == 'unchanged']),
        'modified_files': len([f for f in monitoring_data.get('files_baseline', {}).values() 
                             if f.get('status') == 'modified']),
        'deleted_files': len([f for f in monitoring_data.get('files_baseline', {}).values() 
                            if f.get('status') == 'deleted']),
        'total_alerts': len(monitoring_data.get('alerts', [])),
        'critical_alerts': len([a for a in monitoring_data.get('alerts', []) 
                              if a.get('severity') == 'critical']),
    }
    
    recent_alerts = monitoring_data.get('alerts', [])[-10:]
    modified_files = [f for f in monitoring_data.get('files_baseline', {}).values() 
                     if f.get('status') == 'modified'][-5:]
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_alerts=recent_alerts,
                         modified_files=modified_files)

@app.route('/files')
def files_list():
    files = monitoring_data.get('files_baseline', {})
    return render_template('files.html', files=files)

@app.route('/file/<path:file_path>')
def file_details(file_path):
    file_data = monitoring_data.get('files_baseline', {}).get(file_path)
    if not file_data:
        flash('Arquivo não encontrado', 'danger')
        return redirect(url_for('files_list'))
    
    return render_template('file_details.html', file_path=file_path, file_data=file_data)

@app.route('/alerts')
def alerts_list():
    alerts = monitoring_data.get('alerts', [])
    return render_template('alerts.html', alerts=alerts)

@app.route('/settings')
def settings():
    current_settings = monitoring_data.get('settings', {})
    keys_exist = os.path.exists('keys/private.pem') and os.path.exists('keys/public.pem')
    return render_template('settings.html', settings=current_settings, keys_exist=keys_exist)

# API endpoints
@app.route('/api/scan', methods=['POST'])
def api_scan():
    try:
        data = request.get_json() or {}
        directories = data.get('directories', app_config.get('monitored_dirs', ['/etc', '/usr/bin']))
        file_types = data.get('file_types', app_config.get('file_types', ['.conf', '.sh', '.py']))
        
        # Validar diretórios
        valid_directories = []
        for directory in directories:
            if os.path.exists(directory):
                valid_directories.append(directory)
            else:
                logging.warning(f"Diretório não encontrado: {directory}")
        
        if not valid_directories:
            return jsonify({
                'success': False,
                'message': 'Nenhum diretório válido para scan'
            }), 400
        
        # Configurar hasher
        hasher = AdvancedHasher(
            algorithm=app_config.get('hash_algorithm', 'sha256'),
            private_key_path='keys/private.pem',
            public_key_path='keys/public.pem'
        )
        
        # Criar baseline
        baseline = {}
        total_files = 0
        
        for directory in valid_directories:
            for file_type in file_types:
                try:
                    for file_path in Path(directory).rglob(f"*{file_type}"):
                        if file_path.is_file():
                            file_baseline = hasher.create_file_baseline(
                                str(file_path), 
                                include_signature=app_config.get('enable_signatures', True)
                            )
                            if file_baseline:
                                baseline[str(file_path)] = file_baseline
                                total_files += 1
                except Exception as e:
                    logging.error(f"Erro ao scanear {directory}: {e}")
                    continue
        
        # Atualizar dados
        monitoring_data['files_baseline'] = baseline
        monitoring_data['scan_history'].append({
            'timestamp': datetime.now().isoformat(),
            'directories': valid_directories,
            'file_types': file_types,
            'files_scanned': total_files,
            'duration': 0  # Será preenchido posteriormente
        })
        
        # Atualizar estatísticas
        monitoring_data['statistics']['total_scans'] = len(monitoring_data['scan_history'])
        monitoring_data['statistics']['total_files_monitored'] = total_files
        
        save_monitoring_data(monitoring_data)
        
        return jsonify({
            'success': True,
            'message': f'Baseline criada com {total_files} arquivos',
            'files_scanned': total_files,
            'directories': valid_directories
        })
    
    except Exception as e:
        logging.error(f"Erro durante o scan: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro durante o scan: {str(e)}'
        }), 500

@app.route('/api/verify', methods=['POST'])
def api_verify():
    try:
        hasher = AdvancedHasher(algorithm=app_config.get('hash_algorithm', 'sha256'))
        results = verify_files_against_baseline(monitoring_data.get('files_baseline', {}), hasher)
        
        # Atualizar status dos arquivos
        for file_path in results['unchanged']:
            if file_path in monitoring_data['files_baseline']:
                monitoring_data['files_baseline'][file_path]['status'] = 'unchanged'
        
        for file_info in results['modified']:
            file_path = file_info['file_path']
            if file_path in monitoring_data['files_baseline']:
                monitoring_data['files_baseline'][file_path]['status'] = 'modified'
                monitoring_data['files_baseline'][file_path]['current_hash'] = file_info['current_hash']
                
                # Adicionar alerta
                monitoring_data['alerts'].append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'file_modified',
                    'file_path': file_path,
                    'severity': 'high',
                    'message': f'Arquivo modificado: {file_path}',
                    'details': {
                        'expected_hash': file_info['expected_hash'],
                        'current_hash': file_info['current_hash']
                    }
                })
        
        for file_path in results['deleted']:
            if file_path in monitoring_data['files_baseline']:
                monitoring_data['files_baseline'][file_path]['status'] = 'deleted'
                
                # Adicionar alerta
                monitoring_data['alerts'].append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'file_deleted',
                    'file_path': file_path,
                    'severity': 'critical',
                    'message': f'Arquivo deletado: {file_path}'
                })
        
        # Atualizar estatísticas
        monitoring_data['statistics']['total_alerts_generated'] = len(monitoring_data['alerts'])
        
        save_monitoring_data(monitoring_data)
        
        # Enviar alertas se configurado
        if any([results['modified'], results['deleted']]):
            send_alerts(results)
        
        return jsonify({
            'success': True,
            'results': {
                'unchanged': len(results['unchanged']),
                'modified': len(results['modified']),
                'deleted': len(results['deleted']),
                'errors': len(results['errors'])
            }
        })
    
    except Exception as e:
        logging.error(f"Erro durante verificação: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro durante verificação: {str(e)}'
        }), 500

@app.route('/api/verify-file', methods=['POST'])
def api_verify_file():
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': 'Arquivo não encontrado'
            }), 404
        
        hasher = AdvancedHasher(algorithm=app_config.get('hash_algorithm', 'sha256'))
        
        # Verificar arquivo individual
        baseline_data = monitoring_data['files_baseline'].get(file_path)
        if not baseline_data:
            return jsonify({
                'success': False,
                'message': 'Arquivo não está na baseline'
            }), 404
        
        current_hash = hasher.calculate_hash(file_path)
        baseline_hash = baseline_data['hashes'].get(app_config.get('hash_algorithm', 'sha256'))
        
        if current_hash == baseline_hash:
            monitoring_data['files_baseline'][file_path]['status'] = 'unchanged'
            result = 'unchanged'
        else:
            monitoring_data['files_baseline'][file_path]['status'] = 'modified'
            monitoring_data['files_baseline'][file_path]['current_hash'] = current_hash
            result = 'modified'
        
        save_monitoring_data(monitoring_data)
        
        return jsonify({
            'success': True,
            'result': result,
            'current_hash': current_hash,
            'baseline_hash': baseline_hash
        })
        
    except Exception as e:
        logging.error(f"Erro ao verificar arquivo: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar arquivo: {str(e)}'
        }), 500

@app.route('/api/alerts')
def api_get_alerts():
    alerts = monitoring_data.get('alerts', [])
    return jsonify(alerts)

@app.route('/api/clear-alerts', methods=['POST'])
def api_clear_alerts():
    try:
        monitoring_data['alerts'] = []
        save_monitoring_data(monitoring_data)
        
        return jsonify({
            'success': True,
            'message': 'Alertas limpos com sucesso'
        })
        
    except Exception as e:
        logging.error(f"Erro ao limpar alertas: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao limpar alertas: {str(e)}'
        }), 500

@app.route('/api/stats')
def api_get_stats():
    stats = {
        'total_files': len(monitoring_data.get('files_baseline', {})),
        'unchanged_files': len([f for f in monitoring_data.get('files_baseline', {}).values() 
                              if f.get('status') == 'unchanged']),
        'modified_files': len([f for f in monitoring_data.get('files_baseline', {}).values() 
                             if f.get('status') == 'modified']),
        'deleted_files': len([f for f in monitoring_data.get('files_baseline', {}).values() 
                            if f.get('status') == 'deleted']),
        'total_alerts': len(monitoring_data.get('alerts', [])),
        'critical_alerts': len([a for a in monitoring_data.get('alerts', []) 
                              if a.get('severity') == 'critical']),
        'total_scans': monitoring_data.get('statistics', {}).get('total_scans', 0),
        'last_scan_duration': monitoring_data.get('statistics', {}).get('last_scan_duration', 0)
    }
    return jsonify(stats)

@app.route('/api/export')
def api_export_data():
    try:
        export_data = {
            'export_date': datetime.now().isoformat(),
            'version': '1.0.0',
            'baseline': monitoring_data.get('files_baseline', {}),
            'alerts': monitoring_data.get('alerts', []),
            'scan_history': monitoring_data.get('scan_history', []),
            'statistics': monitoring_data.get('statistics', {})
        }
        
        export_file = f"exports/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('exports', exist_ok=True)
        
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return send_file(export_file, as_attachment=True, download_name='pywatchdog_export.json')
        
    except Exception as e:
        logging.error(f"Erro ao exportar dados: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao exportar dados: {str(e)}'
        }), 500

@app.route('/api/settings/<setting_type>', methods=['POST'])
def api_save_settings(setting_type):
    try:
        data = request.get_json()
        
        if setting_type == 'monitoring':
            monitoring_data['settings'].update({
                'check_interval': data.get('check_interval', 300),
                'hash_algorithm': data.get('hash_algorithm', 'sha256'),
                'enable_signatures': data.get('enable_signatures', True)
            })
        elif setting_type == 'alerts':
            monitoring_data['settings'].update({
                'email_alerts': data.get('email_alerts', False),
                'telegram_alerts': data.get('telegram_alerts', False),
                'alert_email': data.get('alert_email', ''),
                'telegram_chat_id': data.get('telegram_chat_id', '')
            })
        
        save_monitoring_data(monitoring_data)
        
        return jsonify({
            'success': True,
            'message': 'Configurações salvas com sucesso'
        })
        
    except Exception as e:
        logging.error(f"Erro ao salvar configurações: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar configurações: {str(e)}'
        }), 500

@app.route('/api/generate-keys', methods=['POST'])
def api_generate_keys():
    try:
        os.makedirs('keys', exist_ok=True)
        
        hasher = AdvancedHasher()
        hasher.generate_keys('keys/private.pem', 'keys/public.pem')
        
        return jsonify({
            'success': True,
            'message': 'Chaves RSA geradas com sucesso'
        })
        
    except Exception as e:
        logging.error(f"Erro ao gerar chaves: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao gerar chaves: {str(e)}'
        }), 500

# Funções auxiliares
def send_alerts(results):
    """Envia alertas baseado nos resultados da verificação"""
    try:
        alert_system = AlertSystem(app_config)
        
        if results['modified']:
            for file_info in results['modified']:
                alert_system.send_alert(
                    'Arquivo Modificado',
                    f'Arquivo modificado: {file_info["file_path"]}\n'
                    f'Hash esperado: {file_info["expected_hash"]}\n'
                    f'Hash atual: {file_info["current_hash"]}',
                    'email'
                )
        
        if results['deleted']:
            for file_path in results['deleted']:
                alert_system.send_alert(
                    'Arquivo Deletado',
                    f'Arquivo deletado: {file_path}',
                    'email'
                )
                
    except Exception as e:
        logging.error(f"Erro ao enviar alertas: {e}")

def start_monitoring():
    """Inicia monitoramento em background"""
    if config.monitor is None:
        config.monitor = FileIntegrityMonitor()
        config.monitor.create_baseline()
        
        def monitor_loop():
            while True:
                try:
                    config.monitor.monitor_files()
                    time.sleep(config.monitor.config['check_interval'])
                except Exception as e:
                    logging.error(f"Erro no monitoramento: {e}")
                    time.sleep(60)  # Esperar 1 minuto antes de tentar novamente
        
        monitor_thread = Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logging.info("Monitoramento em background iniciado")

# Inicialização
@app.before_first_request
def initialize():
    """Inicializa a aplicação"""
    # Criar diretórios necessários
    os.makedirs('data', exist_ok=True)
    os.makedirs('keys', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Iniciar monitoramento em background
    start_monitoring()

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Criar diretórios necessários
    os.makedirs('data', exist_ok=True)
    os.makedirs('keys', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Iniciar monitoramento
    start_monitoring()
    
    # Executar aplicação Flask
    app.run(
        host=config.host, 
        port=config.port, 
        debug=config.debug,
        threaded=True
    )