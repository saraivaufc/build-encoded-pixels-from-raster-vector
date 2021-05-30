# Requirements

- GDAL -- [Homepage](http://www.gdal.org)

# Install Gdal

Get gdal development libraries:

```shell
$ sudo apt-add-repository ppa:ubuntugis/ubuntugis-unstable
$ sudo apt-get update
$ sudo apt-get install libgdal-dev
$ sudo apt-get install python3-dev
$ sudo apt-get install gdal-bin python3-gdal
```

# Install virtual enviroment

```shell
$ sudo apt-get install virtualenv
```

# Create and activate a virtual environment

```shell
$ virtualenv env -p python3
$ source env/bin/activate
```

Install Others Requirements

```shell
(env) $ pip3 install -r requirements.txt
```

# Install GDAL

```shell
(env) $ pip3 install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
```

# Usage

# Input data

- data/BRASIL_GRID.gpkg (EPSG:4674)
- data/pivos/pivos_2017.gpkg (EPSG:4674)
- /mnt/d/DATASETS/USGS/Landsat/LANDSAT_BRASIL_2017.tif (EPSG:3857)

## Build selected grid

QGIS:

- Vector > Data Managements Tools > Reproject Layer...

  - Input Layer: pivos_2017.gpkg
  - Target CRS: EPSG: 3857
  - Add colum **class_name** with values **CenterPivot**

  - **Output: data/2017/PIVOS_2017.gpkg**

- Vector > Data Managements Tools > Reproject Layer...

  - Input Layer: BRASIL_GRID
  - Target CRS: EPSG: 3857

- Vector > Research Tools > Select by Locations

  - Select features from: Reprojected
  - Where the features: Intersect
  - By comparing to the features from: data/2017/PIVOS_2017.gpkg

- Reprojected Layer > Export > Save Selected Feature as...

  - Format: GeoPackage
  - File name: data/2017/SELECTED_GRID.gpkg
  - Layer name: SELECTED_GRID
  - CRS: EPSG:3857

  - **Output: data/2017/SELECTED_GRID.gpkg**

- Add field code in SELECTED_GRID

  - Add field **code** concat('LANDSAT_2017\_', "id")

## Split SELECTED_GRID and generate shapes

- Create folder in /data/2017/shapes
- Go to QGIS, Vector > Manage data > Split a vetorial layer

  - Input layer: data/2017/SELECTED_GRID.gpkg
  - Id: code
  - Output folder: data/2017/shapes
  - **Output: data/2017/shapes**

## Split raster by grid

```shell
bash 1_split_raster_by_shapes.sh /mnt/d/DATASETS/USGS/Landsat/LANDSAT_BRASIL_2017.tif data/2017/shapes data/2017/rasters
```

```shell
python3 2_build_encoded_pixels.py --images=data/1985/rasters --labels=data/1985/PIVOS_1985.gpkg
python3 2_build_encoded_pixels.py --images=data/2014/rasters --labels=data/2014/PIVOS_2014.gpkg
python3 2_build_encoded_pixels.py --images=data/2017/rasters --labels=data/2017/PIVOS_2017.gpkg
```

<a rel="license" href="http://creativecommons.org/licenses/by-nc/4.0/">
    <img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc/4.0/88x31.png" />
</a>
<br />
This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc/4.0/">Creative Commons Attribution-NonCommercial 4.0 International License</a>.
