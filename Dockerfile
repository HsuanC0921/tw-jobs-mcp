FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    TW_JOBS_TRANSPORT=streamable-http \
    TW_JOBS_HOST=0.0.0.0 \
    TW_JOBS_PORT=8000

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

USER nobody
EXPOSE 8000
CMD ["tw-jobs-mcp"]
