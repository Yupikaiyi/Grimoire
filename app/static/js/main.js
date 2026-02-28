/**
 * Main JavaScript for Grimoire Application
 */

// Global state
let uploadedDocuments = [];
let selectedDocumentId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadArea();
    initializeButtons();
    loadDocuments();
});

/**
 * Initialize drag and drop upload area
 */
function initializeUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    if (!uploadArea) return;

    // Click to select files
    uploadArea.addEventListener('click', (e) => {
        if (e.target.className !== 'click-here') return;
        fileInput.click();
    });

    // File selection
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#764ba2';
        uploadArea.style.backgroundColor = '#f0f0ff';
    });

    uploadArea.addEventListener('dragleave', (e) => {
        uploadArea.style.borderColor = '#667eea';
        uploadArea.style.backgroundColor = '#f8f9ff';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#667eea';
        uploadArea.style.backgroundColor = '#f8f9ff';
        const files = e.dataTransfer.files;
        handleFiles(files);
    });
}

/**
 * Handle file selection from input
 */
function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

/**
 * Handle file upload
 */
function handleFiles(files) {
    const progressContainer = document.getElementById('uploadProgress');
    progressContainer.innerHTML = '';

    Array.from(files).forEach((file, index) => {
        const formData = new FormData();
        formData.append('file', file);

        const progressDiv = document.createElement('div');
        progressDiv.className = 'progress-item';
        progressDiv.innerHTML = `<span>${file.name}</span><span class="spinner"></span>`;
        progressContainer.appendChild(progressDiv);

        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                progressDiv.innerHTML = `<span>${file.name}</span><span style="color: green;">✓ Uploaded</span>`;
                uploadedDocuments.push(data);
                enableButtons();
                loadDocuments();
            } else {
                progressDiv.innerHTML = `<span>${file.name}</span><span style="color: red;">✗ Error</span>`;
            }
        })
        .catch(error => {
            progressDiv.innerHTML = `<span>${file.name}</span><span style="color: red;">✗ Error</span>`;
            console.error('Upload error:', error);
        });
    });
}

/**
 * Initialize button event listeners
 */
function initializeButtons() {
    const extractBtn = document.getElementById('extractBtn');
    const summarizeBtn = document.getElementById('summarizeBtn');
    const searchBtn = document.getElementById('searchBtn');

    if (extractBtn) {
        extractBtn.addEventListener('click', extractText);
    }
    if (summarizeBtn) {
        summarizeBtn.addEventListener('click', summarizeDocument);
    }
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
}

/**
 * Enable/disable buttons based on document selection
 */
function enableButtons() {
    const extractBtn = document.getElementById('extractBtn');
    const summarizeBtn = document.getElementById('summarizeBtn');
    const searchBtn = document.getElementById('searchBtn');

    const hasDocuments = uploadedDocuments.length > 0;

    if (extractBtn) extractBtn.disabled = !hasDocuments;
    if (summarizeBtn) summarizeBtn.disabled = !hasDocuments;
    if (searchBtn) searchBtn.disabled = !hasDocuments;
}

/**
 * Load and display uploaded documents
 */
function loadDocuments() {
    const resultsContainer = document.getElementById('resultsContainer');
    if (!resultsContainer) return;

    if (uploadedDocuments.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">No documents uploaded yet. Upload files to get started.</div>';
        return;
    }

    resultsContainer.innerHTML = uploadedDocuments.map(doc => `
        <div class="result-card" onclick="selectDocument(${doc.document_id})">
            <h4>📄 ${doc.filename}</h4>
            <p>Size: ${formatFileSize(doc.file_size)}</p>
            <div class="result-meta">Uploaded just now</div>
        </div>
    `).join('');
}

/**
 * Extract text from document
 */
function extractText() {
    if (!selectedDocumentId && uploadedDocuments.length > 0) {
        selectedDocumentId = uploadedDocuments[0].document_id;
    }

    if (!selectedDocumentId) {
        showAlert('Please select a document first', 'error');
        return;
    }

    const btn = document.getElementById('extractBtn');
    btn.disabled = true;
    btn.textContent = 'Extracting...';

    fetch(`/api/extract-text/${selectedDocumentId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Text extracted successfully!', 'success');
            displayResults(data);
        } else {
            showAlert(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while extracting text', 'error');
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Extract Text';
    });
}

/**
 * Summarize document
 */
function summarizeDocument() {
    if (!selectedDocumentId && uploadedDocuments.length > 0) {
        selectedDocumentId = uploadedDocuments[0].document_id;
    }

    if (!selectedDocumentId) {
        showAlert('Please select a document first', 'error');
        return;
    }

    const btn = document.getElementById('summarizeBtn');
    btn.disabled = true;
    btn.textContent = 'Summarizing...';

    fetch(`/api/summarize/${selectedDocumentId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Summary generated successfully!', 'success');
            displayResults(data);
        } else {
            showAlert(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while summarizing', 'error');
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Summarize';
    });
}

/**
 * Perform semantic search
 */
function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value.trim();

    if (!query) {
        showAlert('Please enter a search query', 'error');
        return;
    }

    const btn = document.getElementById('searchBtn');
    btn.disabled = true;
    btn.textContent = 'Searching...';

    fetch('/api/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        if (data.results) {
            showAlert('Search completed!', 'success');
            displaySearchResults(data.results);
        } else {
            showAlert(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while searching', 'error');
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Search';
    });
}

/**
 * Display results in the results container
 */
function displayResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    let html = '<div class="result-card">';
    
    if (data.text) {
        html += `<h4>📝 Extracted Text</h4>
                <p>${data.text.substring(0, 500)}${data.text.length > 500 ? '...' : ''}</p>`;
    }
    
    if (data.summary) {
        html += `<h4>✨ Summary</h4>
                <p>${data.summary}</p>`;
    }
    
    html += '</div>';
    resultsContainer.innerHTML = html;
}

/**
 * Display search results
 */
function displaySearchResults(results) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">No results found.</div>';
        return;
    }
    
    resultsContainer.innerHTML = results.map(result => `
        <div class="result-card">
            <h4>🔍 ${result.filename}</h4>
            <p><strong>Relevance:</strong> ${(result.similarity_score * 100).toFixed(1)}%</p>
            <p>${result.summary || 'No summary available'}</p>
            <div class="result-meta">
                ${new Date(result.created_at).toLocaleDateString()}
            </div>
        </div>
    `).join('');
}

/**
 * Select a document
 */
function selectDocument(documentId) {
    selectedDocumentId = documentId;
    console.log('Selected document:', documentId);
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const resultsContainer = document.getElementById('resultsContainer');
    if (!resultsContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    resultsContainer.insertBefore(alertDiv, resultsContainer.firstChild);
    
    // Remove alert after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
