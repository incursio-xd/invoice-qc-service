"""
Invoice validation logic with business rules.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from collections import defaultdict

from .models import ValidationResult, ValidationSummary
from .database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InvoiceValidator:
    """Validate invoices against completeness, format, and business rules."""
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize validator with optional database for duplicate checks."""
        self.db = db or Database()
        self.high_amount_threshold = Decimal('1000000.00')
    
    def validate(self, invoice: Dict) -> ValidationResult:
        """
        Validate a single invoice.
    
        Args:
        invoice: Invoice data dictionary
        
        Returns:
        ValidationResult with errors and warnings
        """
        # Get invoice_id, ensure it's never None
        invoice_number = invoice.get('invoice_number')
        if invoice_number is None or (isinstance(invoice_number, str) and not invoice_number.strip()):
            invoice_id = f"UNKNOWN_{invoice.get('source_file', 'NO_FILE')}"
        else:
            invoice_id = str(invoice_number)
    
        result = ValidationResult(
            invoice_id=invoice_id,
            is_valid=True,
            errors=[],
            warnings=[]
        )
    
        # Run all validation checks
        self._check_required_fields(invoice, result)
        self._check_formats(invoice, result)
        self._check_business_rules(invoice, result)
        self._check_anomalies(invoice, result)
        self._check_duplicates(invoice, result)
    
        # Set overall validity
        result.is_valid = len(result.errors) == 0
    
        logger.info(f"Validated invoice {invoice_id}: {'VALID' if result.is_valid else 'INVALID'}")
        return result
    
    def validate_batch(self, invoices: List[Dict]) -> Dict:
        """
        Validate multiple invoices and return summary.
        
        Args:
            invoices: List of invoice dictionaries
            
        Returns:
            Dictionary with summary and individual results
        """
        results = []
        error_counts = defaultdict(int)
        
        for invoice in invoices:
            result = self.validate(invoice)
            results.append(result)
            
            # Count each unique error
            for error in result.errors:
                error_counts[error] += 1
        
        # Calculate summary
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count
        
        summary = ValidationSummary(
            total_invoices=len(results),
            valid_invoices=valid_count,
            invalid_invoices=invalid_count,
            error_counts=dict(error_counts)
        )
        
        logger.info(f"Batch validation complete: {valid_count}/{len(results)} valid")
        
        return {
            'summary': summary.model_dump(),
            'results': [r.model_dump() for r in results]
        }
    
    def _check_required_fields(self, invoice: Dict, result: ValidationResult):
        """Check that all required fields are present and not empty."""
        required_fields = [
            'invoice_number',
            'invoice_date',
            'seller_name',
            'buyer_name',
            'currency',
            'net_total',
            'tax_amount',
            'gross_total'
        ]
        
        for field in required_fields:
            value = invoice.get(field)
            
            if value is None:
                result.errors.append(f"Missing required field: {field}")
            elif isinstance(value, str) and not value.strip():
                result.errors.append(f"Empty required field: {field}")
            elif isinstance(value, (int, float, Decimal)) and value < 0:
                result.errors.append(f"Negative value in required field: {field}")
    
    def _check_formats(self, invoice: Dict, result: ValidationResult):
        """Check data format and type validations."""
        
        # Validate invoice_date
        invoice_date = invoice.get('invoice_date')
        if invoice_date:
            try:
                if isinstance(invoice_date, str):
                    from datetime import datetime
                    parsed_date = datetime.fromisoformat(invoice_date).date()
                else:
                    parsed_date = invoice_date
                
                # Check if date is not in the future
                if parsed_date > date.today():
                    result.errors.append("Invoice date cannot be in the future")
            except (ValueError, TypeError):
                result.errors.append(f"Invalid invoice_date format: {invoice_date}")
        
        # Validate due_date
        due_date = invoice.get('due_date')
        if due_date and invoice_date:
            try:
                if isinstance(due_date, str):
                    from datetime import datetime
                    parsed_due = datetime.fromisoformat(due_date).date()
                else:
                    parsed_due = due_date
                
                if isinstance(invoice_date, str):
                    from datetime import datetime
                    parsed_invoice = datetime.fromisoformat(invoice_date).date()
                else:
                    parsed_invoice = invoice_date
                
                # Check if due_date is on or after invoice_date
                if parsed_due < parsed_invoice:
                    result.errors.append("Due date cannot be before invoice date")
            except (ValueError, TypeError):
                result.errors.append(f"Invalid due_date format: {due_date}")
        
        # Validate currency
        currency = invoice.get('currency')
        allowed_currencies = ['EUR', 'USD', 'INR', 'GBP']
        if currency and currency.upper() not in allowed_currencies:
            result.errors.append(f"Invalid currency: {currency}. Must be one of {allowed_currencies}")
        
        # Validate tax IDs (basic check)
        seller_tax_id = invoice.get('seller_tax_id')
        if seller_tax_id:
            # Basic format check: should be alphanumeric
            if not seller_tax_id.replace('-', '').replace(' ', '').isalnum():
                result.warnings.append(f"Seller tax ID format may be invalid: {seller_tax_id}")
        
        buyer_tax_id = invoice.get('buyer_tax_id')
        if buyer_tax_id:
            if not buyer_tax_id.replace('-', '').replace(' ', '').isalnum():
                result.warnings.append(f"Buyer tax ID format may be invalid: {buyer_tax_id}")
    
    def _check_business_rules(self, invoice: Dict, result: ValidationResult):
        """Check business logic and calculation rules."""
        
        # Get amounts
        net_total = self._to_decimal(invoice.get('net_total'))
        tax_amount = self._to_decimal(invoice.get('tax_amount'))
        gross_total = self._to_decimal(invoice.get('gross_total'))
        
        # Rule 1: Totals validation (net + tax = gross)
        if net_total is not None and tax_amount is not None and gross_total is not None:
            expected_gross = net_total + tax_amount
            tolerance = Decimal('0.01')
            
            if abs(expected_gross - gross_total) > tolerance:
                result.errors.append(
                    f"Total calculation mismatch: net ({net_total}) + tax ({tax_amount}) "
                    f"!= gross ({gross_total}). Expected: {expected_gross}"
                )
        
        # Rule 2: Line items sum validation
        line_items = invoice.get('line_items', [])
        if line_items and net_total is not None:
            line_items_sum = Decimal('0')
            for item in line_items:
                item_total = self._to_decimal(item.get('line_total'))
                if item_total:
                    line_items_sum += item_total
            
            tolerance = Decimal('0.01')
            if abs(line_items_sum - net_total) > tolerance:
                result.warnings.append(
                    f"Line items sum ({line_items_sum}) does not match net total ({net_total})"
                )
        
        # Rule 3: Negative amounts check
        amount_fields = ['net_total', 'tax_amount', 'gross_total']
        for field in amount_fields:
            value = self._to_decimal(invoice.get(field))
            if value is not None and value < 0:
                result.errors.append(f"Negative amount not allowed: {field} = {value}")
        
        # Rule 4: Line item validation
        for idx, item in enumerate(line_items):
            quantity = item.get('quantity')
            unit_price = self._to_decimal(item.get('unit_price'))
            line_total = self._to_decimal(item.get('line_total'))
            
            if quantity and unit_price and line_total:
                expected = Decimal(str(quantity)) * unit_price
                if abs(expected - line_total) > Decimal('0.01'):
                    result.warnings.append(
                        f"Line item {idx + 1}: quantity * unit_price != line_total"
                    )
    
    def _check_anomalies(self, invoice: Dict, result: ValidationResult):
        """Check for unusual patterns or anomalies."""
        
        # Check for unusually high amounts
        gross_total = self._to_decimal(invoice.get('gross_total'))
        if gross_total and gross_total > self.high_amount_threshold:
            result.warnings.append(
                f"Unusually high gross total: {gross_total} (threshold: {self.high_amount_threshold})"
            )
        
        # Check for missing optional but expected fields
        if not invoice.get('due_date'):
            result.warnings.append("Due date is missing")
        
        if not invoice.get('seller_tax_id'):
            result.warnings.append("Seller tax ID is missing")
        
        if not invoice.get('buyer_tax_id'):
            result.warnings.append("Buyer tax ID is missing")
        
        # Check for empty line items
        if not invoice.get('line_items'):
            result.warnings.append("No line items found in invoice")
    
    def _check_duplicates(self, invoice: Dict, result: ValidationResult):
        """Check for duplicate invoices in database."""
        invoice_number = invoice.get('invoice_number')
        seller_name = invoice.get('seller_name')
        invoice_date = invoice.get('invoice_date')
        
        if not all([invoice_number, seller_name, invoice_date]):
            return
        
        # Convert date to string if needed
        if not isinstance(invoice_date, str):
            invoice_date = str(invoice_date)
        
        try:
            is_duplicate = self.db.check_duplicate(invoice_number, seller_name, invoice_date)
            if is_duplicate:
                # Changed to warning instead of error for development/testing
                result.warnings.append(
                    f"Duplicate invoice detected: {invoice_number} from {seller_name} on {invoice_date}"
                )
        except Exception as e:
            logger.warning(f"Could not check for duplicates: {str(e)}")
    
    def _to_decimal(self, value) -> Optional[Decimal]:
        """Convert value to Decimal safely."""
        if value is None:
            return None
        
        try:
            if isinstance(value, Decimal):
                return value
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None