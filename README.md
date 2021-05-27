# scl-ingest-grid-mssql
Utility for ingesting a "user grid" shapefile into the MSSQL SCL observations database

## Installation

Clone this repository into an environment that includes Docker, and set environment variables in a `.env` file in the root.

### Environment variables

```
OBSDB_HOST=
OBSDB_NAME=
OBSDB_USER=
OBSDB_PASS=
```

## Usage

- Copy the input shapefile into the `src/` directory.

- Build:  
  Note the required `--build-arg` docker argument.  
  `docker build --build-arg OBSDB_HOST=<OBSDB_HOST> -t scl3/shp2mssql .`
- Run:
    - shell: `docker run -it --env-file ./.env -v $PWD/src:/app scl3/shp2mssql bash`
    - direct invocation: `docker run -it --env-file ./.env -v $PWD/src:/app scl3/shp2mssql python shp2mssql.py tiger_region_grid_1.shp --gridname tiger_zone_grid`  

```
usage: shp2mssql.py [-h] [-g GRIDNAME] shapefile

positional arguments:
  shapefile             Path to shapefile, relative to /app in container

optional arguments:
  -h, --help            show this help message and exit
  -g GRIDNAME, --gridname GRIDNAME
                        Human-readable label for grid. If unspecified, shapefile basename will be used. (default: None)
```
