import os
from typing import IO, Union


def extract_text_from_pdf(file_path_or_stream: Union[str, IO[bytes]]) -> str:
    """Extract text from a PDF resume using pdfplumber (no OCR)."""

    try:
        import pdfplumber
    except Exception as e:
        raise RuntimeError("pdfplumber is required to read PDF resumes") from e

    texts = []
    with pdfplumber.open(file_path_or_stream) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            txt = txt.strip()
            if txt:
                texts.append(txt)
    return "\n".join(texts).strip()


def extract_text_from_docx(file_path_or_stream: Union[str, IO[bytes]]) -> str:
    """Extract text from a DOCX resume using python-docx."""

    try:
        import docx
    except Exception as e:
        raise RuntimeError("python-docx is required to read DOCX resumes") from e

    d = docx.Document(file_path_or_stream)
    parts = []
    for p in d.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts).strip()


def extract_text_from_upload(file_storage) -> str:
    """Extract resume text from a Flask FileStorage upload.

    Auto-detects extension from filename and reads from stream.
    """

    if file_storage is None:
        raise ValueError("No file uploaded")

    filename = (getattr(file_storage, "filename", "") or "").lower()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_storage.stream)
    if filename.endswith(".docx"):
        return extract_text_from_docx(file_storage.stream)

    raise ValueError("Unsupported resume file type. Upload a .pdf or .docx")


def load_resume_text_from_upload(file_path: str, original_filename: str) -> str:
    """Backwards-compatible helper: extract from an already-saved upload path."""

    if not file_path or not os.path.exists(file_path):
        raise ValueError("Uploaded file path does not exist")
    name = (original_filename or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    if name.endswith(".docx"):
        return extract_text_from_docx(file_path)
    raise ValueError("Unsupported resume file type. Upload a .pdf or .docx")
