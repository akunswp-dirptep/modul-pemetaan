import arcpy
from sipentautils import samplepoint

arcpy.env.overwriteOutput = True

# Hardcoded layer names
Titik_Sampel = "Titik_Sampel"
Titik_Sampel_Individual = "Titik_Sampel_Individual"

# Get selection
selected_ids = samplepoint.get_selected_oids(Titik_Sampel)
if not selected_ids:
    arcpy.AddError("No features selected in Titik_Sampel.")
    raise arcpy.ExecuteError

# ✅ Step 0: Check that selected features have Jenis_Data == "Individual"
with arcpy.da.SearchCursor(Titik_Sampel, ["OBJECTID", "Jenis_Data"]) as cursor:
    for oid, jenis in cursor:
        if oid in selected_ids and str(jenis).strip().lower() != "individual":
            arcpy.AddError(f"Titik Sampel dengan OBJECTID {oid} bukan jenis 'Individual'. Hanya titik sampel 'Individual' yang dapat diubah.")
            raise arcpy.ExecuteError

# Step 1: Add missing fields to Titik_Sampel_Individual
missing_fields = samplepoint.get_missing_fields(Titik_Sampel, Titik_Sampel_Individual)
for field in missing_fields:
    arcpy.AddMessage(f"Menambahkan field yang kurang: {field.name} ({field.type})")
    arcpy.management.AddField(
        in_table=Titik_Sampel_Individual,
        field_name=field.name,
        field_type=field.type,
        field_precision=field.precision,
        field_scale=field.scale,
        field_length=field.length,
        field_alias=field.aliasName,
        field_is_nullable=field.isNullable,
        field_is_required="NON_REQUIRED"
    )

# Step 2: Transfer selected features
where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
temp_layer = arcpy.management.MakeFeatureLayer(Titik_Sampel, "temp_selected", where_clause)[0]
temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\temp_copy_manual")[0]

# Step 3: Insert only shared fields + geometry
common_fields = samplepoint.get_common_fields(temp_copy, Titik_Sampel_Individual)
insert_fields = common_fields + ["SHAPE@"]

with arcpy.da.InsertCursor(Titik_Sampel_Individual, insert_fields) as icur:
    with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
        for row in scur:
            icur.insertRow(row)

# Step 4: Delete moved features from Titik_Sampel
arcpy.management.DeleteFeatures(temp_layer)
arcpy.AddMessage(f"Memindahkan {len(selected_ids)} titik dari Titik_Sampel ke Titik_Sampel_Individual")
