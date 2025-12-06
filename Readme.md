# Invoice QC Service - Invoice Extraction & Quality Control System

**Author**: Aman  
**Role**: Student
**Version**: 1.0.0  
**Date**: December 2025

---

## 📋 Table of Contents

- [Overview](#overview)
- [What Was Built](#what-was-built)
- [Schema & Validation Design](#schema--validation-design)
- [Architecture](#architecture)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [AI Usage Notes](#ai-usage-notes)
- [Testing](#testing)
- [Assumptions & Limitations](#assumptions--limitations)
- [Video Demonstration](#video-demonstration)

---

## 🎯 Overview

This project implements a complete **Invoice Extraction and Quality Control System** that extracts structured data from invoice PDFs and validates them against business rules. The system is designed to handle invoices in multiple languages (English, German, etc.) and formats.

### Problem Solved

B2B invoice processing requires extracting structured data from PDFs and validating it for accuracy, completeness, and business rule compliance. This system automates that entire workflow.

### Key Features

- 🤖 **AI-Powered Extraction**: Uses Google Gemini for intelligent, language-agnostic data extraction
- 🔄 **Regex Fallback**: Ensures extraction works even without AI/API
- ✅ **Comprehensive Validation**: 8+ validation rules covering completeness, format, and business logic
- 💻 **CLI Interface**: Command-line tool for batch processing
- 🌐 **REST API**: FastAPI-based HTTP endpoints for integration
- 🎨 **Web Console**: Interactive UI for upload and validation
- 💾 **Database Storage**: SQLite for persistent invoice records
- 🧪 **Full Test Coverage**: 48 passing tests (100% pass rate)

---

## 📦 What Was Built

### ✅ Completed Components

| Component | Status | Description |
|-----------|--------|-------------|
| **Extraction Module** | ✅ Complete | AI + regex fallback for PDF data extraction |
| **Validation Core** | ✅ Complete | 8+ validation rules with error/warning system |
| **CLI Tool** | ✅ Complete | `extract`, `validate`, `process` commands |
| **REST API** | ✅ Complete | FastAPI with 5+ endpoints |
| **Database** | ✅ Complete | SQLite with duplicate detection |
| **Web UI** | ✅ Complete | Interactive console for QC operations |
| **Tests** | ✅ Complete | 48 tests covering all modules |

---

## 📊 Schema & Validation Design

### Invoice Schema

I designed a comprehensive invoice schema with **12 core fields** and **line item support**:

#### Core Invoice Fields

| Field | Type | Required | Description | Rationale |
|-------|------|----------|-------------|-----------|
| `invoice_number` | string | ✅ Yes | Unique invoice identifier | Essential for tracking and duplicate detection |
| `invoice_date` | date (YYYY-MM-DD) | ✅ Yes | Date invoice was issued | Required for all invoices, used in validation |
| `due_date` | date (YYYY-MM-DD) | ❌ No | Payment due date | Common but not always present |
| `seller_name` | string | ✅ Yes | Supplier/vendor company name | Required party identification |
| `seller_address` | string | ❌ No | Seller's address | Useful for verification |
| `seller_tax_id` | string | ❌ No | Seller's VAT/Tax ID | Important for tax compliance |
| `buyer_name` | string | ✅ Yes | Customer company name | Required party identification |
| `buyer_address` | string | ❌ No | Buyer's address | Useful for verification |
| `buyer_tax_id` | string | ❌ No | Buyer's VAT/Tax ID | Important for tax compliance |
| `currency` | string (enum) | ✅ Yes | Currency code (EUR, USD, etc.) | Essential for financial data |
| `net_total` | decimal | ✅ Yes | Subtotal before tax | Core financial value |
| `tax_rate` | decimal | ❌ No | Tax percentage | Useful for validation |
| `tax_amount` | decimal | ✅ Yes | Total tax amount | Required for calculation validation |
| `gross_total` | decimal | ✅ Yes | Final total including tax | Primary amount field |

#### Line Items Structure

```json
{
  "description": "Product/service description",
  "quantity": 10,
  "unit_price": 50.00,
  "line_total": 500.00
}
```

**Design Rationale**: Line items are optional because not all invoices include itemized details, but when present, they enable detailed validation.

---

### Validation Rules

I implemented **3 categories** of validation rules:

#### 1️⃣ Completeness Rules (4 rules)

| Rule | Type | Description |
|------|------|-------------|
| **Required Fields** | Error | All 8 required fields must be present and non-empty |
| **Non-Negative Values** | Error | Financial amounts cannot be negative |
| **Valid Currency** | Error | Currency must be one of: EUR, USD, GBP, INR |
| **Date Format** | Error | Dates must be valid and parseable |

**Rationale**: These ensure data integrity and prevent processing invalid/incomplete records.

#### 2️⃣ Business Rules (3 rules)

| Rule | Type | Description |
|------|------|-------------|
| **Totals Calculation** | Error | `net_total + tax_amount = gross_total` (±0.01 tolerance) |
| **Line Items Sum** | Warning | Sum of line items should match net_total |
| **Due Date Logic** | Error | Due date cannot be before invoice date |
| **Future Date Check** | Error | Invoice date cannot be in the future |

**Rationale**: These catch calculation errors and logical inconsistencies that could indicate fraud or data entry mistakes.

#### 3️⃣ Anomaly Detection (2 rules)

| Rule | Type | Description |
|------|------|-------------|
| **High Amount Alert** | Warning | Flag invoices over €1,000,000 for review |
| **Duplicate Detection** | Warning | Check database for same invoice number + seller + date |
| **Missing Optional Fields** | Warning | Alert if tax IDs or due date are missing |

**Rationale**: These flag unusual patterns that need human review but shouldn't block processing.

---

### Data Flow

1. **Input**: PDF files or JSON data
2. **Extraction**: 
   - Primary: Google Gemini AI (language-agnostic)
   - Fallback: Regex patterns (when AI unavailable)
3. **Validation**: 
   - Apply all rules
   - Generate errors/warnings
4. **Storage**: Save to SQLite with validation results
5. **Output**: 
   - JSON reports
   - CLI feedback
   - Web UI display

### Module Structure

```
invoice_qc/
├── __init__.py           # Package initialization
├── models.py             # Pydantic data models
├── extractor.py          # PDF → JSON extraction
├── validator.py          # Validation logic
├── database.py           # SQLite operations
├── config.py             # Settings management
├── cli.py                # Command-line interface
└── api/
    ├── __init__.py
    ├── main.py           # FastAPI app
    ├── routes.py         # API endpoints
    └── schemas.py        # API request/response models
```

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- (Optional) Google Gemini API key for AI extraction

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/invoice-qc-service.git
cd invoice-qc-service
```

#### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment (Optional)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Google API key
# GOOGLE_API_KEY=your_api_key_here
```

**Note**: System works without API key using regex fallback.

#### 5. Verify Installation

```bash
# Run tests
python -m pytest tests/ -v

```

---

## 📖 Usage

### Command-Line Interface (CLI)

#### Extract Invoices from PDFs

```bash
python -m invoice_qc.cli extract pdfs --output extracted.json
```

**Output**: JSON file with extracted invoice data

#### Validate Invoice Data

```bash
python -m invoice_qc.cli validate extracted.json --report report.json
```

**Output**: Validation report with errors and summary

#### Full Pipeline (Extract + Validate + Save)

```bash
python -m invoice_qc.cli process pdfs --output-dir outputs --save-db
```

**Output**: 
- `outputs/extracted_invoices.json`
- `outputs/validation_report.json`
- Database records

#### System Information

```bash
python -m invoice_qc.cli info
```

Shows AI status, database info, and configuration.

---

### REST API

#### Start the API Server

```bash
python -m uvicorn invoice_qc.api.main:app --reload
```

**Access**:
- API Docs: http://localhost:8000/docs
- Frontend UI: http://localhost:8000/
- Health Check: http://localhost:8000/health

#### API Endpoints

##### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "ok",
  "service": "invoice-qc",
  "timestamp": "2024-12-06T10:30:00"
}
```

##### 2. Validate JSON

```bash
curl -X POST http://localhost:8000/validate-json \
  -H "Content-Type: application/json" \
  -d '[
    {
      "invoice_number": "INV-001",
      "invoice_date": "2024-01-15",
      "seller_name": "ABC Corp",
      "buyer_name": "XYZ Ltd",
      "currency": "USD",
      "net_total": 1000.00,
      "tax_amount": 180.00,
      "gross_total": 1180.00
    }
  ]'
```

**Response**:
```json
{
  "summary": {
    "total_invoices": 1,
    "valid_invoices": 1,
    "invalid_invoices": 0,
    "error_counts": {}
  },
  "results": [
    {
      "invoice_id": "INV-001",
      "is_valid": true,
      "errors": [],
      "warnings": ["Due date is missing"]
    }
  ]
}
```

##### 3. Extract and Validate PDFs

```bash
curl -X POST http://localhost:8000/extract-and-validate-pdfs \
  -F "files=@invoice1.pdf" \
  -F "files=@invoice2.pdf"
```

##### 4. Get All Invoices

```bash
curl http://localhost:8000/invoices
```

##### 5. Get Specific Invoice

```bash
curl http://localhost:8000/invoices/1
```

---

### Web Console

1. **Start the server**:
   ```bash
   python -m uvicorn invoice_qc.api.main:app --reload
   ```

2. **Open browser**: http://localhost:8000/

3. **Use the interface**:
   - **Upload PDFs**: Section 1 - Select files and extract
   - **Validate JSON**: Section 2 - Paste JSON data
   - **View Results**: Table with filtering and download options

---

## 🤖 AI Usage Notes

### AI Tools Used

I used **Claude (Anthropic)** minimally for:

1. **Regex Syntax Help**: Multi-format date parsing patterns
2. **Documentation Structure**: README template suggestions

**AI Usage**: ~10% - primarily for syntax references and documentation formatting.

**Core Development**: All extraction logic, validation rules, API endpoints, CLI tool, frontend, tests, and architecture were designed and implemented independently.


## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=invoice_qc --cov-report=html

# Run specific test file
python -m pytest tests/test_validator.py -v
```

## 🎯 Assumptions & Limitations

### Assumptions

1. **Invoice Language**: Primarily English and German, but AI can handle others
2. **PDF Format**: Text-based PDFs (not scanned images without OCR)
3. **Data Completeness**: At minimum, invoices contain number, date, parties, and amounts
4. **Currency Codes**: Using ISO 4217 standard (EUR, USD, GBP, INR)
5. **Date Formats**: Common formats (DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD)
6. **Decimal Precision**: Financial amounts rounded to 2 decimal places
7. **Line Items**: Optional - not all invoices provide itemized details

### Limitations

#### Technical Limitations

1. **AI Dependency**: Best extraction requires Google Gemini API (falls back to regex)
2. **PDF Format**: Cannot process scanned images without OCR preprocessing
3. **Concurrent Processing**: SQLite has limited concurrent write performance
4. **File Size**: PDFs limited to 50MB (configurable in `config.py`)
5. **Database**: SQLite suitable for moderate loads; use PostgreSQL for production

#### Business Logic Limitations

1. **Tax Validation**: Basic tax amount checks; doesn't validate specific tax rates by country
2. **Currency Conversion**: No automatic currency conversion
3. **Line Item Matching**: Warnings only; doesn't enforce strict line item validation
4. **Duplicate Detection**: Based on invoice number + seller + date only
5. **Historical Data**: No tracking of invoice modifications over time

### Edge Cases Not Fully Handled

1. **Credit Notes**: Negative invoices not specifically validated
2. **Multi-Currency**: Invoices with multiple currencies
3. **Partial Payments**: No tracking of payment status
4. **Invoice Amendments**: No versioning system for corrections
5. **Complex Discounts**: Line-level discounts may not calculate correctly

### Known Issues

1. ⚠️ **Regex Fallback**: Less accurate than AI, may miss edge cases
2. ⚠️ **Date Ambiguity**: MM/DD vs DD/MM format requires context
3. ⚠️ **Company Name Extraction**: Regex struggles with non-standard legal entities
4. ⚠️ **Handwritten PDFs**: Cannot process handwritten invoices

### Future Improvements

If given more time, I would add:

1. 🔄 **OCR Integration**: Tesseract for scanned documents
2. 🌐 **Multi-Language**: Better internationalization support
3. 📊 **Analytics Dashboard**: Visual reporting and trends
4. 🔐 **Authentication**: User login and role-based access
5. 🔔 **Notifications**: Email alerts for high-value or invalid invoices
6. 📝 **Audit Trail**: Track all changes and validations
7. 🚀 **Async Processing**: Queue system for large batches
8. 💾 **PostgreSQL**: Better database for production

---

## 🎥 Video Demonstration

**Video Link**: [Google Drive Link Here - Make Public]

---

## 📚 Project Structure

```
invoice-qc-service/
├── invoice_qc/
│   ├── __init__.py
│   ├── models.py              # Pydantic models
│   ├── extractor.py           # PDF extraction logic
│   ├── validator.py           # Validation rules
│   ├── database.py            # SQLite operations
│   ├── config.py              # Configuration
│   ├── cli.py                 # CLI commands
│   └── api/
│       ├── __init__.py
│       ├── main.py            # FastAPI app
│       ├── routes.py          # API endpoints
│       └── schemas.py         # API schemas
├── frontend/
│   ├── index.html             # Web console UI
│   └── app.js                 # Frontend logic
├── tests/
│   ├── conftest.py            # Test fixtures
│   ├── test_extractor.py      # Extractor tests
│   ├── test_validator.py      # Validator tests
│   ├── test_models.py         # Model tests
│   └── test_api.py            # API tests
├── ai-notes/
│   └── README.md              # AI usage documentation
├── pdfs/                      # Sample invoice PDFs
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

---

## 🤝 Contributing

Feedback is welcome!

---

## 📧 Contact

**Name**: Aman Nath Jha  
**Email**: amannathjha14@gmail.com  
**GitHub**: https://github.com/incursio-xd  
**LinkedIn**: www.linkedin.com/in/incursio

---
