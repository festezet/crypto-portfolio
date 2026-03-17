/**
 * Crypto Portfolio Tracker - Import Functions
 * File upload, drag-and-drop, CSV import
 */

// ============================================================
// File Upload Setup
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

// ============================================================
// File Upload Handler
// ============================================================

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
            showToast(`Import reussi : ${result.imported} transactions`, 'success');
            _displayImportResult(result);
        } else {
            showToast(result.error, 'error');
        }
    } catch (error) {
        showToast('Erreur lors de l\'import', 'error');
    }
}

function _displayImportResult(result) {
    document.getElementById('import-result').innerHTML = `
        <div class="card">
            <h4>Resultat de l'import</h4>
            <p>Importees : ${result.imported}</p>
            <p>Ignorees (doublons) : ${result.skipped}</p>
            ${result.errors.length > 0 ? `<p>Erreurs : ${result.errors.length}</p>` : ''}
        </div>
    `;
}
