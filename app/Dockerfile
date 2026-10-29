# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency specifications first for layer caching
COPY requirements.txt .

# Install Python dependencies with network timeout and retry tolerance
RUN pip install --default-timeout=1000 --retries 5 --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose gunicorn web server port
EXPOSE 5000

# Run Flask application with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
