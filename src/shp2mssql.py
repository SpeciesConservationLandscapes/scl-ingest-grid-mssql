import argparse
import os
import pyodbc
# import subprocess
from osgeo import ogr
from pathlib import Path


OBSDB_HOST = os.environ.get("OBSDB_HOST", "")
OBSDB_NAME = os.environ.get("OBSDB_NAME", "")
OBSDB_USER = os.environ.get("OBSDB_USER", "")
OBSDB_PASS = os.environ.get("OBSDB_PASS", "")
JOINSEP = ",\n"
BATCH = 1000  # seems fastest with current server resources (1/4 time of 10000)

credentials = f"database={OBSDB_NAME};UID={OBSDB_USER};PWD={OBSDB_PASS}"
# connection_str = f"server={OBSDB_HOST};{credentials}"
dsn = f"DSN=ObservationsSQLServer;{credentials}"
cnxn = pyodbc.connect(dsn)
cursor = cnxn.cursor()
driver = ogr.GetDriverByName("ESRI Shapefile")


def extant_shp(string):
    if Path(string).is_file():
        return string
    else:
        raise FileNotFoundError(string)


def insert_temp_cells(inserts):
    if not inserts:
        return

    insert_sql = f"""
        INSERT INTO {gridname}
        SELECT CI_GridID, Geom, CI_GridCellCode
        FROM (
            VALUES
                {JOINSEP.join(inserts)}
        ) sub (CI_GridID, Geom, CI_GridCellCode)
    """
    cursor.execute(insert_sql)
    cursor.commit()


class IngestionException(Exception):
    pass


parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "shapefile",
    type=extant_shp,
    help="Path to shapefile, relative to /app in container",
)
parser.add_argument(
    "-g",
    "--gridname",
    help="Human-readable label for grid. If unspecified, shapefile basename will be used.",
)
parser.add_argument(
    "--labelfield",
    help="Name of field containing string to be written to CI_GridCellCode. If unspecified, `id` will be used."
)
options = vars(parser.parse_args())
shapefile = options.get("shapefile")
gridname = options.get("gridname")
shp_basename = os.path.splitext(shapefile.split(os.path.sep)[-1])[0]
shp_basename = shp_basename.replace(" ", "_")
if gridname is None:
    gridname = shp_basename
labelfield = options.get("labelfield", "id") or "id"
ds = driver.Open(shapefile)
layer = ds.GetLayer()

grid_id = None
grid_insert_sql = f"""
    INSERT INTO CI_Grid (
        CI_GridName, 
        CI_OrganizationID_Owner, 
        CI_SecuritySettingID_Row, 
        Archive, 
        CRDate, 
        LMDate, 
        UserID_CR, 
        UserID_LM, 
        CRIPAddress, 
        LMIPAddress, 
        CI_GridExtCode, 
        IsPublic
    )
    VALUES ('{gridname}', 1, 1, 0, GETDATE(), GETDATE(), -1, -1, '', '', '', 0)
"""
with cnxn:
    # have to commit this before running ogr2ogr and GridCell INSERTs
    cursor.execute(grid_insert_sql)
    grid_id = cursor.execute("SELECT MAX(CI_GridID) FROM CI_Grid").fetchval()

if grid_id:
    print(f"new grid: {grid_id}")

    # try:
    #     cmd = [
    #         "ogr2ogr",
    #         "-overwrite",
    #         "-progress",  # won't do anything unless "fast feature count" (?) enabled on server
    #         # "-skipfailures",  # sets -gt 1
    #         # "-gt 250000",
    #         '-a_srs "EPSG:4326"',
    #         f'-f MSSQLSpatial "MSSQL:driver=ODBC Driver 17 for SQL Server;{connection_str}"',
    #         f'"{shapefile}"',
    #         # '-lco "GEOM_TYPE=geography"',
    #         '-lco "GEOMETRY_NAME=Geom"',
    #         '-lco "SPATIAL_INDEX=NO"',
    #         '-lco "UPLOAD_GEOM_FORMAT=wkt"',
    #         # try other odbc driver?
    #     ]
    #     print(" ".join(cmd))
    #     subprocess.check_output(" ".join(cmd), stderr=subprocess.STDOUT, shell=True)
    # except subprocess.CalledProcessError as err:
    #     raise IngestionException(err.stdout)

    table_create_sql = f"CREATE TABLE {gridname} " \
                       f"(CI_GridID int NOT NULL, Geom geometry NOT NULL, CI_GridCellCode nvarchar(255) NULL)"
    cursor.execute(table_create_sql)
    cursor.commit()

    insert_strs = []
    n = 0
    batchcount = 1
    for feature in layer:
        label = feature.GetField(labelfield)
        geom = feature.GetGeometryRef().ExportToWkt()
        insert_strs.append(f"        ({grid_id}, geometry::STGeomFromText('{geom}', 0), '{label}')")

        if n == (BATCH * batchcount) - 1:
            print(f"batch {batchcount}")
            insert_temp_cells(insert_strs)
            insert_strs = []
            batchcount += 1
        n += 1
    insert_temp_cells(insert_strs)  # remainder

    gridcell_insert_sql = f"""
        SELECT {labelfield},  -- from tiger_region_grid2
        1, 1, 0, GETDATE(), GETDATE(), -1, -1, '', '', '',  -- defaults
        Geom,  -- from tiger_region_grid2
        {grid_id}
        INTO CI_GridCell (
            CI_GridCellCode,
            CI_OrganizationID_Owner,
            CI_SecuritySettingID_Row,
            Archive,
            CRDate,
            LMDate,
            UserID_CR,
            UserID_LM,
            CRIPAddress,
            LMIPAddress,
            CI_GridCellExtCode,
            Geom,
            CI_GridID
        )
        FROM {gridname}
    """
    print(gridcell_insert_sql)

    # with cnxn:
    #     cursor.execute(gridcell_insert_sql)
    #     cursor.execute(f"DROP TABLE {gridname}")

    # if something goes wrong:
    # DELETE FROM CI_GridCell WHERE CI_GridID = grid_id
    # DELETE FROM CI_Grid WHERE CI_GridID = grid_id