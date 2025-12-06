"""
Pydantic models for invoice data validation.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class CurrencyEnum(str, Enum):
    """Supported currencies."""
    EUR = "EUR"
    USD = "USD"
    INR = "INR"
    GBP = "GBP"


class LineItem(BaseModel):
    """Individual line item in an invoice."""
    description: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)
    
    @field_validator('unit_price', 'line_total')
    @classmethod
    def validate_decimal_places(cls, v):
        """Ensure amounts have at most 2 decimal places."""
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v
    
    @model_validator(mode='after')
    def validate_line_total(self):
        """Validate that line_total matches quantity * unit_price."""
        expected = Decimal(str(self.quantity)) * self.unit_price
        if abs(self.line_total - expected) > Decimal('0.01'):
            # Allow small rounding differences
            self.line_total = round(expected, 2)
        return self


class Invoice(BaseModel):
    """Complete invoice model with all required fields."""
    invoice_number: str = Field(min_length=1)
    invoice_date: date
    due_date: Optional[date] = None
    seller_name: str = Field(min_length=1)
    seller_address: Optional[str] = None
    seller_tax_id: Optional[str] = None
    buyer_name: str = Field(min_length=1)
    buyer_address: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    currency: CurrencyEnum
    net_total: Decimal = Field(ge=0)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tax_amount: Decimal = Field(ge=0)
    gross_total: Decimal = Field(ge=0)
    line_items: List[LineItem] = Field(default_factory=list)
    
    @field_validator('currency')
    @classmethod
    def validate_currency_uppercase(cls, v):
        """Ensure currency is uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v
    
    @field_validator('net_total', 'tax_amount', 'gross_total')
    @classmethod
    def validate_amounts_non_negative(cls, v):
        """Ensure all amounts are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Amount cannot be negative")
        return round(Decimal(str(v)), 2) if v is not None else v
    
    @field_validator('invoice_date', 'due_date')
    @classmethod
    def validate_dates(cls, v):
        """Ensure dates are valid."""
        if v is not None and isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(v, '%d/%m/%Y').date()
                except ValueError:
                    try:
                        return datetime.strptime(v, '%d.%m.%Y').date()
                    except ValueError:
                        raise ValueError(f"Invalid date format: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_due_date_after_invoice_date(self):
        """Ensure due date is on or after invoice date."""
        if self.due_date is not None and self.invoice_date is not None:
            if self.due_date < self.invoice_date:
                raise ValueError("Due date cannot be before invoice date")
        return self
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


class ValidationResult(BaseModel):
    """Result of validating a single invoice."""
    invoice_id: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    """Summary of validation results for multiple invoices."""
    total_invoices: int
    valid_invoices: int
    invalid_invoices: int
    error_counts: Dict[str, int] = Field(default_factory=dict)
    validation_timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def validation_rate(self) -> float:
        """Calculate percentage of valid invoices."""
        if self.total_invoices == 0:
            return 0.0
        return (self.valid_invoices / self.total_invoices) * 100