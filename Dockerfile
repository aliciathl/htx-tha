FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && apt-get install -y gcc libjpeg-dev zlib1g-dev libpng-dev libfreetype6-dev curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p app/statics/imageOG app/statics/thumbnails app/logs

ENV PYTHONPATH=/app

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app.main:app"]
