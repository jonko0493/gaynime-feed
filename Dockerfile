FROM python

RUN mkdir /app

COPY requirements.txt /app/
COPY .env.example /app/.env
COPY .flaskenv /app/
COPY server app/server

RUN pip install -r /app/requirements.txt

WORKDIR /app

CMD [ "flask", "run" ]