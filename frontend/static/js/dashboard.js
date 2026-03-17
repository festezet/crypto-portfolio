/**
 * Crypto Portfolio Tracker - Dashboard Functions
 * Charts, history, holdings table, summary cards
 */

// ============================================================
// Dashboard
// ============================================================

async function loadDashboard() {
    try {
        // Charger les donnees en parallele
        const [summary, holdings] = await Promise.all([
            apiCall('/portfolio'),
            apiCall('/holdings')
        ]);

        // Mettre a jour les cartes de resume
        updateSummaryCards(summary);

        // Mettre a jour le tableau des holdings
        updateHoldingsTable(holdings);

        // Mettre a jour les graphiques
        updateCharts(summary, holdings);

        // Charger l'historique (periode par defaut: 30 jours)
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

// ============================================================
// Charts
// ============================================================

let allocationChart = null;
let historyChart = null;
let currentPeriod = 30;

function updateCharts(summary, holdings) {
    const allocationCtx = document.getElementById('allocation-chart');
    if (allocationCtx && holdings.length > 0) {
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

function _buildHistoryDatasets(values, invested) {
    return [
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
    ];
}

function _buildHistoryPlugins() {
    return {
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
    };
}

function _buildHistoryScales() {
    return {
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
    };
}

function _buildHistoryChartConfig(labels, values, invested) {
    return {
        type: 'line',
        data: {
            labels: labels,
            datasets: _buildHistoryDatasets(values, invested)
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: _buildHistoryPlugins(),
            scales: _buildHistoryScales()
        }
    };
}

async function loadHistory(period) {
    try {
        _updatePeriodButtons(period);
        currentPeriod = period;

        const history = await _fetchHistoryData(period);
        if (!history || history.length === 0) {
            return;
        }

        _renderHistoryChart(history);
    } catch (error) {
        console.error('Erreur chargement historique:', error);
    }
}

function _updatePeriodButtons(period) {
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.period == period) {
            btn.classList.add('active');
        }
    });
}

async function _fetchHistoryData(period) {
    const endpoint = period === 'all'
        ? '/portfolio/history?days=9999'
        : `/portfolio/history?days=${period}`;
    return await apiCall(endpoint);
}

function _renderHistoryChart(history) {
    const labels = history.map(s => {
        const date = new Date(s.date);
        return date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'short'
        });
    });

    const values = history.map(s => s.total_value);
    const invested = history.map(s => s.total_invested);

    if (historyChart) {
        historyChart.destroy();
    }

    const ctx = document.getElementById('history-chart');
    if (ctx) {
        historyChart = new Chart(ctx, _buildHistoryChartConfig(labels, values, invested));
    }
}

function generateColors(count) {
    const colors = [
        '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
    ];
    return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
}
