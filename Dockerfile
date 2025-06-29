FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11
RUN apt update
RUN apt install -y debian-keyring debian-archive-keyring apt-transport-https curl

# Copy Caddy binary from local folder instead of installing
COPY ./caddy /usr/bin/caddy
RUN chmod +x /usr/bin/caddy

# Copy Renderix binary
COPY ./renderix /usr/bin/renderix
RUN chmod +x /usr/bin/renderix

COPY ./app /app/app
COPY ./domains /app/domains
COPY ./requirements.txt /app/requirements.txt
COPY ./entrypoint.sh /app/entrypoint.sh

WORKDIR /app
RUN  pip3 install -r requirements.txt

CMD ["/app/entrypoint.sh"]
