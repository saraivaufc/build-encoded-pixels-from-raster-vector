import os

import numpy as np
import pandas as pd
from PIL import Image as im
from osgeo import gdal, ogr

from image_utils import sliding_window, get_extent

image_size = 512
image_channels = 3
spatial_resolution = 30
background_pixel = 0

image_path = 'image.tif'
labels_path = 'labels.gpkg'
train_path = 'data/train.csv'
images_folder = 'data/train'
temp_raster = 'data/temp.tif'
temp_vector = 'data/temp.gpkg'

image_dataset = gdal.Open(image_path)
labels_dataset = ogr.Open(labels_path)
if os.path.exists(train_path):
    train_df = pd.read_csv(train_path)
else:
    train_df = pd.DataFrame(columns=['Image_Label', 'EncodedPixels'])

os.makedirs(images_folder, exist_ok=True)

layer = labels_dataset.GetLayer(0)

image = image_dataset.ReadAsArray()
image = image.transpose(1, 2, 0)
extent = get_extent(image_dataset)

filename, extension = os.path.basename(image_path).split('.')

for (x, y, window) in sliding_window(image, image_size):
    chip = np.array(window[:, :, : image_channels], dtype=np.uint8)

    image_id = "{filename}_{x}_{y}.jpg".format(filename=filename, x=x, y=y)

    image_data = im.fromarray(chip)
    image_data.save('{folder}/{filename}'.format(folder=images_folder,
                                                 filename=image_id))

    left = extent[0] + (x * spatial_resolution)
    right = left + (image_size * spatial_resolution)
    top = extent[3] - (y * spatial_resolution)
    bottom = top - (image_size * spatial_resolution)

    chip_extent = [left, right, bottom, top]
    # print(x, y, chip.shape, chip_extent)

    wkt = "POLYGON (({left} {bottom}," \
          "{left} {top}," \
          "{right} {top}," \
          "{right} {bottom}," \
          "{left} {bottom}))" \
        .format(left=left, right=right, top=top, bottom=bottom)

    layer.SetSpatialFilter(ogr.CreateGeometryFromWkt(wkt))

    # print("Features:", layer.GetFeatureCount())

    encoded_pixels = []

    for feature in layer:
        geom = feature.GetGeometryRef()

        target_ds = gdal.GetDriverByName('GTiff').Create(temp_raster,
                                                         image_size,
                                                         image_size, 1,
                                                         gdal.GDT_Byte)

        target_ds.SetGeoTransform((left, spatial_resolution, 0,
                                   bottom, 0, spatial_resolution))

        # Save extent to a new Shapefile
        outDriver = ogr.GetDriverByName("GPKG")

        # Remove output shapefile if it already exists
        if os.path.exists(temp_vector):
            outDriver.DeleteDataSource(temp_vector)

        out_datasource = outDriver.CreateDataSource(temp_vector)
        out_layer = out_datasource.CreateLayer("temp",
                                               geom_type=ogr.wkbPolygon)

        # Add an ID field
        id_field = ogr.FieldDefn("id", ogr.OFTInteger)
        out_layer.CreateField(id_field)

        # Create the feature and set values
        output_feature_def = out_layer.GetLayerDefn()
        output_feature = ogr.Feature(output_feature_def)
        output_feature.SetGeometry(geom)
        output_feature.SetField("id", 1)
        out_layer.CreateFeature(output_feature)

        gdal.RasterizeLayer(target_ds, [1], out_layer)

        target_ds = None
        out_datasource = None
        out_layer = None

        labels_raster = gdal.Open(temp_raster).ReadAsArray()

        pixels = labels_raster.reshape((labels_raster.shape[0] *
                                        labels_raster.shape[1])).tolist()

        feature_encoded_pixels = []

        last_value = background_pixel
        count = 0
        for idx, current_value in enumerate(pixels):
            if last_value == background_pixel and \
                    current_value != background_pixel:
                feature_encoded_pixels.append(idx)
                count += 1
            elif last_value != background_pixel and \
                    current_value != background_pixel:
                count += 1
            elif last_value != background_pixel and \
                    current_value == background_pixel:
                feature_encoded_pixels.append(count)
                count = 0
            elif last_value == background_pixel and \
                    current_value == background_pixel:
                pass

            last_value = current_value

        encoded_pixels = " ".join([str(int) for int in feature_encoded_pixels])

        train_df = train_df.append({'Image_Label': image_id,
                                    'EncodedPixels': encoded_pixels},
                                   ignore_index=True)

train_df.to_csv(train_path, index=None)