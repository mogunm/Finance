# syntax=docker/dockerfile:1
FROM ubuntu:22.04

# define working directory
WORKDIR /app
# install app
COPY . /app

# install app dependencies
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip install -r requirements.txt

# final configuration
ENV FLASK_APP=app
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]