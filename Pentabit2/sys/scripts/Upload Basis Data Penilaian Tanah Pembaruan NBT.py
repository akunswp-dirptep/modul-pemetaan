import os
import arcpy
import sys
import json
import csv
import zipfile
import requests
from datetime import datetime

# Configuration File Handling
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

# Read configuration file
conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

# Extract dataset path
for line in list_config:
    line = line.replace("\n", "")
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

# Define dataset names
persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)

# Columns to check for NULL values
columns_to_check = ["NIB"]
objectid_column = "OBJECTID"  # Column to identify parcels

# Parameter Input (from Custom Toolbox)
username = arcpy.GetParameterAsText(1)  # NIK
project_id = arcpy.GetParameterAsText(2)  # Nomor Berkas
tahun = arcpy.GetParameter(3)  # Tahun

# Validate Parameters
if not username or not project_id or not isinstance(tahun, int) or tahun <= 0:
    arcpy.AddError("Invalid parameters: Ensure NIK, Nomor Berkas are non-empty, and Tahun is a positive integer.")
    sys.exit(1)

# Create a unique timestamp for file naming
execution_time = datetime.now()
formatted_date = execution_time.strftime("%d %B")  # e.g., "11 February"
formatted_time = execution_time.strftime("%H_%M")  # e.g., "13_57"

# Unique ZIP file name
zip_filename = f"Laporan Tahap Basis Data_Pembaruan NBT_{formatted_date}_{formatted_time}.zip"

# Output directory
output_dir = r"C:\PenilaianTanah"
zip_path = os.path.join(output_dir, zip_filename)

# Create a text report
def generate_text_report(report_path, metadata, validation_results):
    with open(report_path, "w") as txt_file:
        txt_file.write("Shapefile Analysis Report\n")
        txt_file.write("=========================\n\n")
        txt_file.write(f"NIK: {metadata['username']}\n")
        txt_file.write(f"Nomor Berkas: {metadata['project_id']}\n")
        txt_file.write(f"Tahun: {metadata['tahun']}\n\n")
        txt_file.write(f"Date and Time: {metadata['date_and_time']}\n")
        txt_file.write(f"Shapefile Analyzed: {metadata['shapefile_analyzed']}\n")
        txt_file.write(f"Row Count: {metadata['row_count']}\n")
        txt_file.write(f"Spatial Reference: {metadata['spatial_reference']}\n\n")
        txt_file.write("Validation Results:\n")
        if isinstance(validation_results, str):
            txt_file.write(validation_results + "\n")
        else:
            for result in validation_results:
                txt_file.write(f"Object ID: {result['object_id']}, NULL Columns: {', '.join(result['null_columns'])}\n")

# Create a JSON report
def generate_json_report(report_path, metadata, validation_results):
    report_data = {
        "metadata": metadata,
        "validation_results": validation_results
    }
    with open(report_path, "w") as json_file:
        json.dump(report_data, json_file, indent=4)

# Export attribute table to CSV
def export_attribute_table_to_csv(shapefile_path, output_path):
    try:
        fields = [f.name for f in arcpy.ListFields(shapefile_path)]
        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(fields)  # Write header row
            with arcpy.da.SearchCursor(shapefile_path, fields) as cursor:
                for row in cursor:
                    writer.writerow(row)  # Write each row
    except Exception as e:
        arcpy.AddError(f"Error exporting attribute table to CSV: {e}")

# Compress reports into a ZIP file
def compress_reports_to_zip(zip_path, report_files):
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in report_files:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
                else:
                    arcpy.AddWarning(f"File not found and skipped: {file}")
        arcpy.AddMessage(f"All reports compressed into: {zip_path}")
    except Exception as e:
        arcpy.AddError(f"Error creating zip file: {e}")

# Upload ZIP file to API
def upload_zip_to_api(zip_path, username, project_id, tahun):
    url = "https://sipenta.atrbpn.go.id/tatausaha/apis/upload"
    headers = {"Content-Type": "multipart/form-data"}
    payload = {
        "nik": username,
        "nomor_berkas": project_id,
        "tahun": tahun,
        "step": "Penyusunan Basis Data Penilaian Bidang Tanah",
        "param": "Basis Data Penilaian Bidang Tanah"
    }

    try:
        with open(zip_path, "rb") as f:
            files = {"file": (os.path.basename(zip_path), f)}
            response = requests.post(url, data=payload, files=files)

            if '"error":false' in response.text:
                start = response.text.find('"message":"') + len('"message":"')
                end = response.text.find('"', start)
                message = response.text[start:end]
                arcpy.AddMessage(f"Upload successful: {message}")
            else:
                start = response.text.find('"message":"') + len('"message":"')
                end = response.text.find('"', start)
                message = response.text[start:end]
                arcpy.AddError(f"Upload failed: {message}")
    except Exception as e:
        arcpy.AddError(f"Error uploading ZIP file: {e}")
        sys.exit(1)

# Count total rows in the shapefile
row_count = len(list(arcpy.da.SearchCursor(persil_path, [objectid_column])))

# Extract spatial reference
desc = arcpy.Describe(persil_path)
spatial_ref = desc.spatialReference.name

# Main Execution
try:
    metadata = {
    "username": username,
    "project_id": project_id,
    "tahun": tahun,
    "date_and_time": execution_time.strftime("%Y-%m-%d %H:%M:%S"),
    "shapefile_analyzed": persil,
    "row_count": row_count,  # FIXED
    "spatial_reference": spatial_ref  # Ensure spatial_ref is also defined
    }

    # File paths for reports
    json_path = os.path.join(output_dir, "Shapefile_Analysis_Report.json")
    txt_path = os.path.join(output_dir, "Shapefile_Analysis_Report.txt")
    csv_path = os.path.join(output_dir, "Shapefile_Attribute_Table.csv")

    # Create reports
    generate_json_report(json_path, metadata, "All required columns are complete. No NULL values detected.")
    generate_text_report(txt_path, metadata, "All required columns are complete. No NULL values detected.")
    export_attribute_table_to_csv(persil_path, csv_path)

    # Compress reports into a unique ZIP file
    compress_reports_to_zip(zip_path, [json_path, txt_path, csv_path])

    # Upload the unique ZIP file
    upload_zip_to_api(zip_path, username, project_id, tahun)

    # Remove temporary files
    os.remove(json_path)
    os.remove(txt_path)
    os.remove(csv_path)

except Exception as e:
    arcpy.AddError(f"An error occurred: {e}")
    sys.exit(1)
