FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN pip install pudb && wget https://gist.githubusercontent.com/0atman/6689a874c1d610dc3a7c/raw/b219fe6ecde53475bf5f5380e14cbfaed685b263/pudb.cfg -O ~/.config/pudb/pudb.cfg
RUN mkdir /code
WORKDIR /code
ADD test_requirements.txt /code/

RUN pip install -r test_requirements.txt
ADD . /tests/
