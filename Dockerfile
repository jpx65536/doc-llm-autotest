# Dockerfile
FROM python:latest

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . .

EXPOSE 5001
# gunicorn -w 8 -k gthread --threads 8 -b 0.0.0.0:5001 run_flask:app
CMD ["gunicorn", "-w", "8", "-k", "gthread", "--threads", "2", "-b", "0.0.0.0:5001", "run_flask:app"]
