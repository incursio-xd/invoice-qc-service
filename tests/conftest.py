"""
Pytest configuration and fixtures for invoice_qc tests.
"""
import pytest
import tempfile
from pathlib import Path
from invoice_qc.database import Database
from invoice_qc.extractor import InvoiceExtractor
from invoice_qc.validator import InvoiceValidator


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def extractor():
    """Create an InvoiceExtractor instance."""
    return InvoiceExtractor()


@pytest.fixture
def validator(temp_db):
    """Create an InvoiceValidator instance with temp database."""
    return InvoiceValidator(temp_db)


@pytest.fixture
def sample_invoice():
    """Return a valid sample invoice dictionary."""
    return {
        'invoice_number': 'INV-001',
        'invoice_date': '2024-01-15',
        'due_date': '2024-02-15',
        'seller_name': 'ABC Corp',
        'seller_address': '123 Business St',
        'seller_tax_id': 'TAX123',
        'buyer_name': 'XYZ Ltd',
        'buyer_address': '456 Commerce Ave',
        'buyer_tax_id': 'TAX456',
        'currency': 'USD',
        'net_total': 1000.00,
        'tax_rate': 18.0,
        'tax_amount': 180.00,
        'gross_total': 1180.00,
        'line_items': [
            {
                'description': 'Product A',
                'quantity': 10,
                'unit_price': 100.00,
                'line_total': 1000.00
            }
        ]
    }


@pytest.fixture
def invalid_invoice():
    """Return an invalid invoice (missing required fields)."""
    return {
        'invoice_number': '',
        'invoice_date': '2024-01-15',
        'seller_name': '',
        'buyer_name': 'XYZ Ltd',
        'currency': 'USD',
        'net_total': None,
        'tax_amount': 100.00,
        'gross_total': 1100.00
    }


@pytest.fixture
def sample_pdf_content():
    """Return sample PDF text content for testing."""
    return """
    INVOICE
    Invoice Number: INV-2024-001
    Invoice Date: 15/01/2024
    Due Date: 30/01/2024
    
    From: ABC Corporation
    123 Business Street
    Tax ID: GB123456789
    
    To: XYZ Limited
    456 Commerce Avenue
    VAT: US987654321
    
    Description         Quantity    Unit Price    Total
    Product A          10          $50.00        $500.00
    Product B          5           $100.00       $500.00
    
    Subtotal:                                    $1,000.00
    Tax (18%):                                   $180.00
    Total:                                       $1,180.00
    
    Payment Due: 30/01/2024
    """


@pytest.fixture
def api_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from invoice_qc.api.main import app
    return TestClient(app)


@pytest.fixture
def sample_invoices(sample_invoice):
    """Return multiple sample invoices."""
    invoice2 = sample_invoice.copy()
    invoice2['invoice_number'] = 'INV-002'
    invoice2['gross_total'] = 2360.00
    invoice2['net_total'] = 2000.00
    invoice2['tax_amount'] = 360.00
    
    return [sample_invoice, invoice2]

import fitz  # PyMuPDF
from pathlib import Path

@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "sample_invoice.pdf"
    
    # Create a simple PDF with PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    
    # Add some invoice text
    text = """
    INVOICE
    Invoice Number: INV-2024-001
    Invoice Date: 15/01/2024
    Due Date: 30/01/2024
    
    From: ACME Corporation
    123 Business St
    Tax ID: 12-3456789
    
    To: XYZ Ltd
    456 Customer Ave
    Tax ID: 98-7654321
    
    Net Total: $1,000.00
    Tax (19%): $190.00
    Gross Total: $1,190.00
    
    Payment Due: 30/01/2024
    """
    
    page.insert_text((50, 50), text, fontsize=11)
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path


@pytest.fixture
def empty_pdf_path(tmp_path):
    """Create an empty PDF file for testing."""
    pdf_path = tmp_path / "empty.pdf"
    
    # Create an empty PDF
    doc = fitz.open()
    doc.new_page()  # Add blank page
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path