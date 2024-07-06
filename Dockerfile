FROM python:3.10-alpine

WORKDIR /app

RUN apk add --no-cache git
RUN pip install pipenv

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --system --deploy

COPY src/ src/
COPY templates/ templates/
COPY static/ static/

VOLUME /app/recipes

CMD flask --app src/app run --debug --host=0.0.0.0
