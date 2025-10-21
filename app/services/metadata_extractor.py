"""
Metadata extraction service using LLM.

Automatically extracts structured metadata from document text
using GPT-4o-mini for cost-effective processing.
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class MetadataExtractorService:
    """Service for extracting metadata from document text using LLM."""

    def __init__(self):
        """Initialize LLM for metadata extraction."""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key
        )

    async def extract_metadata(self, document_text: str) -> Dict[str, Any]:
        """
        Extract structured metadata from document text.

        Args:
            document_text: First ~3000 characters of document.

        Returns:
            Dictionary with extracted metadata fields.
        """
        # Truncate to first 3000 chars for cost efficiency
        truncated_text = document_text[:3000]

        system_prompt = """You are a metadata extraction assistant for IT support documents.

Extract structured metadata from the document and return ONLY valid JSON (no markdown, no explanation).

Required JSON format:
{
  "category": "vpn | network | email | hardware | software | security | other",
  "subcategory": "installation | troubleshooting | configuration | how-to | reference",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "faq_questions": [
    "Question 1 this document can answer?",
    "Question 2 this document can answer?"
  ],
  "platform": "windows | mac | linux | android | ios | all | mixed",
  "problem_type": "installation | error | configuration | guide | reference",
  "difficulty_level": "beginner | intermediate | advanced"
}

Rules:
- Extract 3-5 keywords (most important technical terms)
- Generate 2-5 FAQ questions that this document can answer
- Use exact enum values specified above
- Be specific and accurate
- Questions should be in Bahasa Indonesia if document is in Indonesian, English if in English"""

        user_message = f"""Extract metadata from this IT support document:

{truncated_text}

Return JSON only:"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])

            # Parse JSON response
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            metadata = json.loads(content.strip())

            logger.info(f"Extracted metadata: category={metadata.get('category')}, keywords={len(metadata.get('keywords', []))}, FAQs={len(metadata.get('faq_questions', []))}")
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
            logger.error(f"LLM response was: {content}")
            return {}
        except Exception as e:
            logger.error(f"Failed to extract metadata: {str(e)}")
            return {}

    def extract_metadata_sync(self, document_text: str) -> Dict[str, Any]:
        """
        Synchronous version of extract_metadata for non-async contexts.

        Args:
            document_text: First ~3000 characters of document.

        Returns:
            Dictionary with extracted metadata fields.
        """
        # Truncate to first 3000 chars for cost efficiency
        truncated_text = document_text[:3000]

        system_prompt = """You are a metadata extraction assistant for IT support documents.

Extract structured metadata from the document and return ONLY valid JSON (no markdown, no explanation).

Required JSON format:
{
  "category": "vpn | network | email | hardware | software | security | other",
  "subcategory": "installation | troubleshooting | configuration | how-to | reference",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "faq_questions": [
    "Question 1 this document can answer?",
    "Question 2 this document can answer?"
  ],
  "platform": "windows | mac | linux | android | ios | all | mixed",
  "problem_type": "installation | error | configuration | guide | reference",
  "difficulty_level": "beginner | intermediate | advanced"
}

Rules:
- Extract 3-5 keywords (most important technical terms)
- Generate 2-5 FAQ questions that this document can answer
- Use exact enum values specified above
- Be specific and accurate
- Questions should be in Bahasa Indonesia if document is in Indonesian, English if in English"""

        user_message = f"""Extract metadata from this IT support document:

{truncated_text}

Return JSON only:"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])

            # Parse JSON response
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            metadata = json.loads(content.strip())

            logger.info(f"Extracted metadata: category={metadata.get('category')}, keywords={len(metadata.get('keywords', []))}, FAQs={len(metadata.get('faq_questions', []))}")
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
            logger.error(f"LLM response was: {content}")
            return {}
        except Exception as e:
            logger.error(f"Failed to extract metadata: {str(e)}")
            return {}
