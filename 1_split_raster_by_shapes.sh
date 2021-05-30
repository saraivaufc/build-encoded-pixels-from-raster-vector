input_raster=${1}
shapefiles_dir=${2}
rasters_dir=${3}


mkdir -p ${rasters_dir}

#  delete previous files
rm ${rasters_dir}/*.tif -f

echo ${input_raster}

input_raster_filename="$(basename $input_raster)"
input_raster_filename="${input_raster_filename%.*}"

#  run
count=1
for shapefile_path in ${shapefiles_dir}/*.gpkg; do
  shapefile_filename="$(basename $shapefile_path)"
  output_raster=${rasters_dir}/${input_raster_filename}_${count}

  echo ${count} - ${shapefile_path} - ${shapefile_filename}
  gdalwarp -dstnodata 0 -cutline ${shapefile_path} -crop_to_cutline  -co COMPRESS=DEFLATE -of GTiff ${input_raster} ${output_raster}.tif

  gdal_translate -of JP2OpenJPEG ${output_raster}.tif ${output_raster}.jp2

  rm ${output_raster}.tif
  count=`expr $count + 1`
done
