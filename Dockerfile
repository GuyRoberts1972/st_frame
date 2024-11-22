# Use a lightweight Python image
FROM python:3.9-slim

# Set up the working directory
WORKDIR /app

# Copy application code
# todo: don't do test files
COPY utils ./utils
COPY st_ui ./st_ui
COPY main.py ./main.py

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r utils/requirements.txt
RUN pip install --no-cache-dir -r st_ui/requirements.txt

# Expose Streamlit default port
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.enableCORS=false"]
