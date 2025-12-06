"""
Simple test runner to validate the invoice_qc system.
Run this to test all components before running pytest.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from invoice_qc.validator import InvoiceValidator
from invoice_qc.extractor import InvoiceExtractor
from invoice_qc.database import Database
from invoice_qc.models import ValidationResult, ValidationSummary
import tempfile
import json


def test_validator():
    """Test validator functionality."""
    print("\n" + "="*60)
    print("Testing Validator")
    print("="*60)
    
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    validator = InvoiceValidator(Database(db_path))
    
    # Test 1: Valid invoice
    print("\n✓ Test 1: Valid invoice")
    valid_invoice = {
        'invoice_number': 'INV-001',
        'invoice_date': '2024-01-15',
        'due_date': '2024-02-15',
        'seller_name': 'ABC Corp',
        'buyer_name': 'XYZ Ltd',
        'currency': 'USD',
        'net_total': 1000.00,
        'tax_amount': 180.00,
        'gross_total': 1180.00,
        'line_items': []
    }
    
    result = validator.validate(valid_invoice)
    print(f"  Valid: {result.is_valid}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Warnings: {len(result.warnings)}")
    
    if result.is_valid:
        print("  ✓ PASSED")
    else:
        print(f"  ✗ FAILED: {result.errors}")
    
    # Test 2: Invalid invoice (missing fields)
    print("\n✓ Test 2: Invalid invoice (missing required fields)")
    invalid_invoice = {
        'invoice_number': '',
        'invoice_date': '2024-01-15',
        'seller_name': 'ABC Corp',
        'buyer_name': '',
        'currency': 'USD',
        'net_total': None,
        'tax_amount': 100.00,
        'gross_total': 1100.00
    }
    
    result = validator.validate(invalid_invoice)
    print(f"  Valid: {result.is_valid}")
    print(f"  Errors: {len(result.errors)}")
    
    if not result.is_valid and len(result.errors) > 0:
        print("  ✓ PASSED")
        print(f"  Errors found: {result.errors[:3]}")
    else:
        print("  ✗ FAILED: Should have errors")
    
    # Test 3: Wrong calculation
    print("\n✓ Test 3: Wrong total calculation")
    wrong_calc = {
        'invoice_number': 'INV-003',
        'invoice_date': '2024-01-15',
        'seller_name': 'ABC Corp',
        'buyer_name': 'XYZ Ltd',
        'currency': 'USD',
        'net_total': 1000.00,
        'tax_amount': 200.00,
        'gross_total': 1100.00  # Wrong! Should be 1200
    }
    
    result = validator.validate(wrong_calc)
    has_calc_error = any('mismatch' in e.lower() or 'calculation' in e.lower() for e in result.errors)
    
    if not result.is_valid and has_calc_error:
        print("  ✓ PASSED - Detected calculation error")
    else:
        print(f"  ✗ FAILED - Should detect calculation mismatch")
        print(f"  Errors: {result.errors}")
    
    # Test 4: Batch validation
    print("\n✓ Test 4: Batch validation")
    invoices = [valid_invoice, invalid_invoice, wrong_calc]
    batch_result = validator.validate_batch(invoices)
    
    summary = batch_result['summary']
    print(f"  Total: {summary['total_invoices']}")
    print(f"  Valid: {summary['valid_invoices']}")
    print(f"  Invalid: {summary['invalid_invoices']}")
    
    if summary['total_invoices'] == 3 and summary['invalid_invoices'] >= 2:
        print("  ✓ PASSED")
    else:
        print("  ✗ FAILED")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    print("\n" + "="*60)
    print("Validator Tests Complete")
    print("="*60)


def test_extractor():
    """Test extractor functionality."""
    print("\n" + "="*60)
    print("Testing Extractor")
    print("="*60)
    
    extractor = InvoiceExtractor()
    
    # Test 1: Pattern initialization
    print("\n✓ Test 1: Extractor initialization")
    if hasattr(extractor, 'patterns') and 'invoice_number' in extractor.patterns:
        print("  ✓ PASSED - Patterns loaded")
    else:
        print("  ✗ FAILED - Patterns not loaded")
    
    # Test 2: Invoice number extraction
    print("\n✓ Test 2: Invoice number extraction")
    sample_text = """
    INVOICE
    Invoice Number: INV-2024-001
    Date: 15/01/2024
    """
    
    invoice_num = extractor._extract_invoice_number(sample_text)
    if invoice_num == 'INV-2024-001':
        print(f"  ✓ PASSED - Extracted: {invoice_num}")
    else:
        print(f"  ✗ FAILED - Got: {invoice_num}, Expected: INV-2024-001")
    
    # Test 3: Date parsing
    print("\n✓ Test 3: Date parsing")
    test_dates = [
        ('15/01/2024', '2024-01-15'),
        ('15.01.2024', '2024-01-15'),
        ('2024-01-15', '2024-01-15'),
    ]
    
    passed = 0
    for input_date, expected in test_dates:
        result = extractor._parse_date(input_date)
        if result == expected:
            passed += 1
    
    if passed == len(test_dates):
        print(f"  ✓ PASSED - All {passed} date formats parsed correctly")
    else:
        print(f"  ✗ FAILED - Only {passed}/{len(test_dates)} passed")
    
    # Test 4: Amount parsing
    print("\n✓ Test 4: Amount parsing")
    test_amounts = [
        ('$1,000.00', 1000.00),
        ('€500.50', 500.50),
        ('1234.56', 1234.56),
    ]
    
    passed = 0
    for input_amt, expected in test_amounts:
        result = extractor._parse_amount(input_amt)
        if result == expected:
            passed += 1
    
    if passed == len(test_amounts):
        print(f"  ✓ PASSED - All {passed} amounts parsed correctly")
    else:
        print(f"  ✗ FAILED - Only {passed}/{len(test_amounts)} passed")
    
    # Test 5: Empty invoice structure
    print("\n✓ Test 5: Empty invoice structure")
    empty = extractor._empty_invoice()
    if (empty['invoice_number'] is None and 
        empty['currency'] == 'USD' and 
        empty['line_items'] == []):
        print("  ✓ PASSED - Empty structure correct")
    else:
        print("  ✗ FAILED - Empty structure incorrect")
    
    print("\n" + "="*60)
    print("Extractor Tests Complete")
    print("="*60)


def test_database():
    """Test database functionality."""
    print("\n" + "="*60)
    print("Testing Database")
    print("="*60)
    
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    db = Database(db_path)
    
    # Test 1: Save invoice
    print("\n✓ Test 1: Save invoice")
    invoice_data = {
        'invoice_number': 'TEST-001',
        'invoice_date': '2024-01-15',
        'seller_name': 'Test Seller',
        'buyer_name': 'Test Buyer',
        'currency': 'USD',
        'net_total': 1000.00,
        'tax_amount': 180.00,
        'gross_total': 1180.00
    }
    
    invoice_id = db.save_invoice(invoice_data)
    if invoice_id > 0:
        print(f"  ✓ PASSED - Invoice saved with ID: {invoice_id}")
    else:
        print("  ✗ FAILED - Could not save invoice")
    
    # Test 2: Retrieve invoice
    print("\n✓ Test 2: Retrieve invoice")
    retrieved = db.get_invoice(invoice_id)
    if retrieved and retrieved['invoice_number'] == 'TEST-001':
        print("  ✓ PASSED - Invoice retrieved successfully")
    else:
        print("  ✗ FAILED - Could not retrieve invoice")
    
    # Test 3: Duplicate detection
    print("\n✓ Test 3: Duplicate detection")
    is_dup = db.check_duplicate('TEST-001', 'Test Seller', '2024-01-15')
    if is_dup:
        print("  ✓ PASSED - Duplicate detected")
    else:
        print("  ✗ FAILED - Duplicate not detected")
    
    # Test 4: Get all invoices
    print("\n✓ Test 4: Get all invoices")
    all_invoices = db.get_all_invoices()
    if len(all_invoices) >= 1:
        print(f"  ✓ PASSED - Retrieved {len(all_invoices)} invoice(s)")
    else:
        print("  ✗ FAILED - No invoices retrieved")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    print("\n" + "="*60)
    print("Database Tests Complete")
    print("="*60)


def test_models():
    """Test Pydantic models."""
    print("\n" + "="*60)
    print("Testing Models")
    print("="*60)
    
    # Test 1: ValidationResult
    print("\n✓ Test 1: ValidationResult model")
    try:
        result = ValidationResult(
            invoice_id='TEST-001',
            is_valid=True,
            errors=[],
            warnings=[]
        )
        print("  ✓ PASSED - ValidationResult created")
    except Exception as e:
        print(f"  ✗ FAILED - {e}")
    
    # Test 2: ValidationSummary
    print("\n✓ Test 2: ValidationSummary model")
    try:
        summary = ValidationSummary(
            total_invoices=10,
            valid_invoices=7,
            invalid_invoices=3,
            error_counts={'error1': 2, 'error2': 1}
        )
        print(f"  ✓ PASSED - ValidationSummary created")
        print(f"  Validation rate: {summary.validation_rate:.1f}%")
    except Exception as e:
        print(f"  ✗ FAILED - {e}")
    
    print("\n" + "="*60)
    print("Models Tests Complete")
    print("="*60)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("INVOICE QC - COMPONENT TESTS")
    print("="*60)
    
    try:
        test_models()
        test_database()
        test_extractor()
        test_validator()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETE!")
        print("="*60)
        print("\nYou can now run pytest for more comprehensive tests:")
        print("  pytest tests/ -v")
        print("\nOr run with coverage:")
        print("  pytest tests/ --cov=invoice_qc --cov-report=html")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()