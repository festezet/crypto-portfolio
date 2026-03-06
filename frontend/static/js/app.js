/**
 * Crypto Portfolio Tracker - Application JavaScript
 */

// ============================================================
// API Configuration
// ============================================================

const API_BASE = '/api';

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API Error');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ============================================================
// Utility Functions
// ============================================================

function formatCurrency(value, currency = 'EUR') {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatNumber(value, decimals = 2) {
    return new Intl.NumberFormat('fr-FR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

function formatPercent(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${formatNumber(value)}%`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getCryptoIcon(symbol) {
    // Retourne les initiales du symbole
    return symbol.substring(0, 2).toUpperCase();
}

function getColorClass(value) {
    if (value > 0) return 'positive';
    if (value < 0) return 'negative';
    return 'neutral';
}

// ============================================================
// Toast Notifications
// ============================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================
// Modal Functions
// ============================================================

function openModal(title, content, footer = '') {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-footer').innerHTML = footer;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// Fermer modal avec Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Fermer modal en cliquant à l'extérieur
document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
});

// ============================================================
// Loading State
// ============================================================

function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    }
}

function showEmpty(containerId, message = 'Aucune donnée') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>${message}</h3>
            </div>
        `;
    }
}

// ============================================================
// Alerts Check
// ============================================================

async function checkAlerts() {
    try {
        const alerts = await apiCall('/alerts');
        const indicator = document.getElementById('alerts-indicator');
        const count = document.getElementById('alerts-count');

        if (alerts.length > 0) {
            indicator.style.display = 'flex';
            count.textContent = alerts.length;
        } else {
            indicator.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking alerts:', error);
    }
}

// ============================================================
// Global Refresh
// ============================================================

document.getElementById('btn-refresh')?.addEventListener('click', () => {
    window.location.reload();
});

// Update last update time
function updateLastUpdateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = `Dernière MàJ: ${timeStr}`;
    }
}

// ============================================================
// Dashboard Functions
// ============================================================

async function loadDashboard() {
    try {
        // Charger les données en parallèle
        const [summary, holdings] = await Promise.all([
            apiCall('/portfolio'),
            apiCall('/holdings')
        ]);

        // Mettre à jour les cartes de résumé
        updateSummaryCards(summary);

        // Mettre à jour le tableau des holdings
        updateHoldingsTable(holdings);

        // Mettre à jour les graphiques
        updateCharts(summary, holdings);

        // Charger l'historique (période par défaut: 30 jours)
        await loadHistory(30);

        updateLastUpdateTime();
    } catch (error) {
        showToast('Erreur de chargement', 'error');
    }
}

function updateSummaryCards(summary) {
    const totalValueEl = document.getElementById('total-value');
    const totalInvestedEl = document.getElementById('total-invested');
    const totalPnlEl = document.getElementById('total-pnl');
    const totalPnlPctEl = document.getElementById('total-pnl-pct');

    if (totalValueEl) {
        totalValueEl.textContent = formatCurrency(summary.total_value);
    }
    if (totalInvestedEl) {
        totalInvestedEl.textContent = formatCurrency(summary.total_invested);
    }
    if (totalPnlEl) {
        totalPnlEl.textContent = formatCurrency(summary.total_pnl_brut);
        totalPnlEl.className = `value ${getColorClass(summary.total_pnl_brut)}`;
    }
    if (totalPnlPctEl) {
        totalPnlPctEl.textContent = formatPercent(summary.total_pnl_pct);
        totalPnlPctEl.className = `change ${getColorClass(summary.total_pnl_pct)}`;
    }
}

function updateHoldingsTable(holdings) {
    const tbody = document.getElementById('holdings-tbody');
    if (!tbody) return;

    if (holdings.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center">
                    <div class="empty-state">
                        <p>Aucune position. Importez vos transactions pour commencer.</p>
                        <a href="/import" class="btn btn-primary btn-sm">Importer</a>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = holdings.map(h => `
        <tr onclick="window.location='/holdings/${h.symbol}'">
            <td>
                <div class="crypto-info">
                    <div class="crypto-icon">${getCryptoIcon(h.symbol)}</div>
                    <div>
                        <div class="crypto-name">${h.symbol}</div>
                        <div class="crypto-symbol">${h.name}</div>
                    </div>
                </div>
            </td>
            <td class="text-right">${formatNumber(h.volume, 6)}</td>
            <td class="text-right">${formatCurrency(h.pmp)}</td>
            <td class="text-right">
                ${formatCurrency(h.current_price)}
                ${h.change_24h !== null ? `<div class="change ${getColorClass(h.change_24h)}">${formatPercent(h.change_24h)}</div>` : ''}
            </td>
            <td class="text-right">${formatCurrency(h.current_value)}</td>
            <td class="text-right ${getColorClass(h.pnl_brut)}">${formatCurrency(h.pnl_brut)}</td>
            <td class="text-right ${getColorClass(h.pnl_pct)}">${formatPercent(h.pnl_pct)}</td>
            <td class="text-center">
                <span class="tag">${h.exchanges.join(', ')}</span>
            </td>
        </tr>
    `).join('');
}

let allocationChart = null;
let historyChart = null;
let currentPeriod = 30; // Période par défaut

function updateCharts(summary, holdings) {
    // Graphique de répartition (Pie Chart)
    const allocationCtx = document.getElementById('allocation-chart');
    if (allocationCtx && holdings.length > 0) {
        // Détruire l'ancien graphique si existant
        if (allocationChart) {
            allocationChart.destroy();
        }
        allocationChart = new Chart(allocationCtx, {
            type: 'doughnut',
            data: {
                labels: holdings.map(h => h.symbol),
                datasets: [{
                    data: holdings.map(h => h.current_value),
                    backgroundColor: generateColors(holdings.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#f8fafc' }
                    }
                }
            }
        });
    }
}

async function loadHistory(period = 30) {
    try {
        // Mettre à jour l'UI des boutons
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.period == period) {
                btn.classList.add('active');
            }
        });

        currentPeriod = period;

        // Récupérer l'historique
        const endpoint = period === 'all'
            ? '/portfolio/history?days=9999'
            : `/portfolio/history?days=${period}`;

        const history = await apiCall(endpoint);

        if (!history || history.length === 0) {
            console.log('Pas d\'historique disponible');
            return;
        }

        // Préparer les données pour Chart.js
        const labels = history.map(s => {
            const date = new Date(s.date);
            return date.toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'short'
            });
        });

        const values = history.map(s => s.total_value);
        const invested = history.map(s => s.total_invested);

        // Détruire l'ancien graphique si existant
        if (historyChart) {
            historyChart.destroy();
        }

        // Créer le graphique
        const ctx = document.getElementById('history-chart');
        if (ctx) {
            historyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Valeur totale',
                            data: values,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Total investi',
                            data: invested,
                            borderColor: '#64748b',
                            backgroundColor: 'transparent',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            fill: false,
                            tension: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#f8fafc',
                                usePointStyle: true,
                                padding: 15
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(30, 41, 59, 0.95)',
                            titleColor: '#f8fafc',
                            bodyColor: '#f8fafc',
                            borderColor: '#334155',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: true,
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y;
                                    return label + ': ' + formatCurrency(value);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(51, 65, 85, 0.3)',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                maxRotation: 45,
                                minRotation: 0
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(51, 65, 85, 0.3)',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                callback: function(value) {
                                    return new Intl.NumberFormat('fr-FR', {
                                        style: 'currency',
                                        currency: 'EUR',
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                    }).format(value);
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Erreur chargement historique:', error);
    }
}

function generateColors(count) {
    const colors = [
        '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
    ];
    return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
}

// ============================================================
// Transaction Functions
// ============================================================

async function loadTransactions() {
    try {
        showLoading('transactions-container');
        const result = await apiCall('/transactions');
        updateTransactionsTable(result.transactions);
        updateLastUpdateTime();
    } catch (error) {
        showToast('Erreur de chargement', 'error');
    }
}

function updateTransactionsTable(transactions) {
    const tbody = document.getElementById('transactions-tbody');
    if (!tbody) return;

    if (transactions.length === 0) {
        showEmpty('transactions-container', 'Aucune transaction');
        return;
    }

    tbody.innerHTML = transactions.map(tx => `
        <tr>
            <td>${formatDateTime(tx.date)}</td>
            <td>
                <span class="badge ${tx.type === 'BUY' ? 'badge-success' : 'badge-danger'}">
                    ${tx.type}
                </span>
            </td>
            <td>${tx.crypto_symbol}</td>
            <td class="text-right">${formatNumber(tx.volume, 6)}</td>
            <td class="text-right">${formatCurrency(tx.price)}</td>
            <td class="text-right">${formatCurrency(tx.total)}</td>
            <td class="text-right">${formatCurrency(tx.fee)}</td>
            <td><span class="tag">${tx.exchange}</span></td>
            <td>
                <button class="btn btn-icon btn-sm" onclick="editTransaction(${tx.id})">✏️</button>
                <button class="btn btn-icon btn-sm" onclick="deleteTransaction(${tx.id})">🗑️</button>
            </td>
        </tr>
    `).join('');
}

function showAddTransactionModal() {
    const content = `
        <form id="transaction-form">
            <div class="form-group">
                <label>Type</label>
                <select name="type" required>
                    <option value="BUY">Achat</option>
                    <option value="SELL">Vente</option>
                </select>
            </div>
            <div class="form-group">
                <label>Crypto (symbole)</label>
                <input type="text" name="symbol" placeholder="BTC, ETH..." required>
            </div>
            <div class="form-group">
                <label>Date</label>
                <input type="datetime-local" name="date" required>
            </div>
            <div class="form-group">
                <label>Volume</label>
                <input type="number" name="volume" step="any" required>
            </div>
            <div class="form-group">
                <label>Prix unitaire (EUR)</label>
                <input type="number" name="price" step="any" required>
            </div>
            <div class="form-group">
                <label>Frais (EUR)</label>
                <input type="number" name="fee" step="any" value="0">
            </div>
            <div class="form-group">
                <label>Exchange</label>
                <select name="exchange">
                    <option value="binance">Binance</option>
                    <option value="kucoin">Kucoin</option>
                    <option value="manual">Manuel</option>
                </select>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea name="notes" rows="2"></textarea>
            </div>
        </form>
    `;

    const footer = `
        <button class="btn btn-secondary" onclick="closeModal()">Annuler</button>
        <button class="btn btn-primary" onclick="saveTransaction()">Enregistrer</button>
    `;

    openModal('Nouvelle Transaction', content, footer);

    // Définir la date par défaut à maintenant
    const dateInput = document.querySelector('input[name="date"]');
    if (dateInput) {
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        dateInput.value = now.toISOString().slice(0, 16);
    }
}

async function saveTransaction() {
    const form = document.getElementById('transaction-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        await apiCall('/transactions', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        closeModal();
        showToast('Transaction enregistrée', 'success');
        loadTransactions();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteTransaction(id) {
    if (!confirm('Supprimer cette transaction ?')) return;

    try {
        await apiCall(`/transactions/${id}`, { method: 'DELETE' });
        showToast('Transaction supprimée', 'success');
        loadTransactions();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ============================================================
// Import Functions
// ============================================================

function setupFileUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    const source = document.getElementById('import-source')?.value || 'auto';
    formData.append('source', source);

    try {
        showToast('Import en cours...', 'info');

        const response = await fetch(`${API_BASE}/import`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Import réussi : ${result.imported} transactions`, 'success');
            document.getElementById('import-result').innerHTML = `
                <div class="card">
                    <h4>Résultat de l'import</h4>
                    <p>✅ Importées : ${result.imported}</p>
                    <p>⏭️ Ignorées (doublons) : ${result.skipped}</p>
                    ${result.errors.length > 0 ? `<p>❌ Erreurs : ${result.errors.length}</p>` : ''}
                </div>
            `;
        } else {
            showToast(result.error, 'error');
        }
    } catch (error) {
        showToast('Erreur lors de l\'import', 'error');
    }
}

// ============================================================
// Strategy Functions
// ============================================================

async function loadStrategies() {
    try {
        const strategies = await apiCall('/strategies');
        updateStrategiesTable(strategies);

        // Vérifier les alertes
        await checkAlerts();
    } catch (error) {
        showToast('Erreur de chargement', 'error');
    }
}

function updateStrategiesTable(strategies) {
    const container = document.getElementById('strategies-container');
    if (!container) return;

    if (strategies.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">🎯</div>
                <h3>Aucune stratégie configurée</h3>
                <p>Créez une stratégie de sortie pour vos cryptos</p>
                <button class="btn btn-primary" onclick="showAddStrategyModal()">Créer une stratégie</button>
            </div>
        `;
        return;
    }

    container.innerHTML = strategies.map(s => `
        <div class="card">
            <div class="card-header">
                <div class="crypto-info">
                    <div class="crypto-icon">${getCryptoIcon(s.crypto_symbol)}</div>
                    <div>
                        <div class="crypto-name">${s.crypto_symbol}</div>
                        <span class="badge ${s.enabled ? 'badge-success' : 'badge-warning'}">
                            ${s.enabled ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
                <div>
                    <button class="btn btn-sm btn-secondary" onclick="editStrategy(${s.id})">Modifier</button>
                </div>
            </div>

            <div class="grid grid-2">
                <div>
                    <p class="label">P&L actuel</p>
                    <p class="value ${getColorClass(s.current_profit_pct)}">${formatPercent(s.current_profit_pct)}</p>
                </div>
                <div>
                    <p class="label">Prochain seuil</p>
                    <p class="value">${s.next_threshold ? `${s.next_threshold.profit_pct}%` : 'Aucun'}</p>
                </div>
            </div>

            <h4 style="margin: 15px 0 10px;">Seuils configurés</h4>
            ${s.thresholds.map(t => {
                const isExecuted = s.executed_thresholds.includes(t.profit_pct);
                const isTriggered = s.triggered_thresholds.some(x => x.profit_pct === t.profit_pct);
                return `
                    <div class="threshold-item ${isExecuted ? 'executed' : ''} ${isTriggered ? 'triggered' : ''}">
                        <span class="threshold-profit">+${t.profit_pct}%</span>
                        <span class="threshold-action">Vendre ${t.sell_pct}%</span>
                        ${isExecuted ? '<span class="badge badge-success">Exécuté</span>' : ''}
                        ${isTriggered && !isExecuted ? '<span class="badge badge-warning">Déclenché</span>' : ''}
                    </div>
                `;
            }).join('')}

            ${s.pending_alerts > 0 ? `
                <div style="margin-top: 15px;">
                    <button class="btn btn-warning" onclick="showAlerts(${s.id})">
                        ${s.pending_alerts} alerte(s) en attente
                    </button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

// ============================================================
// Initialization
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Vérifier quelle page on est
    const path = window.location.pathname;

    if (path === '/' || path === '/dashboard') {
        loadDashboard();
    } else if (path === '/transactions') {
        loadTransactions();
    } else if (path === '/strategies') {
        loadStrategies();
    } else if (path === '/import') {
        setupFileUpload();
    }

    // Vérifier les alertes toutes les 5 minutes
    checkAlerts();
    setInterval(checkAlerts, 5 * 60 * 1000);
});
