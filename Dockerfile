FROM python:3-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
RUN chmod +x /app/reserva && mkdir -p /dados
VOLUME ["/dados"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python3 -c "import json, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8080/api/saude', timeout=3); assert r.status == 200 and json.load(r)['ok'] is True"
CMD ["./reserva", "serve", "--host", "0.0.0.0", "--porta", "8080", "--dados", "/dados"]
