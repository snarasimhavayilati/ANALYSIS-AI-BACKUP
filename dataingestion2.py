import os
import time
import requests
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import re

# API key for sec-api.io
API_KEY = '6bc9fcd66ef9da28e9e5d424b7472f7d39f5c5c42f58e300e580ad268a17c7b7'

# Directory to save downloaded PDFs
DOWNLOAD_DIR = '/Users/sainarasimhavayilati/Documents/flatronsai/C2'

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# List of tickers to search for (use tickers now)
tickers = [ 'CVNA',
    'GOOG', 'NVDA', 'AAPL', 'META', 'MSFT', 'AMZN',
    'AAL', 'DAL', 'UAL', 'LUV', 'ALK', 'JBLU', 'SAVE', 'ULCC', 'HA', 'ALGT',
    'TSLA', 'F', 'GM', 'STLA', 'RIVN', 'LCID', 'RIDE', 'PII', 'TM', 'HMC'
]

# Function to sanitize file name
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "-", filename)

# Function to create header and footer canvas
def create_header_footer(file_name, page_width, page_height):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Set font size
    can.setFont("Helvetica", 6)
    
    # Add header (right-aligned) and footer (left-aligned)
    can.drawRightString(page_width - 10, page_height - 10, f"Filename: {file_name}")  # Header
    can.drawString(10, 10, f"Filename: {file_name}")  # Footer
    can.save()
    
    packet.seek(0)
    return PdfReader(packet)

# Function to merge header/footer with the original PDF
def add_filename_to_pdf(input_pdf_content, file_name):
    reader = PdfReader(BytesIO(input_pdf_content))
    writer = PdfWriter()

    # Loop through each page and add header/footer
    for page in reader.pages:
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Create header/footer PDF and merge it
        header_footer_pdf = create_header_footer(file_name, page_width, page_height)
        watermark_page = header_footer_pdf.pages[0]

        # Merge the header/footer into the page
        page.merge_page(watermark_page)
        writer.add_page(page)

    # Write the final output to a BytesIO object
    output_stream = BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()

# Function to download a PDF version of a filing and add header/footer
def download_filing_pdf(filing_url, company_name, ticker, form_type, fiscal_year, fiscal_quarter):
    sanitized_company_name = sanitize_filename(company_name)
    sanitized_form_type = sanitize_filename(form_type)
    pdf_url = f'https://api.sec-api.io/filing-reader?token={API_KEY}&type=pdf&url={filing_url}'

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()

        # Build the sanitized file name and path
        file_name = f"{sanitized_company_name}-{ticker}-{sanitized_form_type}-{fiscal_year}-{fiscal_quarter}.pdf"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)

        # Add the header/footer to the PDF content
        watermarked_pdf_content = add_filename_to_pdf(response.content, file_name)

        # Save the watermarked PDF to the local directory
        with open(file_path, 'wb') as output_pdf:
            output_pdf.write(watermarked_pdf_content)

        print(f"Downloaded and watermarked: {file_name}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF for {company_name} filing: {e}")

# Function to extract fiscal quarter from the periodOfReport
def get_fiscal_quarter(period_of_report):
    try:
        month = int(period_of_report.split('-')[1])
        if 1 <= month <= 3:
            return 'Q1'
        elif 4 <= month <= 6:
            return 'Q2'
        elif 7 <= month <= 9:
            return 'Q3'
        else:
            return 'Q4'
    except (IndexError, ValueError) as e:
        print(f"Error extracting fiscal quarter from {period_of_report}: {e}")
        return 'N/A'

# Function to fetch data for a company based on ticker
def fetch_sec_data(ticker):
    # Starting point for pagination
    from_value = 0
    size = 100  # Adjust size to a large number to retrieve more filings per request
    all_results = []

    # Modigy date accordingly
    filed_at_filter = '[2024-11-01T00:00:00 TO *]'

    while True:
        # Build query to filter by ticker, formType (10-Q, 10-K, 20-F), and filedAt after 2022
        query = {
            "query": f'ticker:("{ticker}") AND (formType:"10-K" OR formType:"10-Q" OR formType:"20-F") AND filedAt:{filed_at_filter}',
            "from": str(from_value),
            "size": str(size),
            "sort": [{"filedAt": {"order": "desc"}}]
        }

        try:
            # Send request to sec-api.io
            response = requests.post(
                'https://api.sec-api.io', 
                headers={'Authorization': API_KEY}, 
                json=query
            )
            
            response.raise_for_status()  # Raise an exception for bad requests

            # Parse the JSON response
            data = response.json()

            filings = data.get('filings', [])
            if not filings:
                break  # Exit if no more filings are returned
            
            for filing in filings:
                try:
                    form_type = filing.get('formType', 'N/A')
                    company_name = filing.get('companyName', 'N/A')
                    ticker = filing.get('ticker', 'N/A')
                    period_of_report = filing.get('periodOfReport', 'N/A')
                    filed_at = filing.get('filedAt', 'N/A')
                    filing_url = filing.get('linkToFilingDetails', 'N/A')

                    # Extract fiscal year and quarter from periodOfReport
                    fiscal_year = 'N/A'
                    fiscal_quarter = 'N/A'
                    if period_of_report != 'N/A':
                        try:
                            # Extract fiscal year
                            fiscal_year = int(period_of_report.split('-')[0])

                            # Extract fiscal quarter
                            fiscal_quarter = get_fiscal_quarter(period_of_report)
                        except ValueError as ve:
                            print(f"Error parsing periodOfReport {period_of_report}: {ve}")
                            continue

                    # Download the filing as a PDF and watermark
                    if filing_url != 'N/A':
                        download_filing_pdf(filing_url, company_name, ticker, form_type, fiscal_year, fiscal_quarter)

                    # Add filing to results
                    all_results.append({
                        'companyName': company_name,
                        'ticker': ticker,
                        'formType': form_type,
                        'fiscalYear': fiscal_year,
                        'fiscalQuarter': fiscal_quarter,
                        'periodOfReport': period_of_report,
                        'filedAt': filed_at
                    })
                except KeyError as ke:
                    print(f"Error processing filing data: {ke}")
                    continue

            # Increment `from_value` to paginate through results
            from_value += size

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for ticker {ticker}: {e}")
            break

    return all_results

# Fetch data for all tickers
for ticker in tickers:
    try:
        ticker_filings = fetch_sec_data(ticker)
        if ticker_filings:
            print(f"Data for {ticker}:")
            for filing in ticker_filings:
                print(filing)
        else:
            print(f"No data found for {ticker}")
    except Exception as e:
        print(f"Unexpected error processing data for {ticker}: {e}")

    # Sleep between requests to avoid hitting API rate limits
    time.sleep(1)
