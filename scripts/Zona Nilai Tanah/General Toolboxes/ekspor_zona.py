import os, json
import arcpy
import zipfile
from sipentautils import zonalayer

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

dataset_path = configs['dataset_path']
tahun = configs['THNNILAI']
lokasi = configs['WADMPR']
coor = configs['coord']
gdb_path = configs['gdb_path']

# ======================
# UNSELECT FIELD 
# ======================

zonalayer.checkIfThereSelectedField()


# ======================
# USER INPUT
# ======================
out = arcpy.GetParameterAsText(0)

# ======================
# MAIN PROCESSING
# ======================
# Define input layer and output shapefile path
shp_name = "Zona_Layer_" + lokasi + "_" + tahun + ".shp"
output_shp = os.path.join(out, shp_name)

# If the shapefile already exists, delete it
if arcpy.Exists(output_shp):
    arcpy.Delete_management(output_shp)

# Project and export the shapefile
out_coordinate_system = arcpy.Describe(zl_path).spatialReference
arcpy.Project_management(zl_path, output_shp, out_coordinate_system)

# Zipping the shapefile components
def zip_shapefile(shp_path):
    # Get the base name without extension
    base_name = os.path.splitext(shp_path)[0]
    
    # Find all associated shapefile components
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]  # Add other extensions if needed
    files_to_zip = [base_name + ext for ext in extensions if os.path.exists(base_name + ext)]
    
    # Zip the shapefile components
    zip_path = base_name + ".zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_zip:
            zipf.write(file, os.path.basename(file))  # Write file to the zip archive
            arcpy.AddMessage(f"Added {file} to {zip_path}")

    arcpy.AddMessage(f"== Zipping completed: {zip_path} ==")

# Call the zipping function
zip_shapefile(output_shp)

arcpy.AddMessage("== Proses selesai ==")
