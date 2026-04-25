# File: agents/orchestrator.py
import logging
import time
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
    Optimized for cloud-native deployment with unbuffered logging and connection resilience.
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
            
            # Bind forensic tools to the model for native tool-calling capabilities.
            # This allows the Llama-3 model to autonomously decide which database tools to trigger.
            self.llm_with_tools = self.client.bind_tools(forensic_tools)
            logger.info(f"Forensic Agent Orchestrator initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Orchestrator initialization failure: {e}")
            self.llm_with_tools = None

    def generate_response(self, prompt: str, system_instruction: str, session_id: str = None) -> Optional[str]:
        """
        Executes an autonomous investigative loop. Retrieves historical context from Postgres, 
        invokes forensic tools as needed, and synthesizes the final case report.
        """
        if not self.llm_with_tools:
            return "Forensic AI Engine is currently offline. Please check API configuration."

        session_context = session_id or "default_stateless_context"
        logger.info(f"--- New Investigative Query [Session: {session_context}] ---")
        logger.info(f"Query: {prompt}")
        
        try:
            # 1. Retrieve historical interaction context from the PostgreSQL persistence layer.
            # This ensures the Agent remembers previous findings in the current case.
            raw_history = db_manager.get_chat_history(session_context)
            message_sequence = [SystemMessage(content=system_instruction)]
            
            for msg in raw_history:
                if msg.role == "user":
                    message_sequence.append(HumanMessage(content=msg.content))
                elif msg.role == "ai":
                    message_sequence.append(AIMessage(content=msg.content))
            
            # Append current query to the prompt sequence
            message_sequence.append(HumanMessage(content=prompt))
            
            # 2. Execute initial reasoning step
            logger.info("Agent is formulating investigative plan...")
            current_msg = self.llm_with_tools.invoke(message_sequence)
            message_sequence.append(current_msg)
            
            loop_limit = 5
            iteration_count = 0
            
            # 3. Autonomous multi-step tool invocation loop.
            # The agent will continue to query databases until it has enough evidence to answer.
            while hasattr(current_msg, "tool_calls") and current_msg.tool_calls and iteration_count < loop_limit:
                logger.info(f"Loop {iteration_count + 1}: Agent identified {len(current_msg.tool_calls)} required tool(s).")
                
                for tool_call in current_msg.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["args"]
                    call_id = tool_call["id"]
                    
                    logger.info(f"Executing Forensic Tool: {name} with args: {args}")
                    
                    # Locate and invoke the specific forensic tool from the registry
                    tool_func = next((t for t in forensic_tools if t.name == name), None)
                    
                    if tool_func:
                        try:
                            # Execute the database/analysis tool
                            tool_result = tool_func.invoke(args)
                            message_sequence.append(ToolMessage(content=str(tool_result), tool_call_id=call_id))
                            logger.info(f"Tool {name} execution successful.")
                        except Exception as e:
                            logger.error(f"Forensic tool failure ({name}): {e}")
                            message_sequence.append(ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=call_id))
                    else:
                        logger.error(f"Critical: Tool {name} not found in registry.")
                        message_sequence.append(ToolMessage(content=f"Error: Tool {name} not found.", tool_call_id=call_id))
                
                # Re-invoke model with updated evidence context to determine if more tools are needed
                current_msg = self.llm_with_tools.invoke(message_sequence)
                message_sequence.append(current_msg)
                iteration_count += 1
                
            # 4. Finalize the forensic synthesis
            final_report = current_msg.content
            
            # Validate output synthesis for safety
            if not final_report:
                if iteration_count >= loop_limit:
                    final_report = "Investigative Analysis Terminated: Maximum reasoning depth reached. Please narrow your query."
                else:
                    final_report = "Analysis complete, but evidence synthesis failed. Please rephrase the investigative query."
            
            logger.info("Forensic report synthesized. Persisting to session memory.")
                
            # 5. Persist the current interaction to the PostgreSQL chat history table
            db_manager.save_chat_message(session_context, "user", prompt)
            db_manager.save_chat_message(session_context, "ai", final_report)
            
            return final_report
            
        except Exception as e:
            logger.error(f"Reasoning loop exception: {e}")
            return "An internal system error occurred during forensic data synthesis. Please verify database connectivity."

    def clear_history(self, session_id: str):
        """Utility to wipe persistent conversation history for a given case context."""
        db_manager.clear_chat_history(session_id)
        logger.info(f"Database memory reset for case: {session_id}")

# Singleton instance for application-wide orchestration
llm_orchestrator = LLMOrchestrator()