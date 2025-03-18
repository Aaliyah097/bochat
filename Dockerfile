FROM python:3.11-alpine

RUN apk add --no-cache bash postgresql-dev gcc musl-dev

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

COPY . /code

EXPOSE 8080

CMD ["/usr/local/bin/hypercorn", "main:app", "-w", "3", "--worker-class", "asyncio", "-b", "0.0.0.0:8080", "--reload"]

