"""
Tests for Pydantic models.
"""
import pytest
from datetime import date
from decimal import Decimal
from invoice_qc.models import (
    Invoice,
    LineItem,
    ValidationResult,
    ValidationSummary,
    CurrencyEnum
)


class TestLineItem:
    """Test LineItem model."""
    
    def test_create_valid_line_item(self):
        """Test creating a valid line item."""
        item = LineItem(
            description="Product A",
            quantity=10,
            unit_price=Decimal('100.00'),
            line_total=Decimal('1000.00')
        )
        
        assert item.description == "Product A"
        assert item.quantity == 10
        assert item.unit_price == Decimal('100.00')
    
    def test_line_item_auto_calculates_total(self):
        """Test that line item auto-corrects total if wrong."""
        item = LineItem(
            description="Product B",
            quantity=5,
            unit_price=Decimal('20.00'),
            line_total=Decimal('99.00')  # Wrong, should be 100
        )
        
        # Should auto-correct to quantity * unit_price
        assert item.line_total == Decimal('100.00')
    
    def test_line_item_negative_quantity_fails(self):
        """Test that negative quantity is rejected."""
        with pytest.raises(Exception):
            LineItem(
                description="Product C",
                quantity=-1,
                unit_price=Decimal('100.00'),
                line_total=Decimal('100.00')
            )


class TestInvoice:
    """Test Invoice model."""
    
    def test_create_valid_invoice(self):
        """Test creating a valid invoice."""
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_date=date(2024, 1, 15),
            seller_name="ABC Corp",
            buyer_name="XYZ Ltd",
            currency=CurrencyEnum.USD,
            net_total=Decimal('1000.00'),
            tax_amount=Decimal('180.00'),
            gross_total=Decimal('1180.00')
        )
        
        assert invoice.invoice_number == "INV-001"
        assert invoice.currency == CurrencyEnum.USD
    
    def test_invoice_validates_due_date(self):
        """Test that due date must be after invoice date."""
        with pytest.raises(Exception):
            Invoice(
                invoice_number="INV-002",
                invoice_date=date(2024, 2, 15),
                due_date=date(2024, 1, 15),  # Before invoice date
                seller_name="ABC Corp",
                buyer_name="XYZ Ltd",
                currency=CurrencyEnum.USD,
                net_total=Decimal('1000.00'),
                tax_amount=Decimal('180.00'),
                gross_total=Decimal('1180.00')
            )
    
    def test_invoice_negative_amounts_fail(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(Exception):
            Invoice(
                invoice_number="INV-003",
                invoice_date=date(2024, 1, 15),
                seller_name="ABC Corp",
                buyer_name="XYZ Ltd",
                currency=CurrencyEnum.USD,
                net_total=Decimal('-1000.00'),  # Negative
                tax_amount=Decimal('180.00'),
                gross_total=Decimal('1180.00')
            )
    
    def test_invoice_currency_uppercase(self):
        """Test that currency accepts uppercase values."""
        invoice = Invoice(
            invoice_number="INV-004",
            invoice_date=date(2024, 1, 15),
            seller_name="ABC Corp",
            buyer_name="XYZ Ltd",
            currency="USD",  # Must be uppercase for enum
            net_total=Decimal('1000.00'),
            tax_amount=Decimal('180.00'),
            gross_total=Decimal('1180.00')
        )
        
        assert invoice.currency == CurrencyEnum.USD


class TestValidationResult:
    """Test ValidationResult model."""
    
    def test_create_validation_result(self):
        """Test creating a validation result."""
        result = ValidationResult(
            invoice_id="INV-001",
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        assert result.invoice_id == "INV-001"
        assert result.is_valid is True
    
    def test_validation_result_with_errors(self):
        """Test validation result with errors."""
        result = ValidationResult(
            invoice_id="INV-002",
            is_valid=False,
            errors=["Missing required field: buyer_name"],
            warnings=["Due date is missing"]
        )
        
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestValidationSummary:
    """Test ValidationSummary model."""
    
    def test_create_validation_summary(self):
        """Test creating a validation summary."""
        summary = ValidationSummary(
            total_invoices=10,
            valid_invoices=7,
            invalid_invoices=3,
            error_counts={'error1': 2, 'error2': 1}
        )
        
        assert summary.total_invoices == 10
        assert summary.valid_invoices == 7
        assert summary.invalid_invoices == 3
    
    def test_validation_rate_calculation(self):
        """Test validation rate property."""
        summary = ValidationSummary(
            total_invoices=10,
            valid_invoices=7,
            invalid_invoices=3,
            error_counts={}
        )
        
        assert summary.validation_rate == 70.0
    
    def test_validation_rate_zero_invoices(self):
        """Test validation rate with zero invoices."""
        summary = ValidationSummary(
            total_invoices=0,
            valid_invoices=0,
            invalid_invoices=0,
            error_counts={}
        )
        
        assert summary.validation_rate == 0.0