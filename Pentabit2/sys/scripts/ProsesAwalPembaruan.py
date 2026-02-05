import os
import math
import errno
import arcpy

ws_path = arcpy.GetParameterAsText(0)
persil_asal_path = arcpy.GetParameterAsText(1)
# sisijalan_asal_path = arcpy.GetParameterAsText(2)

arcpy.AddMessage("== Persiapan ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_path = os.path.join(appdata, "config.dat")
jalan_conf_path = os.path.join(appdata, "jalan.dat")
persil_conf_path = os.path.join(appdata, "persil.dat")
fasilitas_conf_path = os.path.join(appdata, "fasilitas.dat")
resiko_conf_path = os.path.join(appdata, "resiko.dat")

if not os.path.exists(os.path.dirname(conf_path)):
    try:
        os.makedirs(os.path.dirname(conf_path))
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise

if os.path.exists(conf_path):
    os.remove(conf_path)
if os.path.exists(jalan_conf_path):
    os.remove(jalan_conf_path)
if os.path.exists(persil_conf_path):
    os.remove(persil_conf_path)
if os.path.exists(fasilitas_conf_path):
    os.remove(fasilitas_conf_path)
if os.path.exists(resiko_conf_path):
    os.remove(resiko_conf_path)

gdbname = "znt_fgdb.gdb"
dataset = "znt_ds"
dataset_fasilitas = "fasilitas"
dataset_resiko = "resiko"
gdbtemplate = "ds_znt_template"
gdbtemplate_path = os.path.join(appdata, "template.gdb", gdbtemplate)
tbl = "template_var"
tbltemplate_path = os.path.join(appdata, "template.gdb", tbl)
temporary = "temporary.gdb"
temporary_path = os.path.join(appdata, temporary)

sisijalan = "SisiJalan"
jaringanjalan = "Jaringan_Jalan"
midpoint_jaringanjalan = "MidpointJaringanJalan"
simbologi_lebarjalan = "SimbologiLebarJalan"
simbologi_kelasjalan = "SimbologiKelasJalan"
kelas_jalan = "kelasjalan,Lokal Setapak;1:Lokal Sekunder;2:Lokal Primer;3:Kolektor Sekunder;4:Kolektor Primer;5:Arteri Sekunder;6:Arteri Primer;7"
topologi_sisijalan = "TopologiSisiJalan"
topologi_jaringanjalan = "TopologiJaringanJalan"
nd = "JaringanJalan_ND"
jaringanjalannd = "JaringanJalanForND"

persil = "Persil"
persil_line = "PersilLine"
persil_split = "PersilSplit"
persil_centroid = "PersilCentroid"
persil_split_midpoint = "PersilMidpoint"
persil_zonasi = "zonasi,Pertanian;1:Industri;2:Perkampungan;3:Perumahan Sederhana;4:Perumahan Menengah;5:Perumahan Mewah;6:Komersil;7"
persil_bentuk = "bentuk,Segi Banyak Tidak Beraturan;1:Segitiga;2:Segi Empat Tidak Beraturan;3:Segi Empat Beraturan;4"
persil_letak = "letak,Lain-lain;1:Normal;2:Tusuk sate;3:Hook;4"

gdb_path = os.path.join(ws_path, gdbname)
dataset_path = os.path.join(gdb_path, dataset)
dataset_fasilitas_path = os.path.join(gdb_path, dataset_fasilitas)
dataset_resiko_path = os.path.join(gdb_path, dataset_resiko)
sisijalan_path = os.path.join(dataset_path, sisijalan)
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)
midpoint_jaringanjalan_path = os.path.join(dataset_path, midpoint_jaringanjalan)
simbologi_lebarjalan_path = os.path.join(appdata, simbologi_lebarjalan + ".lyr")
simbologi_kelasjalan_path = os.path.join(appdata, simbologi_kelasjalan + ".lyr")
topologi_sisijalan_path = os.path.join(dataset_path, topologi_sisijalan)
topologi_jaringanjalan_path = os.path.join(dataset_path, topologi_jaringanjalan)
nd_path = os.path.join(gdb_path, gdbtemplate, nd)
jaringanjalannd_path = os.path.join(gdb_path, gdbtemplate, jaringanjalannd)

persil_path = os.path.join(dataset_path, persil)
persil_line_path = os.path.join(dataset_path, persil_line)
persil_split_path = os.path.join(dataset_path, persil_split)
persil_centroid_path = os.path.join(dataset_path, persil_centroid)
persil_split_midpoint_path = os.path.join(dataset_path, persil_split_midpoint)

writelist = ["ws," + ws_path, "conf," + conf_path, "gdb," + gdb_path, "dataset," + dataset_path, "jalan," + jalan_conf_path, "persil," + persil_conf_path, "fasilitas," + fasilitas_conf_path, "resiko," + resiko_conf_path]

conf_file = open(conf_path, "w")
conf_file.write("\n".join(writelist) + "\n")
conf_file.close()

writelist = []
writelist = ["dataset," + dataset_path, "sisijalan," + sisijalan + ";" + sisijalan_path, "jaringanjalan," + jaringanjalan + ";" + jaringanjalan_path, "midpointjaringanjalan," + midpoint_jaringanjalan + ";" + midpoint_jaringanjalan_path, "simbologikelasjalan," + simbologi_kelasjalan + ";" + simbologi_kelasjalan_path, "simbologilebarjalan," + simbologi_lebarjalan + ";" + simbologi_lebarjalan_path, kelas_jalan, "topologi_sisijalan," + topologi_sisijalan + ";" + topologi_sisijalan_path, "topologi_jaringanjalan," + topologi_jaringanjalan + ";" + topologi_jaringanjalan_path, "template," + gdbtemplate_path, "temporary," + temporary_path, "nd," + nd + ";" + nd_path, "jaringanjalannd," + jaringanjalannd + ";" + jaringanjalannd_path]

conf_file = open(jalan_conf_path, "w")
conf_file.write("\n".join(writelist) + "\n")
conf_file.close()

writelist = []
writelist = ["dataset," + dataset_path, "persil," + persil + ";" + persil_path, "persilline," + persil_line + ";" + persil_line_path, "persilsplit," + persil_split + ";" + persil_split_path, "persilcentroid," + persil_centroid + ";" + persil_centroid_path, "persilmidpoint," + persil_split_midpoint + ";" + persil_split_midpoint_path, persil_zonasi, persil_bentuk, persil_letak]

conf_file = open(persil_conf_path, "w")
conf_file.write("\n".join(writelist) + "\n")
conf_file.close()

writelist = []
writelist = ["datasetfasilitas," + dataset_fasilitas_path]

conf_file = open(fasilitas_conf_path, "w")
conf_file.write("\n".join(writelist) + "\n")
conf_file.close()

writelist = []
writelist = ["datasetresiko," + dataset_resiko_path]

conf_file = open(resiko_conf_path, "w")
conf_file.write("\n".join(writelist) + "\n")
conf_file.close()

arcpy.AddMessage("== Buat geodatabase dan dataset ==")

if arcpy.Exists(gdb_path):
    arcpy.Delete_management(gdb_path)

arcpy.CreateFileGDB_management(ws_path, gdbname)
arcpy.CreateFeatureDataset_management(gdb_path, dataset, persil_asal_path)
arcpy.CreateFeatureDataset_management(gdb_path, dataset_fasilitas, persil_asal_path)
arcpy.CreateFeatureDataset_management(gdb_path, dataset_resiko, persil_asal_path)

arcpy.AddMessage("== Menyiapkan data ==")

# if sisijalan_asal_path.strip() != "":
#     arcpy.FeatureClassToFeatureClass_conversion(sisijalan_asal_path, dataset_path, sisijalan)
arcpy.FeatureClassToFeatureClass_conversion(persil_asal_path, dataset_path, persil)

arcpy.AddMessage("== Sesuaikan proyeksi pada network dataset ==")

sr = arcpy.Describe(persil_asal_path).spatialReference
arcpy.AddMessage(sr.name)
inproject = gdbtemplate_path
outproject = os.path.join(gdb_path, gdbtemplate)
arcpy.Project_management(inproject, outproject, sr)

arcpy.AddMessage("== Mempersiapkan field-field pada persil ==")
field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persil_path, 'NEAR_DIST')
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(persil_path, 'NEAR_FID')
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(persil_path, 'NEAR_X')
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(persil_path, 'NEAR_Y')

if 'IdBidang' not in field_names:
    arcpy.AddField_management(persil_path, 'IdBidang', "LONG")
arcpy.CalculateField_management(persil_path, 'IdBidang', "!OBJECTID!", "PYTHON")
if 'ls_tnh' not in field_names:
    arcpy.AddField_management(persil_path, 'ls_tnh', "DOUBLE")

if arcpy.Exists("tempo"):
    arcpy.arcpy.Delete_management("tempo")
arcpy.MakeFeatureLayer_management(persil_path, "tempo")

arcpy.AddGeometryAttributes_management("tempo", "AREA", "", "SQUARE_METERS")
arcpy.CalculateField_management(persil_path, 'ls_tnh', "!POLY_AREA!", "PYTHON")
arcpy.DeleteField_management(persil_path, 'POLY_AREA')

if 'lb_dpn' not in field_names:
    arcpy.AddField_management(persil_path, 'lb_dpn', "DOUBLE")
if 'bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 'bentuk', "TEXT")
if 's_bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 's_bentuk', "DOUBLE")
if 'zonasi' not in field_names:
    arcpy.AddField_management(persil_path, 'zonasi', "TEXT")
if 's_zonasi' not in field_names:
    arcpy.AddField_management(persil_path, 's_zonasi', "DOUBLE")
if 'letak' not in field_names:
    arcpy.AddField_management(persil_path, 'letak', "TEXT")
if 's_letak' not in field_names:
    arcpy.AddField_management(persil_path, 's_letak', "DOUBLE")
if 'elvasi' not in field_names:
    arcpy.AddField_management(persil_path, 'elvasi', "TEXT")
if 's_elvasi' not in field_names:
    arcpy.AddField_management(persil_path, 's_elvasi', "DOUBLE")
arcpy.CalculateField_management(persil_path, 'elvasi', "'Sama'", "PYTHON")
arcpy.CalculateField_management(persil_path, 's_elvasi', "2", "PYTHON")
if 'min_lb_jln' not in field_names:
    arcpy.AddField_management(persil_path, 'min_lb_jln', "DOUBLE")

arcpy.PolygonToLine_management(persil_path, persil_line_path, "IGNORE_NEIGHBORS")
arcpy.SplitLine_management(persil_line_path, persil_split_path)

field_names = [field.name for field in arcpy.ListFields(persil_split_path)]
if 'LebarSisi' not in field_names:
    arcpy.AddField_management(persil_split_path, 'LebarSisi', "DOUBLE")


if arcpy.Exists("tempo"):
    arcpy.arcpy.Delete_management("tempo")
arcpy.MakeFeatureLayer_management(persil_split_path, "tempo")

arcpy.AddGeometryAttributes_management("tempo", "LENGTH", "METERS", "")
arcpy.CalculateField_management(persil_split_path, 'LebarSisi', "!LENGTH!", "PYTHON")

if 'XStart' not in field_names:
    arcpy.AddField_management(persil_split_path, 'XStart', "DOUBLE")
if 'XEnd' not in field_names:
    arcpy.AddField_management(persil_split_path, 'XEnd', "DOUBLE")
if 'YStart' not in field_names:
    arcpy.AddField_management(persil_split_path, 'YStart', "DOUBLE")
if 'YEnd' not in field_names:
    arcpy.AddField_management(persil_split_path, 'YEnd', "DOUBLE")
if 'Azimuth' not in field_names:
    arcpy.AddField_management(persil_split_path, 'Azimuth', "DOUBLE")
if 'ATrans' not in field_names:
    arcpy.AddField_management(persil_split_path, 'ATrans', "DOUBLE")

arcpy.FeatureToPoint_management(persil_path, persil_centroid_path, "INSIDE")
arcpy.FeatureToPoint_management(persil_split_path, persil_split_midpoint_path, "INSIDE")

field_names = [field.name for field in arcpy.ListFields(persil_split_midpoint_path)]
if 'X' not in field_names:
    arcpy.AddField_management(persil_split_midpoint_path, 'X', "DOUBLE")

exp = "!Shape.firstpoint.x!"
code_block = """
def get(b):
    return b.split(' ')[0]"""
arcpy.CalculateField_management(persil_split_midpoint_path, "X", exp, "PYTHON")

if 'Y' not in field_names:
    arcpy.AddField_management(persil_split_midpoint_path, 'Y', "DOUBLE")

exp = "!Shape.firstpoint.y!"
code_block = """
def get(b):
    return b.split(' ')[1]"""
arcpy.CalculateField_management(persil_split_midpoint_path, "Y", exp, "PYTHON")

desc = arcpy.Describe(persil_split_path)
shapename = desc.ShapeFieldName
cur = arcpy.UpdateCursor(persil_split_path)
try:
    for row in cur:
        start_fitur = row.getValue(shapename)
        row.XStart = start_fitur.firstPoint.X
        row.XEnd = start_fitur.lastPoint.X
        row.YStart = start_fitur.firstPoint.Y
        row.YEnd = start_fitur.lastPoint.Y
        if (row.YEnd - row.YStart) == 0:
            if (row.XEnd - row.YStart) >= 0:
                row.Azimuth = 90
            else:
                row.Azimuth = -90
        else:
            row.Azimuth = math.atan((row.XEnd - row.XStart) / (row.YEnd - row.YStart)) * (180 / math.pi)
        if row.Azimuth < -45:
            row.ATrans = row.Azimuth + 180
        elif row.Azimuth >= -45 and row.Azimuth <= 45:
            row.ATrans = row.Azimuth + 90
        else:
            row.ATrans = row.Azimuth
        cur.updateRow(row)
    del cur
except:
    del cur

if arcpy.Exists("Persil"):
    arcpy.Delete_management("Persil")
arcpy.MakeFeatureLayer_management(persil_path, "Persil")
arcpy.SetParameterAsText(2, "Persil")

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silakan lanjutkan proses berikutnya ==")

