# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for PDF parsing and OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /app/

# Create uploads directory
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

# Expose the port (Render sets PORT environment variable dynamically)
EXPOSE 10000

# Run uvicorn server
# We use $PORT if defined, otherwise default to 10000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
