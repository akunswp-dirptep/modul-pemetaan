import arcpy
import os

# Input
titik_zona = "Titik_Zona"
zona_layer = "Zona_Layer"
mean_table = os.path.join("in_memory", "indeks_nilai_tanah_table")
mean_field_name = "indeks_nilai_tanah"
join_key_field = "Keterangan"

# Step 1: Add 'join_key' field to Titik_Zona (if needed)
if join_key_field not in [f.name for f in arcpy.ListFields(titik_zona)]:
    arcpy.management.AddField(titik_zona, join_key_field, "TEXT", field_alias="Keterangan")

# Step 2: Calculate join_key as "cluster-JNSZN"
arcpy.management.CalculateField(
    titik_zona,
    join_key_field,
    expression="'Cluster: ' + str(!cluster!) + ' dan ' + 'Jenis Zona: ' + str(!JNSZN!)",
    expression_type="PYTHON3"
)

# Step 3: Calculate mean indeks grouped by cluster & JNSZN
arcpy.analysis.Statistics(
    in_table=titik_zona,
    out_table=mean_table,
    statistics_fields=[["indeks_sampel", "MEAN"]],
    case_field=["cluster", "JNSZN"]
)

# Step 4: Add 'join_key' to the mean table
arcpy.management.AddField(mean_table, join_key_field, "TEXT")
arcpy.management.CalculateField(
    mean_table,
    join_key_field,
    expression="'Cluster: ' + str(!cluster!) + ' dan ' + 'Jenis Zona: ' + str(!JNSZN!)",
    expression_type="PYTHON3"
)

# Step 5: Add mean_indeks field to Titik_Zona if not exists
if mean_field_name not in [f.name for f in arcpy.ListFields(titik_zona)]:
    arcpy.management.AddField(titik_zona, mean_field_name, "DOUBLE", field_alias="INDEKS NILAI TANAH")

# Step 6: Join on 'join_key' and copy MEAN_indeks
arcpy.management.JoinField(
    in_data=titik_zona,
    in_field=join_key_field,
    join_table=mean_table,
    join_field=join_key_field,
    fields=["MEAN_indeks_sampel"]
)

arcpy.management.CalculateField(
    titik_zona,
    mean_field_name,
    expression="!MEAN_indeks_sampel!",
    expression_type="PYTHON3"
)

# Step 7: Clean up joined field
arcpy.management.DeleteField(titik_zona, ["MEAN_indeks_sampel"])

# ==========================================================
# === Tambahan: Hitung indeks_nilai_tanah untuk zona_layer ===
# ==========================================================

# Step 8: Tambahkan join_key pada zona_layer
if join_key_field not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, join_key_field, "TEXT")

arcpy.management.CalculateField(
    zona_layer,
    join_key_field,
    expression="('Cluster: ' + str(!cluster!) + ' dan Jenis Zona: ' + str(!JNSZN!)) if !cluster! not in [None, '', 'NULL'] else 'Zona merupakan zona outlier'",
    expression_type="PYTHON3"
)


# Step 9: Tambahkan field indeks_nilai_tanah jika belum ada
if mean_field_name not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, mean_field_name, "DOUBLE", field_alias="INDEKS NILAI TANAH")

# Step 10: Join mean_table ke zona_layer berdasarkan join_key
arcpy.management.JoinField(
    in_data=zona_layer,
    in_field=join_key_field,
    join_table=mean_table,
    join_field=join_key_field,
    fields=["MEAN_indeks_sampel"]
)

# Step 11: Hanya isi nilai indeks_nilai_tanah untuk zona yang cluster-nya tidak null
with arcpy.da.UpdateCursor(zona_layer, ["cluster", "MEAN_indeks_sampel", mean_field_name]) as cursor:
    for cluster_val, mean_val, existing_val in cursor:
        if cluster_val is not None and cluster_val != "":  # hanya jika cluster ada nilainya
            cursor.updateRow((cluster_val, mean_val, mean_val))
        else:
            cursor.updateRow((cluster_val, mean_val, None))  # kosongkan jika cluster-nya null
    del cursor

# Step 12: Hapus field join hasil sementara
arcpy.management.DeleteField(zona_layer, ["MEAN_indeks_sampel"])

arcpy.AddMessage("✅ Indeks Nilai Tanah hanya ditambahkan pada zona dengan cluster yang valid (tidak null).")

