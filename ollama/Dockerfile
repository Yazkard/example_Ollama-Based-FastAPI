FROM ollama/ollama:latest
LABEL authors="Maciej Krzywda"

COPY startup.sh ./startup.sh

RUN apt-get update && apt-get install -y dos2unix && dos2unix startup.sh && chmod +x ./startup.sh

EXPOSE 11434

ENTRYPOINT ["/bin/sh"]
CMD ["./startup.sh"]