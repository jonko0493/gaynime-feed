FROM python

RUN mkdir -p /app/data
RUN mkdir /db

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_lg

COPY .flaskenv /app/
COPY server /app/server
COPY filters/filter_slurs.txt /app/data/filter_slurs.txt
COPY predictors_class /app/predictors_class

WORKDIR /app

ENV HOSTNAME=feed.gayni.me
ENV GAYNIME_URI=at://did:plc:ule2mp6xfttyeeuatsidaylr/app.bsky.feed.generator/gaynime

CMD [ "flask", "run" ]