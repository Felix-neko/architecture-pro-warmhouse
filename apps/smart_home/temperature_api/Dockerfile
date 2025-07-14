FROM python:3.11-slim

WORKDIR /app

# Install uv (uv is a Python package installer and resolver)
RUN pip install --no-cache-dir uv

# Copy only the dependency files first for better caching
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system --no-cache-dir .

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8081

# Command to run the application
CMD ["uvicorn", "temperature_api.main:app", "--host", "0.0.0.0", "--port", "8081"]
