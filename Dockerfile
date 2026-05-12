FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apk add --no-cache bash postgresql-dev gcc musl-dev

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

COPY . /code

EXPOSE 8080

CMD ["/usr/local/bin/hypercorn", "main:app", "-w", "3", "--worker-class", "asyncio", "-b", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-", "--access-logformat", "%(h)s %(r)s %(s)s %(b)s %(D)s"]

