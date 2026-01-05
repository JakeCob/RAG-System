"""Dolphin Parser Agent - "The Eyes".

Ingests raw documents (PDF, HTML, DOCX, PPTX) and converts them
into semantically rich, structured data. Handles OCR, layout
detection (tables vs. text), and chunking.

Primary Task: Convert Blob -> List[ParsedChunk]
"""
