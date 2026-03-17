/**
 * Crypto Portfolio Tracker - Transaction Functions
 * Loading, displaying, adding, editing, deleting transactions
 */

// ============================================================
// Transaction Loading & Display
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
                <button class="btn btn-icon btn-sm" onclick="editTransaction(${tx.id})">Edit</button>
                <button class="btn btn-icon btn-sm" onclick="deleteTransaction(${tx.id})">Del</button>
            </td>
        </tr>
    `).join('');
}

// ============================================================
// Transaction Modal & CRUD
// ============================================================

function _buildTransactionFormHtml() {
    return `
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
}

function _setDefaultDateOnForm() {
    const dateInput = document.querySelector('input[name="date"]');
    if (dateInput) {
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        dateInput.value = now.toISOString().slice(0, 16);
    }
}

function showAddTransactionModal() {
    const content = _buildTransactionFormHtml();

    const footer = `
        <button class="btn btn-secondary" onclick="closeModal()">Annuler</button>
        <button class="btn btn-primary" onclick="saveTransaction()">Enregistrer</button>
    `;

    openModal('Nouvelle Transaction', content, footer);
    _setDefaultDateOnForm();
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
        showToast('Transaction enregistree', 'success');
        loadTransactions();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteTransaction(id) {
    if (!confirm('Supprimer cette transaction ?')) return;

    try {
        await apiCall(`/transactions/${id}`, { method: 'DELETE' });
        showToast('Transaction supprimee', 'success');
        loadTransactions();
    } catch (error) {
        showToast(error.message, 'error');
    }
}
