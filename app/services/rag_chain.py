"""
RAG (Retrieval-Augmented Generation) chain service.

This module implements the RAG pipeline that combines document retrieval
with LLM generation to answer questions based on retrieved context.
"""

from typing import List, Dict, Any, Union
from base64 import b64decode
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from app.core.config import settings
from app.core.exceptions import RAGChainError
import logging

logger = logging.getLogger(__name__)


class RAGChainService:
    """
    Service for RAG-based question answering.

    Combines retrieved documents (text, tables, images) with GPT-4o-mini
    to generate answers based on multi-modal context.
    """

<<<<<<< HEAD
    def __init__(self):
=======
    def __init__(self) -> None:
>>>>>>> bb677be (feat : update logging error)
        """Initialize RAG chain with GPT-4o-mini model."""
        self.model = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
        )

    def generate_answer_with_history(
        self,
        question: str,
        retrieved_docs: List[Union[str, Document]],
        chat_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Generate an answer with chat history context.

        Args:
            question: User's question.
            retrieved_docs: List of documents retrieved from vector store.
            chat_history: List of previous messages with 'role' and 'content' keys.

        Returns:
            Dictionary containing answer and metadata.
        """
        try:
            logger.info(f"Generating answer with history for: {question[:50]}...")

            # Parse documents by type
            docs_by_type = self._parse_documents(retrieved_docs)

            # Build prompt with history
            prompt = self._build_prompt_with_history(question, docs_by_type, chat_history)

            # Generate response
            chain = prompt | self.model | StrOutputParser()
            answer = chain.invoke({})

            logger.info("Answer with history generated successfully")

            return {
                "answer": answer,
                "context": {
                    "num_texts": len(docs_by_type["texts"]),
                    "num_images": len(docs_by_type["images"]),
                    "has_chat_history": len(chat_history) > 0,
                    "history_length": len(chat_history),
                },
            }

        except Exception as e:
            msg = f"Failed to generate answer with history: {str(e)}"
            logger.error(msg)
            raise RAGChainError(msg)

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
            raise RAGChainError(msg)

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
            raise RAGChainError(msg)

    def _parse_documents(
        self, docs: List[Union[str, Document]]
    ) -> Dict[str, List[Union[str, Document]]]:
        """
        Separate documents into text and image categories.

        Args:
            docs: List of retrieved documents (strings or Document objects).

        Returns:
            Dictionary with ``'texts'`` and ``'images'`` lists.
            - ``'texts'``: List of Document objects or strings (non-image content)
            - ``'images'``: List of base64-encoded image strings
        """
        texts: List[Union[str, Document]] = []
        images: List[str] = []

        for doc in docs:
            # Extract string content from Document if needed
            content = doc.page_content if isinstance(doc, Document) else doc

            try:
                # Try to decode as base64 image
                b64decode(content)
                images.append(content)
            except Exception:
                # If not base64, treat as text document
                texts.append(doc)

        logger.info(f"Parsed {len(texts)} text docs and {len(images)} image docs")
        return {"texts": texts, "images": images}

    def _build_context_text(self, docs: List[Any]) -> str:
        """
        Build context text from list of documents.

        Args:
            docs: List of document objects.

        Returns:
            Combined text context from all documents.
        """
        context_text = ""
        for doc in docs:
            if hasattr(doc, "text"):
                context_text += doc.text + "\n\n"
            else:
                context_text += str(doc) + "\n\n"
        return context_text

    def _build_prompt_with_history(
        self,
        question: str,
        docs_by_type: Dict[str, List[Any]],
        chat_history: List[Dict[str, str]],
    ) -> ChatPromptTemplate:
        """
        Build a prompt with chat history and context.

        Args:
            question: User's question.
            docs_by_type: Parsed documents by type.
            chat_history: List of previous messages.

        Returns:
            ChatPromptTemplate with history, context, and question.
        """
        # Combine text context using helper method
        context_text = ""
        if docs_by_type["texts"]:
            context_text = self._build_context_text(docs_by_type["texts"])

        # Convert chat history to LangChain message format
        history_messages = []
        for msg in chat_history:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_messages.append(AIMessage(content=msg["content"]))

        # Build system message with instructions
        system_message = SystemMessage(
            content="""Anda adalah asisten IT support. Jawab pertanyaan berdasarkan konteks yang diberikan dan riwayat percakapan.
<<<<<<< HEAD
Jika pertanyaan merujuk ke percakapan sebelumnya (menggunakan kata seperti 'itu', 'tersebut', 'ini'), gunakan riwayat chat untuk memahami yang dimaksud pengguna.
Berikan jawaban yang jelas dan ringkas dalam bahasa Indonesia."""
        )

        # Build prompt content with context
        prompt_text = f"""Konteks dari knowledge base:
{context_text}

Pertanyaan saat ini: {question}

Berikan jawaban yang jelas dan ringkas berdasarkan konteks di atas dan riwayat percakapan. Jawab dalam bahasa Indonesia."""
=======
            Jika pertanyaan merujuk ke percakapan sebelumnya (menggunakan kata seperti 'itu', 'tersebut', 'ini'), gunakan riwayat chat untuk memahami yang dimaksud pengguna.
            Berikan jawaban yang jelas dan ringkas dalam bahasa Indonesia."""
                    )

        # Build prompt content with context
        prompt_text = f"""Konteks dari knowledge base:
        {context_text}

        Pertanyaan saat ini: {question}

        Berikan jawaban yang jelas dan ringkas berdasarkan konteks di atas dan riwayat percakapan. Jawab dalam bahasa Indonesia."""
>>>>>>> bb677be (feat : update logging error)

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

        # Construct messages: system + history + current question with context
        messages = [system_message] + history_messages + [HumanMessage(content=prompt_content)]

        return ChatPromptTemplate.from_messages(messages)

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
        # Combine text context using helper method
        context_text = ""
        if docs_by_type["texts"]:
            context_text = self._build_context_text(docs_by_type["texts"])

        # Build prompt template
        prompt_text = f"""Jawab pertanyaan hanya berdasarkan konteks berikut, yang dapat berisi teks, tabel, dan gambar.

<<<<<<< HEAD
Konteks:
{context_text}

Pertanyaan: {question}

Berikan jawaban yang jelas dan ringkas berdasarkan konteks di atas. Jawab dalam bahasa Indonesia."""
=======
        Konteks:
        {context_text}

        Pertanyaan: {question}

        Berikan jawaban yang jelas dan ringkas berdasarkan konteks di atas. Jawab dalam bahasa Indonesia."""
>>>>>>> bb677be (feat : update logging error)

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
            metadata = doc.metadata or {}
            source["metadata"] = metadata
            source_link = metadata.get("source_link")
            document_name = metadata.get("document_name")
            if source_link:
                source["source_link"] = source_link
            if document_name:
                source["document_name"] = document_name

        return source
