FROM python:3.10-alpine

WORKDIR /app

RUN apk add --no-cache git
RUN pip install pipenv

COPY Pipfile Pipfile.lock ./

RUN pipenv install --system --deploy

COPY src/ src/
COPY templates/ templates/
COPY static/ static/

#CMD flask --app src/app run --debug --host=0.0.0.0
CMD gunicorn --config src/gunicorn.py src.app:app
