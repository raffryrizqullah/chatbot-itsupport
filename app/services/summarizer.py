"""
Summarization service using GPT-4o-mini for text and images.

This module provides summarization capabilities for text chunks, tables,
and images extracted from PDF documents.
"""

from typing import List, Any, Union
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from unstructured.documents.elements import CompositeElement, Table
from app.core.config import settings
from app.core.exceptions import SummarizerError
import logging

logger = logging.getLogger(__name__)


class SummarizerService:
    """
    Service for summarizing text, tables, and images using GPT-4o-mini.

    Uses LangChain with OpenAI's GPT-4o-mini model for both text and
    multi-modal (image) summarization.
    """

    def __init__(self):
        """Initialize summarizer with GPT-4o-mini model."""
        self.model = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
        )
        self.batch_concurrency = settings.rag_batch_concurrency

    def summarize_texts(self, texts: List[CompositeElement]) -> List[str]:
        """
        Summarize text chunks.

        Args:
            texts: List of CompositeElement text chunks to summarize.

        Returns:
            List of summary strings.
        """
        if not texts:
            return []

        logger.info(f"Summarizing {len(texts)} text chunks")

        prompt_text = """You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.

Respond only with the summary, no additional comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.

Table or text chunk: {element}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = {"element": lambda x: x} | prompt | self.model | StrOutputParser()

        try:
            summaries = chain.batch(texts, {"max_concurrency": self.batch_concurrency})
            logger.info(f"Generated {len(summaries)} text summaries")
            return summaries
        except Exception as e:
            msg = f"Failed to summarize texts: {str(e)}"
            logger.error(msg)
            raise SummarizerError(msg)

    def summarize_tables(self, tables: List[Table]) -> List[str]:
        """
        Summarize table elements using their HTML representation.

        Args:
            tables: List of Table elements to summarize.

        Returns:
            List of summary strings.
        """
        if not tables:
            return []

        logger.info(f"Summarizing {len(tables)} tables")

        # Extract HTML representation of tables
        tables_html = [table.metadata.text_as_html for table in tables]

        prompt_text = """You are an assistant tasked with summarizing tables.
Give a concise summary of the table content and structure.

Respond only with the summary, no additional comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.

Table HTML: {element}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = {"element": lambda x: x} | prompt | self.model | StrOutputParser()

        try:
            summaries = chain.batch(
                tables_html, {"max_concurrency": self.batch_concurrency}
            )
            logger.info(f"Generated {len(summaries)} table summaries")
            return summaries
        except Exception as e:
            msg = f"Failed to summarize tables: {str(e)}"
            logger.error(msg)
            raise SummarizerError(msg)

    def summarize_images(self, images: List[str]) -> List[str]:
        """
        Summarize images using GPT-4o-mini vision capabilities.

        Args:
            images: List of base64-encoded image strings.

        Returns:
            List of image description strings.
        """
        if not images:
            return []

        logger.info(f"Summarizing {len(images)} images")

        prompt_template = """Describe the image in detail. For context,
the image is part of a document that may contain diagrams, charts, graphs, or other visual elements.
Be specific about any data visualizations, such as bar plots, line graphs, or tables.
Focus on the key information and structure visible in the image."""

        messages = [
            (
                "user",
                [
                    {"type": "text", "text": prompt_template},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image}"},
                    },
                ],
            )
        ]

        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.model | StrOutputParser()

        try:
            summaries = chain.batch(images, {"max_concurrency": self.batch_concurrency})
            logger.info(f"Generated {len(summaries)} image summaries")
            return summaries
        except Exception as e:
            msg = f"Failed to summarize images: {str(e)}"
            logger.error(msg)
            raise SummarizerError(msg)
