import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Core LangChain Imports
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

# Import the tools and the database manager
from agents.tools import forensic_tools
from database.postgres_db import get_db

# Configure professional logging
logger = logging.getLogger("LLMCore")

load_dotenv()

class LLMClient:
    """
    LangChain-powered Agent Interface for the UFDR Forensic Engine.
    Uses native LCEL Tool-Calling with Persistent Database Chat History.
    """

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        if not self.api_key:
            logger.error("GROQ_API_KEY missing from environment variables.")
            self.client = None
            self.llm_with_tools = None
            return

        try:
            # 1. Base Client
            self.client = ChatGroq(
                temperature=0.1,  # Low temp for deterministic forensic output
                model_name=self.model,
                groq_api_key=self.api_key,
                max_retries=5
            )
            
            # 2. Bind Tools directly to the client
            self.llm_with_tools = self.client.bind_tools(forensic_tools)
            
            logger.info(f"Native Tool-Calling Engine initialized using model: {self.model} with Persistent DB Memory.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Client: {e}")
            self.client = None
            self.llm_with_tools = None

    def generate_response(self, prompt: str, system_instruction: str, session_id: str = None) -> Optional[str]:
        """
        Public interface for passing queries. 
        Executes a native multi-step tool-calling loop and permanently stores conversations.
        """
        if not self.llm_with_tools:
            return "Forensic AI Engine offline."

        active_session = session_id if session_id else "default_stateless_session"
        logger.info(f"Dispatching query to Agent (Session Context: {active_session}).")
        
        db = get_db()
        
        try:
            # 1. Fetch Persistent History from Postgres
            raw_history = db.get_chat_history(active_session)
            chat_history_messages = []
            
            # Convert database records back into LangChain Message objects
            for msg in raw_history:
                if msg.role == "user":
                    chat_history_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "ai":
                    chat_history_messages.append(AIMessage(content=msg.content))
            
            # 2. Build the message sequence
            messages = [SystemMessage(content=system_instruction)]
            messages.extend(chat_history_messages)
            messages.append(HumanMessage(content=prompt))
            
            # 3. Initial LLM invocation
            ai_msg = self.llm_with_tools.invoke(messages)
            messages.append(ai_msg)
            
            final_response_text = ""
            
            # 4. Multi-Step Tool Execution Loop
            # Uses a while loop so the AI can sequence multiple tool calls before answering
            current_msg = ai_msg
            loop_count = 0
            max_loops = 5 # Safety limit to prevent infinite loops
            
            while hasattr(current_msg, "tool_calls") and current_msg.tool_calls and loop_count < max_loops:
                for tool_call in current_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    logger.info(f"Agent requested tool execution: {tool_name}")
                    
                    # Find the corresponding tool function
                    tool_func = next((t for t in forensic_tools if t.name == tool_name), None)
                    
                    if tool_func:
                        try:
                            # Execute the database query
                            tool_result = tool_func.invoke(tool_args)
                            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))
                        except Exception as e:
                            logger.error(f"Tool {tool_name} failed: {e}")
                            messages.append(ToolMessage(content=f"Error executing tool: {e}", tool_call_id=tool_id))
                    else:
                        messages.append(ToolMessage(content=f"Tool {tool_name} not found.", tool_call_id=tool_id))
                
                # 5. Re-invoke the LLM with the new tool results
                current_msg = self.llm_with_tools.invoke(messages)
                messages.append(current_msg)
                loop_count += 1
                
            # The final response after all tools have been executed
            final_response_text = current_msg.content
            
            # Fallback safeguard in case Groq drops the text content
            if not final_response_text:
                if loop_count >= max_loops:
                    final_response_text = "The AI reached the maximum number of tool calls and stopped. Please simplify your query."
                else:
                    final_response_text = "I have analyzed the database using my tools, but could not generate a textual summary. Please rephrase your query."
                
            # 6. Save the new interaction to Persistent Storage
            db.save_chat_message(active_session, "user", prompt)
            db.save_chat_message(active_session, "ai", final_response_text)
            
            return final_response_text
            
        except Exception as e:
            logger.error(f"Agent execution loop failed: {e}")
            return "An error occurred while executing forensic analysis tools."

    def clear_history(self, session_id: str):
        """Utility to wipe the chat history for a given case from the database."""
        db = get_db()
        db.clear_chat_history(session_id)
        logger.info(f"Database memory cleared via Agent for case: {session_id}")

# Singleton instance
llm_engine = LLMClient()