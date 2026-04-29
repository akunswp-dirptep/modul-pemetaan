import arcpy
import os
import shutil
import zipfile
import requests
from os.path import basename
from .document import validate_coordinate_system

path = r'C:\PenilaianTanah\temp'

def upload_shapefile_to_sipenta(nomor_berkas, token, param, in_feature, shapefile_path, use_production=True):
    zipname = None

    validate_coordinate_system(shapefile_path=shapefile_path)  
    arcpy.AddMessage('Mempersiapkan folder sementara untuk upload...')

    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)
    except Exception as e:
        arcpy.AddError(f"Terdapat kesalahan saat membuat folder sementara: {str(e)}")
        return

    shapefile_base = os.path.splitext(shapefile_path)[0]
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
    shapefile_components = [shapefile_base + ext for ext in extensions if os.path.exists(shapefile_base + ext)]

    if not shapefile_components:
        arcpy.AddError("Komponen shapefile tidak ditemukan untuk di-zip.")
        return

    try:
        zipname = os.path.join(path, in_feature + ".zip")
        with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in shapefile_components:
                zipf.write(file, basename(file))
    except Exception as e:
        arcpy.AddError(f"Terdapat kesalahan saat membuat file zip: {str(e)}")
        return

    try:
        arcpy.AddMessage('Mengupload file ke server...')
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/upload"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha-2/api/pemetaan/upload"
        url = prod_url if use_production else test_url

        headers = {
                "Authorization": f"Bearer {token}"
            }

        data = {
                "no_berkas": f'{nomor_berkas}',
                "param": f'{param}'
            }

        with open(zipname, "rb") as zip_file:
            files = {
                    "file": (
                        in_feature + '.zip',
                        zip_file,
                        "application/zip"
                    )
                }

            response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files
                )
            response.raise_for_status()  # Raise an exception for HTTP errors
            if response.status_code == 200:
                arcpy.AddMessage("File berhasil diupload ke modul tatausaha sipenta.")

    except requests.RequestException as e:
            arcpy.AddError(f"Error during file upload: {str(e)}")
    return

def upload_feature_layer_to_sipenta(nomor_berkas, token, param, in_feature, feature_layer, use_production=True):
    zipname = None
    arcpy.AddMessage('Mempersiapkan folder sementara untuk upload...')

    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)
    except Exception as e:
        arcpy.AddError(f"Terdapat kesalahan saat membuat folder sementara: {str(e)}")
        return

    temp_shapefile_folder = os.path.join(path, "Feature_Layer_Shapefile")
    try:
        os.makedirs(temp_shapefile_folder, exist_ok=True)
    except Exception as e:
        arcpy.AddError(f"Error creating shapefile output folder: {str(e)}")
        return
    try:
        arcpy.AddMessage(f"Exporting feature class to shapefile: {feature_layer}")
        arcpy.FeatureClassToShapefile_conversion([feature_layer], temp_shapefile_folder)
    except Exception as e:
        arcpy.AddError(f"Error exporting feature class to shapefile: {str(e)}")
        return
    shapefile_base = os.path.join(temp_shapefile_folder, os.path.basename(feature_layer))
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
    shapefile_components = [shapefile_base + ext for ext in extensions if os.path.exists(shapefile_base + ext)]

    if not shapefile_components:
        arcpy.AddError("Komponen shapefile tidak ditemukan untuk di-zip.")
        return

    try:
        zipname = os.path.join(path, in_feature + ".zip")
        with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in shapefile_components:
                zipf.write(file, basename(file))
    except Exception as e:
        arcpy.AddError(f"Terdapat kesalahan saat membuat file zip: {str(e)}")
        return

    try:
        arcpy.AddMessage('Mengupload file ke server...')
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/upload"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha-2/api/pemetaan/upload"
        url = prod_url if use_production else test_url

        headers = {
                "Authorization": f"Bearer {token}"
            }

        data = {
                "no_berkas": f'{nomor_berkas}',
                "param": f'{param}'
            }

        with open(zipname, "rb") as zip_file:
            files = {
                    "file": (
                        in_feature + '.zip',
                        zip_file,
                        "application/zip"
                    )
                }

            response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files
                )
            response.raise_for_status()  # Raise an exception for HTTP errors
            if response.status_code == 200:
                arcpy.AddMessage("File berhasil diupload ke modul tatausaha sipenta.")

    except requests.RequestException as e:
            arcpy.AddError(f"Error during file upload: {str(e)}")
    return



