"""
SQLite database operations for invoice storage.
"""
import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for invoices and validation results."""
    
    def __init__(self, db_path: str = "invoices.db"):
        """
        Initialize database connection and create tables.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._create_tables()
        logger.info(f"Database initialized at {db_path}")
    
    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create invoices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                seller_name TEXT NOT NULL,
                buyer_name TEXT NOT NULL,
                currency TEXT,
                net_total REAL,
                tax_amount REAL,
                gross_total REAL,
                data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(invoice_number, seller_name, invoice_date)
            )
        ''')
        
        # Create validation_results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                is_valid BOOLEAN,
                errors_json TEXT,
                validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database tables created/verified")
    
    def save_invoice(self, invoice_data: Dict) -> int:
        """
        Save invoice to database.
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Invoice ID in database
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO invoices (
                    invoice_number, invoice_date, seller_name, buyer_name,
                    currency, net_total, tax_amount, gross_total, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('invoice_date'),
                invoice_data.get('seller_name'),
                invoice_data.get('buyer_name'),
                invoice_data.get('currency'),
                invoice_data.get('net_total'),
                invoice_data.get('tax_amount'),
                invoice_data.get('gross_total'),
                json.dumps(invoice_data)
            ))
            
            invoice_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Saved invoice {invoice_data.get('invoice_number')} with ID {invoice_id}")
            return invoice_id
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate invoice detected: {str(e)}")
            # Get existing invoice ID
            cursor.execute('''
                SELECT id FROM invoices 
                WHERE invoice_number = ? AND seller_name = ? AND invoice_date = ?
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('seller_name'),
                invoice_data.get('invoice_date')
            ))
            result = cursor.fetchone()
            return result[0] if result else -1
        except Exception as e:
            logger.error(f"Error saving invoice: {str(e)}")
            return -1
        finally:
            conn.close()
    
    def get_invoice(self, invoice_id: int) -> Optional[Dict]:
        """
        Retrieve invoice by ID.
        
        Args:
            invoice_id: Database ID of invoice
            
        Returns:
            Invoice data dictionary or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, invoice_number, invoice_date, seller_name, buyer_name,
                       currency, net_total, tax_amount, gross_total, data_json, created_at
                FROM invoices WHERE id = ?
            ''', (invoice_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'invoice_number': row[1],
                    'invoice_date': row[2],
                    'seller_name': row[3],
                    'buyer_name': row[4],
                    'currency': row[5],
                    'net_total': row[6],
                    'tax_amount': row[7],
                    'gross_total': row[8],
                    'data_json': json.loads(row[9]) if row[9] else {},
                    'created_at': row[10]
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving invoice {invoice_id}: {str(e)}")
            return None
        finally:
            conn.close()
    
    def check_duplicate(self, invoice_number: str, seller_name: str, invoice_date: str) -> bool:
        """
        Check if invoice already exists in database.
        
        Args:
            invoice_number: Invoice number
            seller_name: Seller name
            invoice_date: Invoice date
            
        Returns:
            True if duplicate exists, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM invoices
                WHERE invoice_number = ? AND seller_name = ? AND invoice_date = ?
            ''', (invoice_number, seller_name, invoice_date))
            
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"Error checking duplicate: {str(e)}")
            return False
        finally:
            conn.close()
    
    def save_validation_result(self, invoice_id: int, result: Dict):
        """
        Save validation result for an invoice.
        
        Args:
            invoice_id: Database ID of invoice
            result: ValidationResult dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO validation_results (invoice_id, is_valid, errors_json)
                VALUES (?, ?, ?)
            ''', (
                invoice_id,
                result.get('is_valid', False),
                json.dumps(result.get('errors', []))
            ))
            
            conn.commit()
            logger.info(f"Saved validation result for invoice ID {invoice_id}")
        except Exception as e:
            logger.error(f"Error saving validation result: {str(e)}")
        finally:
            conn.close()
    
    def get_all_invoices(self) -> List[Dict]:
        """
        Retrieve all invoices from database.
        
        Returns:
            List of invoice dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, invoice_number, invoice_date, seller_name, buyer_name,
                       currency, net_total, tax_amount, gross_total, created_at
                FROM invoices
                ORDER BY created_at DESC
            ''')
            
            rows = cursor.fetchall()
            invoices = []
            for row in rows:
                invoices.append({
                    'id': row[0],
                    'invoice_number': row[1],
                    'invoice_date': row[2],
                    'seller_name': row[3],
                    'buyer_name': row[4],
                    'currency': row[5],
                    'net_total': row[6],
                    'tax_amount': row[7],
                    'gross_total': row[8],
                    'created_at': row[9]
                })
            
            logger.info(f"Retrieved {len(invoices)} invoices from database")
            return invoices
        except Exception as e:
            logger.error(f"Error retrieving invoices: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_validation_results(self, invoice_id: int) -> List[Dict]:
        """
        Get all validation results for an invoice.
        
        Args:
            invoice_id: Database ID of invoice
            
        Returns:
            List of validation result dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, is_valid, errors_json, validated_at
                FROM validation_results
                WHERE invoice_id = ?
                ORDER BY validated_at DESC
            ''', (invoice_id,))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'is_valid': bool(row[1]),
                    'errors': json.loads(row[2]) if row[2] else [],
                    'validated_at': row[3]
                })
            
            return results
        except Exception as e:
            logger.error(f"Error retrieving validation results: {str(e)}")
            return []
        finally:
            conn.close()
    
    def clear_all_data(self):
        """Clear all data from database (for testing/reset)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM validation_results')
            cursor.execute('DELETE FROM invoices')
            conn.commit()
            logger.info("All database data cleared")
        except Exception as e:
            logger.error(f"Error clearing database: {str(e)}")
        finally:
            conn.close()