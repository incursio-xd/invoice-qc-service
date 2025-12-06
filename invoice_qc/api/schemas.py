from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    seller_name: Optional[str] = None
    seller_address: Optional[str] = None
    seller_tax_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    currency: Optional[str] = None
    net_total: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    gross_total: Optional[float] = None
    line_items: List[Dict[str, Any]] = []


class ValidationResultResponse(BaseModel):
    invoice_id: str
    is_valid: bool
    errors: List[str]
    warnings: List[str] = []


class ValidationSummaryResponse(BaseModel):
    total_invoices: int
    valid_invoices: int
    invalid_invoices: int
    error_counts: Dict[str, int]
    validation_timestamp: datetime


class ValidateJsonResponse(BaseModel):
    summary: ValidationSummaryResponse
    results: List[ValidationResultResponse]


class ExtractedInvoiceResult(BaseModel):
    filename: str
    extracted_data: Dict[str, Any]
    validation: ValidationResultResponse


class ExtractAndValidateResponse(BaseModel):
    total_files: int
    results: List[ExtractedInvoiceResult]
    summary: ValidationSummaryResponse


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime = datetime.now()