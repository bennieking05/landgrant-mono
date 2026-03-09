"""Title Agent for title search and OCR analysis.

This agent handles:
- OCR processing of title documents
- Entity extraction from title records
- Chain of title analysis
- Public data integration (GIS, tax, zoning)
- Title issue identification

It integrates with:
- OCR service for document processing
- Property data service for public records
- Gemini AI for issue analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ocr_service import OCRService, OCRResult

logger = logging.getLogger(__name__)


# Prompt for title analysis
TITLE_ANALYSIS_PROMPT = """Analyze this title document for an eminent domain case.

OCR Text:
{ocr_text}

Document Type: {doc_type}
Parcel APN: {apn}

Extract:
1. Grantor(s) and Grantee(s) with full names
2. Legal description of the property
3. Recording information (book, page, instrument number)
4. Any liens, encumbrances, or restrictions
5. Any clouds on title or issues

Flag Issues:
- Unclear or disputed ownership
- Undischarged liens or mortgages
- Easement conflicts
- Legal description discrepancies
- Missing signatures or acknowledgments

Return JSON:
{{
    "document_type": "deed|mortgage|easement|lien|release|other",
    "parties": {{
        "grantors": ["name1", "name2"],
        "grantees": ["name1"]
    }},
    "legal_description": "full legal description",
    "recording_info": {{
        "book": "123",
        "page": "456",
        "instrument_number": "2024-001234",
        "recording_date": "2024-01-15"
    }},
    "liens": [
        {{"type": "mortgage", "amount": 250000, "holder": "Bank Name", "status": "active"}}
    ],
    "encumbrances": ["utility easement", "deed restrictions"],
    "issues": [
        {{"severity": "low|medium|high", "description": "issue description", "recommendation": "suggested action"}}
    ],
    "confidence": 0.0-1.0
}}
"""

CHAIN_OF_TITLE_PROMPT = """Analyze this chain of title for completeness.

Chain (chronological):
{chain_json}

Current Owner per Records: {current_owner}
Parcel: {parcel_info}

Verify:
1. Is the chain unbroken from current owner back 40+ years?
2. Are all conveyances properly recorded?
3. Any gaps in the chain?
4. Outstanding interests (life estates, remainders)?
5. Any adverse possession risks?

Return JSON:
{{
    "chain_complete": true/false,
    "years_covered": <number>,
    "gaps": [
        {{"from_date": "...", "to_date": "...", "description": "gap description"}}
    ],
    "outstanding_interests": ["description1", "description2"],
    "title_quality": "good|marketable|insurable|defective",
    "curative_actions": ["action1", "action2"],
    "confidence": 0.0-1.0
}}
"""


@dataclass
class TitleDocument:
    """Analyzed title document."""
    document_id: str
    document_type: str
    parties: dict[str, list[str]]
    legal_description: str
    recording_info: dict[str, str]
    liens: list[dict[str, Any]]
    encumbrances: list[str]
    issues: list[dict[str, Any]]
    ocr_confidence: float
    analysis_confidence: float


@dataclass
class ChainOfTitle:
    """Chain of title analysis result."""
    instruments: list[TitleDocument]
    chain_complete: bool
    years_covered: int
    gaps: list[dict[str, Any]]
    outstanding_interests: list[str]
    title_quality: str
    curative_actions: list[str]
    current_owner: str


class TitleAgent(BaseAgent):
    """Agent for title search and analysis.
    
    Responsibilities:
    - Process title documents with OCR
    - Extract parties, legal descriptions, liens
    - Build and analyze chain of title
    - Fetch supplementary public data
    - Identify title issues
    
    Escalation triggers:
    - Title defects detected
    - Chain of title gaps
    - Unresolved liens
    - Ownership disputes
    """
    
    agent_type = AgentType.TITLE
    confidence_threshold = 0.85
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the title agent.
        
        Args:
            db_session: Database session
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
        self.ocr_service = OCRService()
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute title analysis based on context.
        
        Args:
            context: Agent context with action details
            
        Returns:
            AgentResult with analysis
        """
        start_time = datetime.utcnow()
        
        try:
            action = context.action or "analyze_document"
            
            if action == "analyze_document":
                if not context.document_id:
                    return AgentResult.failure_result(
                        error="document_id required",
                        error_code="MISSING_DOCUMENT_ID",
                    )
                result = await self.analyze_title_document(context.document_id)
                return self._build_document_result(result, start_time)
            
            elif action == "build_chain":
                if not context.parcel_id:
                    return AgentResult.failure_result(
                        error="parcel_id required",
                        error_code="MISSING_PARCEL_ID",
                    )
                result = await self.build_chain_of_title(context.parcel_id)
                return self._build_chain_result(result, start_time)
            
            else:
                return AgentResult.failure_result(
                    error=f"Unknown action: {action}",
                    error_code="UNKNOWN_ACTION",
                )
            
        except Exception as e:
            self.logger.error(f"Title agent failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="TITLE_ERROR",
            )
    
    async def ocr_document(self, document_id: str) -> OCRResult:
        """Process a document with OCR.
        
        Args:
            document_id: Document to process
            
        Returns:
            OCR result
        """
        # Get document path
        document = await self._get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        storage_path = document.get("storage_path")
        
        # Process with OCR
        return await self.ocr_service.process(storage_path)
    
    async def analyze_title_document(self, document_id: str) -> TitleDocument:
        """Analyze a title document for entities and issues.
        
        Args:
            document_id: Document to analyze
            
        Returns:
            Analyzed title document
        """
        # Get document
        document = await self._get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get OCR result (may already be cached)
        ocr_result = await self.ocr_document(document_id)
        
        # Extract entities
        entities = await self.ocr_service.extract_entities(
            ocr_result.text,
            document.get("doc_type", "deed"),
        )
        
        # Use AI for deeper analysis
        analysis = await self._analyze_with_ai(
            ocr_result.text,
            document.get("doc_type", "deed"),
            document.get("apn", ""),
        )
        
        # Build result
        title_doc = TitleDocument(
            document_id=document_id,
            document_type=analysis.get("document_type", "unknown"),
            parties=analysis.get("parties", {"grantors": [], "grantees": []}),
            legal_description=analysis.get("legal_description", ""),
            recording_info=analysis.get("recording_info", {}),
            liens=analysis.get("liens", []),
            encumbrances=analysis.get("encumbrances", []),
            issues=analysis.get("issues", []),
            ocr_confidence=ocr_result.confidence,
            analysis_confidence=analysis.get("confidence", 0.7),
        )
        
        # Update title instrument record
        await self._update_title_instrument(document_id, title_doc)
        
        return title_doc
    
    async def build_chain_of_title(self, parcel_id: str) -> ChainOfTitle:
        """Build and analyze chain of title for a parcel.
        
        Args:
            parcel_id: Parcel to analyze
            
        Returns:
            Chain of title analysis
        """
        # Get all title instruments for parcel
        instruments = await self._get_title_instruments(parcel_id)
        
        # Analyze each instrument
        analyzed_instruments = []
        for instrument in instruments:
            doc_id = instrument.get("document_id")
            if doc_id:
                analyzed = await self.analyze_title_document(doc_id)
                analyzed_instruments.append(analyzed)
        
        # Sort by recording date
        analyzed_instruments.sort(
            key=lambda x: x.recording_info.get("recording_date", ""),
            reverse=True,
        )
        
        # Determine current owner
        current_owner = ""
        if analyzed_instruments:
            latest = analyzed_instruments[0]
            grantees = latest.parties.get("grantees", [])
            current_owner = ", ".join(grantees) if grantees else ""
        
        # Analyze chain with AI
        chain_analysis = await self._analyze_chain_with_ai(
            analyzed_instruments,
            current_owner,
            parcel_id,
        )
        
        # Fetch supplementary public data
        public_data = await self.fetch_all_public_data(parcel_id, "")
        
        return ChainOfTitle(
            instruments=analyzed_instruments,
            chain_complete=chain_analysis.get("chain_complete", False),
            years_covered=chain_analysis.get("years_covered", 0),
            gaps=chain_analysis.get("gaps", []),
            outstanding_interests=chain_analysis.get("outstanding_interests", []),
            title_quality=chain_analysis.get("title_quality", "unknown"),
            curative_actions=chain_analysis.get("curative_actions", []),
            current_owner=current_owner,
        )
    
    async def fetch_all_public_data(
        self,
        parcel_id: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch all public records for a parcel.
        
        Args:
            parcel_id: Parcel ID
            county_fips: County FIPS code
            
        Returns:
            Combined public data
        """
        from app.services.property_data_service import PropertyDataService
        
        property_service = PropertyDataService(self.db)
        
        # Fetch in parallel (would use actual APIs)
        tax_records = await self._fetch_tax_records(parcel_id, county_fips)
        gis_data = await self._fetch_gis_data(parcel_id, county_fips)
        zoning_info = await self._fetch_zoning_info(parcel_id, county_fips)
        environmental_data = await self._fetch_environmental_data(parcel_id, county_fips)
        
        return {
            "tax_records": tax_records,
            "gis_data": gis_data,
            "zoning": zoning_info,
            "environmental": environmental_data,
        }
    
    async def identify_issues_with_ai(
        self,
        parcel_id: str,
        chain_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Use AI to identify potential title issues.
        
        Args:
            parcel_id: Parcel ID
            chain_data: Chain of title data
            
        Returns:
            Identified issues
        """
        prompt = f"""Analyze this chain of title for potential issues.

Parcel: {parcel_id}
Chain Data: {str(chain_data)[:5000]}

Identify:
1. Any ownership disputes or unclear title
2. Outstanding liens that could affect the taking
3. Easements that conflict with the intended use
4. Any other title defects

Return JSON:
{{
    "issues": [
        {{"severity": "low|medium|high", "description": "...", "recommendation": "..."}}
    ],
    "overall_risk": "low|medium|high",
    "clear_to_proceed": true/false,
    "curative_actions": ["action1", "action2"]
}}
"""
        
        response = await self.call_ai(prompt, task_type="title_issues")
        return response or {"issues": [], "overall_risk": "unknown", "clear_to_proceed": False}
    
    async def _analyze_with_ai(
        self,
        ocr_text: str,
        doc_type: str,
        apn: str,
    ) -> dict[str, Any]:
        """Analyze document with AI.
        
        Args:
            ocr_text: OCR extracted text
            doc_type: Document type
            apn: Parcel APN
            
        Returns:
            Analysis result
        """
        prompt = TITLE_ANALYSIS_PROMPT.format(
            ocr_text=ocr_text[:8000],
            doc_type=doc_type,
            apn=apn,
        )
        
        response = await self.call_ai(prompt, task_type="title_analysis")
        
        if response:
            return response
        
        # Default response if AI unavailable
        return {
            "document_type": doc_type,
            "parties": {"grantors": [], "grantees": []},
            "legal_description": "",
            "recording_info": {},
            "liens": [],
            "encumbrances": [],
            "issues": [],
            "confidence": 0.5,
        }
    
    async def _analyze_chain_with_ai(
        self,
        instruments: list[TitleDocument],
        current_owner: str,
        parcel_id: str,
    ) -> dict[str, Any]:
        """Analyze chain of title with AI.
        
        Args:
            instruments: Analyzed instruments
            current_owner: Current owner name
            parcel_id: Parcel ID
            
        Returns:
            Chain analysis
        """
        # Build chain JSON
        chain_json = []
        for inst in instruments:
            chain_json.append({
                "document_type": inst.document_type,
                "parties": inst.parties,
                "recording_date": inst.recording_info.get("recording_date"),
                "liens": len(inst.liens),
            })
        
        prompt = CHAIN_OF_TITLE_PROMPT.format(
            chain_json=str(chain_json),
            current_owner=current_owner,
            parcel_info=parcel_id,
        )
        
        response = await self.call_ai(prompt, task_type="chain_analysis")
        
        if response:
            return response
        
        # Default response
        return {
            "chain_complete": len(instruments) > 0,
            "years_covered": 0,
            "gaps": [],
            "outstanding_interests": [],
            "title_quality": "unknown",
            "curative_actions": [],
            "confidence": 0.5,
        }
    
    async def _get_document(self, document_id: str) -> Optional[dict[str, Any]]:
        """Get document by ID."""
        if not self.db:
            return {
                "id": document_id,
                "doc_type": "deed",
                "storage_path": f"documents/{document_id}.pdf",
            }
        
        try:
            from app.db.models import Document
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            
            if doc:
                return {
                    "id": doc.id,
                    "doc_type": doc.doc_type,
                    "storage_path": doc.storage_path,
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch document: {e}")
            return None
    
    async def _get_title_instruments(self, parcel_id: str) -> list[dict[str, Any]]:
        """Get all title instruments for a parcel."""
        if not self.db:
            return [
                {"id": "ti-1", "document_id": "doc-1", "parcel_id": parcel_id},
            ]
        
        try:
            from app.db.models import TitleInstrument
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(TitleInstrument).where(TitleInstrument.parcel_id == parcel_id)
            )
            instruments = result.scalars().all()
            
            return [
                {
                    "id": ti.id,
                    "document_id": ti.document_id,
                    "parcel_id": ti.parcel_id,
                    "ocr_payload": ti.ocr_payload,
                }
                for ti in instruments
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to fetch title instruments: {e}")
            return []
    
    async def _update_title_instrument(
        self,
        document_id: str,
        analysis: TitleDocument,
    ) -> None:
        """Update title instrument with analysis results."""
        if not self.db:
            return
        
        try:
            from app.db.models import TitleInstrument
            from sqlalchemy import select, update
            
            await self.db.execute(
                update(TitleInstrument)
                .where(TitleInstrument.document_id == document_id)
                .values(
                    ocr_payload={
                        "parties": analysis.parties,
                        "legal_description": analysis.legal_description,
                        "recording_info": analysis.recording_info,
                        "liens": analysis.liens,
                        "encumbrances": analysis.encumbrances,
                        "issues": analysis.issues,
                    },
                    metadata_json={
                        "ocr_confidence": analysis.ocr_confidence,
                        "analysis_confidence": analysis.analysis_confidence,
                        "analyzed_at": datetime.utcnow().isoformat(),
                    },
                )
            )
            await self.db.commit()
            
        except Exception as e:
            self.logger.warning(f"Failed to update title instrument: {e}")
    
    async def _fetch_tax_records(
        self,
        parcel_id: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch tax records for parcel."""
        # TODO: Integrate with county tax APIs
        return {
            "parcel_id": parcel_id,
            "tax_year": 2023,
            "assessed_value": 350000,
            "tax_status": "current",
        }
    
    async def _fetch_gis_data(
        self,
        parcel_id: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch GIS data for parcel."""
        # TODO: Integrate with county GIS APIs
        return {
            "parcel_id": parcel_id,
            "acreage": 0.25,
            "coordinates": {"lat": 32.7767, "lng": -96.7970},
        }
    
    async def _fetch_zoning_info(
        self,
        parcel_id: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch zoning information."""
        # TODO: Integrate with zoning APIs
        return {
            "parcel_id": parcel_id,
            "zoning_code": "R-1",
            "description": "Single Family Residential",
            "restrictions": [],
        }
    
    async def _fetch_environmental_data(
        self,
        parcel_id: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch environmental data."""
        # TODO: Integrate with environmental databases
        return {
            "parcel_id": parcel_id,
            "flood_zone": "X",
            "wetlands": False,
            "contamination_sites_nearby": 0,
        }
    
    def _build_document_result(
        self,
        doc: TitleDocument,
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from document analysis."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        flags = []
        if doc.issues:
            for issue in doc.issues:
                if issue.get("severity") == "high":
                    flags.append("title_defect")
                    break
        
        if doc.liens:
            active_liens = [l for l in doc.liens if l.get("status") == "active"]
            if active_liens:
                flags.append("active_liens")
        
        return AgentResult(
            success=True,
            confidence=min(doc.ocr_confidence, doc.analysis_confidence),
            data={
                "document_id": doc.document_id,
                "document_type": doc.document_type,
                "parties": doc.parties,
                "legal_description": doc.legal_description,
                "recording_info": doc.recording_info,
                "liens": doc.liens,
                "encumbrances": doc.encumbrances,
                "issues": doc.issues,
            },
            flags=flags,
            requires_review=bool(flags),
            audit_payload={
                "explanation": f"Analyzed {doc.document_type} document with {len(doc.issues)} issues identified",
            },
            execution_time_ms=int(execution_time),
        )
    
    def _build_chain_result(
        self,
        chain: ChainOfTitle,
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from chain analysis."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        flags = []
        if not chain.chain_complete:
            flags.append("chain_incomplete")
        if chain.gaps:
            flags.append("chain_gaps")
        if chain.title_quality == "defective":
            flags.append("title_defect")
        
        return AgentResult(
            success=chain.chain_complete,
            confidence=0.9 if chain.chain_complete else 0.6,
            data={
                "chain_complete": chain.chain_complete,
                "years_covered": chain.years_covered,
                "gaps": chain.gaps,
                "outstanding_interests": chain.outstanding_interests,
                "title_quality": chain.title_quality,
                "curative_actions": chain.curative_actions,
                "current_owner": chain.current_owner,
                "instrument_count": len(chain.instruments),
            },
            flags=flags,
            requires_review=not chain.chain_complete or chain.title_quality != "good",
            audit_payload={
                "explanation": f"Chain of title: {chain.years_covered} years, {len(chain.gaps)} gaps, quality={chain.title_quality}",
            },
            execution_time_ms=int(execution_time),
        )
