"""Dolphin Parser Agent - "The Eyes".

Ingests raw documents (PDF, DOCX, PPTX, TXT/MD, XLSX/CSV) and converts them
into semantically rich, structured data. Handles OCR, layout
detection (tables vs. text), and chunking.

Primary Task: Convert Blob -> List[ParsedChunk]
"""
