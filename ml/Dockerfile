FROM python

RUN pip install spacy pandas scikit-learn discord-webhook dask[complete]
RUN python -m spacy download en_core_web_sm

RUN mkdir /ml
WORKDIR /ml