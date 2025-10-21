"""
LangGraph-based Conversational RAG service.

This module implements a stateful conversational RAG system using LangGraph,
providing automatic query rewriting, tool-calling for retrieval, and memory
management across conversation turns.
"""

from typing import List, Dict, Any, Optional, Literal, Callable, Tuple
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.core.exceptions import RAGChainError
from app.services.vectorstore import VectorStoreService
from app.services.hybrid_search import HybridSearchService
from app.services.prompts import (
    get_query_routing_prompt,
    get_answer_generation_prompt,
    get_greeting_response,
    get_no_documents_response,
)
import logging

logger = logging.getLogger(__name__)


class LangGraphRAGService:
    """
    LangGraph-based Conversational RAG service.

    Implements a stateful RAG system with:
    - Automatic query rewriting based on chat history
    - Tool-calling for intelligent retrieval decisions
    - Short-circuiting for greetings/small talk
    - Strict knowledge base boundaries
    """

    def __init__(
        self,
        vectorstore: Optional[VectorStoreService] = None,
        *,
        enable_memory: bool = True,
        enable_hybrid_search: bool = True,
    ) -> None:
        """
        Initialize LangGraph RAG service.

        Args:
            vectorstore: VectorStoreService instance for document retrieval.
            enable_memory: Whether to enable conversation memory (default: True).
            enable_hybrid_search: Whether to enable hybrid search (vector + BM25) (default: True).
        """
        self.vectorstore = vectorstore or VectorStoreService()
        self.hybrid_search = HybridSearchService() if enable_hybrid_search else None
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
        )

        # Store current metadata filter (will be set per query)
        self._current_metadata_filter: Optional[Dict[str, Any]] = None

        # Store retrieved documents metadata for response
        self._retrieved_metadata: Dict[str, Any] = {}

        # Build the graph
        self.graph = self._build_graph(enable_memory=enable_memory)
        logger.info(
            f"LangGraph RAG service initialized successfully "
            f"(hybrid_search={'enabled' if enable_hybrid_search else 'disabled'})"
        )

    def _is_pure_greeting(self, query: str) -> bool:
        """
        Check if query is a pure greeting without IT content.

        Uses hybrid approach:
        1. Regex for obvious standalone greetings
        2. IT keyword detection to filter out technical questions
        3. Pattern matching for conversational greetings

        Args:
            query: User's query string.

        Returns:
            True if query is a pure greeting, False otherwise.
        """
        import re

        query_lower = query.lower().strip()

        # Step 1: Check obvious standalone greetings (safe regex patterns)
        obvious_greetings = [
            r'^(hai|halo|hello|hi|hey|hallo|haloo)[\s,!.?]*$',  # "Halo!" only
            r'^(terima\s+kasih|thanks?|thx|thank\s+you)[\s,!.?]*$',  # "Thanks" only
            r'^(oke|ok|okay|baik|siap|yes|ya)[\s,!.?]*$',  # "Oke" only
            r'^(selamat\s+(pagi|siang|sore|malam|datang))[\s,!.?]*$',  # "Selamat pagi" only
            r'^(maaf|sorry|excuse\s+me|permisi|pardon)[\s,!.?]*$',  # Apologies
        ]

        if any(re.search(pattern, query_lower) for pattern in obvious_greetings):
            return True

        # Step 2: Conversational greetings with context (check BEFORE IT keywords)
        greeting_with_context = [
            r'^(hai|halo|hello|hi|hey|haloo|hallo)\s*,?\s*(apa\s+kabar|bagaimana\s+kabar|how\s+are\s+you|what\'s\s+up)',
            r'^(apa\s+kabar|how\s+are\s+you|bagaimana\s+kabar)',
            r'^(nice\s+to\s+meet\s+you|senang\s+bertemu)',
        ]

        if any(re.search(pattern, query_lower) for pattern in greeting_with_context):
            return True

        # Step 3: Check for IT keywords (if found → NOT a pure greeting)
        it_keywords = [
            'install', 'setup', 'konfigurasi', 'configure', 'config', 'setting',
            'error', 'troubleshoot', 'masalah', 'problem', 'issue', 'bug',
            'vpn', 'firewall', 'wifi', 'network', 'jaringan', 'internet',
            'software', 'hardware', 'aplikasi', 'program', 'sistem', 'system',
            'cara', 'kenapa', 'mengapa', 'apa itu', 'what is',
            'eap', 'tls', 'ssl', 'certificate', 'sertifikat',
            'password', 'login', 'akses', 'access', 'user', 'admin',
            'download', 'upload', 'file', 'folder', 'direktori',
            'server', 'client', 'database', 'backup', 'restore',
            'update', 'upgrade', 'patch', 'security', 'keamanan',
        ]

        # If query contains IT keywords → NOT a pure greeting
        if any(keyword in query_lower for keyword in it_keywords):
            return False

        # Default: Not a pure greeting
        return False

    def _detect_user_role(self) -> str:
        """
        Detect current user role from metadata filter.

        Uses metadata_filter pattern to infer user role:
        - None → Admin (no restrictions)
        - {"sensitivity": "public"} → Student or Anonymous
        - {"sensitivity": {"$in": [...]}} → Lecturer

        Returns:
            User role: "admin", "student", "lecturer", or "anonymous".
        """
        if self._current_metadata_filter is None:
            return "admin"  # No filter = admin access

        sensitivity_filter = self._current_metadata_filter.get("sensitivity")

        if sensitivity_filter is None:
            return "anonymous"  # No sensitivity field
        elif sensitivity_filter == "public":
            return "student"  # Student or anonymous (both use "public")
        elif isinstance(sensitivity_filter, dict) and "$in" in sensitivity_filter:
            return "lecturer"  # Lecturer filter: {"$in": ["public", "internal"]}

        return "anonymous"  # Default fallback

    def _check_authorization_restrictions(
        self, query: str, retrieved_docs: List[Any]
    ) -> Optional[Tuple[str, List]]:
        """
        Check if empty result is due to authorization restrictions.

        Generates role-specific rejection messages:
        - Anonymous → "Akses ditolak. Login diperlukan untuk mengakses informasi ini."
        - Student → "Informasi ini khusus Dosen. Hubungi dosen Anda jika perlu akses."
        - Lecturer → "Informasi ini khusus Administrator sistem."

        Args:
            query: Search query string.
            retrieved_docs: List of retrieved documents (empty if checking).

        Returns:
            Tuple of (role_specific_error_message, empty_list) if access denied, None otherwise.
        """
        if retrieved_docs or self._current_metadata_filter is None:
            return None

        logger.info("No docs found with filter, checking if data exists without filter...")
        try:
            unrestricted_docs, _ = self.vectorstore.search(
                query,
                k=1,
                metadata_filter=None,
                return_metadata=False,
                include_scores=False,
            )

            if unrestricted_docs:
                # Detect current user role
                current_role = self._detect_user_role()
                logger.warning(f"Access denied: Data exists but user role '{current_role}' lacks permission")

                # Generate role-specific rejection message
                if current_role == "student":
                    rejection_message = "Informasi ini khusus Dosen. Hubungi dosen Anda jika perlu akses."
                    required_role = "lecturer"
                elif current_role == "lecturer":
                    rejection_message = "Informasi ini khusus Administrator sistem."
                    required_role = "admin"
                elif current_role == "anonymous":
                    rejection_message = "Akses ditolak. Login diperlukan untuk mengakses informasi ini."
                    required_role = "authenticated"
                else:
                    # Fallback for admin or unexpected roles
                    rejection_message = "Akses ditolak."
                    required_role = "unknown"

                # Store metadata with role information
                self._retrieved_metadata = {
                    "num_documents_retrieved": 0,
                    "retrieved_documents": [],
                    "source_links": [],
                    "similarity_scores": [],
                    "rejection_reason": "insufficient_permissions",
                    "user_role": current_role,
                    "required_role": required_role,
                }

                return (rejection_message, [])

        except Exception as e:
            logger.error(f"Error during authorization check: {str(e)}")

        return None

    def _extract_retrieval_metadata(
        self, summary_docs: List[Any]
    ) -> Tuple[List[Dict[str, Any]], List[float], List[str]]:
        """
        Extract metadata from retrieved documents.

        Args:
            summary_docs: List of retrieved document objects with metadata.

        Returns:
            Tuple of (retrieved_documents_metadata, similarity_scores, source_links).
        """
        retrieved_documents_metadata = []
        similarity_scores: List[float] = []
        source_links = []
        seen_links = set()

        for doc in summary_docs:
            doc_metadata = getattr(doc, "metadata", {})

            # Extract similarity score
            score = doc_metadata.get("similarity_score")
            if isinstance(score, (int, float)):
                similarity_scores.append(score)

            # Build document metadata
            retrieved_documents_metadata.append({
                "document_id": doc_metadata.get("document_id"),
                "document_name": doc_metadata.get("document_name"),
                "source_link": doc_metadata.get("source_link"),
                "content_type": doc_metadata.get("content_type"),
                "similarity_score": score,
            })

            # Collect unique source links
            link = doc_metadata.get("source_link")
            if link and link not in seen_links:
                seen_links.add(link)
                source_links.append(link)

        return retrieved_documents_metadata, similarity_scores, source_links

    def _validate_similarity_threshold(
        self, similarity_scores: List[float]
    ) -> Optional[Tuple[str, List]]:
        """
        Validate if documents meet similarity threshold.

        Args:
            similarity_scores: List of similarity scores from retrieved documents.

        Returns:
            Tuple of (rejection_message, empty_list) if threshold not met, None otherwise.
        """
        if not similarity_scores:
            return None

        max_score = max(similarity_scores)
        if max_score < settings.rag_similarity_threshold:
            logger.warning(
                f"Similarity threshold not met: max_score={max_score:.2f} < "
                f"threshold={settings.rag_similarity_threshold}"
            )
            self._retrieved_metadata["rejection_reason"] = "low_similarity"
            return (
                f"No sufficiently relevant documents found. Maximum similarity score "
                f"({max_score:.2f}) is below threshold ({settings.rag_similarity_threshold}).",
                [],
            )

        return None

    def _serialize_documents(self, summary_docs: List[Any]) -> str:
        """
        Serialize documents for LLM context.

        Args:
            summary_docs: List of retrieved document objects.

        Returns:
            Serialized string with document sources and content.
        """
        return "\n\n".join(
            f"Source: {doc.metadata.get('document_name', 'Unknown')}\n"
            f"Content: {doc.page_content}"
            for doc in summary_docs
            if hasattr(doc, "page_content")
        )

    def _create_retrieve_tool(self) -> Callable:
        """
        Create a retrieve tool that uses the current metadata filter.

        Returns:
            Tool function for document retrieval.
        """

        @tool(response_format="content_and_artifact")
        def retrieve(query: str):
            """
            Retrieve relevant documents from the IT support knowledge base.

            Use this tool when you need to search the knowledge base to answer
            user questions about IT support topics.

            Args:
                query: The search query to find relevant documents.

            Returns:
                Tuple of (serialized content, list of retrieved documents).
            """
            try:
                logger.info(f"Retrieving documents for query: {query[:50]}...")

                # Perform vectorstore search with RBAC metadata filter
                retrieved_docs, summary_docs = self.vectorstore.search(
                    query,
                    k=settings.rag_top_k,
                    metadata_filter=self._current_metadata_filter,
                    return_metadata=True,
                    include_scores=True,
                )

                # NEW: Boost documents with FAQ question matches
                query_lower = query.lower()
                for doc in summary_docs:
                    faq_questions = doc.metadata.get("faq_questions", [])
                    if faq_questions:
                        for faq in faq_questions:
                            # Simple similarity: check if query contains FAQ words
                            faq_lower = faq.lower()
                            # Count matching words
                            query_words = set(query_lower.split())
                            faq_words = set(faq_lower.split())
                            match_ratio = len(query_words & faq_words) / max(len(query_words), 1)

                            if match_ratio > 0.6:  # 60% word overlap
                                # Boost this document's score
                                current_score = doc.metadata.get("similarity_score", 0.0)
                                doc.metadata["similarity_score"] = min(current_score + 0.15, 1.0)
                                doc.metadata["faq_boosted"] = True
                                logger.info(
                                    f"FAQ boost applied: query='{query[:30]}...' matched FAQ='{faq[:50]}...'"
                                )
                                break  # Only boost once per doc

                # Re-sort by boosted scores
                boosted_pairs = sorted(
                    zip(retrieved_docs, summary_docs),
                    key=lambda x: x[1].metadata.get("similarity_score", 0.0),
                    reverse=True
                )
                retrieved_docs = [doc for doc, _ in boosted_pairs]
                summary_docs = [doc for _, doc in boosted_pairs]

                # Apply hybrid search (vector + BM25) if enabled
                if self.hybrid_search and summary_docs:
                    logger.info("Applying hybrid search re-ranking...")
                    vector_scores = [
                        doc.metadata.get("similarity_score", 0.0)
                        for doc in summary_docs
                    ]

                    # Hybrid re-ranking (vector + BM25)
                    summary_docs, hybrid_scores = self.hybrid_search.rerank_with_keywords(
                        query=query,
                        documents=summary_docs,
                        vector_scores=vector_scores
                    )

                    # Metadata-based boost (keywords, category, platform)
                    summary_docs, final_scores = self.hybrid_search.boost_by_metadata(
                        query=query,
                        documents=summary_docs,
                        scores=hybrid_scores
                    )

                    # Update scores in metadata
                    for doc, score in zip(summary_docs, final_scores):
                        doc.metadata["similarity_score"] = score
                        doc.metadata["hybrid_search_applied"] = True

                    # Re-pair with retrieved_docs (maintain same order)
                    # Note: retrieved_docs order should match summary_docs
                    retrieved_docs = retrieved_docs[:len(summary_docs)]

                # Check if empty result is due to authorization restrictions
                if not retrieved_docs:
                    logger.warning("No documents retrieved for query")

                    auth_check = self._check_authorization_restrictions(query, retrieved_docs)
                    if auth_check:
                        return auth_check

                    # Normal "no documents found" response
                    self._retrieved_metadata = {
                        "num_documents_retrieved": 0,
                        "retrieved_documents": [],
                        "source_links": [],
                        "similarity_scores": [],
                        "rejection_reason": "no_documents_found",
                    }
                    return "No relevant documents found in knowledge base.", []

                # Extract metadata from retrieved documents
                retrieved_documents_metadata, similarity_scores, source_links = (
                    self._extract_retrieval_metadata(summary_docs)
                )

                # Store metadata for response
                self._retrieved_metadata = {
                    "num_documents_retrieved": len(retrieved_docs),
                    "retrieved_documents": retrieved_documents_metadata,
                    "source_links": source_links,
                    "similarity_scores": similarity_scores,
                }

                # Add score summary if available
                if similarity_scores:
                    self._retrieved_metadata.update({
                        "max_similarity_score": max(similarity_scores),
                        "min_similarity_score": min(similarity_scores),
                        "avg_similarity_score": sum(similarity_scores) / len(similarity_scores),
                    })

                # Validate similarity threshold
                threshold_check = self._validate_similarity_threshold(similarity_scores)
                if threshold_check:
                    return threshold_check

                # Serialize documents for LLM context
                serialized = self._serialize_documents(summary_docs)

                logger.info(f"Retrieved {len(retrieved_docs)} documents")
                return serialized, retrieved_docs

            except Exception as e:
                msg = f"Document retrieval failed: {str(e)}"
                logger.error(msg)
                return f"Error retrieving documents: {str(e)}", []

        return retrieve

    def _build_graph(self, *, enable_memory: bool = True) -> Any:
        """
        Build the LangGraph StateGraph for conversational RAG.

        Creates a graph with three nodes:
        1. query_or_respond: LLM decides whether to retrieve or answer directly
        2. tools: Executes retrieval tool
        3. generate: Generates final answer with retrieved context

        Args:
            enable_memory: Whether to compile with MemorySaver checkpointer.

        Returns:
            Compiled LangGraph graph.
        """
        # Create retrieve tool (without filter for now - will be parameterized in query)
        retrieve_tool = self._create_retrieve_tool()

        # Node 1: Query or Respond (LLM with tool-calling)
        def query_or_respond(state: MessagesState) -> Dict[str, List]:
            """
            Decide whether to retrieve documents or respond directly.

            Uses hybrid greeting detection:
            1. Pre-filter for pure greetings (regex + keyword check)
            2. LLM with strict instructions for IT questions

            Args:
                state: Current conversation state with messages.

            Returns:
                Dictionary with updated messages including LLM response.
            """
            # Extract user query from last message
            user_query = ""
            if state["messages"]:
                last_message = state["messages"][-1]
                if hasattr(last_message, "content"):
                    user_query = last_message.content
                elif isinstance(last_message, dict):
                    user_query = last_message.get("content", "")

            # Pre-filter: Check for pure greetings (fast path, no LLM call)
            if self._is_pure_greeting(user_query):
                logger.info(f"Pure greeting detected, responding directly: {user_query[:50]}...")
                greeting_response = AIMessage(content=get_greeting_response())
                return {"messages": [greeting_response]}

            # For all non-greeting questions: Use LLM with strict knowledge base enforcement
            logger.info(f"Question detected, enforcing knowledge base search: {user_query[:50]}...")
            strict_instruction = SystemMessage(content=get_query_routing_prompt())

            # Prepend instruction to conversation messages
            messages_with_instruction = [strict_instruction] + state["messages"]

            llm_with_tools = self.llm.bind_tools([retrieve_tool])
            response = llm_with_tools.invoke(messages_with_instruction)
            return {"messages": [response]}

        # Node 2: Tools (ToolNode executes retrieve)
        # Enable error handling per LangGraph best practices
        tools_node = ToolNode([retrieve_tool], handle_tool_errors=True)

        # Node 3: Generate final answer
        def generate(state: MessagesState) -> Dict[str, List]:
            """
            Generate final answer using retrieved context.

            Collects the most recent ToolMessages (retrieval results) and
            constructs a prompt with strict instructions to only use the
            provided context.

            Per LangGraph agentic RAG pattern: handles empty results by
            returning "tidak tahu" message when no documents found.

            Args:
                state: Current conversation state with messages.

            Returns:
                Dictionary with final AI response message.
            """
            # Collect recent ToolMessages (retrieval results)
            recent_tool_messages = []
            for message in reversed(state["messages"]):
                if message.type == "tool":
                    recent_tool_messages.append(message)
                else:
                    break
            tool_messages = recent_tool_messages[::-1]

            # Format retrieved context
            docs_content = "\n\n".join(doc.content for doc in tool_messages)

            # Handle empty results - per LangGraph agentic RAG pattern
            # If no documents found in knowledge base, return "tidak tahu" response
            if not docs_content or "No relevant documents found" in docs_content:
                logger.info("No documents found in knowledge base, responding with 'tidak tahu'")
                no_knowledge_response = AIMessage(content=get_no_documents_response())
                return {"messages": [no_knowledge_response]}

            # Detect user role for role-based prompt adaptation
            current_user_role = self._detect_user_role()
            logger.info(f"Generating answer for user role: {current_user_role}")

            # Get improved system prompt with few-shot examples
            system_message_content = get_answer_generation_prompt(
                docs_content=docs_content,
                user_role=current_user_role
            )

            # Filter conversation messages (exclude tool-related messages)
            conversation_messages = [
                message
                for message in state["messages"]
                if message.type in ("human", "system")
                or (message.type == "ai" and not message.tool_calls)
            ]

            # Build final prompt
            prompt = [SystemMessage(content=system_message_content)] + conversation_messages

            # Generate response
            response = self.llm.invoke(prompt)
            return {"messages": [response]}

        # Build graph
        graph_builder = StateGraph(MessagesState)

        # Add nodes
        graph_builder.add_node("query_or_respond", query_or_respond)
        graph_builder.add_node("tools", tools_node)
        graph_builder.add_node("generate", generate)

        # Set entry point
        graph_builder.set_entry_point("query_or_respond")

        # Add conditional edge for short-circuiting
        # If query_or_respond doesn't call tools (e.g., greeting), go to END
        # Otherwise, go to tools node
        # Per LangGraph docs: tools_condition returns "tools" if tool_calls exist, else END
        graph_builder.add_conditional_edges(
            "query_or_respond",
            tools_condition,
            {"tools": "tools", END: END},  # Order: tools first, then END
        )

        # Add edges
        graph_builder.add_edge("tools", "generate")
        graph_builder.add_edge("generate", END)

        # Compile with or without memory
        if enable_memory:
            memory = MemorySaver()
            graph = graph_builder.compile(checkpointer=memory)
            logger.info("Graph compiled with MemorySaver checkpointer")
        else:
            graph = graph_builder.compile()
            logger.info("Graph compiled without memory")

        return graph

    def query(
        self,
        question: str,
        *,
        thread_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query the RAG system with a question.

        Args:
            question: User's question.
            thread_id: Optional conversation thread ID for memory persistence.
            metadata_filter: Optional metadata filter for role-based access control.

        Returns:
            Dictionary containing answer and metadata.

        Raises:
            RAGChainError: If query processing fails.
        """
        try:
            logger.info(f"Processing LangGraph query: {question[:50]}...")

            # Set metadata filter for this query (used by retrieve tool)
            self._current_metadata_filter = metadata_filter

            # Reset retrieved metadata to prevent leaking data from previous queries
            self._retrieved_metadata = {}

            # Prepare config with thread_id for memory
            config = {"configurable": {"thread_id": thread_id}} if thread_id else None

            # Stream through graph and track execution
            messages_history = []
            executed_nodes = []
            for step in self.graph.stream(
                {"messages": [{"role": "user", "content": question}]},
                stream_mode="values",
                config=config,
            ):
                messages_history = step["messages"]
                # Track which nodes were executed (for debugging/metadata)
                if len(step.get("messages", [])) > 0:
                    last_msg = step["messages"][-1]
                    if hasattr(last_msg, "type"):
                        executed_nodes.append(last_msg.type)

            # Extract final answer
            if not messages_history:
                raise RAGChainError("No response generated from graph")

            final_message = messages_history[-1]

            # Extract answer based on message type
            if hasattr(final_message, "content"):
                answer = final_message.content
            else:
                answer = str(final_message)

            logger.info("LangGraph query processed successfully")

            # Build metadata response with execution tracking
            metadata = {
                "thread_id": thread_id,
                "message_count": len(messages_history),
                "used_tools": any(
                    hasattr(msg, "tool_calls") and msg.tool_calls
                    for msg in messages_history
                ),
                "langgraph_enabled": True,
                "executed_node_types": executed_nodes,  # Track execution flow
            }

            # Add retrieved documents metadata if tools were used
            if self._retrieved_metadata:
                metadata.update(self._retrieved_metadata)

            return {
                "answer": answer,
                "metadata": metadata,
            }

        except Exception as e:
            msg = f"LangGraph query failed: {str(e)}"
            logger.error(msg)
            raise RAGChainError(msg)

    async def query_stream(
        self,
        question: str,
        *,
        thread_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ):
        """
        Stream query responses token by token from the RAG system.

        Yields LLM tokens as they are generated, followed by final metadata.
        Uses LangGraph's stream_mode="messages" for real-time token streaming.

        Args:
            question: User's question.
            thread_id: Optional conversation thread ID for memory persistence.
            metadata_filter: Optional metadata filter for role-based access control.

        Yields:
            Dict with either:
            - {"type": "token", "content": str, "done": False} for LLM tokens
            - {"type": "metadata", "metadata": dict, "done": True} for final metadata

        Raises:
            RAGChainError: If streaming fails.
        """
        try:
            logger.info(f"Starting streaming query: {question[:50]}...")

            # Set metadata filter for this query
            self._current_metadata_filter = metadata_filter

            # Reset retrieved metadata to prevent leaking data from previous queries
            self._retrieved_metadata = {}

            # Prepare config with thread_id for memory
            config = {"configurable": {"thread_id": thread_id}} if thread_id else None

            # Track if we've yielded any tokens
            has_streamed_tokens = False
            executed_nodes = []

            # Stream LLM tokens using messages mode
            async for chunk in self.graph.astream(
                {"messages": [{"role": "user", "content": question}]},
                stream_mode="messages",
                config=config,
            ):
                # chunk is a tuple: (message_chunk, metadata)
                message_chunk, chunk_metadata = chunk

                # Only stream tokens from the "generate" node
                # This avoids streaming from query_or_respond node's tool calls
                if chunk_metadata.get("langgraph_node") == "generate":
                    if hasattr(message_chunk, "content") and message_chunk.content:
                        has_streamed_tokens = True
                        yield {
                            "type": "token",
                            "content": message_chunk.content,
                            "done": False,
                        }

                # Track executed nodes for metadata
                node_name = chunk_metadata.get("langgraph_node")
                if node_name and node_name not in executed_nodes:
                    executed_nodes.append(node_name)

            # If no tokens were streamed (e.g., pure greeting), get the final answer
            if not has_streamed_tokens:
                logger.info("No tokens streamed, retrieving final state...")
                final_state = self.graph.get_state(config)
                if final_state and final_state.values:
                    messages = final_state.values.get("messages", [])
                    if messages:
                        final_message = messages[-1]
                        if hasattr(final_message, "content"):
                            yield {
                                "type": "token",
                                "content": final_message.content,
                                "done": False,
                            }

            # Build and yield final metadata
            metadata = {
                "thread_id": thread_id,
                "used_tools": any(
                    node in executed_nodes for node in ["tools"]
                ),
                "langgraph_enabled": True,
                "executed_node_types": executed_nodes,
            }

            # Add retrieved documents metadata if tools were used
            if self._retrieved_metadata:
                metadata.update(self._retrieved_metadata)

            yield {
                "type": "metadata",
                "metadata": metadata,
                "done": True,
            }

            logger.info("Streaming query completed successfully")

        except Exception as e:
            msg = f"LangGraph streaming query failed: {str(e)}"
            logger.error(msg)
            raise RAGChainError(msg)

    def get_conversation_history(self, thread_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a thread using LangGraph checkpointer.

        Args:
            thread_id: Thread ID to retrieve history for.

        Returns:
            List of messages with role and content.

        Raises:
            Exception: If history retrieval fails.
        """
        try:
            # Get current state from checkpointer using thread_id
            config = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(config)

            # Extract messages from state
            if not state or not state.values:
                logger.info(f"No history found for thread {thread_id}")
                return []

            messages = state.values.get("messages", [])

            # Convert messages to dict format
            history = []
            for msg in messages:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    # Filter out tool messages for cleaner history
                    if msg.type in ("human", "ai"):
                        history.append({
                            "role": "user" if msg.type == "human" else "assistant",
                            "content": msg.content,
                        })

            logger.info(f"Retrieved {len(history)} messages from thread {thread_id}")
            return history

        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {str(e)}")
            return []
