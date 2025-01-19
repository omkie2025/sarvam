FROM python:3.8-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the application files into the container
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose necessary ports (if needed)
EXPOSE 5555

# Command to start the Celery worker
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info", "--concurrency=10", "--queues=audio_transcription"]
