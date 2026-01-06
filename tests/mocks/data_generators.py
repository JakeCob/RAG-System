from io import BytesIO
from typing import Any

from pydantic import BaseModel


# =============================================================================
# Mock Objects
# =============================================================================


class MockCrawlResult(BaseModel):
    """Simulates crawl4ai.CrawlResult object."""

    markdown: str
    url: str
    metadata: dict[str, Any]
    html: str = ""
    success: bool = True


# =============================================================================
# Web Content Data
# =============================================================================

RAW_HTML_GOV_SITE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Department of Bureaucracy - Public Notice 123</title>
    <style>
        .sidebar { display: none; }
    </style>
</head>
<body bgcolor="#FFFFFF">
    <div id="header">
        <img src="logo.gif" alt="Gov Logo">
        <h1>Department of Bureaucracy</h1>
    </div>
    <div class="main-content">
        <h2>Public Notice: 2025-Q1 Updates</h2>
        <p><strong>Date:</strong> January 15, 2025</p>
        <p>
            This is an official notice regarding the
            <em>simulation</em> of government data.
        </p>

        <table border="1">
            <tr>
                <th>Category</th>
                <th>Status</th>
                <th>Notes</th>
            </tr>
            <tr>
                <td>Infrastructure</td>
                <td>Delayed</td>
                <td>Awaiting funding &quot;approval&quot;</td>
            </tr>
            <tr>
                <td>Education</td>
                <td>Ongoing</td>
                <td>See <a href="/docs/edu.pdf">Attachment A</a></td>
            </tr>
        </table>

        <br>
        <div class="footer">
            Contact: admin@gov.local | &copy; 2025
        </div>
        <!-- Broken HTML tag below for robustness testing -->
        <span class="broken>Missing quote here</span>
    </div>
</body>
</html>
"""

BROKEN_ENCODING_HTML = b"""
<!DOCTYPE html>
<html>
<head><title>Old Site</title></head>
<body>
    <p>This is some text with encoding issues: \xe9\xe0\xf6 (latin-1)</p>
    <p>Mixed with UTF-8 like: \xc3\xa9</p>
</body>
</html>
"""

CLEANED_MARKDOWN_GOV_SITE = """# Department of Bureaucracy

## Public Notice: 2025-Q1 Updates

**Date:** January 15, 2025

This is an official notice regarding the *simulation* of government data.

| Category | Status | Notes |
|---|---|---|
| Infrastructure | Delayed | Awaiting funding "approval" |
| Education | Ongoing | See [Attachment A](/docs/edu.pdf) |

Contact: admin@gov.local | © 2025
"""

# =============================================================================
# PDF Data
# =============================================================================

MALFORMED_PDF_BYTES = b"%PDF-1.4\n...garbage content... %%EOF"


def generate_mock_pdf_bytes() -> BytesIO:
    """Generates a valid-enough PDF byte stream for testing."""
    # This is a minimal valid PDF structure
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        b"endobj\n"
        b"5 0 obj\n"
        b"<< /Length 44 >>\n"
        b"stream\n"
        b"BT /F1 24 Tf 100 700 Td (Mock PDF Content) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000243 00000 n \n"
        b"0000000330 00000 n \n"
        b"trailer\n"
        b"<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"424\n"
        b"%%EOF"
    )
    return BytesIO(pdf_content)
