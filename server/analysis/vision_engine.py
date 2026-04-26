import logging
import io
import os
import torch
from PIL import Image
from transformers import pipeline
from dotenv import load_dotenv
from db.postgres import db_manager

# Force Python to load the .env file into the OS environment variables
load_dotenv()

logger = logging.getLogger("VisionEngine")

class VisionEngine:
    """
    True Forensic Vision Engine utilizing local Transformers (BLIP).
    Configured explicitly for Hugging Face Spaces CPU-only environment.
    """
    def __init__(self, model_name="Salesforce/blip-image-captioning-base"):
        # CRITICAL: Force CPU mode (device = -1) for HF Spaces Free Tier.
        self.device = -1
        
        logger.info(f"Initializing True Vision Pipeline: {model_name} on CPU")
        
        try:
            # FIXED: Updated task name to 'image-text-to-text' to match latest Transformers version
            self.captioner = pipeline(
                "image-text-to-text", 
                model=model_name, 
                device=self.device
            )
            logger.info("Vision pipeline weights loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Vision pipeline: {e}")
            self.captioner = None

    def _optimize_image(self, binary_data: bytes) -> Image.Image:
        """
        Converts raw database binary data into an optimized PIL Image.
        Instead of re-encoding to bytes, we pass the PIL Image directly to 
        the Transformers pipeline to save processing time on the CPU.
        """
        try:
            img = Image.open(io.BytesIO(binary_data))
            
            # Normalize image mode to RGB
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Constrain dimensions to max 800px for speed
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            return img
        except Exception as e:
            logger.warning(f"Image optimization bypassed due to error: {e}")
            # Return raw image if thumbnailing fails
            return Image.open(io.BytesIO(binary_data)).convert("RGB")

    def analyze_image(self, case_id: str, file_name: str) -> str:
        """
        Orchestrates visual evidence analysis via local BLIP model.
        Retrieves binary from DB, optimizes it, and runs native inference.
        """
        if not self.captioner:
            return "Vision capabilities are offline: Model failed to load."
            
        # Retrieve the raw media from the PostgreSQL persistence layer
        image_binary = db_manager.get_image_binary(case_id, file_name)
        if not image_binary:
            return f"Evidence item '{file_name}' could not be located in the repository."

        try:
            logger.info(f"Executing native forensic vision analysis for: {file_name}")
            
            # Optimize image directly into a PIL object
            pil_image = self._optimize_image(image_binary)
            
            # Query local HF Transformers Pipeline
            result = self.captioner(pil_image)
            
            if result and isinstance(result, list) and len(result) > 0:
                analysis_text = result[0].get("generated_text", "No description generated.")
                return (
                    f"--- Forensic Visual Analysis of {file_name} ---\n\n"
                    f"OBSERVATION: {analysis_text.capitalize()}.\n\n"
                    "Note: This analysis was generated natively on the Forensic Server."
                )
            
            return f"Vision Engine was unable to generate a meaningful report for {file_name}."
            
        except Exception as e:
            logger.error(f"Native vision inference failed for {file_name}: {e}")
            return f"Error during visual evidence processing: {str(e)}"

# Singleton engine instance
vision_engine = VisionEngine()