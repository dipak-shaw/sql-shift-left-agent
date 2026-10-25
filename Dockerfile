FROM python:3.9-slim

WORKDIR /app

COPY . /app
ENV PYTHONPATH=/app/src

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

ENTRYPOINT ["poetry", "run", "sql-shift-left"]
