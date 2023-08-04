FROM python

RUN mkdir /app

COPY requirements.txt /app/
COPY .flaskenv /app/
COPY server app/server

RUN pip install -r /app/requirements.txt
RUN python -m spacy download en_core_web_trf

WORKDIR /app

ENV HOSTNAME=feed.gayni.me
ENV GAYNIME_URI=at://did:plc:ule2mp6xfttyeeuatsidaylr/app.bsky.feed.generator/gaynime

CMD [ "flask", "run" ]