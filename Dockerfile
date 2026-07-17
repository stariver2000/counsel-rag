FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv pip install --system -e .
CMD ["uvicorn", "counsel_rag.api.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8100"]
