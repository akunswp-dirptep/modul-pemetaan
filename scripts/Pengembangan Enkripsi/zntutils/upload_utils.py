import arcpy
import os
import shutil
import zipfile
import requests
from os.path import basename
from .document import validate_coordinate_system

path = r'C:\PenilaianTanah\temp'
def main_upload(project_id, username, menu, tahapan, in_feature, tahun, kategori, feature_class, use_production=True):
    zipname = None
    if len(tahun) == 4:  # Ensure the year format is correct
        arcpy.AddMessage('========== Preparing Temp Folder ==========')
        
        # Attempt to create the temporary directory
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path)
        except Exception as e:
            arcpy.AddError(f"Error creating temporary directory: {str(e)}")
            return

        temp_shapefile_folder = os.path.join(path, "temp_shapefile_output")
        try:
            os.makedirs(temp_shapefile_folder, exist_ok=True)
        except Exception as e:
            arcpy.AddError(f"Error creating shapefile output folder: {str(e)}")
            return

        # Attempt to export the feature class to a shapefile
        try:
            arcpy.AddMessage(f"Exporting feature class to shapefile: {feature_class}")
            arcpy.FeatureClassToShapefile_conversion([feature_class], temp_shapefile_folder)
        except Exception as e:
            arcpy.AddError(f"Error exporting feature class to shapefile: {str(e)}")
            return

        # Collect shapefile components
        shapefile_base = os.path.join(temp_shapefile_folder, os.path.basename(feature_class))
        extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
        shapefile_components = [shapefile_base + ext for ext in extensions if os.path.exists(shapefile_base + ext)]

        if not shapefile_components:
            arcpy.AddError("Shapefile components not found!")
            return

        # Attempt to zip the shapefile
        try:
            zipname = os.path.join(path, in_feature + ".zip")
            with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in shapefile_components:
                    zipf.write(file, basename(file))
        except Exception as e:
            arcpy.AddError(f"Error creating zip file: {str(e)}")
            return

        # Attempt to upload the zip file
        try:
            arcpy.AddMessage('========== Mengupload File ==========')
            test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/upload"
            prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/upload"
            url = prod_url if use_production else test_url
            headers = {"Content-Type": "multipart/form-data"}

            with open(zipname, 'rb') as f:

                files = {'file': (in_feature + '.zip', f)}
                response = requests.post(url, data={'nomor_berkas': project_id, 'nik': username, 'param': menu, 'step': tahapan}, files=files, timeout=300)

                try:
                    data = response.json()
                except requests.exceptions.JSONDecodeError:
                    if '"error":false' in response.text:
                        arcpy.AddMessage("Upload berhasil")
                    if '"error":true' in response.text:
                        arcpy.AddError("Upload gagal, server mengembalikan error.")
                    return

                # Check if response indicates success or failure
                if data.get("error") == False:
                    # Extract and display the success message
                    message = data.get("message", "Upload successful, but no message provided.")
                    arcpy.AddMessage(f"{message}")
                else:
                    # Extract the error message
                    message = data.get("message", "Upload failed, but no message provided.")
                    
                    # Handle special case for "le" message
                    if message.lower() == "le":
                        arcpy.AddWarning("Data sedang dalam proses dikirim ke server. Silakan tunggu beberapa saat dan cek kembali.")
                    else:
                        arcpy.AddError(f"Upload gagal: {message}")
                    
                    # Optional: Log raw response for debugging
                    # arcpy.AddMessage(f"Raw API Response: {response.text}")
        except requests.RequestException as e:
            arcpy.AddError(f"Error during file upload: {str(e)}")
    else:
        arcpy.AddError("Invalid year format!")

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


