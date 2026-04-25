import base64
import logging
import io
import os
import time
import requests
from PIL import Image
from db.postgres import db_manager

logger = logging.getLogger("VisionEngine")

class VisionEngine:
    """
    Forensic Vision Engine utilizing Hugging Face Serverless Inference.
    Features automated image optimization to comply with Cloud API payload limits
    and memory-optimized processing for Render/Railway deployments.
    """
    def __init__(self, model_name="Salesforce/blip-image-captioning-large"):
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.api_key = os.getenv("HF_API_KEY")
        
        logger.info(f"Initializing Forensic Vision Engine using Cloud Inference: {model_name}")
        
        if not self.api_key:
            logger.error("HF_API_KEY not found in environment variables. Vision analysis will fail.")

    def _query_api(self, binary_data):
        """Executes a request to Hugging Face with exponential backoff for image data."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        max_retries = 5
        for i in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, data=binary_data, timeout=30)
                result = response.json()
                
                # Handle model loading state (common in free tier)
                if isinstance(result, dict) and "estimated_time" in result:
                    wait_time = result.get("estimated_time", 15)
                    logger.info(f"HF Vision Model is loading. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code == 200:
                    return result
                
                logger.warning(f"HF Vision API returned status {response.status_code}: {result}")
            except Exception as e:
                logger.error(f"HF Vision API Connection Error: {e}")
            
            time.sleep(2 ** i)
            
        return None

    def _optimize_image(self, binary_data: bytes) -> bytes:
        """
        Resizes and compresses image data to ensure fast transit and 
        compliance with HF Inference API size limits.
        """
        try:
            img = Image.open(io.BytesIO(binary_data))
            
            # Normalize image mode to RGB
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Constrain dimensions to max 800px for speed on free tier
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=80, optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.warning(f"Image optimization bypassed due to error: {e}")
            return binary_data

    def analyze_image(self, case_id: str, file_name: str) -> str:
        """
        Orchestrates visual evidence analysis via Hugging Face.
        Retrieves binary from DB, optimizes, and queries the cloud model.
        """
        if not self.api_key:
            return "Vision capabilities are offline: HF_API_KEY missing."
            
        # Retrieve the raw media from the PostgreSQL persistence layer
        image_binary = db_manager.get_image_binary(case_id, file_name)
        if not image_binary:
            return f"Evidence item '{file_name}' could not be located in the repository."

        try:
            # Optimize image to keep payload small
            optimized_data = self._optimize_image(image_binary)
            
            logger.info(f"Executing cloud-based forensic vision analysis for: {file_name}")
            
            # Query HF Inference API
            result = self._query_api(optimized_data)
            
            if result and isinstance(result, list) and len(result) > 0:
                # BLIP model returns a list with generated text
                analysis_text = result[0].get("generated_text", "No description generated.")
                return (
                    f"--- Forensic Visual Analysis of {file_name} ---\n\n"
                    f"OBSERVATION: {analysis_text.capitalize()}.\n\n"
                    "Note: This analysis was generated via Serverless Cloud Inference."
                )
            
            return f"Vision Engine was unable to generate a meaningful report for {file_name}."
            
        except Exception as e:
            logger.error(f"Cloud vision inference failed for {file_name}: {e}")
            return f"Error during visual evidence processing: {str(e)}"

# Singleton engine instance
vision_engine = VisionEngine()