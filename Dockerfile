# Base Image
FROM python:3.12.3

# Working directory in the container
WORKDIR /opt/genpod

# copy files to the container workspace
COPY . .

# update and install necessary packages
RUN apt-get update && apt-get install -y make less sqlite3 && pip install -r requirements.txt

CMD ["sleep", "infinity"]
