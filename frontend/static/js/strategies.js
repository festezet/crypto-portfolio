/**
 * Crypto Portfolio Tracker - Strategy Functions
 * Loading and displaying exit strategies
 */

// ============================================================
// Strategy Loading & Display
// ============================================================

async function loadStrategies() {
    try {
        const strategies = await apiCall('/strategies');
        updateStrategiesTable(strategies);

        // Verifier les alertes
        await checkAlerts();
    } catch (error) {
        showToast('Erreur de chargement', 'error');
    }
}

function _renderEmptyStrategies() {
    return `
        <div class="empty-state">
            <div class="icon">Target</div>
            <h3>Aucune strategie configuree</h3>
            <p>Creez une strategie de sortie pour vos cryptos</p>
            <button class="btn btn-primary" onclick="showAddStrategyModal()">Creer une strategie</button>
        </div>
    `;
}

function _renderThresholdItem(t, executedThresholds, triggeredThresholds) {
    const isExecuted = executedThresholds.includes(t.profit_pct);
    const isTriggered = triggeredThresholds.some(x => x.profit_pct === t.profit_pct);
    return `
        <div class="threshold-item ${isExecuted ? 'executed' : ''} ${isTriggered ? 'triggered' : ''}">
            <span class="threshold-profit">+${t.profit_pct}%</span>
            <span class="threshold-action">Vendre ${t.sell_pct}%</span>
            ${isExecuted ? '<span class="badge badge-success">Execute</span>' : ''}
            ${isTriggered && !isExecuted ? '<span class="badge badge-warning">Declenche</span>' : ''}
        </div>
    `;
}

function _renderStrategyCard(s) {
    const thresholdsHtml = s.thresholds.map(t =>
        _renderThresholdItem(t, s.executed_thresholds, s.triggered_thresholds)
    ).join('');

    const alertsHtml = s.pending_alerts > 0 ? `
        <div style="margin-top: 15px;">
            <button class="btn btn-warning" onclick="showAlerts(${s.id})">
                ${s.pending_alerts} alerte(s) en attente
            </button>
        </div>
    ` : '';

    return `
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

            <h4 style="margin: 15px 0 10px;">Seuils configures</h4>
            ${thresholdsHtml}
            ${alertsHtml}
        </div>
    `;
}

function updateStrategiesTable(strategies) {
    const container = document.getElementById('strategies-container');
    if (!container) return;

    if (strategies.length === 0) {
        container.innerHTML = _renderEmptyStrategies();
        return;
    }

    container.innerHTML = strategies.map(s => _renderStrategyCard(s)).join('');
}
