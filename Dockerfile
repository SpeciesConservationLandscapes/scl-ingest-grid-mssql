FROM python:3.8-slim-buster

ARG OBSDB_HOST
ENV OBSDB_HOST $OBSDB_HOST
ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update && apt-get install -y \
    gnupg \
    build-essential \
    libpq-dev \
    curl \
    apt-transport-https ca-certificates \
    gdal-bin \
    libgdal-dev
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/9/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17

RUN pip install pyodbc==4.0.30
RUN CFLAGS=`gdal-config --cflags`; \
    pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

WORKDIR /app
COPY $PWD/odbc_template.ini .
RUN sed "s/<DBSERVER>/$OBSDB_HOST/" <odbc_template.ini >"/etc/odbc.ini"
RUN rm odbc_template.ini
