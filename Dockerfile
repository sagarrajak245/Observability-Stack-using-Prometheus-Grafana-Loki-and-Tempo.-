FROM python:3.9-slim

# Set a neutral working directory
WORKDIR /code

# Copy and install requirements first to leverage Docker cache
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy the application code into a subdirectory
# This creates a clean /code/app structure
COPY ./app /code/app

EXPOSE 8000

# The command is run from /code, so Python can now correctly find the 'app' package
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
