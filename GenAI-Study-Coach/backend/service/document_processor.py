import PyPDF2
from docx import Document
import os

class DocumentProcessor:
    @staticmethod
    def extract_text_from_pdf(file):
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error reading PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_docx(file):
        """Extract text from DOCX file"""
        try:
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error reading DOCX: {str(e)}")
    
    @staticmethod
    def extract_text_from_txt(file):
        """Extract text from TXT file"""
        try:
            return file.read().decode('utf-8').strip()
        except Exception as e:
            raise ValueError(f"Error reading TXT: {str(e)}")
    
    @staticmethod
    def process_file(file):
        """Process uploaded file and extract text"""
        if not file:
            return None
        
        filename = file.filename.lower()
        
        if filename.endswith('.pdf'):
            return DocumentProcessor.extract_text_from_pdf(file)
        elif filename.endswith('.docx'):
            return DocumentProcessor.extract_text_from_docx(file)
        elif filename.endswith('.txt'):
            return DocumentProcessor.extract_text_from_txt(file)
        else:
            raise ValueError("Unsupported file format. Please upload PDF, DOCX, or TXT files.")
    
    @staticmethod
    def chunk_text(text, max_chars=8000, overlap=200):
        """Split large text into chunks with overlap to preserve boundary context"""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current_chunk = ""
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # carry last `overlap` chars into next chunk for context continuity
                current_chunk = current_chunk[-overlap:] + para + "\n\n" if overlap else para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks
