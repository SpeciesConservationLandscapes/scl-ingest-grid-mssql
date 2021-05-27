# Local development convenience

IMAGE="scl3/shp2mssql"

build:
	docker build --build-arg OBSDB_HOST=conservationinnovation.database.windows.net --no-cache -t $(IMAGE) .

run:
	docker run -it --env-file ./.env -v $(PWD)/.git:/app/.git $(IMAGE) python shp2mssql.py

shell:
	docker run -it --env-file ./.env -v $(PWD)/src:/app -v $(PWD)/.git:/app/.git $(IMAGE) bash
