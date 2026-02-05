
import arcpy
from sipentautils import samplepoint

arcpy.env.overwriteOutput = True

# Hardcoded layer names
titik_zona = "Titik_Zona"
titik_sampel = "Titik_Sampel"

# Get selection
selected_ids = samplepoint.get_selected_oids(titik_zona)
if len(selected_ids) <= 0:
    arcpy.AddError("No features selected in Titik_Zona.")
    raise arcpy.ExecuteError

# Step 1: Transfer selected features
where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
temp_layer = arcpy.management.MakeFeatureLayer(titik_zona, "temp_selected", where_clause)[0]
temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\temp_copy_manual")[0]

# Step 2: Insert only shared fields + geometry
common_fields = samplepoint.get_common_fields(temp_copy, titik_sampel)
insert_fields = common_fields + ["SHAPE@"]

with arcpy.da.InsertCursor(titik_sampel, insert_fields) as icur:
    with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
        for row in scur:
            icur.insertRow(row)

# Step 3: Delete moved features from Titik_Zona
arcpy.management.DeleteFeatures(temp_layer)
arcpy.AddMessage(f"Memindahkan {len(selected_ids)} titik dari Titik_Zona ke Titik_Sampel")
