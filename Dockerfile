# Use the official Python image as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y libgl1-mesa-glx

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

