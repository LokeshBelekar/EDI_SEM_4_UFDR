# File: analysis/vision_engine.py
import base64
import logging
import io
from PIL import Image
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from core.config import settings
from db.postgres import db_manager

logger = logging.getLogger("VisionEngine")

class VisionEngine:
    """
    Multimodal Image Analysis Engine for the forensic suite.
    Features automated image optimization to ensure payloads remain within 
    LLM API limits, preventing 413 (Payload Too Large) errors.
    """
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model_name = "llama-3.2-11b-vision-preview"
        
        if self.api_key:
            self.chat = ChatGroq(
                temperature=0.0,
                model_name=self.model_name,
                groq_api_key=self.api_key,
                max_retries=3
            )
            logger.info(f"Vision Engine initialized using multimodal model: {self.model_name}")
        else:
            self.chat = None
            logger.error("Vision Engine configuration incomplete: GROQ_API_KEY missing.")

    def _optimize_image(self, binary_data: bytes) -> bytes:
        """
        Resizes and compresses image data to optimize transit and comply with 
        upstream API constraints.
        """
        try:
            img = Image.open(io.BytesIO(binary_data))
            
            # Normalize image mode to RGB for standard JPEG conversion
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Constrain dimensions while maintaining aspect ratio (Max 1024px)
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.warning(f"Image optimization bypassed due to error: {e}")
            return binary_data

    def analyze_image(self, case_id: str, file_name: str) -> str:
        """
        Orchestrates visual evidence analysis. Retrieves binary data, optimizes 
        the image, and executes multimodal forensic reasoning.
        """
        if not self.chat:
            return "Forensic vision capabilities are currently unavailable."
            
        # Retrieve the raw media from the PostgreSQL persistence layer
        image_binary = db_manager.get_image_binary(case_id, file_name)
        if not image_binary:
            return f"Evidence item '{file_name}' could not be located in the repository."

        try:
            # Process and optimize image for the multimodal payload
            optimized_data = self._optimize_image(image_binary)
            base64_image = base64.b64encode(optimized_data).decode('utf-8')
            
            # Construct a structured multimodal investigative prompt
            message = HumanMessage(
                content=[
                    {
                        "type": "text", 
                        "text": (
                            "You are an expert digital forensics analyst. Describe this image in detail. "
                            "Identify key entities, objects, geographical locations, and visible text (OCR). "
                            "Maintain a professional, clinical, and objective tone."
                        )
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            )
            
            logger.info(f"Executing multimodal forensic analysis for evidence item: {file_name}")
            response = self.chat.invoke([message])
            
            return f"Forensic visual analysis of {file_name}:\n\n{response.content}"
            
        except Exception as e:
            logger.error(f"Multimodal inference failed for {file_name}: {e}")
            return f"Error during visual evidence processing: {str(e)}"

# Singleton engine instance
vision_engine = VisionEngine()