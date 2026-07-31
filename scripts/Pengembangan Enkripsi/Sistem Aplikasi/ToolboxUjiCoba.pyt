import os
import math
import shutil
import tempfile
import urllib.request
import arcpy
from datetime import datetime
import concurrent.futures

class Toolbox(object):
    def __init__(self):
        self.label = "Tile Download"
        self.alias = "Tile_Downloader"
        self.tools = [TileDownloaderTool]

class TileDownloaderTool(object):
    def __init__(self):
        self.label = "Unduh Citra Tile (XYZ)"
        self.description = "Mengunduh tile citra dari server XYZ dan menggabungkannya ke dalam raster ArcGIS Pro."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Parameter 0: Area of Interest (Feature Layer atau Extent)
        param_aoi = arcpy.Parameter(
            displayName="Area of Interest (AOI Layer / Extent)",
            name="in_aoi",
            datatype=["GPFeatureLayer", "GPExtent"],
            parameterType="Required",
            direction="Input"
        )

        # Parameter 1: Template URL Tile Server
        param_url = arcpy.Parameter(
            displayName="URL Server Tile (XYZ Template)",
            name="tile_url",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_url.filter.type = "ValueList"
        param_url.filter.list = [
            'ArcGIS',
            'Peta Dasar ATR/BPN',
            'Open Street Map',
        ]
        param_url.value = "ArcGIS"

        # Parameter 2: Zoom Level
        param_zoom = arcpy.Parameter(
            displayName="Zoom Level (0 - 19)",
            name="zoom_level",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        param_zoom.value = 15

        # Parameter 3: Output Raster
        param_output = arcpy.Parameter(
            displayName="Output Raster Dataset",
            name="out_raster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        default_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')

        waktu_unik = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        file_name = f"citra_{waktu_unik}.tif"
        param_output.value = os.path.join(default_downloads, file_name)

        return [param_aoi, param_url, param_zoom, param_output]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        aoi = parameters[0].value

        penyedia = parameters[1].valueAsText
        zoom = int(parameters[2].value)
        out_raster = parameters[3].valueAsText

        mapping_link = {
            'Open Street Map': "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            'ArcGIS': "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            'Peta Dasar ATR/BPN': 'https://sipenta.atrbpn.go.id/petadasar/drone/{x}/{y}/{z}'
        }
        url_template = mapping_link.get(penyedia, 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}')
        wgs84 = arcpy.SpatialReference(4326)
        
        if isinstance(aoi, arcpy.Extent):
            extent_obj = aoi
        else:
            desc = arcpy.Describe(aoi)
            extent_obj = desc.extent

        if not extent_obj.spatialReference or extent_obj.spatialReference.name == "Unknown":
            arcpy.AddError("Layer input tidak memiliki sistem koordinat yang terdefinisi. Harap definisikan proyeksi layer terlebih dahulu.")
            return

        extent_wgs84 = extent_obj.projectAs(wgs84)

        min_lon, min_lat = extent_wgs84.XMin, extent_wgs84.YMin
        max_lon, max_lat = extent_wgs84.XMax, extent_wgs84.YMax
 
        def lon2tile(lon, z):
            return int(math.floor((lon + 180.0) / 360.0 * (1 << z)))

        def lat2tile(lat, z):
            lat_rad = math.radians(lat)
            return int(math.floor((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * (1 << z)))

        x_min = lon2tile(min_lon, zoom)
        x_max = lon2tile(max_lon, zoom)
        y_min = lat2tile(max_lat, zoom)
        y_max = lat2tile(min_lat, zoom)

        total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
        arcpy.AddMessage(f"Jumlah tile yang akan diunduh: {total_tiles} pada Zoom {zoom}")


        temp_dir = tempfile.mkdtemp()
        downloaded_files = []
        prj_content = 'PROJCS["WGS_1984_Web_Mercator_Auxiliary_Sphere",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Mercator_Auxiliary_Sphere"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],PARAMETER["Standard_Parallel_1",0.0],PARAMETER["Auxiliary_Sphere_Type",0.0],UNIT["Meter",1.0]]'


        C = 20037508.342789244
        initial_resolution = (2 * C) / 256.0
        res = initial_resolution / (2 ** zoom)
        tile_size_m = res * 256.0

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        def download_single_tile(x, y):
            tile_url = url_template.replace('{z}', str(zoom)).replace('{x}', str(x)).replace('{y}', str(y))
            filename = f"tile_{x}_{y}.png"
            filepath = os.path.join(temp_dir, filename)
            pgw_path = os.path.join(temp_dir, f"tile_{x}_{y}.pgw")

            try:

                req = urllib.request.Request(tile_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read()
                    
                    if len(data) > 500:
                        with open(filepath, 'wb') as out_file:
                            out_file.write(data)

                        top_left_x = -C + (x * tile_size_m)
                        top_left_y = C - (y * tile_size_m)
                        center_x = top_left_x + (res / 2.0)
                        center_y = top_left_y - (res / 2.0)

                        with open(pgw_path, 'w') as pgw:
                            pgw.write(f"{res}\n0.0\n0.0\n{-res}\n{center_x}\n{center_y}\n")

                        prj_path = os.path.join(temp_dir, f"tile_{x}_{y}.prj")
                        with open(prj_path, 'w') as prj:
                            prj.write(prj_content)

                        return filepath 
            except Exception:
                pass 
            return None 

        try:
            arcpy.AddMessage(f"Memulai unduhan {total_tiles} tile...")
            
            tasks = [(x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]
            
            count = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_tile = {executor.submit(download_single_tile, t[0], t[1]): t for t in tasks}
                
                for future in concurrent.futures.as_completed(future_to_tile):
                    count += 1
                    result_filepath = future.result()
                    
                    if result_filepath:
                        downloaded_files.append(result_filepath)

                    if count % 20 == 0 or count == total_tiles:
                        arcpy.AddMessage(f"Progres unduh: {count}/{total_tiles} tile diproses...")

            if not downloaded_files:
                arcpy.AddError("Gagal! Tidak ada tile yang berhasil diunduh. Periksa koneksi internet atau batas koordinat.")
                return

            arcpy.AddMessage("Proses stitching/menggabungkan tile menjadi satu raster...")
            out_folder, out_name = os.path.split(out_raster)


            if not out_name.lower().endswith(('.tif', '.tiff', '.png', '.jpg')):
                out_name += ".tif"
                arcpy.AddMessage(f"Ekstensi otomatis ditambahkan menjadi: {out_name}")

            num_bands = 3 
            sr_3857 = arcpy.SpatialReference(3857)

            # Proses Penggabungan
            arcpy.management.MosaicToNewRaster(
                input_rasters=downloaded_files,
                output_location=out_folder,
                raster_dataset_name_with_extension=out_name,
                coordinate_system_for_the_raster=sr_3857,
                pixel_type="8_BIT_UNSIGNED",
                number_of_bands=num_bands,
                mosaic_method="LAST"
                
            )

            arcpy.AddMessage("Selesai! Citra berhasil dimuat.")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)