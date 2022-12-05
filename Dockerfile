FROM python:3.11.0

WORKDIR /app

RUN apt-get update && apt-get install -y

git

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "MetaButler"]
