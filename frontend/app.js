/**
 * Invoice QC Console - Frontend JavaScript
 */

const API_BASE = 'http://localhost:8000';
let currentResults = null;

// Check API health on load
window.addEventListener('load', async () => {
    await checkApiHealth();
});

// Health check
async function checkApiHealth() {
    const statusElement = document.getElementById('apiStatus');
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        if (data.status === 'ok') {
            statusElement.textContent = '✓ Connected';
            statusElement.style.color = 'green';
        } else {
            statusElement.textContent = '⚠ Degraded';
            statusElement.style.color = 'orange';
        }
    } catch (error) {
        statusElement.textContent = '✗ Disconnected';
        statusElement.style.color = 'red';
        console.error('API health check failed:', error);
    }
}

// Handle PDF upload form
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const filesInput = document.getElementById('pdfFiles');
    const files = filesInput.files;
    
    if (files.length === 0) {
        alert('Please select at least one PDF file');
        return;
    }
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = '<p><strong>Processing...</strong> Extracting and validating PDFs...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/extract-and-validate-pdfs`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        statusDiv.innerHTML = `<p style="color: green;"><strong>✓ Success!</strong> Processed ${data.total_files} file(s)</p>`;
        
        // Transform data to match expected format
        const transformedData = {
            summary: data.summary,
            results: data.results.map(r => ({
                invoice_id: r.validation.invoice_id,
                invoice_date: r.extracted_data.invoice_date,
                seller_name: r.extracted_data.seller_name,
                buyer_name: r.extracted_data.buyer_name,
                currency: r.extracted_data.currency,
                gross_total: r.extracted_data.gross_total,
                is_valid: r.validation.is_valid,
                errors: r.validation.errors,
                warnings: r.validation.warnings || []
            }))
        };
        
        displayResults(transformedData);
    } catch (error) {
        console.error('Error:', error);
        statusDiv.innerHTML = `<p style="color: red;"><strong>✗ Error:</strong> ${error.message}</p>`;
    }
});

// Handle JSON validation form
document.getElementById('jsonForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const jsonText = document.getElementById('jsonInput').value.trim();
    
    if (!jsonText) {
        alert('Please enter JSON data');
        return;
    }
    
    let invoices;
    try {
        invoices = JSON.parse(jsonText);
        if (!Array.isArray(invoices)) {
            invoices = [invoices];
        }
    } catch (error) {
        alert('Invalid JSON format: ' + error.message);
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/validate-json`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(invoices)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Validation error: ' + error.message);
    }
});

// Display results in table
function displayResults(data) {
    currentResults = data;
    
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    
    // Display summary
    const summary = data.summary;
    const summaryDiv = document.getElementById('summary');
    
    const validRate = summary.total_invoices > 0 
        ? (summary.valid_invoices / summary.total_invoices * 100).toFixed(1)
        : 0;
    
    summaryDiv.innerHTML = `
        <table border="1" cellpadding="8" cellspacing="0">
            <tr>
                <th>Total Invoices</th>
                <td>${summary.total_invoices}</td>
            </tr>
            <tr>
                <th>Valid Invoices</th>
                <td style="color: green;"><strong>${summary.valid_invoices}</strong></td>
            </tr>
            <tr>
                <th>Invalid Invoices</th>
                <td style="color: red;"><strong>${summary.invalid_invoices}</strong></td>
            </tr>
            <tr>
                <th>Validation Rate</th>
                <td><strong>${validRate}%</strong></td>
            </tr>
        </table>
    `;
    
    // Display detailed results table
    const tbody = document.querySelector('#resultsTable tbody');
    tbody.innerHTML = '';
    
    data.results.forEach(result => {
        const row = tbody.insertRow();
        
        row.innerHTML = `
            <td>${result.invoice_id || 'N/A'}</td>
            <td>${result.invoice_date || 'N/A'}</td>
            <td>${result.seller_name || 'N/A'}</td>
            <td>${result.buyer_name || 'N/A'}</td>
            <td>${result.currency || 'N/A'}</td>
            <td>${result.gross_total !== null && result.gross_total !== undefined ? result.gross_total.toFixed(2) : 'N/A'}</td>
            <td style="color: ${result.is_valid ? 'green' : 'red'}; font-weight: bold;">
                ${result.is_valid ? '✓ Valid' : '✗ Invalid'}
            </td>
            <td>${formatErrors(result.errors, result.warnings)}</td>
        `;
        
        row.dataset.valid = result.is_valid;
    });
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Format errors and warnings
function formatErrors(errors, warnings) {
    const parts = [];
    
    if (errors && errors.length > 0) {
        parts.push('<strong>Errors:</strong><ul>' + 
            errors.map(e => `<li>${escapeHtml(e)}</li>`).join('') + 
            '</ul>');
    }
    
    if (warnings && warnings.length > 0) {
        parts.push('<em>Warnings:</em><ul>' + 
            warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('') + 
            '</ul>');
    }
    
    return parts.length > 0 ? parts.join('') : 'None';
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Filter invalid invoices
document.getElementById('filterInvalid').addEventListener('change', (e) => {
    const filterValid = document.getElementById('filterValid').checked;
    const rows = document.querySelectorAll('#resultsTable tbody tr');
    
    rows.forEach(row => {
        const isValid = row.dataset.valid === 'true';
        
        if (e.target.checked && isValid) {
            row.style.display = 'none';
        } else if (filterValid && !isValid) {
            row.style.display = 'none';
        } else if (!e.target.checked && !filterValid) {
            row.style.display = '';
        } else if (e.target.checked && !isValid) {
            row.style.display = '';
        }
    });
    
    if (e.target.checked) {
        document.getElementById('filterValid').checked = false;
    }
});

// Filter valid invoices
document.getElementById('filterValid').addEventListener('change', (e) => {
    const filterInvalid = document.getElementById('filterInvalid').checked;
    const rows = document.querySelectorAll('#resultsTable tbody tr');
    
    rows.forEach(row => {
        const isValid = row.dataset.valid === 'true';
        
        if (e.target.checked && !isValid) {
            row.style.display = 'none';
        } else if (filterInvalid && isValid) {
            row.style.display = 'none';
        } else if (!e.target.checked && !filterInvalid) {
            row.style.display = '';
        } else if (e.target.checked && isValid) {
            row.style.display = '';
        }
    });
    
    if (e.target.checked) {
        document.getElementById('filterInvalid').checked = false;
    }
});

// Download report
document.getElementById('downloadReport').addEventListener('click', () => {
    if (!currentResults) {
        alert('No results to download');
        return;
    }
    
    const dataStr = JSON.stringify(currentResults, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `invoice-validation-report-${Date.now()}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
});

// Clear results
document.getElementById('clearResults').addEventListener('click', () => {
    if (confirm('Clear all results?')) {
        document.getElementById('resultsSection').style.display = 'none';
        document.querySelector('#resultsTable tbody').innerHTML = '';
        document.getElementById('summary').innerHTML = '';
        currentResults = null;
    }
});

// Clear upload form
document.getElementById('clearUpload').addEventListener('click', () => {
    document.getElementById('pdfFiles').value = '';
    document.getElementById('uploadStatus').innerHTML = '';
});

// Clear JSON form
document.getElementById('clearJson').addEventListener('click', () => {
    document.getElementById('jsonInput').value = '';
});