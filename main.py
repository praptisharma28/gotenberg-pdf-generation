from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
import httpx
from pydantic import BaseModel
from pathlib import Path
import os
import logging
import pandas as pd
import io
from typing import Optional, List
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Generation Service")
templates = Jinja2Templates(directory="templates")

# Gotenberg service URL
GOTENBERG_URL = "http://localhost:3000"

# Create directories for temporary storage
TEMP_DIR = Path("temp_pdfs")
TEMP_DIR.mkdir(exist_ok=True)

class InvoiceItem(BaseModel):
    description: str
    quantity: int
    price: float
    total: float

class InvoiceRequest(BaseModel):
    invoice_number: str
    date: str
    due_date: str
    company_name: str
    company_address: str
    client_name: str
    client_address: str
    items: List[InvoiceItem]
    subtotal: float
    tax: float
    total: float
    notes: Optional[str] = None

async def generate_invoice_html(invoice_data: InvoiceRequest) -> str:
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Invoice</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }
            .invoice-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 40px;
            }
            .company-details {
                text-align: right;
            }
            .invoice-title {
                font-size: 24px;
                color: #333;
                margin-bottom: 20px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f8f9fa;
            }
            .totals {
                text-align: right;
                margin-top: 20px;
            }
            .totals div {
                margin: 5px 0;
            }
            .notes {
                margin-top: 30px;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .footer {
                margin-top: 50px;
                text-align: center;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="invoice-header">
            <div>
                <div class="invoice-title">INVOICE</div>
                <div>Invoice #: """ + invoice_data.invoice_number + """</div>
                <div>Date: """ + invoice_data.date + """</div>
                <div>Due Date: """ + invoice_data.due_date + """</div>
            </div>
            <div class="company-details">
                <strong>""" + invoice_data.company_name + """</strong><br>
                """ + invoice_data.company_address.replace('\n', '<br>') + """
            </div>
        </div>

        <div class="client-details">
            <strong>Bill To:</strong><br>
            """ + invoice_data.client_name + """<br>
            """ + invoice_data.client_address.replace('\n', '<br>') + """
        </div>

        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                """ + '\n'.join([f"""
                <tr>
                    <td>{item.description}</td>
                    <td>{item.quantity}</td>
                    <td>${item.price:.2f}</td>
                    <td>${item.total:.2f}</td>
                </tr>
                """ for item in invoice_data.items]) + """
            </tbody>
        </table>

        <div class="totals">
            <div>Subtotal: $""" + f"{invoice_data.subtotal:.2f}" + """</div>
            <div>Tax: $""" + f"{invoice_data.tax:.2f}" + """</div>
            <div><strong>Total: $""" + f"{invoice_data.total:.2f}" + """</strong></div>
        </div>

        """ + (f"""
        <div class="notes">
            <strong>Notes:</strong><br>
            {invoice_data.notes}
        </div>
        """ if invoice_data.notes else "") + """

        <div class="footer">
            Thank you for your business!
        </div>
    </body>
    </html>
    """

@app.post("/convert/invoice", response_class=FileResponse)
async def convert_invoice_to_pdf(invoice_data: InvoiceRequest):
    """Convert invoice data to PDF using Gotenberg"""
    try:
        # Generate HTML from invoice data
        html_content = await generate_invoice_html(invoice_data)
        pdf_path = TEMP_DIR / f"invoice_{os.urandom(8).hex()}.pdf"

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {
                'index.html': ('index.html', html_content.encode(), 'text/html'),
            }
            
            response = await client.post(
                f"{GOTENBERG_URL}/forms/chromium/convert/html",
                files=files
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="PDF generation failed")
            
            pdf_path.write_bytes(response.content)
            
            return FileResponse(
                path=pdf_path,
                filename=f"invoice_{invoice_data.invoice_number}.pdf",
                media_type="application/pdf"
            )
    except Exception as e:
        logger.error(f"Error generating invoice PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert/csv", response_class=FileResponse)
async def convert_csv_to_pdf(file: UploadFile = File(...)):
    """Convert CSV to PDF using Gotenberg"""
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Convert DataFrame to HTML table with styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 8px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
            </style>
        </head>
        <body>
            <h2>CSV Data Report</h2>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            {df.to_html(index=False)}
        </body>
        </html>
        """
        
        pdf_path = TEMP_DIR / f"csv_{os.urandom(8).hex()}.pdf"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {
                'index.html': ('index.html', html_content.encode(), 'text/html'),
            }
            
            response = await client.post(
                f"{GOTENBERG_URL}/forms/chromium/convert/html",
                files=files
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="PDF generation failed")
            
            pdf_path.write_bytes(response.content)
            
            return FileResponse(
                path=pdf_path,
                filename="csv_report.pdf",
                media_type="application/pdf"
            )
    except Exception as e:
        logger.error(f"Error converting CSV to PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert/html", response_class=FileResponse)
async def convert_html_to_pdf():
    """Convert HTML template to PDF using Gotenberg"""
    try:
        # Read HTML template from file
        template_path = Path("templates/index.html")
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template file not found")
            
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        pdf_path = TEMP_DIR / f"report_{os.urandom(8).hex()}.pdf"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare files dictionary with HTML and images
            files = {
                'index.html': ('index.html', html_content.encode('utf-8'), 'text/html'),
            }
            
            # Add image files to the request
            image_files = {
                'sales-trend-losses.png': 'templates/sales-trend-losses.png',
                'regional-performance.jpg': 'templates/regional-performance.jpg'
            }
            
            for img_name, img_path in image_files.items():
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as img_file:
                        files[img_name] = (img_name, img_file.read(), f'image/{img_path.split(".")[-1]}')
                else:
                    logger.warning(f"Image file not found: {img_path}")
            
            response = await client.post(
                f"{GOTENBERG_URL}/forms/chromium/convert/html",
                data={
                    'paperWidth': '8.27',
                    'paperHeight': '11.7',
                    'marginTop': '0.5',
                    'marginBottom': '0.5',
                    'marginLeft': '0.5',
                    'marginRight': '0.5',
                },
                files=files
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="PDF generation failed")
            
            if not response.content:
                raise HTTPException(status_code=500, detail="Received empty PDF content")
                
            pdf_path.write_bytes(response.content)
            
            return FileResponse(
                path=pdf_path,
                filename="report.pdf",
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=report.pdf"}
            )
    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
