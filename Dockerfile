FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -U pip \
    && pip install -e . \
    && pip install uvicorn

EXPOSE 8000
ENV DATABASE_URL=sqlite:///./dev.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
