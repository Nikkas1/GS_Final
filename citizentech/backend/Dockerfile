FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

ARG INSTALL_VISION=false
COPY requirements.txt requirements-vision.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$INSTALL_VISION" = "true" ]; then pip install --no-cache-dir -r requirements-vision.txt; fi

# usuário sem privilégio; /data é o volume do banco SQLite
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app /data
# --chown: o usuário app vira dono dos arquivos e consegue ler mesmo os que estão com permissão restrita na máquina
COPY --chown=app:app . .
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
