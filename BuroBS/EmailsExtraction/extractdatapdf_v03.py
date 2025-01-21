from pdfplumber import open as open_pdf
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import re
import pandas as pd

# Path to the PDF file
pdf_path = 'C:/Users/alexj/OneDrive/Documents/GitHub/DataMining/BuroBS/AmCham-Guatemala-Membership-Directory-2021.pdf'

# Function to extract text from all pages using pdfplumber
def extract_text_with_pdfplumber(pdf_path):
    """
    Extracts text from a PDF file using pdfplumber.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        str: The extracted text from the PDF.
    """
    text = ""
    with open_pdf(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# Function to extract text using OCR with pytesseract
def extract_text_with_ocr(pdf_path):
    """
    Extracts text from a PDF file using OCR (Tesseract).
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        str: The extracted text from the PDF using OCR.
    """
    text = ""
    pdf_document = fitz.open(pdf_path)
    for page_number in range(len(pdf_document)):
        # Render the page as an image
        pix = pdf_document[page_number].get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # Apply OCR to the image
        text += pytesseract.image_to_string(image, lang="eng+spa") + "\n"
    return text

# Function to extract emails from the text
def extract_emails_from_text(text):
    """
    Extracts email addresses from the given text using a regular expression.
    Args:
        text (str): The input text.
    Returns:
        list: A list of unique email addresses found in the text.
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(email_pattern, text)))  # Remove duplicates

# Main script to process the PDF
try:
    # Extract text using pdfplumber
    text_from_pdf = extract_text_with_pdfplumber(pdf_path)

    # If the extracted text is insufficient, apply OCR
    if len(text_from_pdf.strip()) < 100:  # Check if the extracted text is minimal
        print("Insufficient text extracted. Using OCR...")
        text_from_pdf = extract_text_with_ocr(pdf_path)

    # Extract email addresses
    emails = extract_emails_from_text(text_from_pdf)

    # Save the extracted emails to a CSV file
    df = pd.DataFrame(emails, columns=["Email"])
    output_path = "Extracted_Emails_AmCham_GT.csv"
    df.to_csv(output_path, index=False)
    print(f"Emails extracted and saved to {output_path}")

except Exception as e:
    print(f"An error has occurred: {e}")
