"""
Direct test script for PDF extraction and validation.
Bypasses CLI issues.
"""
from invoice_qc.extractor import InvoiceExtractor
from invoice_qc.validator import InvoiceValidator
from invoice_qc.database import Database
import json
from pathlib import Path

def main():
    print("\n" + "="*60)
    print("INVOICE QC - PDF EXTRACTION & VALIDATION TEST")
    print("="*60 + "\n")
    
    # Step 1: Extract from PDFs
    print("Step 1: Extracting invoices from PDFs...")
    print("-" * 60)
    
    pdf_dir = "pdfs"
    pdf_path = Path(pdf_dir)
    
    if not pdf_path.exists():
        print(f"❌ Error: Directory not found: {pdf_dir}")
        return
    
    pdf_files = list(pdf_path.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Warning: No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()
    
    extractor = InvoiceExtractor()
    invoices = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"Processing {i}/{len(pdf_files)}: {pdf_file.name}...", end=" ")
        try:
            invoice_data = extractor.extract_from_pdf(str(pdf_file))
            invoices.append(invoice_data)
            print("✓")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✓ Successfully extracted {len(invoices)} invoices\n")
    
    # Save extracted data
    output_path = Path("outputs/extracted_invoices.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(invoices, f, indent=2, default=str)
    
    print(f"✓ Saved extracted data to: {output_path}\n")
    
    # Step 2: Validate
    print("Step 2: Validating invoices...")
    print("-" * 60)
    
    validator = InvoiceValidator()
    validation_result = validator.validate_batch(invoices)
    
    summary = validation_result['summary']
    
    print(f"Total Invoices:   {summary['total_invoices']}")
    print(f"Valid Invoices:   {summary['valid_invoices']} ✓")
    print(f"Invalid Invoices: {summary['invalid_invoices']} ✗")
    print(f"Validation Rate:  {summary['valid_invoices'] / summary['total_invoices'] * 100:.1f}%\n")
    
    # Save validation report
    report_path = Path("outputs/validation_report.json")
    with open(report_path, 'w') as f:
        json.dump(validation_result, f, indent=2, default=str)
    
    print(f"✓ Saved validation report to: {report_path}\n")
    
    # Show validation details
    if summary['error_counts']:
        print("Top Validation Errors:")
        print("-" * 60)
        sorted_errors = sorted(
            summary['error_counts'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for error, count in sorted_errors:
            print(f"  [{count}x] {error}")
        print()
    
    # Show sample of extracted data
    print("Sample Extracted Data (First Invoice):")
    print("-" * 60)
    if invoices:
        sample = invoices[0]
        print(f"Invoice Number: {sample.get('invoice_number', 'N/A')}")
        print(f"Invoice Date:   {sample.get('invoice_date', 'N/A')}")
        print(f"Seller:         {sample.get('seller_name', 'N/A')}")
        print(f"Buyer:          {sample.get('buyer_name', 'N/A')}")
        print(f"Currency:       {sample.get('currency', 'N/A')}")
        print(f"Net Total:      {sample.get('net_total', 'N/A')}")
        print(f"Tax Amount:     {sample.get('tax_amount', 'N/A')}")
        print(f"Gross Total:    {sample.get('gross_total', 'N/A')}")
        print(f"Line Items:     {len(sample.get('line_items', []))} items")
    print()
    
    # Step 3: Save to database
    print("Step 3: Saving to database...")
    print("-" * 60)
    
    db = Database("invoices.db")
    saved_count = 0
    
    for invoice_data, result in zip(invoices, validation_result['results']):
        try:
            invoice_id = db.save_invoice(invoice_data)
            if invoice_id > 0:
                db.save_validation_result(invoice_id, result)
                saved_count += 1
        except Exception as e:
            print(f"⚠️  Warning: Could not save invoice: {str(e)}")
    
    print(f"✓ Saved {saved_count} records to database\n")
    
    # Final summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✓ Processed {len(pdf_files)} PDF files")
    print(f"✓ Extracted {len(invoices)} invoices")
    print(f"✓ {summary['valid_invoices']} valid, {summary['invalid_invoices']} invalid")
    print(f"✓ Data saved to outputs/ directory")
    print(f"✓ Database saved to invoices.db")
    print("="*60 + "\n")
    
    if summary['invalid_invoices'] > 0:
        print("⚠️  Some invoices have validation errors. Check validation_report.json for details.\n")
    else:
        print("✓ All invoices passed validation!\n")


if __name__ == "__main__":
    main()