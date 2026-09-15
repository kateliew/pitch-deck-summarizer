import logging
import PyPDF2

def parse_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file."""
    pdf_text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                pdf_text += page.extract_text()
        logging.info(f"Extracted text from PDF: {pdf_text[:500]}...")
    except Exception as e:
        logging.error(f"Error reading PDF file: {str(e)}")
        return ""
    return pdf_text