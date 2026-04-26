# Use the official Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .

# Install packages and clear cache to save space
# This will install FastAPI, Torch, Transformers, and all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Hugging Face expects (7860)
EXPOSE 7860

# Command to run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]