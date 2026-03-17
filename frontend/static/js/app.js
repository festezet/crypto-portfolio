/**
 * Crypto Portfolio Tracker - Core Application JavaScript
 * Shared utilities: API, formatting, toast, modal, loading, alerts, refresh
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

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

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

function showEmpty(containerId, message = 'Aucune donnee') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">Empty</div>
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

function updateLastUpdateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = `Derniere MaJ: ${timeStr}`;
    }
}

// ============================================================
// Initialization (alerts only - page init is in page-specific JS)
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    checkAlerts();
    setInterval(checkAlerts, 5 * 60 * 1000);
});
