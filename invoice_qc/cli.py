import json
import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

from .extractor import InvoiceExtractor
from .validator import InvoiceValidator
from .database import Database
from .config import settings

app = typer.Typer(
    name="invoice-qc",
    help="Invoice Quality Control - Extract and validate invoices from PDFs",
    add_completion=False
)
console = Console()


@app.command(name="extract")
def extract_command(
    pdf_dir: str = typer.Argument(..., help="Directory containing PDF files"),
    output: str = typer.Option("extracted_invoices.json", "--output", "-o", help="Output JSON file")
):
    """
    Extract invoice data from PDF files.
    
    Example:
        python -m invoice_qc.cli extract pdfs --output output.json
    """
    console.print(Panel.fit(
        f"[bold cyan]Invoice Extraction[/bold cyan]\n"
        f"PDF Directory: {pdf_dir}\n"
        f"Output File: {output}",
        border_style="cyan"
    ))
    
    # Validate directory
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        console.print(f"[bold red]✗ Error:[/bold red] Directory not found: {pdf_dir}")
        raise typer.Exit(code=1)
    
    # Find PDFs
    pdf_files = sorted(pdf_path.glob("*.pdf"))
    if not pdf_files:
        console.print(f"[bold yellow]⚠ Warning:[/bold yellow] No PDF files found in {pdf_dir}")
        raise typer.Exit(code=0)
    
    console.print(f"\n[cyan]Found {len(pdf_files)} PDF file(s)[/cyan]\n")
    
    # Extract with progress
    extractor = InvoiceExtractor()
    invoices = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Extracting...", total=len(pdf_files))
        
        for pdf_file in pdf_files:
            progress.update(task, description=f"Processing {pdf_file.name[:30]}...")
            try:
                invoice_data = extractor.extract_from_pdf(str(pdf_file))
                invoices.append(invoice_data)
            except Exception as e:
                console.print(f"[yellow]⚠ Warning: Failed to extract {pdf_file.name}: {e}[/yellow]")
            progress.advance(task)
    
    # Save results
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, indent=2, default=str, ensure_ascii=False)
    
    # Summary table
    console.print()
    table = Table(title="Extraction Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("PDF Files Processed", str(len(pdf_files)))
    table.add_row("Invoices Extracted", str(len(invoices)))
    table.add_row("Output File", str(output_path.absolute()))
    
    console.print(table)
    console.print(f"\n[bold green]✓ Extraction complete![/bold green]\n")


@app.command(name="validate")
def validate_command(
    input_file: str = typer.Argument(..., help="Input JSON file with invoices"),
    report: str = typer.Option("validation_report.json", "--report", "-r", help="Output report file")
):
    console.print(Panel.fit(
        f"[bold cyan]Invoice Validation[/bold cyan]\n"
        f"Input File: {input_file}\n"
        f"Report File: {report}",
        border_style="cyan"
    ))
    
    # Load invoices
    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[bold red]✗ Error:[/bold red] File not found: {input_file}")
        raise typer.Exit(code=1)
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            invoices = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[bold red]✗ Error:[/bold red] Invalid JSON: {e}")
        raise typer.Exit(code=1)
    
    console.print(f"\n[cyan]Loaded {len(invoices)} invoice(s)[/cyan]\n")
    
    # Validate
    validator = InvoiceValidator()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Validating...", total=None)
        validation_result = validator.validate_batch(invoices)
        progress.update(task, completed=True)
    
    # Save report
    report_path = Path(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(validation_result, f, indent=2, default=str, ensure_ascii=False)
    
    # Display results
    summary = validation_result['summary']
    
    console.print()
    table = Table(title="Validation Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", justify="right")
    
    table.add_row("Total Invoices", str(summary['total_invoices']))
    table.add_row("Valid Invoices", f"[green]{summary['valid_invoices']}[/green]")
    table.add_row("Invalid Invoices", f"[red]{summary['invalid_invoices']}[/red]")
    
    if summary['total_invoices'] > 0:
        rate = (summary['valid_invoices'] / summary['total_invoices']) * 100
        table.add_row("Success Rate", f"{rate:.1f}%")
    
    console.print(table)
    
    # Show top errors if any
    if summary.get('error_counts'):
        console.print("\n[bold]Top Validation Errors:[/bold]")
        error_table = Table(show_header=True, header_style="bold red")
        error_table.add_column("Error", style="red")
        error_table.add_column("Count", justify="right", style="yellow")
        
        sorted_errors = sorted(
            summary['error_counts'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for error, count in sorted_errors:
            error_table.add_row(error, str(count))
        
        console.print(error_table)
    
    console.print(f"\n[dim]Report saved to: {report_path.absolute()}[/dim]")
    
    # Exit status
    if summary['invalid_invoices'] > 0:
        console.print(f"\n[bold yellow]⚠ Completed with {summary['invalid_invoices']} invalid invoice(s)[/bold yellow]\n")
        raise typer.Exit(code=1)
    else:
        console.print("\n[bold green]✓ All invoices are valid![/bold green]\n")
        raise typer.Exit(code=0)


@app.command(name="process")
def process_command(
    pdf_dir: str = typer.Argument(..., help="Directory containing PDF files"),
    output_dir: str = typer.Option("outputs", "--output-dir", "-o", help="Output directory for results"),
    save_db: bool = typer.Option(True, "--save-db/--no-save-db", help="Save to database"),
):
    console.print(Panel.fit(
        "[bold cyan]Invoice QC - Full Pipeline[/bold cyan]\n"
        f"PDF Directory: {pdf_dir}\n"
        f"Output Directory: {output_dir}\n"
        f"Save to Database: {save_db}",
        border_style="cyan"
    ))
    
    # Validate directory
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        console.print(f"[bold red]✗ Error:[/bold red] Directory not found: {pdf_dir}")
        raise typer.Exit(code=1)
    
    pdf_files = sorted(pdf_path.glob("*.pdf"))
    if not pdf_files:
        console.print(f"[bold yellow]⚠ Warning:[/bold yellow] No PDF files found")
        raise typer.Exit(code=0)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # STEP 1: Extract
    console.print("\n[bold]═══ Step 1/3: Extraction ═══[/bold]")
    extractor = InvoiceExtractor()
    invoices = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Extracting PDFs...", total=len(pdf_files))
        
        for pdf_file in pdf_files:
            progress.update(task, description=f"Processing {pdf_file.name[:25]}...")
            try:
                invoice_data = extractor.extract_from_pdf(str(pdf_file))
                invoices.append(invoice_data)
            except Exception as e:
                console.print(f"[yellow]⚠ Failed: {pdf_file.name}[/yellow]")
            progress.advance(task)
    
    console.print(f"[green]✓ Extracted {len(invoices)} invoice(s)[/green]")
    
    # Save extracted data
    extracted_file = output_path / "extracted_invoices.json"
    with open(extracted_file, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, indent=2, default=str, ensure_ascii=False)
    
    # STEP 2: Validate
    console.print("\n[bold]═══ Step 2/3: Validation ═══[/bold]")
    validator = InvoiceValidator()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Validating invoices...", total=None)
        validation_result = validator.validate_batch(invoices)
        progress.update(task, completed=True)
    
    summary = validation_result['summary']
    console.print(f"[green]✓ Validated {summary['total_invoices']} invoice(s)[/green]")
    
    # Save validation report
    report_file = output_path / "validation_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(validation_result, f, indent=2, default=str, ensure_ascii=False)
    
    # STEP 3: Save to database
    if save_db:
        console.print("\n[bold]═══ Step 3/3: Database Storage ═══[/bold]")
        db = Database(settings.database_path)
        saved_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Saving to database...", total=len(invoices))
            
            for invoice_data, result in zip(invoices, validation_result['results']):
                try:
                    invoice_id = db.save_invoice(invoice_data)
                    if invoice_id > 0:
                        db.save_validation_result(invoice_id, result)
                        saved_count += 1
                except Exception:
                    pass  # Continue on error
                progress.advance(task)
        
        console.print(f"[green]✓ Saved {saved_count} record(s) to database[/green]")
    else:
        console.print("\n[dim]═══ Step 3/3: Database Storage (Skipped) ═══[/dim]")
    
    # Final Summary
    console.print("\n" + "═" * 60)
    console.print("[bold cyan]Final Summary[/bold cyan]")
    console.print("═" * 60)
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("PDF Files", str(len(pdf_files)))
    table.add_row("Invoices Extracted", str(len(invoices)))
    table.add_row("Valid Invoices", f"[green]{summary['valid_invoices']}[/green]")
    table.add_row("Invalid Invoices", f"[red]{summary['invalid_invoices']}[/red]")
    
    if summary['total_invoices'] > 0:
        rate = (summary['valid_invoices'] / summary['total_invoices']) * 100
        table.add_row("Success Rate", f"{rate:.1f}%")
    
    table.add_row("Extracted Data", str(extracted_file.absolute()))
    table.add_row("Validation Report", str(report_file.absolute()))
    if save_db:
        table.add_row("Database", str(Path(settings.database_path).absolute()))
    
    console.print(table)
    console.print("═" * 60)
    
    # Exit status
    if summary['invalid_invoices'] > 0:
        console.print("\n[bold yellow]⚠ Pipeline completed with validation errors[/bold yellow]\n")
        raise typer.Exit(code=1)
    else:
        console.print("\n[bold green]✓ Pipeline completed successfully![/bold green]\n")
        raise typer.Exit(code=0)


@app.command(name="info")
def info_command():
    """Show system information and status."""
    console.print(Panel.fit(
        "[bold cyan]Invoice QC System Information[/bold cyan]",
        border_style="cyan"
    ))
    
    # Check AI availability
    extractor = InvoiceExtractor()
    ai_status = "✓ Enabled (Gemini)" if extractor.use_ai else "✗ Disabled (using regex fallback)"
    ai_color = "green" if extractor.use_ai else "yellow"
    
    # System info table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    table.add_row("AI Extraction", f"[{ai_color}]{ai_status}[/{ai_color}]")
    table.add_row("Database", settings.database_path)
    table.add_row("API Host", f"{settings.api_host}:{settings.api_port}")
    table.add_row("Log Level", settings.log_level)
    
    console.print(table)
    
    # Database stats
    try:
        db = Database(settings.database_path)
        invoices = db.get_all_invoices()
        console.print(f"\n[cyan]Database contains {len(invoices)} invoice(s)[/cyan]")
    except Exception:
        console.print("\n[dim]Database not initialized[/dim]")
    
    console.print()


if __name__ == "__main__":
    app()