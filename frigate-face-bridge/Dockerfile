FROM python:3.12-alpine

RUN apk add --no-cache bash tzdata

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY config.yaml /app/addon_config.yaml
COPY run.sh /run.sh
COPY app/ /app/
RUN chmod +x /run.sh

EXPOSE 8099
CMD ["/run.sh"]
