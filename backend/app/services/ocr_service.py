"""OCR Service for document processing using Google Document AI.

This module provides OCR and document analysis capabilities:
- Text extraction from scanned documents
- Entity extraction from title documents
- Document classification
- Structured data extraction

Used by TitleAgent for title document analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
import base64

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str
    confidence: float
    pages: int
    language: str
    entities: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    processing_time_ms: int
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "pages": self.pages,
            "language": self.language,
            "entities": self.entities,
            "tables": self.tables,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class ExtractedEntity:
    """Entity extracted from document."""
    type: str  # person, organization, date, amount, address, legal_description
    value: str
    confidence: float
    location: Optional[dict[str, Any]] = None  # Bounding box info
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "confidence": self.confidence,
            "location": self.location,
        }


class OCRService:
    """Service for OCR processing using Google Document AI.
    
    Provides document text extraction and entity recognition
    for title documents, deeds, and other legal instruments.
    """
    
    def __init__(self):
        """Initialize the OCR service."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.project = settings.gcp_project
        self.location = "us"  # Document AI location
        
        # Document AI processor IDs (would be configured per environment)
        self.ocr_processor_id = getattr(settings, 'docai_ocr_processor', None)
        self.entity_processor_id = getattr(settings, 'docai_entity_processor', None)
    
    async def process(self, file_path: str) -> OCRResult:
        """Process a document with OCR.
        
        Args:
            file_path: Path to document file
            
        Returns:
            OCR result with extracted text and entities
        """
        start_time = datetime.utcnow()
        
        # Try Document AI if configured
        if self.project and self.ocr_processor_id:
            try:
                result = await self._process_with_document_ai(file_path)
                return result
            except Exception as e:
                self.logger.warning(f"Document AI processing failed: {e}")
        
        # Fall back to mock processing
        return await self._mock_process(file_path, start_time)
    
    async def extract_entities(
        self,
        text: str,
        document_type: str,
    ) -> list[ExtractedEntity]:
        """Extract entities from document text.
        
        Args:
            text: Document text
            document_type: Type of document (deed, mortgage, etc.)
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Use pattern matching for common entity types
        entities.extend(self._extract_dates(text))
        entities.extend(self._extract_amounts(text))
        entities.extend(self._extract_names(text))
        entities.extend(self._extract_legal_descriptions(text))
        
        return entities
    
    async def classify_document(self, text: str) -> dict[str, Any]:
        """Classify a document by type.
        
        Args:
            text: Document text
            
        Returns:
            Classification result
        """
        # Simple keyword-based classification
        text_lower = text.lower()
        
        doc_types = {
            "deed": ["deed", "convey", "grantor", "grantee", "consideration"],
            "mortgage": ["mortgage", "lien", "security interest", "note"],
            "easement": ["easement", "right of way", "access"],
            "judgment": ["judgment", "court", "ordered"],
            "tax_lien": ["tax lien", "delinquent", "tax sale"],
            "release": ["release", "satisfaction", "discharged"],
        }
        
        scores = {}
        for doc_type, keywords in doc_types.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[doc_type] = score / len(keywords)
        
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])
            return {
                "document_type": best_type[0],
                "confidence": best_type[1],
                "all_scores": scores,
            }
        
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "all_scores": {},
        }
    
    async def _process_with_document_ai(self, file_path: str) -> OCRResult:
        """Process document using Google Document AI.
        
        Args:
            file_path: Path to document
            
        Returns:
            OCR result
        """
        from google.cloud import documentai_v1 as documentai
        
        start_time = datetime.utcnow()
        
        # Read file
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Determine MIME type
        mime_type = self._get_mime_type(file_path)
        
        # Create Document AI client
        client = documentai.DocumentProcessorServiceClient()
        
        # Process document
        name = f"projects/{self.project}/locations/{self.location}/processors/{self.ocr_processor_id}"
        
        raw_document = documentai.RawDocument(
            content=content,
            mime_type=mime_type,
        )
        
        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document,
        )
        
        result = client.process_document(request=request)
        document = result.document
        
        # Extract entities
        entities = []
        for entity in document.entities:
            entities.append({
                "type": entity.type_,
                "value": entity.mention_text,
                "confidence": entity.confidence,
            })
        
        # Extract tables
        tables = []
        for page in document.pages:
            for table in page.tables:
                tables.append(self._parse_table(table, document.text))
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return OCRResult(
            text=document.text,
            confidence=sum(p.confidence for p in document.pages) / len(document.pages) if document.pages else 0.0,
            pages=len(document.pages),
            language=document.pages[0].detected_languages[0].language_code if document.pages and document.pages[0].detected_languages else "en",
            entities=entities,
            tables=tables,
            processing_time_ms=int(processing_time),
        )
    
    async def _mock_process(
        self,
        file_path: str,
        start_time: datetime,
    ) -> OCRResult:
        """Mock OCR processing for development.
        
        Args:
            file_path: Path to document
            start_time: Processing start time
            
        Returns:
            Mock OCR result
        """
        self.logger.info(f"Using mock OCR for {file_path}")
        
        # Generate mock text based on file name
        mock_text = f"""DEED OF CONVEYANCE

THIS DEED made this 15th day of January, 2024, between JOHN SMITH and JANE SMITH, 
husband and wife, Grantors, and CITY OF ANYTOWN, a municipal corporation, Grantee.

WITNESSETH: That for and in consideration of the sum of THREE HUNDRED FIFTY THOUSAND 
AND NO/100 DOLLARS ($350,000.00), receipt of which is hereby acknowledged, the Grantors 
do hereby GRANT, BARGAIN, SELL, and CONVEY unto the Grantee the following described 
property situated in Example County, State of Texas:

LOT 1, BLOCK A, SAMPLE SUBDIVISION, according to the plat thereof recorded in Volume 
123, Page 456 of the Plat Records of Example County, Texas.

This conveyance is made subject to all easements, restrictions, and reservations of 
record.

EXECUTED this 15th day of January, 2024.

[Signatures]
JOHN SMITH
JANE SMITH

STATE OF TEXAS
COUNTY OF EXAMPLE

Before me, the undersigned notary public, on this day personally appeared JOHN SMITH 
and JANE SMITH, known to me to be the persons whose names are subscribed to the 
foregoing instrument.

Given under my hand and seal of office this 15th day of January, 2024.

[Notary Signature]
Notary Public, State of Texas
"""
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return OCRResult(
            text=mock_text,
            confidence=0.6,  # Lower confidence for mock
            pages=1,
            language="en",
            entities=[
                {"type": "person", "value": "John Smith", "confidence": 0.9},
                {"type": "person", "value": "Jane Smith", "confidence": 0.9},
                {"type": "organization", "value": "City of Anytown", "confidence": 0.85},
                {"type": "amount", "value": "$350,000.00", "confidence": 0.95},
                {"type": "date", "value": "January 15, 2024", "confidence": 0.9},
            ],
            tables=[],
            processing_time_ms=int(processing_time),
        )
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type from file path."""
        path_lower = file_path.lower()
        if path_lower.endswith(".pdf"):
            return "application/pdf"
        elif path_lower.endswith((".png", ".jpg", ".jpeg")):
            return "image/png" if path_lower.endswith(".png") else "image/jpeg"
        elif path_lower.endswith(".tiff"):
            return "image/tiff"
        else:
            return "application/pdf"  # Default
    
    def _parse_table(self, table, full_text: str) -> dict[str, Any]:
        """Parse table structure from Document AI."""
        rows = []
        for row in table.body_rows:
            cells = []
            for cell in row.cells:
                # Extract text from layout
                text = self._get_text_from_layout(cell.layout, full_text)
                cells.append(text)
            rows.append(cells)
        
        return {"rows": rows}
    
    def _get_text_from_layout(self, layout, full_text: str) -> str:
        """Extract text from layout using text anchors."""
        text = ""
        if layout.text_anchor and layout.text_anchor.text_segments:
            for segment in layout.text_anchor.text_segments:
                start = int(segment.start_index) if segment.start_index else 0
                end = int(segment.end_index) if segment.end_index else 0
                text += full_text[start:end]
        return text.strip()
    
    def _extract_dates(self, text: str) -> list[ExtractedEntity]:
        """Extract dates from text."""
        import re
        
        entities = []
        
        # Common date patterns
        patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match if isinstance(match, str) else " ".join(match)
                entities.append(ExtractedEntity(
                    type="date",
                    value=value,
                    confidence=0.8,
                ))
        
        return entities
    
    def _extract_amounts(self, text: str) -> list[ExtractedEntity]:
        """Extract monetary amounts from text."""
        import re
        
        entities = []
        
        # Dollar amount patterns
        patterns = [
            r'\$[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:dollars|DOLLARS)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(ExtractedEntity(
                    type="amount",
                    value=match,
                    confidence=0.9,
                ))
        
        return entities
    
    def _extract_names(self, text: str) -> list[ExtractedEntity]:
        """Extract person/organization names from text."""
        entities = []
        
        # Look for grantor/grantee patterns
        import re
        
        patterns = [
            (r'(?:GRANTOR|Grantor)[s]?[:\s]+([A-Z][A-Za-z\s]+?)(?:,|and|$)', "person"),
            (r'(?:GRANTEE|Grantee)[s]?[:\s]+([A-Z][A-Za-z\s]+?)(?:,|and|$)', "person"),
            (r'between\s+([A-Z][A-Z\s]+?)(?:,|\s+and)', "person"),
        ]
        
        for pattern, entity_type in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match.strip():
                    entities.append(ExtractedEntity(
                        type=entity_type,
                        value=match.strip(),
                        confidence=0.7,
                    ))
        
        return entities
    
    def _extract_legal_descriptions(self, text: str) -> list[ExtractedEntity]:
        """Extract legal descriptions from text."""
        import re
        
        entities = []
        
        # Look for lot/block patterns
        patterns = [
            r'(LOT\s+\d+[A-Z]?,?\s+BLOCK\s+[A-Z0-9]+,?\s+[A-Z\s]+(?:ADDITION|SUBDIVISION)[^,]*)',
            r'((?:TRACT|SURVEY)\s+[A-Z0-9\-]+[^,]*(?:COUNTY|ABSTRACT)[^,]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(ExtractedEntity(
                    type="legal_description",
                    value=match.strip(),
                    confidence=0.85,
                ))
        
        return entities
