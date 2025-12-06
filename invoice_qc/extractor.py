"""
PDF invoice extraction using AI (Google Gemini) with regex fallback.
Language-agnostic, layout-agnostic solution.
"""

from dotenv import load_dotenv
load_dotenv() 

import fitz  # PyMuPDF
import json
import logging
import re
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """Extract structured invoice data from PDF files using AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize invoice extractor.
    
        Args:
            api_key: Google API key for Gemini (or set GOOGLE_API_KEY env var)
                    If not provided, will fall back to regex extraction
        """
        from .config import settings
    
        # Priority: passed parameter > config settings > environment variable
        self.api_key = api_key or settings.google_api_key or os.getenv('GOOGLE_API_KEY')
    
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('models/gemini-2.5-flash')
                self.use_ai = True
                logger.info("✓ AI-powered extraction enabled (Gemini)")
            except ImportError:
                logger.warning("google-generativeai not installed. Install with: pip install google-generativeai")
                self.use_ai = False
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
            logger.info("No API key provided. Using fallback regex extraction.")
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extract invoice data from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted invoice data
        """
        try:
            logger.info(f"Extracting data from {pdf_path}")
            
            # Extract text from PDF
            with fitz.open(pdf_path) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
            
            if not text.strip():
                logger.warning(f"No text extracted from {pdf_path}")
                return self._empty_invoice(Path(pdf_path).name)
            
            # Use AI extraction if available, otherwise fallback to regex
            if self.use_ai:
                invoice_data = self._extract_with_ai(text)
            else:
                invoice_data = self._extract_with_regex(text)
            
            invoice_data['source_file'] = Path(pdf_path).name
            
            logger.info(f"Successfully extracted invoice {invoice_data.get('invoice_number', 'UNKNOWN')}")
            return invoice_data
            
        except Exception as e:
            logger.error(f"Error extracting from {pdf_path}: {str(e)}")
            return self._empty_invoice(Path(pdf_path).name)
    
    def _extract_with_ai(self, text: str) -> Dict:
        """
        Extract invoice data using Google Gemini AI.
        Language-agnostic and robust to format variations.
        """
        prompt = f"""You are an expert invoice data extraction system. Extract structured data from this document.

Document text:
{text}

Extract and return ONLY a valid JSON object with these exact fields:
{{
    "invoice_number": "the invoice or purchase order number",
    "invoice_date": "date in YYYY-MM-DD format",
    "due_date": "due date in YYYY-MM-DD format or null if not found",
    "seller_name": "seller/supplier company name",
    "seller_address": "seller address or null if not found",
    "seller_tax_id": "seller tax/VAT ID or null if not found",
    "buyer_name": "buyer/customer company name",
    "buyer_address": "buyer address or null if not found",
    "buyer_tax_id": "buyer tax/VAT ID or null if not found",
    "currency": "currency code like EUR, USD, GBP, INR",
    "net_total": "net/subtotal amount as a number without currency symbol",
    "tax_rate": "tax rate percentage as number or null if not found",
    "tax_amount": "tax amount as a number",
    "gross_total": "gross/total amount including tax as a number"
}}

CRITICAL EXTRACTION RULES:
1. Return ONLY the JSON object - no markdown, no code blocks, no explanation
2. Do NOT use ```json or ``` - just raw JSON
3. Use null (not "null" string, not "N/A", not empty string) for missing fields
4. Convert ALL dates to YYYY-MM-DD format regardless of source format
5. Convert ALL amounts to plain numbers (remove currency symbols, spaces, commas)
6. For German documents: convert number format (1.234,56 → 1234.56)
7. For German "Bestellung" (purchase order): use AUFNR number as invoice_number
8. For Indian documents: convert lakhs/crores notation if present
9. Identify currency from symbols: € = EUR, $ = USD, £ = GBP, ₹ = INR
10. If multiple companies appear, seller is usually the supplier (bottom/footer), buyer is the customer (top)

Return the JSON now:"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response - remove any markdown formatting
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            invoice_data = json.loads(response_text)
            
            # Ensure line_items field exists
            if 'line_items' not in invoice_data:
                invoice_data['line_items'] = []
            
            logger.info("✓ AI extraction successful")
            return invoice_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response_text[:300]}...")
            logger.info("Falling back to regex extraction")
            return self._extract_with_regex(text)
        except Exception as e:
            logger.error(f"AI extraction failed: {str(e)}")
            logger.info("Falling back to regex extraction")
            return self._extract_with_regex(text)
    
    def _extract_with_regex(self, text: str) -> Dict:
        """
        Fallback extraction using regex patterns.
        Language-agnostic where possible.
        """
        invoice = self._empty_invoice()
        
        # Invoice/Order number patterns (multi-language)
        inv_patterns = [
            r'AUFNR(\d+)',  # German purchase orders
            r'(?:Invoice|Rechnung|Facture|Factura)[:\s#]*([A-Z0-9-]+)',
            r'(?:Order|Bestellung|Commande|Pedido)[:\s#]*([A-Z0-9-]+)',
            r'(?:PO|REF)[:\s#-]*([A-Z0-9-]+)',
            r'\b([A-Z]{2,}\d{4,})\b',  # Generic pattern like AUFNR123456
        ]
        
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'AUFNR' in pattern:
                    invoice['invoice_number'] = f"AUFNR{match.group(1)}"
                else:
                    invoice['invoice_number'] = match.group(1).strip()
                break
        
        # Date extraction (multiple formats)
        date_patterns = [
            r'\d{2}\.\d{2}\.\d{4}',  # DD.MM.YYYY (German/European)
            r'\d{2}/\d{2}/\d{4}',    # DD/MM/YYYY or MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2}',    # YYYY-MM-DD (ISO)
        ]
        
        dates_found = []
        for pattern in date_patterns:
            dates_found.extend(re.findall(pattern, text))
        
        # Parse first two dates found
        for i, date_str in enumerate(dates_found[:2]):
            parsed = self._parse_date(date_str)
            if parsed:
                if i == 0:
                    invoice['invoice_date'] = parsed
                elif i == 1:
                    invoice['due_date'] = parsed
        
        # Currency detection
        if '€' in text or 'EUR' in text:
            invoice['currency'] = 'EUR'
        elif '$' in text or 'USD' in text:
            invoice['currency'] = 'USD'
        elif '£' in text or 'GBP' in text:
            invoice['currency'] = 'GBP'
        elif '₹' in text or 'INR' in text or 'Rs' in text:
            invoice['currency'] = 'INR'
        
        # Company name extraction (look for legal entity indicators)
        company_indicators = ['Corporation', 'Corp', 'GmbH', 'gGmbH', 'Ltd', 
                             'LLC', 'Inc', 'AG', 'Pvt', 'Limited']
        
        companies = []
        for indicator in company_indicators:
            pattern = rf'([A-Z][A-Za-z\s]+{indicator})'
            matches = re.findall(pattern, text)
            companies.extend(matches)
        
        # Remove duplicates and clean
        companies = list(dict.fromkeys(companies))
        companies = [c.strip() for c in companies if len(c.strip()) > 5]
        
        if companies:
            invoice['seller_name'] = companies[0] if len(companies) >= 1 else None
            invoice['buyer_name'] = companies[1] if len(companies) >= 2 else None
        
        # Amount extraction (basic - AI is much better at this)
        # Look for numbers with 2 decimal places
        amounts = re.findall(r'[\d.,]+\d{2}', text)
        parsed_amounts = []
        
        for amt in amounts:
            try:
                # Try both German (1.234,56) and English (1,234.56) formats
                if ',' in amt and '.' in amt:
                    # Has both - check which is decimal separator
                    if amt.rindex(',') > amt.rindex('.'):
                        # German format: 1.234,56
                        clean = amt.replace('.', '').replace(',', '.')
                    else:
                        # English format: 1,234.56
                        clean = amt.replace(',', '')
                elif ',' in amt:
                    # Could be either - assume decimal if only 2 digits after
                    parts = amt.split(',')
                    if len(parts[-1]) == 2:
                        # Likely German decimal: 1234,56
                        clean = amt.replace(',', '.')
                    else:
                        # Likely English thousand: 1,234
                        clean = amt.replace(',', '')
                else:
                    clean = amt
                
                parsed_amounts.append(float(clean))
            except:
                pass
        
        # Sort amounts and assign (largest is usually gross total)
        if parsed_amounts:
            parsed_amounts.sort(reverse=True)
            if len(parsed_amounts) >= 1:
                invoice['gross_total'] = parsed_amounts[0]
            if len(parsed_amounts) >= 2:
                invoice['net_total'] = parsed_amounts[1]
            if len(parsed_amounts) >= 3:
                invoice['tax_amount'] = parsed_amounts[2]
        
        logger.info("Used fallback regex extraction")
        return invoice
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format (YYYY-MM-DD)."""
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%d.%m.%Y',  # German/European: 22.05.2024
            '%d/%m/%Y',  # European: 22/05/2024
            '%m/%d/%Y',  # US: 05/22/2024
            '%Y-%m-%d',  # ISO: 2024-05-22
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        
        return None
    
    def _empty_invoice(self, filename: str = "") -> Dict:
        """Return empty invoice structure."""
        return {
            'invoice_number': None,
            'invoice_date': None,
            'due_date': None,
            'seller_name': None,
            'seller_address': None,
            'seller_tax_id': None,
            'buyer_name': None,
            'buyer_address': None,
            'buyer_tax_id': None,
            'currency': 'USD',
            'net_total': None,
            'tax_rate': None,
            'tax_amount': None,
            'gross_total': None,
            'line_items': [],
            'source_file': filename,
        }
    
    def extract_batch(self, pdf_dir: str) -> List[Dict]:
        """
        Extract data from all PDFs in a directory.
        
        Args:
            pdf_dir: Directory containing PDF files
            
        Returns:
            List of extracted invoice dictionaries
        """
        pdf_path = Path(pdf_dir)
        if not pdf_path.exists():
            logger.error(f"Directory not found: {pdf_dir}")
            return []
        
        pdf_files = list(pdf_path.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
        
        invoices = []
        for pdf_file in pdf_files:
            try:
                invoice_data = self.extract_from_pdf(str(pdf_file))
                invoices.append(invoice_data)
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {str(e)}")
                continue
        
        logger.info(f"Successfully extracted {len(invoices)} invoices")
        return invoices