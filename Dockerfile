FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn prometheus_client httpx
COPY main.py .
CMD ["uvicorn", "main.py", "--host", "0.0.0.0", "--port", "8000"]
