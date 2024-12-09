import os
import requests
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import utils
import re

# API key for the earnings call transcript service
API_KEY = 'cb9e5b2e-803e-421e-8a93-76690b87688b'
BASE_URL = 'https://discountingcashflows.com/api/transcript/'

# Directory to save downloaded PDFs
DOWNLOAD_DIR = '/Users/sainarasimhavayilati/Documents/flatronsai/C2'

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Company names and tickers dictionary
company_info = {
    'CVNA': 'CARVANA CO.',
    'GOOG': 'Alphabet Inc.',
    'NVDA': 'NVIDIA Corporation',
    'AAPL': 'Apple Inc.',
    'META': 'Meta Platforms, Inc.',
    'MSFT': 'Microsoft Corporation',
    'AMZN': 'Amazon.com, Inc.',
    'AAL': 'American Airlines Group',
    'DAL': 'Delta Air Lines',
    'UAL': 'United Airlines Holdings',
    'LUV': 'Southwest Airlines',
    'ALK': 'Alaska Air Group',
    'JBLU': 'JetBlue Airways',
    'SAVE': 'Spirit Airlines',
    'ULCC': 'Frontier Airlines Holdings',
    'HA': 'Hawaiian Holdings',
    'ALGT': 'Allegiant Travel',
    'TSLA': 'Tesla Inc.',
    'F': 'Ford Motor Company',
    'GM': 'General Motors',
    'STLA': 'Stellantis N.V.',
    'RIVN': 'Rivian Automotive',
    'LCID': 'Lucid Group',
    'RIDE': 'Lordstown Motors',
    'PII': 'Polaris Inc.',
    'TM': 'Toyota Motor Corporation',
    'HMC': 'Honda Motor Co., Ltd.'
}

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

# Function to fetch and download the earnings call transcript
def download_transcript_pdf(ticker, company_name, fiscal_year, quarter):
    url = f'{BASE_URL}?ticker={ticker}&quarter={quarter}&year={fiscal_year}&key={API_KEY}'

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Check if there's any content in the response
        if response.status_code == 200:
            transcript_data = response.json()

            if transcript_data and 'content' in transcript_data[0]:
                # Get the transcript content and generate a PDF
                content = transcript_data[0]['content']
                
                # Generate the PDF with ReportLab
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)
                can.setFont("Helvetica", 10)

                # Define the maximum width and height for text placement
                text_width = 540  # Based on letter page width, leave some margin
                text_height = 750  # Max height before adding a new page

                y_position = text_height  # Start from top of the page

                # Split the content into paragraphs
                paragraphs = content.split('\n')

                for paragraph in paragraphs:
                    # Split long paragraphs into smaller lines
                    wrapped_text = utils.simpleSplit(paragraph, "Helvetica", 10, text_width)

                    for line in wrapped_text:
                        if y_position < 40:  # Add new page when out of space
                            can.showPage()
                            y_position = text_height  # Reset y position for new page
                            can.setFont("Helvetica", 10)

                        can.drawString(30, y_position, line)  # Adjust left margin
                        y_position -= 12  # Move down by line height (12 pts)

                can.save()

                # Retrieve the generated PDF
                packet.seek(0)
                transcript_pdf = packet.read()

                # Build the sanitized file name
                sanitized_company_name = sanitize_filename(company_name)
                sanitized_filename = sanitize_filename(f'{sanitized_company_name}-{ticker}-Transcript-{fiscal_year}-Q{quarter}.pdf')

                # Add the filename watermark to the PDF
                watermarked_pdf_content = add_filename_to_pdf(transcript_pdf, sanitized_filename)

                # Save the final PDF
                file_path = os.path.join(DOWNLOAD_DIR, sanitized_filename)
                with open(file_path, 'wb') as output_pdf:
                    output_pdf.write(watermarked_pdf_content)

                print(f"Successfully downloaded and saved: {file_path}")
            else:
                print(f"No content found for {ticker} Q{quarter} {fiscal_year}")
        else:
            print(f"Error fetching transcript for {ticker} Q{quarter} {fiscal_year}: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading transcript for {ticker}: {e}")

# Function to download transcripts for each ticker from 2022 to 2024 for all quarters
def download_transcripts_for_ticker(ticker, company_name):
    for fiscal_year in range(2024, 2026):  # From 2022 to present (2024)
        for quarter in range(1, 5):  # Q1 to Q4
            download_transcript_pdf(ticker, company_name, fiscal_year, quarter)

# Main function to fetch and save transcripts for all the tickers
for ticker, company_name in company_info.items():
    download_transcripts_for_ticker(ticker, company_name)
