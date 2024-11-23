# Use a lightweight Python image
FROM python:3.10-slim

# Update system packages
RUN apt-get update && apt-get upgrade -y && apt-get clean

RUN python --version

# Set up the working directory
WORKDIR /app

# Copy application code
COPY utils ./utils
COPY st_ui ./st_ui

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r utils/requirements.txt
RUN pip install --no-cache-dir -r st_ui/requirements.txt

# Expose Streamlit default port
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]
