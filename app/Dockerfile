FROM python:3.12-slim
LABEL authors="MaciejKrzywda"

WORKDIR /app

COPY . .

RUN pip install --upgrade pip && pip install -r requirements.txt

RUN apt-get update && apt-get install -y dos2unix && dos2unix startup.sh && chmod +x startup.sh

EXPOSE 8000
ENTRYPOINT ["/app/startup.sh"]
