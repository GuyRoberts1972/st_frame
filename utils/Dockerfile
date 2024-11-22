# Use a lightweight Python image
FROM python:3.9-slim

# Set up the working directory
WORKDIR /app

# Copy application code and install dependencies
COPY utils/requirements.txt ./utils
COPY st/requirements.txt ./st
RUN pip install --no-cache-dir -r utils/requirements.txt
RUN pip install --no-cache-dir -r st/requirements.txt

COPY utils ./utils
COPY st_ui ./st_ui
COPY main.py ./main.py

# Expose Streamlit default port
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.enableCORS=false"]
