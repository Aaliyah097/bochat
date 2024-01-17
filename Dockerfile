FROM python:3.11-alpine

RUN apk add --no-cache bash

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

COPY . /code

EXPOSE 8000

CMD ["sh", "-c", "wait-for-it -t 30 postgres-chat-db:5432 -- alembic upgrade head && hypercorn main:app -b 0.0.0.0:8080 --reload"]
# CMD ["sh", "-c", "wait-for-it -t 30 postgres-chat-db:5432 -- alembic upgrade head && uvicorn main:app --host=0.0.0.0 --port=8000 --reload"]
