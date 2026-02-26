import os
from typing import Optional


def load_resume_text_from_upload(file_path: str, original_filename: str) -> str:
    """Extract resume text from an uploaded file.

    Supported:
    - PDF via pdfplumber
    - DOCX via python-docx

    Notes:
    - No OCR is performed.
    - The caller is responsible for saving the uploaded file to disk first.
    """

    if not file_path or not os.path.exists(file_path):
        raise ValueError("Uploaded file path does not exist")

    name = (original_filename or "").lower()

    if name.endswith(".pdf"):
        try:
            import pdfplumber
        except Exception as e:
            raise RuntimeError("pdfplumber is required to read PDF resumes") from e

        texts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                txt = txt.strip()
                if txt:
                    texts.append(txt)
        return "\n".join(texts).strip()

    if name.endswith(".docx"):
        try:
            import docx
        except Exception as e:
            raise RuntimeError("python-docx is required to read DOCX resumes") from e

        d = docx.Document(file_path)
        parts = []
        for p in d.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts).strip()

    raise ValueError("Unsupported resume file type. Upload a .pdf or .docx")
