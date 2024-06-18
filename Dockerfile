# Base Image
FROM ubuntu:latest

# Working directory in the container
WORKDIR /opt/genpod

# copy files to the container workspace
COPY . .

# update and install necessary packages
RUN apt-get update && apt-get install -y make less python3 python3-pip && pip install jupyter

CMD ["sleep", "infinity"]