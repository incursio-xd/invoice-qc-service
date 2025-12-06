"""
Tests for the InvoiceValidator class.
"""
import pytest
from invoice_qc.validator import InvoiceValidator
from invoice_qc.models import ValidationResult


class TestInvoiceValidator:
    """Test suite for InvoiceValidator."""
    
    def test_validate_valid_invoice(self, validator, sample_invoice):
        """Test validation of a valid invoice."""
        result = validator.validate(sample_invoice)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.invoice_id == 'INV-001'
    
    def test_validate_missing_required_fields(self, validator, invalid_invoice):
        """Test validation catches missing required fields."""
        result = validator.validate(invalid_invoice)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        # Should have errors for empty invoice_number, empty seller_name, missing net_total
        assert any('invoice_number' in error for error in result.errors)
    
    def test_validate_calculation_mismatch(self, validator):
        """Test validation catches incorrect total calculations."""
        invoice = {
            'invoice_number': 'INV-003',
            'invoice_date': '2024-01-15',
            'seller_name': 'ABC Corp',
            'buyer_name': 'XYZ Ltd',
            'currency': 'USD',
            'net_total': 1000.00,
            'tax_amount': 200.00,
            'gross_total': 1100.00  # Wrong! Should be 1200
        }
        
        result = validator.validate(invoice)
        
        assert result.is_valid is False
        assert any('mismatch' in error.lower() for error in result.errors)
    
    def test_validate_future_date(self, validator):
        """Test validation catches future invoice dates."""
        invoice = {
            'invoice_number': 'INV-FUTURE',
            'invoice_date': '2099-12-31',  # Future date
            'seller_name': 'ABC Corp',
            'buyer_name': 'XYZ Ltd',
            'currency': 'USD',
            'net_total': 1000.00,
            'tax_amount': 180.00,
            'gross_total': 1180.00
        }
        
        result = validator.validate(invoice)
        
        assert result.is_valid is False
        assert any('future' in error.lower() for error in result.errors)
    
    def test_validate_due_before_invoice(self, validator):
        """Test validation catches due date before invoice date."""
        invoice = {
            'invoice_number': 'INV-004',
            'invoice_date': '2024-02-15',
            'due_date': '2024-01-15',  # Before invoice date
            'seller_name': 'ABC Corp',
            'buyer_name': 'XYZ Ltd',
            'currency': 'USD',
            'net_total': 1000.00,
            'tax_amount': 180.00,
            'gross_total': 1180.00
        }
        
        result = validator.validate(invoice)
        
        assert result.is_valid is False
        assert any('due date' in error.lower() for error in result.errors)
    
    def test_validate_negative_amounts(self, validator):
        """Test validation catches negative amounts."""
        invoice = {
            'invoice_number': 'INV-005',
            'invoice_date': '2024-01-15',
            'seller_name': 'ABC Corp',
            'buyer_name': 'XYZ Ltd',
            'currency': 'USD',
            'net_total': -1000.00,  # Negative
            'tax_amount': 180.00,
            'gross_total': 1180.00
        }
        
        result = validator.validate(invoice)
        
        assert result.is_valid is False
        assert any('negative' in error.lower() for error in result.errors)
    
    def test_validate_batch(self, validator, sample_invoice, invalid_invoice):
        """Test batch validation of multiple invoices."""
        invoices = [sample_invoice, invalid_invoice]
        
        result = validator.validate_batch(invoices)
        
        assert 'summary' in result
        assert 'results' in result
        assert result['summary']['total_invoices'] == 2
        assert result['summary']['valid_invoices'] >= 1
        assert result['summary']['invalid_invoices'] >= 1
    
    def test_validate_invalid_currency(self, validator):
        """Test validation catches invalid currency."""
        invoice = {
            'invoice_number': 'INV-006',
            'invoice_date': '2024-01-15',
            'seller_name': 'ABC Corp',
            'buyer_name': 'XYZ Ltd',
            'currency': 'XYZ',  # Invalid currency
            'net_total': 1000.00,
            'tax_amount': 180.00,
            'gross_total': 1180.00
        }
        
        result = validator.validate(invoice)
        
        assert result.is_valid is False
        assert any('currency' in error.lower() for error in result.errors)
    
    def test_validate_warnings_for_missing_optional(self, validator, sample_invoice):
        """Test that missing optional fields generate warnings."""
        # Remove optional fields
        invoice = sample_invoice.copy()
        invoice.pop('due_date', None)
        invoice.pop('seller_tax_id', None)
        
        result = validator.validate(invoice)
        
        # Should still be valid but have warnings
        assert len(result.warnings) > 0