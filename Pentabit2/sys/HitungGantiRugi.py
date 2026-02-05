import os
import arcpy

batas_bawah = arcpy.GetParameterAsText(0)
batas_atas = arcpy.GetParameterAsText(1)

arcpy.AddMessage("== Proses dimulai ==")

if batas_bawah == "":
    batas_bawah = 10
if batas_atas == "":
    batas_atas = 40

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "config.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

ws = ""
ganti_rugi = "ganti_rugi"

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "ws":
        ws = persil_config[1]

ganti_rugi = os.path.join(ws, ganti_rugi)

peta_nilai_tanah = os.path.join(ganti_rugi, "PetaNilaiTanah.shp")
peta_data_bangunan = os.path.join(ganti_rugi, "DataBangunan.shp")
peta_ada_tanah = os.path.join(ganti_rugi, "PengadaanTanah.shp")
peta_join1 = os.path.join(ganti_rugi, "Join1.shp")

if arcpy.Exists(peta_join1):
    arcpy.Delete_management(peta_join1)

arcpy.SpatialJoin_analysis(peta_nilai_tanah, peta_data_bangunan, peta_join1, "JOIN_ONE_TO_ONE", "KEEP_ALL", "IdBidangAwal \"IdBidangAwal\" true true false 50 Long 0 0 ,None,#," + peta_nilai_tanah + ",FID,-1,-1;LuasBidang \"LuasBidang\" true true false 50 Double 0 0 ,None,#," + peta_nilai_tanah + ",LuasBidang,-1,-1;NIB \"NIB\" true true false 50 Text 0 0 ,None,#," + peta_nilai_tanah + ",NIB,-1,-1;Predicted \"Predicted\" true true false 50 Double 0 0 ,None,#," + peta_nilai_tanah + ",Predicted,-1,-1;IdBidang \"IdBidang\" true true false 50 Float 0 0 ,None,#," + peta_nilai_tanah + ",IdBidang,-1,-1;IdSampel \"IdSampel\" true true false 50 Long 0 0 ,None,#," + peta_data_bangunan + ",FID,-1,-1;Luas_Bang \"Luas_Bang\" true true false 50 Double 0 0 ,None,#," + peta_data_bangunan + ",Luas_Bang,-1,-1;Nilai_Bang \"Nilai_Bang\" true true false 50 Double 0 0 ,None,#," + peta_data_bangunan + ",Nilai_Bang,-1,-1", "INTERSECT", "", "")

arcpy.MakeFeatureLayer_management(peta_join1, "temp_join1")
# arcpy.SelectLayerByLocation_management("temp_join1", "INTERSECT", peta_data_bangunan)

peta_tanah_bangunan = os.path.join(ganti_rugi, "PetaTanahBangunan.shp")
if arcpy.Exists(peta_tanah_bangunan):
    arcpy.Delete_management(peta_tanah_bangunan)

arcpy.CopyFeatures_management("temp_join1", peta_tanah_bangunan)
arcpy.Delete_management("temp_join1")

peta_terkena_pengadaan = os.path.join(ganti_rugi, "PetaTerkenaPengadaan.shp")
if arcpy.Exists(peta_terkena_pengadaan):
    arcpy.Delete_management(peta_terkena_pengadaan)

arcpy.Clip_analysis(peta_tanah_bangunan, peta_ada_tanah, peta_terkena_pengadaan)

field_names = [field.name for field in arcpy.ListFields(peta_terkena_pengadaan)]
if 'LuasKena' not in field_names:
    arcpy.AddField_management(peta_terkena_pengadaan, 'LuasKena', "DOUBLE")
if 'Persen' not in field_names:
    arcpy.AddField_management(peta_terkena_pengadaan, 'Persen', "DOUBLE")
if 'Ganti_Bang' not in field_names:
    arcpy.AddField_management(peta_terkena_pengadaan, 'Ganti_Bang', "DOUBLE")
if 'GantiTanah' not in field_names:
    arcpy.AddField_management(peta_terkena_pengadaan, 'GantiTanah', "DOUBLE")
if 'TotalGanti' not in field_names:
    arcpy.AddField_management(peta_terkena_pengadaan, 'TotalGanti', "DOUBLE")

arcpy.CalculateField_management(peta_terkena_pengadaan, 'LuasKena', "!shape.area!", "PYTHON")
arcpy.CalculateField_management(peta_terkena_pengadaan, 'Persen', "(!LuasKena! / !LuasBidang!) * 100", "PYTHON")

exp = "ganti_tanah(!Persen!, " + batas_bawah + ", " + batas_atas + ", !LuasKena!, !Predicted!, !LuasBidang!)"
code_block = """
def ganti_tanah(b, bawah, atas, lkena, ntanah, ltanah):
    if b <= bawah:
        return (lkena * ntanah)
    elif b > bawah and b <= atas:
        return (lkena * ntanah)
    elif b > atas:
        return (ltanah * ntanah)"""
arcpy.CalculateField_management(peta_terkena_pengadaan, 'GantiTanah', exp, "PYTHON", code_block)

exp = "ganti_bang(!Persen!, " + batas_bawah + ", " + batas_atas + ", !LuasKena!, !Predicted!, !Nilai_Bang!, !LuasBidang!)"
code_block = """
def ganti_bang(b, bawah, atas, lkena, ntanah, nbangunan, ltanah):
    if b <= bawah:
        return (b * nbangunan)
    elif b > bawah and b <= atas:
        return nbangunan
    elif b > atas:
        return nbangunan"""
arcpy.CalculateField_management(peta_terkena_pengadaan, 'Ganti_Bang', exp, "PYTHON", code_block)

arcpy.CalculateField_management(peta_terkena_pengadaan, 'TotalGanti', "!GantiTanah! + !Ganti_Bang!", "PYTHON", code_block)

arcpy.AddMessage("== Rekap ==")

cur = arcpy.SearchCursor(peta_terkena_pengadaan)
row = None
Jumlah_Bidang = 0
Jumlah_Bangun = 0
Nilai_Bidang = 0
Nilai_Bangun = 0
Total_Ganti = 0

try:
    for row in cur:
        Jumlah_Bidang = Jumlah_Bidang + 1
        if row.Ganti_Bang == 0:
            Jumlah_Bangun = Jumlah_Bangun + 1
        Nilai_Bidang = Nilai_Bidang + row.GantiTanah
        Nilai_Bangun = Nilai_Bangun + row.Ganti_Bang
    Total_Ganti = Nilai_Bidang + Nilai_Bangun
except:
    arcpy.AddMessage("Error 1...")
finally:
    del row, cur

dbf_rekap = os.path.join(ganti_rugi, "Tabel_Rekap.dbf")
if arcpy.Exists(dbf_rekap):
    arcpy.Delete_management(dbf_rekap)

arcpy.CreateTable_management(ganti_rugi, "Tabel_Rekap.dbf")
arcpy.AddField_management(dbf_rekap, "Deskripsi", "TEXT")
arcpy.AddField_management(dbf_rekap, "Nilai", "DOUBLE")

cur = arcpy.UpdateCursor(dbf_rekap)
row = None
try:
    for row in cur:
        if row.Deskripsi == "Jumlah Bidang Tanah":
            cur.deleteRow(row)
        if row.Deskripsi == "Jumlah Bangunan":
            cur.deleteRow(row)
        if row.Deskripsi == "Nilai Bidang Tanah":
            cur.deleteRow(row)
        if row.Deskripsi == "Nilai Bangunan":
            cur.deleteRow(row)
        if row.Deskripsi == "Total Perkiraan Ganti Kerugian":
            cur.deleteRow(row)
    del cur

    cur = arcpy.InsertCursor(dbf_rekap)
    feat = cur.newRow()
    feat.Deskripsi = "Jumlah Bidang Tanah"
    feat.Nilai = Jumlah_Bidang
    cur.insertRow(feat)
    feat = cur.newRow()
    feat.Deskripsi = "Jumlah Bangunan"
    feat.Nilai = Jumlah_Bangun
    cur.insertRow(feat)
    feat = cur.newRow()
    feat.Deskripsi = "Nilai Bidang Tanah"
    feat.Nilai = Nilai_Bidang
    cur.insertRow(feat)
    feat = cur.newRow()
    feat.Deskripsi = "Nilai Bangunan"
    feat.Nilai = Nilai_Bangun
    cur.insertRow(feat)
    feat = cur.newRow()
    feat.Deskripsi = "Total Perkiraan Ganti Kerugian"
    feat.Nilai = Total_Ganti
    cur.insertRow(feat)
except:
    arcpy.AddMessage("Error 2...")
finally:
    del cur, row

# exp = "ganti_rugi(!Persen!, " + batas_bawah + ", " + batas_atas + ", !LuasKena!, !Predicted!, !Nilai_Bang!, !LuasBidang!)"
# code_block = """
# def ganti_rugi(b, bawah, atas, lkena, ntanah, nbangunan, ltanah):
#     if b <= bawah:
#         return (lkena * ntanah) + (b * nbangunan)
#     elif b > bawah and b <= atas:
#         return (lkena * ntanah) + nbangunan
#     elif b > atas:
#         return (ltanah * ntanah) + nbangunan"""
# arcpy.CalculateField_management(peta_terkena_pengadaan, u'TotalGanti', exp, "PYTHON", code_block)

if arcpy.Exists("Peta_Terkena_Pengadaan"):
    arcpy.Delete_management("Peta_Terkena_Pengadaan")
if arcpy.Exists("Tabel_Rekap"):
    arcpy.Delete_management("Tabel_Rekap")

arcpy.MakeFeatureLayer_management(peta_terkena_pengadaan, "Peta_Terkena_Pengadaan")
arcpy.SetParameterAsText(2, "Peta_Terkena_Pengadaan")
arcpy.MakeTableView_management(dbf_rekap, "Tabel_Rekap")
arcpy.SetParameterAsText(3, "Tabel_Rekap")

arcpy.AddMessage("== Proses selesai ==")
