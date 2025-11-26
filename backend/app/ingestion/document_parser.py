import os
import re
from typing import Dict, List, Optional
from datetime import datetime
import pdfplumber
from docx import Document as DocxDocument

class DocumentParser:
    """Parse various document formats and extract structured content"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract full text from PDF"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
            return ""
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract full text from DOCX"""
        try:
            doc = DocxDocument(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error parsing DOCX {file_path}: {e}")
            return ""
    
    @staticmethod
    def extract_headings(text: str) -> List[str]:
        """Extract headings using pattern matching"""
        headings = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                if line.isupper() and len(line) > 3 and len(line) < 100:
                    headings.append(line)
                elif re.match(r'^\d+\.(\d+\.)*\s+[A-Z]', line):
                    headings.append(line)
        return headings[:20]
    
    @staticmethod
    def extract_section(text: str, section_keywords: List[str]) -> Optional[str]:
        """Extract specific section content based on keywords"""
        text_lower = text.lower()
        for keyword in section_keywords:
            pattern = rf'\b{keyword.lower()}\b'
            match = re.search(pattern, text_lower)
            if match:
                start_idx = match.start()
                remaining_text = text[start_idx:]
                next_section = re.search(r'\n[A-Z\d][A-Z\s]{5,}\n', remaining_text[100:])
                if next_section:
                    section_text = remaining_text[:100 + next_section.start()]
                else:
                    section_text = remaining_text[:1500]
                return section_text.strip()
        return None
    
    @classmethod
    def parse_document(cls, file_path: str) -> Optional[Dict]:
        """Main method to parse document and extract all fields"""
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if file_ext == '.pdf':
            text = cls.extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            text = cls.extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        else:
            return None
        
        if not text:
            return None
        
        headings = cls.extract_headings(text)
        background = cls.extract_section(text, ['background', 'introduction', 'overview'])
        scope = cls.extract_section(text, ['scope', 'scope of work', 'objectives'])
        title = headings[0] if headings else file_name
        
        return {
            'title': title,
            'file_path': file_path,
            'file_type': file_ext,
            'headings': headings,
            'background': background,
            'scope': scope,
            'content': text[:5000],
            'category': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
