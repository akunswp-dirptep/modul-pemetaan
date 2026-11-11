import os
import math
import errno
import arcpy
from datetime import datetime
import sys
import json

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils.constant import PROJECT_CONFIG_FILE_NAME
from nbtutils.persil import get_config_values

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Persiapan Data"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Buat_Workspace, 
                      Deklarasi_Variabel]
        
class Buat_Workspace(object):
    def __init__(self):
        self.label = "Buat Workspace NBT"
        self.description = "Membuat geodatabase dan menyiapkan data persil"

    def getParameterInfo(self):

        ws_path = arcpy.Parameter(
            displayName="Workspace Output",
            name="ws_path",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )

        persil_asal_path = arcpy.Parameter(
            displayName="Feature Class Persil",
            name="persil_asal_path",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )
        persil_asal_path.filter.list = ["Polygon"]

        sisijalan_asal_path = arcpy.Parameter(
            displayName="Feature Class Sisi Jalan",
            name="sisijalan_asal_path",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input"
        )
        sisijalan_asal_path.filter.list = ["Polyline"]

        return [ws_path, persil_asal_path, sisijalan_asal_path]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        if parameters[2].valueAsText:
            desc = arcpy.Describe(parameters[2].valueAsText)
            if desc.shapeType != "Polyline":
                parameters[2].setErrorMessage(
                    "Input Sisi Jalan harus berupa feature class Polyline."
                )

    def execute(self, parameters, messages):

        # Kondisi yang harus dipenuhi
        # 1. Ambil input dari user/tool ArcGIS
        # 2. Bersihkan dan buat ulang file konfigurasi
        # 3. Menentukan seluruh struktur nama dataset
        # 4. Menulis file konfigurasi
        # 5. Menyalin data input ke geodatabase
        # 6. Menyiapkan field-field pada layer persil
        # 7. Mengubah polygon persil jadi garis
        # 8. Menghitung panjang tiap sisi
        # 9. Membuat titik centroid dan midpoint
        # 10. Menghitung koordinat tiap midpoint

        # Kondisi 1: Ambil input dari user/tool ArcGIS
        ws_path = parameters[0].valueAsText
        persil_asal_path = parameters[1].valueAsText
        sisijalan_asal_path = parameters[2].valueAsText


        arcpy.AddMessage("Setup File Config")

        # Kondisi 2: Bersihkan dan buat ulang file konfigurasi
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


        # Kondisi 3: Menentukan seluruh struktur nama dataset
        gdbname = "NilaiBidangTanah.gdb"
        dataset = "nbt_ds"
        dataset_fasilitas = "fasilitas"
        dataset_resiko = "resiko"

        gdbtemplate = "ds_znt_template"
        utils_folder = os.path.join(appdata, 'nbtutils')
        gdbtemplate_path = os.path.join(utils_folder, "template.gdb", gdbtemplate)

        tbl = "template_var"
        tbltemplate_path = os.path.join(utils_folder, "template.gdb", tbl)

        temporary = "temporary.gdb"
        temporary_path = os.path.join(utils_folder, temporary)

        sisijalan = "SisiJalan"
        jaringanjalan = "Jaringan_Jalan"
        midpoint_jaringanjalan = "MidpointJaringanJalan"
        simbologi_lebarjalan = "SimbologiLebarJalan"
        simbologi_kelasjalan = "SimbologiKelasJalan"

        kelas_jalan = [
            {"label": "Lokal Setapak", "value": 1},
            {"label": "Lokal Sekunder", "value": 2},
            {"label": "Lokal Primer", "value": 3},
            {"label": "Kolektor Sekunder", "value": 4},
            {"label": "Kolektor Primer", "value": 5},
            {"label": "Arteri Sekunder", "value": 6},
            {"label": "Arteri Primer", "value": 7}
        ]
        topologi_sisijalan = "TopologiSisiJalan"
        topologi_jaringanjalan = "TopologiJaringanJalan"

        nd = "JaringanJalan_ND"
        jaringanjalannd = "JaringanJalanForND"

        persil = "Persil"
        persil_line = "PersilLine"
        persil_split = "PersilSplit"
        persil_centroid = "PersilCentroid"
        persil_split_midpoint = "PersilMidpoint"

        persil_zonasi = [
            {"label": "Pertanian", "value": 1},
            {"label": "Industri", "value": 2},
            {"label": "Perkampungan", "value": 3},
            {"label": "Perumahan Sederhana", "value": 4},
            {"label": "Perumahan Menengah", "value": 5},
            {"label": "Perumahan Mewah", "value": 6},
            {"label": "Komersil", "value": 7}
        ]

        persil_bentuk = [
            {"label": "Segi Banyak Tidak Beraturan", "value": 1},
            {"label": "Segitiga", "value": 2},
            {"label": "Segi Empat Tidak Beraturan", "value": 3},
            {"label": "Segi Empat Beraturan", "value": 4}
        ]

        persil_letak = [
            {"label": "Lain-lain", "value": 1},
            {"label": "Normal", "value": 2},
            {"label": "Tusuk sate", "value": 3},
            {"label": "Hook", "value": 4}
        ]

        # ==================================================
        # PATH
        # ==================================================
        gdb_path = os.path.join(ws_path, gdbname)
        dataset_path = os.path.join(gdb_path, dataset)
        conf_path = os.path.join(gdb_path, "config.json")

        if os.path.exists(conf_path):
            os.remove(conf_path)

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

        variabel_prediksi = [
                {
                    "variabel_id": "lb_dpn",
                    "variabel_nama": "Lebar depan"
                },
                {
                    "variabel_id": "bentuk",
                    "variabel_nama": "Bentuk"
                },
                {
                    "variabel_id": "lb_jln",
                    "variabel_nama": "Lebar jalan"
                },
                {
                    "variabel_id": "kls_jln",
                    "variabel_nama": "Kelas Jalan"
                },
                {
                    "variabel_id": "jk_atrp",
                    "variabel_nama": "Jarak ke Arteri Primer"
                },
                {
                    "variabel_id": "jk_atrs",
                    "variabel_nama": "Jarak ke Arteri Sekunder"
                },
                {
                    "variabel_id": "jk_kolp",
                    "variabel_nama": "Jarak ke Kolektor Primer"
                },
                {
                    "variabel_id": "jk_kols",
                    "variabel_nama": "Jarak ke Kolektor Sekunder"
                },
                {
                    "variabel_id": "letak",
                    "variabel_nama": "Letak Tanah"
                },
                {
                    "variabel_id": "zonasi",
                    "variabel_nama": "Zonasi"
                },
                {
                    "variabel_id": "ls_tnh",
                    "variabel_nama": "Luas Tanah"
                },
                {
                    "variabel_id": "min_lb_jln",
                    "variabel_nama": "Minimal Lebar Jalan"
                }
            ]

        # kondisi 4: Menulis file konfigurasi
        config = {
            "main": {
                "ws": ws_path,
                "conf": conf_path,
                "gdb": gdb_path,
                "dataset": dataset_path
            },
            "jalan": {
                "dataset": dataset_path,
                "sisijalan": {
                    "nama": sisijalan,
                    "path": sisijalan_path
                },
                "jaringanjalan": {
                    "nama": jaringanjalan,
                    "path": jaringanjalan_path
                },
                "midpointjaringanjalan": {
                    "nama": midpoint_jaringanjalan,
                    "path": midpoint_jaringanjalan_path
                },
                "simbologikelasjalan": {
                    "nama": simbologi_kelasjalan,
                    "path": simbologi_kelasjalan_path
                },
                "simbologilebarjalan": {
                    "nama": simbologi_lebarjalan,
                    "path": simbologi_lebarjalan_path
                },
                "kelasjalan": kelas_jalan,
                "topologi_sisijalan": {
                    "nama": topologi_sisijalan,
                    "path": topologi_sisijalan_path
                },
                "topologi_jaringanjalan": {
                    "nama": topologi_jaringanjalan,
                    "path": topologi_jaringanjalan_path
                },
                "template": gdbtemplate_path,
                "table_template": tbltemplate_path,
                "temporary": temporary_path,
                "nd": {
                    "nama": nd,
                    "path": nd_path
                },
                "jaringanjalannd": {
                    "nama": jaringanjalannd,
                    "path": jaringanjalannd_path
                }
            },
            "persil": {
                "dataset": dataset_path,
                "persil": {
                    "nama": persil,
                    "path": persil_path
                },
                "persilline": {
                    "nama": persil_line,
                    "path": persil_line_path
                },
                "persilsplit": {
                    "nama": persil_split,
                    "path": persil_split_path
                },
                "persilcentroid": {
                    "nama": persil_centroid,
                    "path": persil_centroid_path
                },
                "persilmidpoint": {
                    "nama": persil_split_midpoint,
                    "path": persil_split_midpoint_path
                },
                "zonasi": persil_zonasi,
                "bentuk": persil_bentuk,
                "letak": persil_letak
            },
            "fasilitas": {
                "datasetfasilitas": dataset_fasilitas_path
            },
            "resiko": {
                "datasetresiko": dataset_resiko_path
            },
            'variabel': variabel_prediksi
        }

        with open(conf_path, "w+") as f:
            json.dump(config, f, indent=4)

        # Kondisi 5: Menyalin data input ke geodatabase

        if arcpy.Exists(gdb_path):
            arcpy.management.Delete(gdb_path)

        arcpy.management.CreateFileGDB(ws_path, gdbname)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset, persil_asal_path)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_fasilitas, persil_asal_path)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_resiko, persil_asal_path)

        arcpy.AddMessage("Menyiapkan Dataset")

        if sisijalan_asal_path:
            arcpy.conversion.FeatureClassToFeatureClass(
                sisijalan_asal_path,
                dataset_path,
                sisijalan
            )

        arcpy.conversion.FeatureClassToFeatureClass(
            persil_asal_path,
            dataset_path,
            persil
        )

        arcpy.AddMessage("== Sesuaikan proyeksi pada network dataset ==")

        sr = arcpy.Describe(persil_asal_path).spatialReference

        arcpy.management.Project(
            gdbtemplate_path,
            os.path.join(gdb_path, gdbtemplate),
            sr
        )

        # 6. Menyiapkan Field-Field Pada Layer Persil

        field_names = [field.name for field in arcpy.ListFields(persil_path)]

        for fld in ['NEAR_DIST', 'NEAR_FID', 'NEAR_X', 'NEAR_Y']:
            if fld in field_names:
                arcpy.DeleteField_management(persil_path, fld)

        field_defs = [
            ('IdBidang', 'LONG'),
            ('ls_tnh', 'DOUBLE'),
            ('lb_dpn', 'DOUBLE'),
            ('bentuk', 'TEXT'),
            ('s_bentuk', 'DOUBLE'),
            ('zonasi', 'TEXT'),
            ('s_zonasi', 'DOUBLE'),
            ('letak', 'TEXT'),
            ('s_letak', 'DOUBLE'),
            ('elevasi', 'TEXT'),
            ('s_elevasi', 'DOUBLE'),
            ('min_lb_jln', 'DOUBLE')
        ]

        for fname, ftype in field_defs:
            if fname not in field_names:
                arcpy.management.AddField(persil_path, fname, ftype)

        arcpy.management.CalculateField(persil_path, 'IdBidang', '!OBJECTID!', 'PYTHON')

        arcpy.management.MakeFeatureLayer(persil_path, "tempo")
        arcpy.management.AddGeometryAttributes("tempo", "AREA", "", "SQUARE_METERS")
        arcpy.management.CalculateField(persil_path, 'ls_tnh', '!POLY_AREA!', 'PYTHON')
        arcpy.management.CalculateField(persil_path, 'elevasi', "'Sama'", "PYTHON")
        arcpy.management.CalculateField(persil_path, 's_elevasi', "2", "PYTHON")
        
        # Kondisi 7 : Mengubah polygon persil jadi garis
        arcpy.management.PolygonToLine(persil_path, persil_line_path, "IGNORE_NEIGHBORS")
        arcpy.management.SplitLine(persil_line_path, persil_split_path)

        # Kondisi 8: Menghitung panjang tiap sisi

        field_names = [field.name for field in arcpy.ListFields(persil_split_path)]
        if 'LebarSisi' not in field_names:
            arcpy.management.AddField(persil_split_path, 'LebarSisi', "DOUBLE")


        if arcpy.Exists("tempo"):
            arcpy.management.Delete("tempo")
        arcpy.management.MakeFeatureLayer(persil_split_path, "tempo")

        arcpy.management.AddGeometryAttributes("tempo", "LENGTH", "METERS", "")
        arcpy.management.CalculateField(persil_split_path, 'LebarSisi', "!LENGTH!", "PYTHON")

        fields_to_add = ['XStart', 'XEnd',  'YStart', 'YEnd', 'Azimuth', 'ATrans']
        for field in fields_to_add:
            arcpy.management.AddField(persil_split_path, field, "DOUBLE")
            
        # Kondisi 9: Membuat titik centroid dan midpoint
        arcpy.management.FeatureToPoint(persil_path, persil_centroid_path, "INSIDE")
        arcpy.management.FeatureToPoint(persil_split_path, persil_split_midpoint_path, "INSIDE")

        # Kondisi 10: Menghitung koordinat tiap midpoint
        field_names = [field.name for field in arcpy.ListFields(persil_split_midpoint_path)]
        if 'X' not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path, 'X', "DOUBLE")

        exp = "!Shape.firstpoint.x!"
        code_block = """def get(b):
            return b.split(' ')[0]"""
        arcpy.management.CalculateField(persil_split_midpoint_path, "X", exp, "PYTHON")

        if 'Y' not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path, 'Y', "DOUBLE")

        exp = "!Shape.firstpoint.y!"
        code_block = """def get(b):
            return b.split(' ')[1]"""
        arcpy.management.CalculateField(persil_split_midpoint_path, "Y", exp, "PYTHON")

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


        arcpy.AddMessage("== Proses selesai ==")

    def postExecute(self, parameters):
        return

class Deklarasi_Variabel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Deklarasi Variabel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        daftar_variabel = arcpy.Parameter(
            displayName='Daftar Variabel Prediksi',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input')
        daftar_variabel.columns = [['GPString', 'Variabel'], ['GPString', 'Akronim']]
        params = [daftar_variabel]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed.
        Variabel-variabel yang tidak boleh dihapus:
        (Luas Tanah, Lebar Depan, Lebar Jalan, Kelas Jalan, Jarak ke Kelas Jalan, Bentuk Bidang, Letak Bidang, Zonasi)"""
        if parameters[0].altered:
            allval = parameters[0].valueAsText
            splitval = []
            if ";" in allval:
                splitval = allval.split(";")
            else:
                splitval.append(allval)
            valcek_1 = self.mySplitString(splitval[(len(splitval) - 1)])[0]
            valcek_2 = self.mySplitString(splitval[(len(splitval) - 1)])[1]
            i = 0
            statusSama = 0
            skorSama = 0
            vtab = arcpy.ValueTable(2)
            for a in splitval:
                tmp = self.mySplitString(a)
                nm = tmp[0]
                akr = tmp[1]
                if valcek_1 == nm:
                    statusSama = statusSama + 1
                if valcek_2 == akr:
                    skorSama = skorSama + 1
                if statusSama == 2 or skorSama == 2:
                    break
                if " " in nm:
                    nm = "'" + nm + "'"
                vtab.addRow("{0} {1}".format(str(nm), str(akr)))
                i = i + 1
            parameters[0].value = vtab.exportToString()
        else:
            appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            nbtfolder = os.path.join(appdata, 'nbtutils')
            conf_var_path = os.path.join(nbtfolder, "def_var.dat")
            conf_file = open(conf_var_path, "r")
            list_config = conf_file.readlines()
            conf_file.close()
            for line in list_config:
                line = line.replace("\n", "")
                parameters[0].value = line
        return

    def mySplitString(self, somestring):
        hasil = []
        lenstr = len(somestring)
        kutipcounter = 0
        myword = ""
        i=0
        for a in somestring:
            i = i + 1
            if a == "'":
                kutipcounter = kutipcounter + 1
            if kutipcounter == 1:
                if a != "'":
                    myword = myword + a
            elif kutipcounter == 2:
                kutipcounter = 0
            else:
                if a == " ":
                    hasil.append(myword)
                    myword = ""
                else:
                    myword = myword + a
                    if i == lenstr:
                        hasil.append(myword)
        return hasil

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        variabel_prediksi = parameters[0].valueAsText
        if "#" in variabel_prediksi:
            messages.addErrorMessage("== Nilai-nilai parameter tidak boleh kosong ==")
            raise arcpy.ExecuteError
            # sys.exit(1)
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        nbtfolder = os.path.join(appdata, 'nbtutils')
        messages.AddMessage("== Proses Dimulai ==")
        conf_path = os.path.join(nbtfolder, "def_var.dat")
        if not os.path.exists(os.path.dirname(conf_path)):
            try:
                os.makedirs(os.path.dirname(conf_path))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        if os.path.exists(conf_path):
            os.remove(conf_path)
        conf_file = open(conf_path, "w")
        conf_file.write(variabel_prediksi)
        conf_file.close()
        messages.AddMessage(appdata)
        messages.AddMessage("== Proses Selesai ==")
        return

