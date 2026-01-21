# Dockerfile for FastAPI Backend
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed for mysqlclient, though connector is pure python usually)
# RUN apt-get update && apt-get install -y default-libmysqlclient-dev build-essential

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port (Azure often expects 80 or 8080)
EXPOSE 8000

# Command to run
# We bind to 0.0.0.0 so the container is accessible
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
