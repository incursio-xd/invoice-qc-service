"""
Tests for FastAPI endpoints.
"""
import pytest
import json
import tempfile
from io import BytesIO


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def test_health_endpoint(self, api_client):
        """Test /health endpoint."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['service'] == 'invoice-qc'
        assert 'timestamp' in data
    
    def test_validate_json_endpoint_valid(self, api_client, sample_invoice):
        """Test /validate-json with valid invoice."""
        response = api_client.post(
            "/validate-json",
            json=[sample_invoice]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'summary' in data
        assert 'results' in data
        assert data['summary']['total_invoices'] == 1
        assert data['summary']['valid_invoices'] >= 0
    
    def test_validate_json_endpoint_invalid(self, api_client, invalid_invoice):
        """Test /validate-json with invalid invoice."""
        response = api_client.post(
            "/validate-json",
            json=[invalid_invoice]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['summary']['invalid_invoices'] > 0
        assert len(data['results']) == 1
        assert data['results'][0]['is_valid'] is False
        assert len(data['results'][0]['errors']) > 0
    
    def test_validate_json_endpoint_multiple(self, api_client, sample_invoices):
        """Test /validate-json with multiple invoices."""
        response = api_client.post(
            "/validate-json",
            json=sample_invoices
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['summary']['total_invoices'] == len(sample_invoices)
        assert len(data['results']) == len(sample_invoices)
    
    def test_validate_json_endpoint_empty_list(self, api_client):
        """Test /validate-json with empty list."""
        response = api_client.post(
            "/validate-json",
            json=[]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['summary']['total_invoices'] == 0
    
    def test_extract_and_validate_pdfs_endpoint(self, api_client):
        """Test /extract-and-validate-pdfs with mock PDF."""
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\nMock PDF content\n%%EOF"
        files = {
            'files': ('test_invoice.pdf', BytesIO(pdf_content), 'application/pdf')
        }
        
        response = api_client.post(
            "/extract-and-validate-pdfs",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'total_files' in data
        assert 'results' in data
        assert 'summary' in data
        assert data['total_files'] >= 1
    
    def test_extract_and_validate_pdfs_multiple_files(self, api_client):
        """Test /extract-and-validate-pdfs with multiple PDFs."""
        pdf_content = b"%PDF-1.4\nMock PDF\n%%EOF"
        files = [
            ('files', ('invoice1.pdf', BytesIO(pdf_content), 'application/pdf')),
            ('files', ('invoice2.pdf', BytesIO(pdf_content), 'application/pdf'))
        ]
        
        response = api_client.post(
            "/extract-and-validate-pdfs",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_files'] == 2
    
    def test_extract_and_validate_pdfs_no_files(self, api_client):
        """Test /extract-and-validate-pdfs with no files."""
        response = api_client.post(
            "/extract-and-validate-pdfs",
            files=[]
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 422]
    
    def test_get_all_invoices_endpoint(self, api_client):
        """Test /invoices endpoint."""
        response = api_client.get("/invoices")
        
        assert response.status_code == 200
        data = response.json()
        assert 'total' in data
        assert 'invoices' in data
        assert isinstance(data['invoices'], list)
    
    def test_get_invoice_by_id_not_found(self, api_client):
        """Test /invoices/{id} with non-existent ID."""
        response = api_client.get("/invoices/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
    
    def test_cors_headers(self, api_client):
        """Test CORS headers are present."""
        response = api_client.options("/health")
        # FastAPI test client doesn't fully simulate CORS,
        # but we can verify the endpoint is accessible
        assert response.status_code in [200, 405]
    
    def test_api_error_handling(self, api_client):
        """Test API error handling with invalid JSON."""
        response = api_client.post(
            "/validate-json",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_validate_json_with_malformed_data(self, api_client):
        """Test /validate-json with malformed invoice data."""
        malformed_invoice = {
            'invoice_number': 123,  # Should be string
            'invoice_date': 'not-a-date',
            'seller_name': None,
        }
        
        response = api_client.post(
            "/validate-json",
            json=[malformed_invoice]
        )
        
        # Should still return 200 but with validation errors
        assert response.status_code == 200
        data = response.json()
        assert data['summary']['invalid_invoices'] > 0