

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });


    initTableFilters();
    

    initCharts();
});


function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Texto copiado para a área de transferência!', 'success');
    }).catch(err => {
        showToast('Erro ao copiar texto: ' + err, 'error');
    });
}

function showToast(message, type = 'info') {
    // Criar container de toasts se não existir
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    

    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}


function initTableFilters() {
    const searchInputs = document.querySelectorAll('input[type="text"][id*="search"]');
    searchInputs.forEach(input => {
        input.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const tableId = this.getAttribute('data-table');
            const table = tableId ? document.getElementById(tableId) : this.closest('.card').querySelector('table');
            
            if (table) {
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(filter) ? '' : 'none';
                });
            }
        });
    });
}

// Gráficos
function initCharts() {
    const chartCanvases = document.querySelectorAll('canvas[data-chart]');
    chartCanvases.forEach(canvas => {
        const chartType = canvas.getAttribute('data-chart-type') || 'doughnut';
        const chartData = JSON.parse(canvas.getAttribute('data-chart-data') || '{}');
        
        if (Object.keys(chartData).length > 0) {
            new Chart(canvas.getContext('2d'), {
                type: chartType,
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        }
                    }
                }
            });
        }
    });
}


async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showToast('Erro na comunicação com o servidor', 'error');
        throw error;
    }
}


function downloadFile(content, fileName, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}


function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    updateThemeToggle(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeToggle(newTheme);
}

function updateThemeToggle(theme) {
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
        toggleBtn.innerHTML = theme === 'light' 
            ? '<i class="fas fa-moon"></i>' 
            : '<i class="fas fa-sun"></i>';
    }
}


initTheme();


document.addEventListener('click', function(e) {
    // Copiar para clipboard
    if (e.target.closest('[data-copy]')) {
        const text = e.target.closest('[data-copy]').getAttribute('data-copy');
        copyToClipboard(text);
    }
    

    if (e.target.closest('[data-download]')) {
        const data = e.target.closest('[data-download]').getAttribute('data-download');
        const fileName = e.target.closest('[data-download]').getAttribute('data-filename') || 'download.txt';
        const contentType = e.target.closest('[data-download]').getAttribute('data-type') || 'text/plain';
        downloadFile(data, fileName, contentType);
    }
});


function startRealTimeMonitoring() {
    const eventSource = new EventSource('/api/events');
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        showToast(`Alerta: ${data.message}`, data.type === 'alert' ? 'warning' : 'info');
        
        if (window.location.pathname === '/dashboard') {
            updateDashboardCounters();
        }
    };
    
    eventSource.onerror = function() {
        console.error('EventSource failed.');
        eventSource.close();
        setTimeout(startRealTimeMonitoring, 5000);
    };
}

function updateDashboardCounters() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            document.querySelectorAll('[data-counter]').forEach(element => {
                const counterType = element.getAttribute('data-counter');
                if (data[counterType] !== undefined) {
                    element.textContent = data[counterType];
                }
            });
        })
        .catch(error => {
            console.error('Error updating counters:', error);
        });
}

if (window.location.pathname === '/dashboard') {
    startRealTimeMonitoring();
}
