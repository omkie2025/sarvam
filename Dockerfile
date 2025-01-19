# Step 1: Use Python 3.13 as the base image
FROM python:3.13-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements.txt into the container
COPY req.txt .

# Step 4: Install dependencies
RUN pip install --no-cache-dir -r req.txt

# Step 6: Copy the rest of the application files
COPY . .

# Step 7: Expose port for FastAPI
EXPOSE 8000

# Step 8: Run FastAPI app using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
