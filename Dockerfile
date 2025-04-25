# Use an official Python base image
FROM python:3.9-slim

ENV PORT=8080

# Set an appropriate working directory
WORKDIR /app

# Copy the requirements.txt file
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend directory
COPY backend/ ./backend/

# Copy the index.html
COPY index.html .

# Specify the command to execute backend/app.py
CMD ["python", "backend/app.py"]