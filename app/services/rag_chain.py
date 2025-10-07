"""
RAG (Retrieval-Augmented Generation) chain service.

This module implements the RAG pipeline that combines document retrieval
with LLM generation to answer questions based on retrieved context.
"""

from typing import List, Dict, Any, Union
from base64 import b64decode
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RAGChainService:
    """
    Service for RAG-based question answering.

    Combines retrieved documents (text, tables, images) with GPT-4o-mini
    to generate answers based on multi-modal context.
    """

    def __init__(self):
        """Initialize RAG chain with GPT-4o-mini model."""
        self.model = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
        )

    def generate_answer(
        self, question: str, retrieved_docs: List[Union[str, Document]]
    ) -> Dict[str, Any]:
        """
        Generate an answer to a question using retrieved documents.

        Args:
            question: User's question.
            retrieved_docs: List of documents (strings or Document objects) retrieved from vector store.

        Returns:
            Dictionary containing answer and metadata.
        """
        try:
            logger.info(f"Generating answer for question: {question[:50]}...")

            # Parse documents by type
            docs_by_type = self._parse_documents(retrieved_docs)

            # Build prompt with context
            prompt = self._build_prompt(question, docs_by_type)

            # Generate response
            chain = prompt | self.model | StrOutputParser()
            answer = chain.invoke({})

            logger.info("Answer generated successfully")

            return {
                "answer": answer,
                "context": {
                    "num_texts": len(docs_by_type["texts"]),
                    "num_images": len(docs_by_type["images"]),
                },
            }

        except Exception as e:
            msg = f"Failed to generate answer: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

    def generate_answer_with_sources(
        self, question: str, retrieved_docs: List[Union[str, Document]]
    ) -> Dict[str, Any]:
        """
        Generate an answer with source documents included.

        Args:
            question: User's question.
            retrieved_docs: List of documents (strings or Document objects) retrieved from vector store.

        Returns:
            Dictionary containing answer, sources, and metadata.
        """
        try:
            logger.info(f"Generating answer with sources for: {question[:50]}...")

            # Parse documents by type
            docs_by_type = self._parse_documents(retrieved_docs)

            # Build prompt with context
            prompt = self._build_prompt(question, docs_by_type)

            # Generate response
            chain = prompt | self.model | StrOutputParser()
            answer = chain.invoke({})

            # Prepare source information
            sources = {
                "texts": [self._format_text_source(doc) for doc in docs_by_type["texts"]],
                "images": docs_by_type["images"],  # Base64 strings
            }

            logger.info("Answer with sources generated successfully")

            return {
                "answer": answer,
                "sources": sources,
                "metadata": {
                    "num_text_sources": len(sources["texts"]),
                    "num_image_sources": len(sources["images"]),
                },
            }

        except Exception as e:
            msg = f"Failed to generate answer with sources: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

    def _parse_documents(self, docs: List[Union[str, Document]]) -> Dict[str, List[Any]]:
        """
        Separate documents into text and image categories.

        Args:
            docs: List of retrieved documents (strings or Document objects).

        Returns:
            Dictionary with ``'texts'`` and ``'images'`` lists.
        """
        texts = []
        images = []

        for doc in docs:
            try:
                # Try to decode as base64 image
                b64decode(doc)
                images.append(doc)
            except Exception:
                # If not base64, treat as text
                texts.append(doc)

        logger.info(f"Parsed {len(texts)} text docs and {len(images)} image docs")
        return {"texts": texts, "images": images}

    def _build_prompt(
        self, question: str, docs_by_type: Dict[str, List[Any]]
    ) -> ChatPromptTemplate:
        """
        Build a prompt with question and context.

        Args:
            question: User's question.
            docs_by_type: Parsed documents by type.

        Returns:
            ChatPromptTemplate with context and question.
        """
        # Combine text context
        context_text = ""
        if docs_by_type["texts"]:
            for text_element in docs_by_type["texts"]:
                if hasattr(text_element, "text"):
                    context_text += text_element.text + "\n\n"
                else:
                    context_text += str(text_element) + "\n\n"

        # Build prompt template
        prompt_text = f"""Answer the question based only on the following context, which can include text, tables, and images.

        Context:
        {context_text}

        Question: {question}

        Provide a clear and concise answer based on the context above."""

        prompt_content = [{"type": "text", "text": prompt_text}]

        # Add images to prompt
        if docs_by_type["images"]:
            for image in docs_by_type["images"]:
                prompt_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                    }
                )

        return ChatPromptTemplate.from_messages(
            [HumanMessage(content=prompt_content)]
        )

    def _format_text_source(self, doc: Union[str, Document]) -> Dict[str, Any]:
        """
        Format a text document as a source reference.

        Args:
            doc: Document to format (string or Document object).

        Returns:
            Dictionary with source information.
        """
        source = {"content": str(doc)}

        # Add metadata if available
        if hasattr(doc, "metadata"):
            source["metadata"] = doc.metadata

        return source
