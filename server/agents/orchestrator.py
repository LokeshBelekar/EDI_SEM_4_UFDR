# File: agents/orchestrator.py
import logging
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

from agents.tools import forensic_tools
from db.postgres import db_manager
from core.config import settings

logger = logging.getLogger("ForensicOrchestrator")

class LLMOrchestrator:
    """
    Core Agentic Orchestrator for the forensic platform.
    Manages autonomous multi-step tool execution loops, persistent 
    conversational memory, and integration with high-performance LLMs.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        
        if not self.api_key:
            logger.error("Groq API configuration incomplete. Orchestrator offline.")
            self.llm_with_tools = None
            return

        try:
            self.client = ChatGroq(
                temperature=0.1,  # Low temperature for deterministic forensic synthesis
                model_name=self.model,
                groq_api_key=self.api_key,
                max_retries=5
            )
            
            # Bind forensic tools to the model for native tool-calling capabilities
            self.llm_with_tools = self.client.bind_tools(forensic_tools)
            logger.info(f"Agentic orchestrator initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Orchestrator initialization failure: {e}")
            self.llm_with_tools = None

    def generate_response(self, prompt: str, system_instruction: str, session_id: str = None) -> Optional[str]:
        """
        Executes an autonomous investigative loop. Retrieves historical context, 
        invokes forensic tools as needed, and synthesizes the final case report.
        """
        if not self.llm_with_tools:
            return "Forensic AI Engine is currently offline."

        session_context = session_id or "default_stateless_context"
        logger.info(f"Processing investigative query for session: {session_context}")
        
        try:
            # Retrieve historical interaction context from the PostgreSQL layer
            raw_history = db_manager.get_chat_history(session_context)
            message_sequence = [SystemMessage(content=system_instruction)]
            
            for msg in raw_history:
                if msg.role == "user":
                    message_sequence.append(HumanMessage(content=msg.content))
                elif msg.role == "ai":
                    message_sequence.append(AIMessage(content=msg.content))
            
            # Append current query to the prompt sequence
            message_sequence.append(HumanMessage(content=prompt))
            
            # Execute initial reasoning step
            current_msg = self.llm_with_tools.invoke(message_sequence)
            message_sequence.append(current_msg)
            
            loop_limit = 5
            iteration_count = 0
            
            # Autonomous multi-step tool invocation loop
            while hasattr(current_msg, "tool_calls") and current_msg.tool_calls and iteration_count < loop_limit:
                for tool_call in current_msg.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["args"]
                    call_id = tool_call["id"]
                    
                    logger.info(f"Agent executing tool: {name}")
                    
                    # Locate and invoke the specific forensic tool
                    tool_func = next((t for t in forensic_tools if t.name == name), None)
                    
                    if tool_func:
                        try:
                            tool_result = tool_func.invoke(args)
                            message_sequence.append(ToolMessage(content=str(tool_result), tool_call_id=call_id))
                        except Exception as e:
                            logger.error(f"Forensic tool failure ({name}): {e}")
                            message_sequence.append(ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=call_id))
                    else:
                        message_sequence.append(ToolMessage(content=f"Error: Tool {name} not found.", tool_call_id=call_id))
                
                # Re-invoke model with updated evidence context
                current_msg = self.llm_with_tools.invoke(message_sequence)
                message_sequence.append(current_msg)
                iteration_count += 1
                
            final_report = current_msg.content
            
            # Validate output synthesis
            if not final_report:
                if iteration_count >= loop_limit:
                    final_report = "Analysis stopped: Maximum reasoning depth reached without synthesis."
                else:
                    final_report = "Analysis complete, but evidence synthesis failed. Please rephrase the query."
                
            # Persist current interaction to the database
            db_manager.save_chat_message(session_context, "user", prompt)
            db_manager.save_chat_message(session_context, "ai", final_report)
            
            return final_report
            
        except Exception as e:
            logger.error(f"Reasoning loop exception: {e}")
            return "An internal error occurred during forensic data synthesis."

    def clear_history(self, session_id: str):
        """Utility to wipe persistent conversation history for a given case context."""
        db_manager.clear_chat_history(session_id)
        logger.info(f"Database memory reset for case: {session_id}")

# Singleton instance for application-wide orchestration
llm_orchestrator = LLMOrchestrator()