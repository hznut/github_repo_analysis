# syntax=docker/dockerfile:1
FROM python:3.9
RUN pip install pipenv
WORKDIR /code
COPY ./Pipfile /code/Pipfile
COPY ./Pipfile.lock /code/Pipfile.lock

RUN pipenv lock -r > requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./src/*.py /code/
COPY ./wait_for_db.sh /code/
ARG DB_HOST
CMD ["/code/wait_for_db.sh", "db", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
