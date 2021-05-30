import os
import argparse

import numpy as np
import pandas as pd
from PIL import Image as im
from osgeo import gdal, ogr
from sklearn.model_selection import train_test_split

from image_utils import sliding_window, get_extent, apply_contrast

image_size = 512
image_channels = 3
spatial_resolution = 30
background_pixel = 0

parser = argparse.ArgumentParser()
parser.add_argument('--images', type=str, nargs='?',
                    help="Folder images e.g data")
parser.add_argument('--labels', type=str, nargs='?',
                    help="Labels e.g labels.shp")

args = parser.parse_args()

images = [f'{args.images}/{x}' for x in os.listdir(args.images) if x.endswith('.jp2')]
labels_path = args.labels

train_images, validation_images = train_test_split(images, test_size=0.2, random_state=42)
validation_images, test_images = train_test_split(validation_images, test_size=0.5, random_state=42)

data = [
    ('train', train_images), 
    ('validation', validation_images),
    ('test', test_images), 
]

labels_dataset = ogr.Open(labels_path)
layer = labels_dataset.GetLayer(0)

temp_raster = 'data/temp.tif'
temp_vector = 'data/temp.gpkg'

for dataset_name, dataset_images in data:

    dataset_path = f'data/{dataset_name}.csv'
    images_folder = f'data/{dataset_name}_images'


    if os.path.exists(dataset_path):
        train_df = pd.read_csv(dataset_path)
    else:
        train_df = pd.DataFrame(columns=['Image_Label', 'EncodedPixels'])

    os.makedirs(images_folder, exist_ok=True)

    for image_path in dataset_images:
        print(image_path)
        image_dataset = gdal.Open(image_path)

        image = image_dataset.ReadAsArray()
        image = image.transpose(1, 2, 0)
        image = apply_contrast(image)
        extent = get_extent(image_dataset)

        filename, extension = os.path.basename(image_path).split('.')

        filename = filename.replace('_', '-')

        for x, y, window in sliding_window(image, image_size):
            
            chip = np.array(window[:, :, : image_channels], dtype=np.uint8)

            image_data = im.fromarray(chip)

            image_id = "{filename}-{x}-{y}.jp2".format(filename=filename, x=x, y=y)

            output_image = '{folder}/{filename}'.format(folder=images_folder,
                                                        filename=image_id)

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

            layer.SetAttributeFilter("")
            layer.SetSpatialFilter(ogr.CreateGeometryFromWkt(wkt))

            if layer.GetFeatureCount() >= 1:
                if not os.path.exists(output_image):
                    image_data.save(output_image, format='JPEG2000')

                encoded_pixels = []

                for feature in layer:
                    geom = feature.GetGeometryRef()
                    class_name = feature.GetField("class_name")\
                        .replace('_','').replace('-','')

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

                    train_df = train_df.append({'Image_Label': image_id + '_' + class_name,
                                                'EncodedPixels': encoded_pixels},
                                            ignore_index=True)

    train_df.to_csv(dataset_path, index=None)
