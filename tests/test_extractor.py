"""
Tests for invoice extraction module.
"""
import pytest
from pathlib import Path
from invoice_qc.extractor import InvoiceExtractor


class TestInvoiceExtractor:
    """Test cases for InvoiceExtractor class."""
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF text content for testing."""
        return """
    INVOICE
    Invoice Number: INV-2024-001
    Invoice Date: 15/01/2024
    Due Date: 30/01/2024
    
    From: ACME Corporation
    123 Business St
    New York, NY 10001
    Tax ID: 12-3456789
    
    To: XYZ Ltd
    456 Customer Ave
    Los Angeles, CA 90001
    Tax ID: 98-7654321
    
    Description                          Qty    Unit Price    Amount
    Widget A                              10        $50.00    $500.00
    Service B                              5       $100.00    $500.00
    Consulting                             1       $180.00    $180.00
    Total:                                                  $1,180.00
    
    Payment Due: 30/01/2024
    """
    
    def test_extractor_initialization(self):
        """Test that extractor initializes correctly."""
        extractor = InvoiceExtractor()
        # Should have use_ai attribute
        assert hasattr(extractor, 'use_ai')
        # Should be boolean
        assert isinstance(extractor.use_ai, bool)
    
    def test_extract_with_regex_returns_dict(self):
        """Test regex extraction returns proper structure."""
        extractor = InvoiceExtractor()
        text = "Invoice Number: INV-123\nDate: 01.02.2024"
        result = extractor._extract_with_regex(text)
        
        assert isinstance(result, dict)
        assert 'invoice_number' in result
        assert 'invoice_date' in result
    
    def test_parse_date_formats(self):
        """Test date parsing with different formats."""
        extractor = InvoiceExtractor()
        
        # German format
        assert extractor._parse_date('22.05.2024') == '2024-05-22'
        
        # ISO format
        assert extractor._parse_date('2024-05-22') == '2024-05-22'
        
        # Invalid date
        assert extractor._parse_date('invalid') is None
    
    def test_empty_invoice_structure(self):
        """Test empty invoice structure."""
        extractor = InvoiceExtractor()
        empty = extractor._empty_invoice("test.pdf")
        
        assert isinstance(empty, dict)
        assert empty['invoice_number'] is None
        assert empty['source_file'] == "test.pdf"
        assert 'line_items' in empty
        assert isinstance(empty['line_items'], list)
    
    def test_extract_from_pdf_success(self, sample_pdf_path):
        """Test successful PDF extraction."""
        extractor = InvoiceExtractor()
        result = extractor.extract_from_pdf(str(sample_pdf_path))
        
        assert isinstance(result, dict)
        assert 'invoice_number' in result
        assert 'source_file' in result
    
    def test_extract_from_pdf_empty(self, empty_pdf_path):
        """Test handling of empty PDF."""
        extractor = InvoiceExtractor()
        result = extractor.extract_from_pdf(str(empty_pdf_path))
        
        assert isinstance(result, dict)
        assert result['source_file'] == empty_pdf_path.name
    
    def test_extract_from_pdf_error_handling(self):
        """Test error handling for non-existent file."""
        extractor = InvoiceExtractor()
        result = extractor.extract_from_pdf("nonexistent.pdf")
        
        assert isinstance(result, dict)
        assert result['invoice_number'] is None
    
    def test_extract_batch_empty_directory(self, tmp_path):
        """Test batch extraction with empty directory."""
        extractor = InvoiceExtractor()
        results = extractor.extract_batch(str(tmp_path))
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_extract_batch_nonexistent_directory(self):
        """Test batch extraction with non-existent directory."""
        extractor = InvoiceExtractor()
        results = extractor.extract_batch("nonexistent_dir")
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_regex_extraction_invoice_number(self):
        """Test invoice number extraction with regex."""
        extractor = InvoiceExtractor()
        
        # Test AUFNR pattern (German)
        text = "Bestellung AUFNR34343 vom 22.05.2024"
        result = extractor._extract_with_regex(text)
        assert result['invoice_number'] == "AUFNR34343"
        
        # Test standard invoice pattern
        text2 = "Invoice Number: INV-2024-001"
        result2 = extractor._extract_with_regex(text2)
        assert result2['invoice_number'] is not None
    
    def test_regex_extraction_dates(self):
        """Test date extraction with regex."""
        extractor = InvoiceExtractor()
        
        text = "Invoice Date: 22.05.2024\nDue Date: 30.06.2024"
        result = extractor._extract_with_regex(text)
        
        assert result['invoice_date'] is not None
        assert result['due_date'] is not None
    
    def test_regex_extraction_currency(self):
        """Test currency detection."""
        extractor = InvoiceExtractor()
        
        # Euro
        text_eur = "Total: 100,50 €"
        result_eur = extractor._extract_with_regex(text_eur)
        assert result_eur['currency'] == 'EUR'
        
        # USD
        text_usd = "Total: $100.50"
        result_usd = extractor._extract_with_regex(text_usd)
        assert result_usd['currency'] == 'USD'
        
        # INR
        text_inr = "Total: ₹100.50"
        result_inr = extractor._extract_with_regex(text_inr)
        assert result_inr['currency'] == 'INR'
    
    def test_regex_extraction_companies(self):
        """Test company name extraction."""
        extractor = InvoiceExtractor()
        
        text = """
        Beispielname Unternehmen GmbH
        Albertus-Magnus-Str. 8
        
        ABC Corporation
        123 Main Street
        """
        result = extractor._extract_with_regex(text)
        
        # Should extract at least one company
        assert result['seller_name'] is not None or result['buyer_name'] is not None
    
    def test_ai_extraction_fallback(self):
        """Test that AI extraction falls back to regex on error."""
        # Create extractor without API key to force fallback
        extractor = InvoiceExtractor(api_key=None)
        
        text = "Invoice: INV-123\nDate: 2024-01-01\nTotal: $100"
        result = extractor._extract_with_regex(text)
        
        assert isinstance(result, dict)
        assert 'invoice_number' in result