"""Document Generation Agent for AI-assisted legal document creation.

This agent handles:
- Template-based document generation
- AI enhancement of legal documents
- Jurisdiction-specific clause insertion
- PDF/DOCX rendering
- Human-in-the-loop review workflow

It integrates with:
- Template library for document templates
- Gemini AI for document enhancement
- Document service for rendering
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.hashing import sha256_hex

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"


# Prompt for document enhancement
DOCUMENT_ENHANCEMENT_PROMPT = """Enhance this legal document for {jurisdiction}.

Template: {template_name}
Document Type: {document_type}

Draft Content:
{draft_content}

Case Variables:
{variables}

Tasks:
1. Insert jurisdiction-specific statutory citations where appropriate
2. Ensure proper legal terminology for {jurisdiction}
3. Verify all required elements are present
4. Flag any missing information that needs to be filled in
5. Suggest improvements to strengthen the document

IMPORTANT: 
- Do NOT change substantive legal positions
- Only enhance form, citations, and terminology
- Preserve all variable placeholders like {{variable_name}}

Return JSON:
{{
    "enhanced_sections": [
        {{
            "section_id": "...",
            "original": "original text",
            "enhanced": "enhanced text",
            "changes_made": ["list of changes"]
        }}
    ],
    "inserted_citations": ["citation1", "citation2"],
    "missing_elements": ["element1"],
    "suggestions": ["suggestion1"],
    "review_notes": ["note for attorney review"]
}}
"""


@dataclass
class DocumentDraft:
    """Generated document draft."""
    document_id: str
    template_id: str
    content: str
    variables: dict[str, Any]
    jurisdiction: str
    enhanced: bool
    enhancements: Optional[dict[str, Any]]
    storage_path: Optional[str]
    sha256: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "template_id": self.template_id,
            "content_preview": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "variables": self.variables,
            "jurisdiction": self.jurisdiction,
            "enhanced": self.enhanced,
            "enhancements": self.enhancements,
            "storage_path": self.storage_path,
            "sha256": self.sha256,
        }


class DocGenAgent(BaseAgent):
    """Agent for document generation with AI enhancement.
    
    Responsibilities:
    - Generate documents from templates
    - Enhance documents with AI (citations, terminology)
    - Render to PDF/DOCX formats
    - Create review tasks for counsel
    
    All generated legal documents require human review.
    """
    
    agent_type = AgentType.DOCGEN
    confidence_threshold = 0.90  # Higher threshold for legal docs
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the document generation agent.
        
        Args:
            db_session: Database session
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Generate a document from template.
        
        Args:
            context: Agent context with template and variables
            
        Returns:
            AgentResult with generated document
        """
        start_time = datetime.utcnow()
        
        try:
            if not context.template_id:
                return AgentResult.failure_result(
                    error="No template_id provided",
                    error_code="MISSING_TEMPLATE_ID",
                )
            
            if not context.variables:
                return AgentResult.failure_result(
                    error="No variables provided",
                    error_code="MISSING_VARIABLES",
                )
            
            jurisdiction = context.jurisdiction or "TX"
            
            # Generate the document
            draft = await self.generate_document(
                context.template_id,
                context.variables,
                jurisdiction,
            )
            
            # Create review task
            review_task_id = await self._create_review_task(
                draft,
                context.project_id,
                context.parcel_id,
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return AgentResult(
                success=True,
                confidence=0.85 if draft.enhanced else 0.75,
                data={
                    "document": draft.to_dict(),
                    "document_id": draft.document_id,
                    "review_task_id": review_task_id,
                },
                flags=[],
                requires_review=True,  # Always require review for legal docs
                audit_payload={
                    "explanation": f"Generated {context.template_id} document for {jurisdiction}",
                    "enhanced": draft.enhanced,
                },
                execution_time_ms=int(execution_time),
            )
            
        except Exception as e:
            self.logger.error(f"Document generation failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="DOCGEN_ERROR",
            )
    
    async def generate_document(
        self,
        template_id: str,
        variables: dict[str, Any],
        jurisdiction: str,
    ) -> DocumentDraft:
        """Generate a document from template with AI enhancement.
        
        Args:
            template_id: Template identifier
            variables: Template variables
            jurisdiction: State code
            
        Returns:
            Generated document draft
        """
        # Load template
        template_content, template_meta = await self._load_template(template_id)
        
        # Get jurisdiction-specific clauses
        clauses = await self._get_jurisdiction_clauses(jurisdiction, template_id, template_meta)
        
        # Merge clauses into variables
        merged_variables = {**variables, **clauses}
        
        # Render template with variables
        rendered_content = self._render_template(template_content, merged_variables)
        
        # AI enhancement
        enhancements = await self.enhance_with_ai(
            rendered_content,
            template_id,
            template_meta.get("type", "legal_document"),
            jurisdiction,
            merged_variables,
        )
        
        # Apply enhancements if available
        if enhancements and enhancements.get("enhanced_sections"):
            rendered_content = self._apply_enhancements(rendered_content, enhancements)
        
        # Generate document ID and hash
        document_id = str(uuid4())
        content_hash = sha256_hex(rendered_content + str(variables))
        
        # Create draft
        draft = DocumentDraft(
            document_id=document_id,
            template_id=template_id,
            content=rendered_content,
            variables=merged_variables,
            jurisdiction=jurisdiction,
            enhanced=enhancements is not None,
            enhancements=enhancements,
            storage_path=None,  # Set after persistence
            sha256=content_hash,
        )
        
        # Persist document if DB available
        if self.db:
            await self._persist_document(draft)
        
        return draft
    
    async def enhance_with_ai(
        self,
        content: str,
        template_id: str,
        document_type: str,
        jurisdiction: str,
        variables: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Enhance document with AI suggestions.
        
        Args:
            content: Document content
            template_id: Template identifier
            document_type: Type of document
            jurisdiction: State code
            variables: Template variables
            
        Returns:
            Enhancement suggestions or None
        """
        prompt = DOCUMENT_ENHANCEMENT_PROMPT.format(
            jurisdiction=jurisdiction,
            template_name=template_id,
            document_type=document_type,
            draft_content=content[:8000],  # Limit length
            variables=str(variables)[:2000],
        )
        
        response = await self.call_ai(prompt, task_type="document_enhancement")
        return response
    
    async def render_to_pdf(self, document_id: str) -> dict[str, Any]:
        """Render document to PDF format.
        
        Args:
            document_id: Document ID to render
            
        Returns:
            PDF metadata with storage path
        """
        # TODO: Implement PDF rendering with WeasyPrint
        # For now, return placeholder
        return {
            "document_id": document_id,
            "storage_path": f"rendered/{document_id}.pdf",
            "page_count": 1,
            "rendered_at": datetime.utcnow().isoformat(),
        }
    
    async def render_to_docx(self, document_id: str) -> dict[str, Any]:
        """Render document to DOCX format.
        
        Args:
            document_id: Document ID to render
            
        Returns:
            DOCX metadata with storage path
        """
        # TODO: Implement DOCX rendering with python-docx
        return {
            "document_id": document_id,
            "storage_path": f"rendered/{document_id}.docx",
            "rendered_at": datetime.utcnow().isoformat(),
        }
    
    async def generate_court_petition(
        self,
        project_id: str,
        parcel_id: str,
        petition_type: str = "condemnation",
    ) -> dict[str, Any]:
        """Generate a court petition document.
        
        Args:
            project_id: Project ID
            parcel_id: Parcel ID
            petition_type: Type of petition
            
        Returns:
            Generated petition with review task
        """
        # Map petition type to template
        template_mapping = {
            "condemnation": "condemnation_petition",
            "motion_possession": "motion_for_possession",
            "motion_deposit": "motion_to_deposit",
        }
        
        template_id = template_mapping.get(petition_type, "condemnation_petition")
        
        # Fetch case data for variables
        case_data = await self._get_case_data(project_id, parcel_id)
        
        # Generate document
        context = AgentContext(
            template_id=template_id,
            variables=case_data,
            jurisdiction=case_data.get("jurisdiction", "TX"),
            project_id=project_id,
            parcel_id=parcel_id,
        )
        
        result = await self.execute(context)
        return result.data
    
    async def _load_template(self, template_id: str) -> tuple[str, dict[str, Any]]:
        """Load template content and metadata.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Tuple of (content, metadata)
        """
        # Try library templates first
        template_path = TEMPLATES_DIR / "library" / template_id / "template.md"
        meta_path = TEMPLATES_DIR / "library" / template_id / "meta.json"
        
        if not template_path.exists():
            # Fall back to base templates
            template_path = TEMPLATES_DIR / "base" / template_id / "template.md"
            meta_path = TEMPLATES_DIR / "base" / template_id / "meta.json"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_id}")
        
        content = template_path.read_text()
        
        meta = {}
        if meta_path.exists():
            import json
            meta = json.loads(meta_path.read_text())
        
        return content, meta
    
    async def _get_jurisdiction_clauses(
        self,
        jurisdiction: str,
        template_id: str,
        template_meta: dict[str, Any],
    ) -> dict[str, str]:
        """Get jurisdiction-specific clauses for template.
        
        Args:
            jurisdiction: State code
            template_id: Template identifier
            template_meta: Template metadata
            
        Returns:
            Dict of clause variables
        """
        clauses = {}
        
        # Check for jurisdiction clauses in template metadata
        jurisdiction_clauses = template_meta.get("jurisdiction_clauses", {})
        if jurisdiction in jurisdiction_clauses:
            clauses.update(jurisdiction_clauses[jurisdiction])
        
        return clauses
    
    def _render_template(self, content: str, variables: dict[str, Any]) -> str:
        """Render template with variable substitution.
        
        Args:
            content: Template content
            variables: Variables to substitute
            
        Returns:
            Rendered content
        """
        rendered = content
        
        for key, value in variables.items():
            placeholder = "{{ " + key + " }}"
            alt_placeholder = "{{" + key + "}}"
            
            str_value = str(value) if value is not None else ""
            
            rendered = rendered.replace(placeholder, str_value)
            rendered = rendered.replace(alt_placeholder, str_value)
        
        return rendered
    
    def _apply_enhancements(
        self,
        content: str,
        enhancements: dict[str, Any],
    ) -> str:
        """Apply AI enhancements to content.
        
        Args:
            content: Original content
            enhancements: Enhancement suggestions
            
        Returns:
            Enhanced content
        """
        enhanced_content = content
        
        for section in enhancements.get("enhanced_sections", []):
            original = section.get("original", "")
            enhanced = section.get("enhanced", "")
            
            if original and enhanced and original != enhanced:
                enhanced_content = enhanced_content.replace(original, enhanced)
        
        return enhanced_content
    
    async def _create_review_task(
        self,
        draft: DocumentDraft,
        project_id: str = None,
        parcel_id: str = None,
    ) -> str:
        """Create a review task for the generated document.
        
        Also sends notifications to counsel about the pending review.
        
        Args:
            draft: Document draft
            project_id: Optional project ID
            parcel_id: Optional parcel ID
            
        Returns:
            Review task ID
        """
        task_id = str(uuid4())
        reviewer_ids = []
        
        if self.db:
            try:
                from app.db.models import Task, Persona, User
                from sqlalchemy import select
                
                task = Task(
                    id=task_id,
                    project_id=project_id or "",
                    parcel_id=parcel_id,
                    title=f"Review generated document: {draft.template_id}",
                    persona=Persona.IN_HOUSE_COUNSEL,
                    status="open",
                    metadata_json={
                        "document_id": draft.document_id,
                        "template_id": draft.template_id,
                        "jurisdiction": draft.jurisdiction,
                        "enhanced": draft.enhanced,
                    },
                )
                self.db.add(task)
                await self.db.commit()
                
                # Get counsel users to notify
                result = await self.db.execute(
                    select(User).where(User.persona == Persona.IN_HOUSE_COUNSEL)
                )
                users = result.scalars().all()
                reviewer_ids = [u.id for u in users]
                
            except Exception as e:
                self.logger.warning(f"Failed to create review task: {e}")
        
        # Send notification to reviewers
        if reviewer_ids:
            await self._notify_document_ready(
                draft.document_id,
                reviewer_ids,
                draft.template_id,
                project_id,
            )
        
        return task_id
    
    async def _notify_document_ready(
        self,
        document_id: str,
        reviewer_ids: list[str],
        document_type: str,
        project_id: str = None,
    ) -> None:
        """Send notification that document is ready for review.
        
        Args:
            document_id: Document ID
            reviewer_ids: Users to notify
            document_type: Type of document
            project_id: Related project ID
        """
        try:
            from app.tasks.notifications import send_document_ready_notification
            
            send_document_ready_notification.delay(
                document_id=document_id,
                reviewer_ids=reviewer_ids,
                document_type=document_type,
                project_id=project_id,
            )
            
            self.logger.info(
                f"Queued document review notification for {document_id} to {len(reviewer_ids)} reviewers"
            )
            
        except Exception as e:
            # Don't fail the document generation if notification fails
            self.logger.warning(f"Failed to queue document notification: {e}")
    
    async def _persist_document(self, draft: DocumentDraft) -> None:
        """Persist document to database and storage.
        
        Args:
            draft: Document draft to persist
        """
        try:
            from app.db.models import Document
            
            storage_path = f"generated/{draft.document_id}.md"
            draft.storage_path = storage_path
            
            document = Document(
                id=draft.document_id,
                doc_type=draft.template_id,
                template_id=draft.template_id,
                sha256=draft.sha256,
                storage_path=storage_path,
                privilege="non_privileged",
                metadata_json={
                    "jurisdiction": draft.jurisdiction,
                    "variables": draft.variables,
                    "enhanced": draft.enhanced,
                },
            )
            self.db.add(document)
            await self.db.commit()
            
        except Exception as e:
            self.logger.warning(f"Failed to persist document: {e}")
    
    async def _get_case_data(
        self,
        project_id: str,
        parcel_id: str,
    ) -> dict[str, Any]:
        """Fetch case data for petition generation.
        
        Args:
            project_id: Project ID
            parcel_id: Parcel ID
            
        Returns:
            Case data for template variables
        """
        # Return mock data if no DB
        if not self.db:
            return {
                "jurisdiction": "TX",
                "project_name": "Sample Project",
                "parcel_address": "123 Main Street, Anytown, TX 75001",
                "owner_names": "John Smith and Jane Smith",
                "condemning_authority": "City of Anytown",
                "public_use": "Road expansion",
                "appraisal_value": 350000.0,
            }
        
        try:
            from app.db.models import Project, Parcel, Appraisal
            from sqlalchemy import select
            
            # Fetch project
            project_result = await self.db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            
            # Fetch parcel
            parcel_result = await self.db.execute(
                select(Parcel).where(Parcel.id == parcel_id)
            )
            parcel = parcel_result.scalar_one_or_none()
            
            # Fetch appraisal
            appraisal_result = await self.db.execute(
                select(Appraisal).where(Appraisal.parcel_id == parcel_id)
            )
            appraisal = appraisal_result.scalar_one_or_none()
            
            return {
                "jurisdiction": project.jurisdiction_code if project else "TX",
                "project_name": project.name if project else "",
                "parcel_address": parcel.metadata_json.get("address", "") if parcel else "",
                "appraisal_value": float(appraisal.value) if appraisal else 0,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to fetch case data: {e}")
            return {}
