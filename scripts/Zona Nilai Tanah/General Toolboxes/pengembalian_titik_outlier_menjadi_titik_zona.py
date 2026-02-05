import sys
import arcpy, os
from sipentautils import samplepoint, zonalayer

arcpy.env.overwriteOutput = True

appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
dataset_path, tahun, provinsi, kota, coor, gdb_path = zonalayer.get_config_values()
zl = os.path.join(dataset_path, "Zona_Layer")      # Layer zona
ts = os.path.join(dataset_path, "Titik_Sampel")
tz = os.path.join(dataset_path, "Titik_Zona")      # Layer sumber
tzt = os.path.join(dataset_path, "Titik_Zona_Temp") # Layer tujuan

def get_necessary_fields(feaure_1):
    # Mendefinisikan path untuk feature classes yang akan digunakan

    # Buat feature class baru berdasarkan geometri sumber
    spatial_ref = arcpy.Describe(tz).spatialReference
    geometry_type = arcpy.Describe(tz).shapeType

    # Hapus jika sudah ada
    if arcpy.Exists(tzt):
        arcpy.management.Delete(tzt)

    # Buat feature class baru dengan geometri yang sama
    arcpy.management.CreateFeatureclass(dataset_path, "Titik_Zona_Temp", geometry_type, spatial_reference=spatial_ref)
    arcpy.analysis.Identity(feaure_1, zl, tzt)
    # Menambahkan field baru untuk menyimpan nilai indeks sampel
    arcpy.management.AddField(tzt, "indeks_sampel", "DOUBLE")

    bulat1 = "100"  # Faktor pembulatan untuk jenis zona 1
    bulat2 = "100"  # Faktor pembulatan untuk jenis zona 2
    # Code block Python untuk menghitung nilai indeks berdasarkan jenis zona
    code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
        if jeniszona == 1:
            return round(bulat1 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 1
        elif jeniszona == 2:
            return round(bulat2 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 2"""

    # Menghitung nilai indeks sampel menggunakan fungsi Python di atas
    arcpy.management.CalculateField(tzt, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)
    arcpy.management.Append(tzt, tz, "NO_TEST")

    arcpy.management.Delete(tzt)


def transfer_features(source_layer, target_layer, selected_ids):
    where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
    temp_layer = arcpy.management.MakeFeatureLayer(source_layer, "temp_selected", where_clause)[0]
    temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\Titik_Sampel")[0]     

    get_necessary_fields(temp_copy)

    with arcpy.da.UpdateCursor(source_layer, ["OBJECTID"]) as ucur:
        for row in ucur:
            if row[0] in selected_ids:
                ucur.deleteRow()
    

    arcpy.management.DeleteFeatures(temp_layer)
    arcpy.management.Delete("in_memory\\Titik_Sampel")
    
    ui_folder = os.path.join(appdata, "ui")
    symbology_folder = os.path.join(ui_folder, "symbology")
    tz_simbology_path = os.path.join(symbology_folder, "Titik_Zona.lyrx")
    ts_simbology_path = os.path.join(symbology_folder, "Titik_Sampel.lyrx")

    arcpy.management.MakeFeatureLayer(tz, "Titik_Zona")
    arcpy.management.ApplySymbologyFromLayer("Titik_Zona", tz_simbology_path)

    arcpy.management.MakeFeatureLayer(ts, "Titik_Sampel")
    arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

    arcpy.SetParameter(0, "Titik_Zona")
    arcpy.SetParameter(1, "Titik_Sampel")

def check_individual_data(source_layer, selected_ids):
    """Check if any selected features have 'Jenis_Data' as 'Individual'."""
    individual_found = False
    where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
    with arcpy.da.SearchCursor(source_layer, ["Jenis_Data"], where_clause) as cursor:
        for row in cursor:
            if row[0] == "Individual":
                individual_found = True
                break
    return individual_found

# MAIN
outlier_selected = samplepoint.get_selected_oids('Titik_Sampel')
zona_selected = samplepoint.get_selected_oids('Titik_Zona')

if  zona_selected:
    arcpy.AddError("Hanya pilih titik di layer Titik Sampel")
    raise arcpy.ExecuteError
elif not outlier_selected and not zona_selected:
    arcpy.AddError("Tidak ada titik yang dipilih. Silakan pilih titik sampel (pencilan/outlier) di layer Titik Sampel.")
    raise arcpy.ExecuteError

if outlier_selected:
    if check_individual_data(ts, outlier_selected):
        arcpy.AddWarning("Data 'Individual' tidak dapat dipindahkan ke Titik Zona.")
        sys.exit()
    arcpy.AddMessage(f"Memindahkan {len(outlier_selected)} titik dari Titik_Sampel ke Titik_Zona...")
    transfer_features(ts, tz, outlier_selected)
    arcpy.AddMessage("Pemindahan fitur selesai. Nilai atribut bersama dipertahankan.")
