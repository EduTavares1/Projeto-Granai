FROM python:3.12-slim

# Impede que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instala dependências do sistema necessárias para o Postgres
RUN apt-get update && apt-get install -y libpq-dev gcc tesseract-ocr tesseract-ocr-por && rm -rf /var/lib/apt/lists/*

# Instala o Poetry
RUN pip install poetry

# Copia apenas os arquivos de dependências primeiro (otimiza o cache do Docker)
COPY pyproject.toml  /app/

# Instala as dependências do projeto
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# Copia o restante do código
COPY . /app/

# Comando para rodar a aplicação (usando a porta definida pelo servidor ou 8000 por padrão)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]