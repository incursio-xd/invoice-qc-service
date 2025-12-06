import tempfile
import logging
from pathlib import Path
from typing import List, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime

from .schemas import (
    HealthResponse,
    ValidateJsonResponse,
    ExtractAndValidateResponse,
    ValidationSummaryResponse,
    ValidationResultResponse,
    ExtractedInvoiceResult
)
from ..extractor import InvoiceExtractor
from ..validator import InvoiceValidator
from ..database import Database
from ..config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
extractor = InvoiceExtractor()
validator = InvoiceValidator(Database(settings.database_path))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        service="invoice-qc",
        timestamp=datetime.now()
    )


@router.post("/validate-json", response_model=ValidateJsonResponse)
async def validate_json(invoices: List[Dict]):
    try:
        logger.info(f"Validating {len(invoices)} invoices from JSON")
        
        # Validate all invoices
        validation_result = validator.validate_batch(invoices)
        
        # Convert to response models
        summary_data = validation_result['summary']
        summary = ValidationSummaryResponse(
            total_invoices=summary_data['total_invoices'],
            valid_invoices=summary_data['valid_invoices'],
            invalid_invoices=summary_data['invalid_invoices'],
            error_counts=summary_data['error_counts'],
            validation_timestamp=summary_data.get('validation_timestamp', datetime.now())
        )
        
        results = [
            ValidationResultResponse(
                invoice_id=r['invoice_id'],
                is_valid=r['is_valid'],
                errors=r['errors'],
                warnings=r.get('warnings', [])
            )
            for r in validation_result['results']
        ]
        
        return ValidateJsonResponse(summary=summary, results=results)
    
    except Exception as e:
        logger.error(f"Error validating JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.post("/extract-and-validate-pdfs", response_model=ExtractAndValidateResponse)
async def extract_and_validate_pdfs(files: List[UploadFile] = File(...)):
    try:
        logger.info(f"Processing {len(files)} uploaded PDF files")
        
        results = []
        all_invoices = []
        
        # Process each uploaded file
        for file in files:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                logger.warning(f"Skipping non-PDF file: {file.filename}")
                continue
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Extract invoice data
                invoice_data = extractor.extract_from_pdf(tmp_path)
                invoice_data['filename'] = file.filename
                all_invoices.append(invoice_data)
                
                # Validate individual invoice
                validation_result = validator.validate(invoice_data)
                
                # Create result object
                result = ExtractedInvoiceResult(
                    filename=file.filename,
                    extracted_data=invoice_data,
                    validation=ValidationResultResponse(
                        invoice_id=validation_result.invoice_id,
                        is_valid=validation_result.is_valid,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings
                    )
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                # Add error result
                results.append(ExtractedInvoiceResult(
                    filename=file.filename,
                    extracted_data={},
                    validation=ValidationResultResponse(
                        invoice_id=file.filename,
                        is_valid=False,
                        errors=[f"Processing error: {str(e)}"],
                        warnings=[]
                    )
                ))
            finally:
                # Clean up temporary file
                try:
                    Path(tmp_path).unlink()
                except:
                    pass
        
        # Calculate overall summary
        valid_count = sum(1 for r in results if r.validation.is_valid)
        invalid_count = len(results) - valid_count
        
        # Collect all errors
        error_counts = {}
        for result in results:
            for error in result.validation.errors:
                error_counts[error] = error_counts.get(error, 0) + 1
        
        summary = ValidationSummaryResponse(
            total_invoices=len(results),
            valid_invoices=valid_count,
            invalid_invoices=invalid_count,
            error_counts=error_counts,
            validation_timestamp=datetime.now()
        )
        
        logger.info(f"Completed processing: {valid_count}/{len(results)} valid")
        
        return ExtractAndValidateResponse(
            total_files=len(files),
            results=results,
            summary=summary
        )
    
    except Exception as e:
        logger.error(f"Error processing PDFs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/invoices")
async def get_all_invoices():
    try:
        db = Database(settings.database_path)
        invoices = db.get_all_invoices()
        return {"total": len(invoices), "invoices": invoices}
    except Exception as e:
        logger.error(f"Error retrieving invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: int):
    try:
        db = Database(settings.database_path)
        invoice = db.get_invoice(invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")