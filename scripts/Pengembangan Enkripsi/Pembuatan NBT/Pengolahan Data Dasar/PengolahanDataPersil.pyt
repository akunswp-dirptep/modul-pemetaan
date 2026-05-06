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
gp_dir = os.path.dirname(parent_dir)
if gp_dir not in sys.path:
    sys.path.insert(0, gp_dir)

from nbtutils.constant import PROJECT_CONFIG_FILE_NAME
from nbtutils.persil import get_config_values


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tampilkan_Persil]


class Tampilkan_Persil(object):

    def __init__(self):
        self.label = "Load Persil"
        self.description = "Memuat layer persil ke ArcGIS Pro"
        self.canRunInBackground = False

    def getParameterInfo(self):

        out_layer = arcpy.Parameter(
            displayName="Output Layer Persil",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import arcpy

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        persil = configs["persil"]["persil"]["nama"]
        persil_path = configs["persil"]["persil"]["path"]

        # =========================
        # DELETE EXISTING LAYER
        # =========================
        if arcpy.Exists(persil):

            messages.addMessage(
                "Menghapus layer persil lama..."
            )

            arcpy.management.Delete(persil)

        # =========================
        # MAKE FEATURE LAYER
        # =========================
        messages.addMessage(
            "Memuat layer persil..."
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =========================
        # ADD TO CURRENT MAP
        # =========================
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(persil_path)

        # =========================
        # SET OUTPUT
        # =========================
        parameters[0].value = persil

        messages.addMessage(
            "== Menjalankan proses berhasil dilakukan. "
            "Silakan lanjutkan proses berikutnya... =="
        )

class Hitung_Luas_Persil(object):

    def __init__(self):
        self.label = "Hitung Luas Persil"
        self.description = "Menghitung luas bidang persil"
        self.canRunInBackground = False

    def getParameterInfo(self):

        out_layer = arcpy.Parameter(
            displayName="Output Layer Persil",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import arcpy

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        persil = configs["persil"]["persil"]["nama"]
        persil_path = configs["persil"]["persil"]["path"]

        # =========================
        # FIELD CHECK
        # =========================
        field_names = [
            field.name
            for field in arcpy.ListFields(persil_path)
        ]

        # =========================
        # ADD FIELD LUASBIDANG
        # =========================
        if 'LuasBidang' not in field_names:

            messages.addMessage(
                "Menambahkan field LuasBidang..."
            )

            arcpy.management.AddField(
                persil_path,
                'LuasBidang',
                "DOUBLE"
            )

        # =========================
        # DELETE OLD LAYER
        # =========================
        if arcpy.Exists(persil):

            messages.addMessage(
                "Menghapus layer persil lama..."
            )

            arcpy.management.Delete(persil)

        # =========================
        # MAKE FEATURE LAYER
        # =========================
        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =========================
        # ADD GEOMETRY ATTRIBUTE
        # =========================
        messages.addMessage(
            "Menghitung luas polygon..."
        )

        arcpy.management.AddGeometryAttributes(
            persil,
            "AREA",
            Area_Unit="SQUARE_METERS"
        )

        # =========================
        # CALCULATE LUASBIDANG
        # =========================
        arcpy.management.CalculateField(
            persil_path,
            'LuasBidang',
            '!POLY_AREA!',
            'PYTHON3'
        )

        # =========================
        # ADD FIELD LS_TNH
        # =========================
        if 'ls_tnh' not in field_names:

            messages.addMessage(
                "Menambahkan field ls_tnh..."
            )

            arcpy.management.AddField(
                persil_path,
                'ls_tnh',
                "DOUBLE"
            )

        # =========================
        # CALCULATE LS_TNH
        # =========================
        arcpy.management.CalculateField(
            persil_path,
            'ls_tnh',
            '!POLY_AREA!',
            'PYTHON3'
        )

        # =========================
        # DELETE TEMP FIELD
        # =========================
        temp_fields = [
            field.name
            for field in arcpy.ListFields(persil_path)
        ]

        if 'POLY_AREA' in temp_fields:

            messages.addMessage(
                "Menghapus field sementara POLY_AREA..."
            )

            arcpy.management.DeleteField(
                persil_path,
                'POLY_AREA'
            )

        # =========================
        # REFRESH LAYER
        # =========================
        if arcpy.Exists(persil):
            arcpy.management.Delete(persil)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =========================
        # ADD TO CURRENT MAP
        # =========================
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(persil_path)

        # =========================
        # SET OUTPUT
        # =========================
        parameters[0].value = persil

        messages.addMessage("== Proses selesai ==")

class Analisis_Bentuk_Persil(object):

    def __init__(self):
        self.label = "Analisis Bentuk Persil"
        self.description = "Menganalisis bentuk persil berdasarkan geometri bidang"
        self.canRunInBackground = False

    def getParameterInfo(self):

        out_layer = arcpy.Parameter(
            displayName="Output Persil",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import os
        import math
        import arcpy

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        dataset_path = configs["main"]["dataset"]

        persil = configs["persil"]["persil"]["nama"]
        persil_path = configs["persil"]["persil"]["path"]

        persil_split_path = configs["persil"]["persilsplit"]["path"]

        simbologi_path = configs["persil"]["simbologibentukpersil"]["path"]

        # =========================
        # TEMP DATASET
        # =========================
        persil_dissolve_bentuk = "PersilDissolveBentuk"
        persil_dissolve_bentuk_path = os.path.join(
            dataset_path,
            persil_dissolve_bentuk
        )

        persil_line = "PersilLine"
        persil_line_path = os.path.join(
            dataset_path,
            persil_line
        )

        persil_split = "PersilSplit"
        persil_split_path = os.path.join(
            dataset_path,
            persil_split
        )

        # =========================
        # DELETE OLD DATA
        # =========================
        delete_list = [
            persil_dissolve_bentuk,
            persil_dissolve_bentuk_path,
            persil_line_path,
            persil_split_path
        ]

        for item in delete_list:

            if arcpy.Exists(item):

                messages.addMessage(
                    "Menghapus data lama: {}".format(item)
                )

                arcpy.management.Delete(item)

        # =========================
        # POLYGON TO LINE
        # =========================
        messages.addMessage(
            "Mengubah polygon menjadi garis..."
        )

        arcpy.management.PolygonToLine(
            persil_path,
            persil_line_path,
            "IGNORE_NEIGHBORS"
        )

        # =========================
        # SPLIT LINE
        # =========================
        messages.addMessage(
            "Memotong garis persil..."
        )

        arcpy.management.SplitLine(
            persil_line_path,
            persil_split_path
        )

        # =========================
        # FIELD MANAGEMENT
        # =========================
        field_names = [
            field.name
            for field in arcpy.ListFields(persil_split_path)
        ]

        field_defs = [
            ("LebarSisi", "DOUBLE"),
            ("XStart", "DOUBLE"),
            ("XEnd", "DOUBLE"),
            ("YStart", "DOUBLE"),
            ("YEnd", "DOUBLE"),
            ("Azimuth", "DOUBLE"),
            ("ATrans", "DOUBLE")
        ]

        for field_name, field_type in field_defs:

            if field_name in field_names:
                arcpy.management.DeleteField(
                    persil_split_path,
                    field_name
                )

            arcpy.management.AddField(
                persil_split_path,
                field_name,
                field_type
            )

        # =========================
        # TEMP LAYER
        # =========================
        temp_layer = "tempe"

        if arcpy.Exists(temp_layer):
            arcpy.management.Delete(temp_layer)

        arcpy.management.MakeFeatureLayer(
            persil_split_path,
            temp_layer
        )

        # =========================
        # LENGTH ATTRIBUTE
        # =========================
        messages.addMessage(
            "Menghitung panjang sisi..."
        )

        arcpy.management.AddGeometryAttributes(
            temp_layer,
            "LENGTH",
            "METERS"
        )

        arcpy.management.CalculateField(
            persil_split_path,
            'LebarSisi',
            '!LENGTH!',
            'PYTHON3'
        )

        # =========================
        # CALCULATE AZIMUTH
        # =========================
        messages.addMessage(
            "Menghitung orientasi sisi bidang..."
        )

        desc = arcpy.Describe(persil_split_path)
        shapename = desc.ShapeFieldName

        with arcpy.da.UpdateCursor(
            persil_split_path,
            [
                shapename,
                "XStart",
                "XEnd",
                "YStart",
                "YEnd",
                "Azimuth",
                "ATrans"
            ]
        ) as cursor:

            for row in cursor:

                geom = row[0]

                x_start = geom.firstPoint.X
                x_end = geom.lastPoint.X
                y_start = geom.firstPoint.Y
                y_end = geom.lastPoint.Y

                row[1] = x_start
                row[2] = x_end
                row[3] = y_start
                row[4] = y_end

                # Hitung azimuth
                if (y_end - y_start) == 0:

                    if (x_end - x_start) >= 0:
                        azimuth = 90
                    else:
                        azimuth = -90

                else:

                    azimuth = math.atan(
                        (x_end - x_start) /
                        (y_end - y_start)
                    ) * (180 / math.pi)

                row[5] = azimuth

                # Transformasi sudut
                if azimuth < -45:
                    atrans = azimuth + 180

                elif -45 <= azimuth <= 45:
                    atrans = azimuth + 90

                else:
                    atrans = azimuth

                row[6] = atrans

                cursor.updateRow(row)

        # =========================
        # DISSOLVE
        # =========================
        messages.addMessage(
            "Melakukan dissolve bentuk bidang..."
        )

        arcpy.management.Dissolve(
            persil_split_path,
            persil_dissolve_bentuk_path,
            ["IdBidang"],
            [["ATrans", "RANGE"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        # =========================
        # FIELD CHECK PERSIL
        # =========================
        field_names = [
            field.name
            for field in arcpy.ListFields(persil_path)
        ]

        if 'bentuk' not in field_names:

            arcpy.management.AddField(
                persil_path,
                'bentuk',
                'TEXT'
            )

        if 's_bentuk' not in field_names:

            arcpy.management.AddField(
                persil_path,
                's_bentuk',
                'DOUBLE'
            )

        if 'RANGE_ATrans' in field_names:

            arcpy.management.DeleteField(
                persil_path,
                'RANGE_ATrans'
            )

        # =========================
        # JOIN FIELD
        # =========================
        messages.addMessage(
            "Menggabungkan hasil analisis..."
        )

        arcpy.management.JoinField(
            persil_path,
            'IdBidang',
            persil_dissolve_bentuk_path,
            'IdBidang',
            ['RANGE_ATrans']
        )

        # =========================
        # CALCULATE BENTUK
        # =========================
        exp = "trans(float(!RANGE_ATrans!))"

        code_block = """
def trans(trans):
    if trans < 16.3:
        return 'Segi Empat Beraturan'
    elif trans >= 16.3 and trans <= 58:
        return 'Segi Empat Tidak Beraturan'
    else:
        return 'Segi Banyak Tidak Beraturan'
"""

        arcpy.management.CalculateField(
            persil_path,
            'bentuk',
            exp,
            'PYTHON3',
            code_block
        )

        # =========================
        # CALCULATE SCORE
        # =========================
        exp = "skor(!bentuk!)"

        code_block = """
def skor(b):
    if b == 'Segi Empat Beraturan':
        return 4
    elif b == 'Segi Empat Tidak Beraturan':
        return 3
    else:
        return 1
"""

        arcpy.management.CalculateField(
            persil_path,
            's_bentuk',
            exp,
            'PYTHON3',
            code_block
        )

        # =========================
        # POINT COUNT
        # =========================
        arcpy.management.AddGeometryAttributes(
            persil_path,
            'POINT_COUNT'
        )

        with arcpy.da.UpdateCursor(
            persil_path,
            ['bentuk', 's_bentuk', 'PNT_COUNT']
        ) as cursor:

            for row in cursor:

                if int(row[2]) == 4:

                    row[0] = 'Segi Tiga'
                    row[1] = 2

                cursor.updateRow(row)

        # =========================
        # DELETE TEMP FIELD
        # =========================
        field_names = [
            field.name
            for field in arcpy.ListFields(persil_path)
        ]

        if 'PNT_COUNT' in field_names:

            arcpy.management.DeleteField(
                persil_path,
                'PNT_COUNT'
            )

        # =========================
        # REFRESH LAYER
        # =========================
        if arcpy.Exists(persil):

            arcpy.management.Delete(persil)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =========================
        # APPLY SYMBOLOGY
        # =========================
        arcpy.management.ApplySymbologyFromLayer(
            persil,
            simbologi_path
        )

        # =========================
        # ADD TO MAP
        # =========================
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(persil_path)

        # =========================
        # OUTPUT
        # =========================
        parameters[0].value = persil

        messages.addMessage("== Proses selesai ==")
class Set_Bentuk_Persil(object):

    def __init__(self):
        self.label = "Set Bentuk Persil"
        self.description = "Mengatur bentuk persil"
        self.canRunInBackground = False

    def getParameterInfo(self):

        bentuk = arcpy.Parameter(
            displayName="Bentuk Persil",
            name="bentuk",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        bentuk.filter.list = [
            "Segi Empat Beraturan",
            "Segi Empat Tidak Beraturan",
            "Segi Tiga",
            "Segi Banyak Tidak Beraturan"
        ]

        return [bentuk]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        bentuk = parameters[0].valueAsText

        mapping_bentuk = {
            "Segi Empat Beraturan": 4,
            "Segi Empat Tidak Beraturan": 3,
            "Segi Tiga": 2,
            "Segi Banyak Tidak Beraturan": 1
        }

        if bentuk not in mapping_bentuk:

            messages.addErrorMessage(
                "Bentuk tidak valid."
            )
            return

        skor_bentuk = mapping_bentuk[bentuk]

        configs = get_config_values()

        persil = configs["persil"]["persil"]["nama"]
        persil_path = configs["persil"]["persil"]["path"]

        # =========================
        # ADD REQUIRED FIELD
        # =========================
        field_names = [
            field.name.lower()
            for field in arcpy.ListFields(persil_path)
        ]

        if "bentuk" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "bentuk",
                "TEXT",
                field_length=50
            )

        if "s_bentuk" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "s_bentuk",
                "DOUBLE"
            )

        # =========================
        # CHECK SELECTION
        # =========================
        ada_seleksi = len(
            arcpy.Describe(persil).FIDSet
        )

        if ada_seleksi <= 0:

            messages.addWarningMessage(
                "Tidak ada persil yang dipilih."
            )
            return

        messages.addMessage(
            "Jumlah fitur terseleksi: {}".format(
                ada_seleksi
            )
        )

        # =========================
        # UPDATE
        # =========================
        messages.addMessage(
            "Mengubah bentuk persil menjadi {}...".format(
                bentuk
            )
        )

        with arcpy.da.UpdateCursor(
            persil,
            ["bentuk", "s_bentuk"]
        ) as cursor:

            for row in cursor:

                row[0] = bentuk
                row[1] = skor_bentuk

                cursor.updateRow(row)

        messages.addMessage(
            "Bentuk persil berhasil diperbarui."
        )
class Simbologi_Elevasi_Persil(object):

    def __init__(self):
        self.label = "Simbologi Elevasi Persil"
        self.description = "Menerapkan simbologi elevasi pada layer persil"
        self.canRunInBackground = False

    def getParameterInfo(self):

        out_layer = arcpy.Parameter(
            displayName="Output Layer Persil",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import arcpy

        messages.addMessage("== Proses dimulai ==")

        # =========================
        # CONFIG
        # =========================
        configs = get_config_values()

        persil = configs["persil"]["persil"]["nama"]
        persil_path = configs["persil"]["persil"]["path"]

        simbologi_path = configs["persil"]["simbologielevasipersil"]["path"]

        # =========================
        # DELETE OLD LAYER
        # =========================
        if arcpy.Exists(persil):

            messages.addMessage(
                "Menghapus layer persil lama..."
            )

            arcpy.management.Delete(persil)

        # =========================
        # CHECK FIELD
        # =========================
        field_names = [
            field.name
            for field in arcpy.ListFields(persil_path)
        ]

        if 'elvasi' not in field_names:

            messages.addMessage(
                "Menambahkan field elvasi..."
            )

            arcpy.management.AddField(
                persil_path,
                'elvasi',
                'TEXT'
            )

        if 's_elvasi' not in field_names:

            messages.addMessage(
                "Menambahkan field s_elvasi..."
            )

            arcpy.management.AddField(
                persil_path,
                's_elvasi',
                'DOUBLE'
            )

        # =========================
        # MAKE FEATURE LAYER
        # =========================
        messages.addMessage(
            "Membuat layer persil..."
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =========================
        # APPLY SYMBOLOGY
        # =========================
        messages.addMessage(
            "Menerapkan simbologi elevasi persil..."
        )

        arcpy.management.ApplySymbologyFromLayer(
            persil,
            simbologi_path
        )

        # =========================
        # ADD TO CURRENT MAP
        # =========================
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap

        current_map.addDataFromPath(persil_path)

        # =========================
        # SET OUTPUT
        # =========================
        parameters[0].value = persil

        messages.addMessage("== Proses selesai ==")

class Set_Elevasi_Persil(object):

    def __init__(self):
        self.label = "Set Elevasi Persil"
        self.description = "Mengatur elevasi persil"
        self.canRunInBackground = False

    def getParameterInfo(self):

        elevasi = arcpy.Parameter(
            displayName="Elevasi Persil",
            name="elevasi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        elevasi.filter.list = [
            "Lebih Rendah",
            "Sama",
            "Lebih Tinggi"
        ]

        return [elevasi]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        elevasi = parameters[0].valueAsText

        mapping_elevasi = {
            "Lebih Rendah": 3,
            "Sama": 2,
            "Lebih Tinggi": 1
        }

        if elevasi not in mapping_elevasi:

            messages.addErrorMessage(
                "Elevasi tidak valid."
            )
            return

        skor_elevasi = mapping_elevasi[elevasi]

        configs = get_config_values()

        persil = configs["persil"]["persil"]["nama"]
        persil_path = configs["persil"]["persil"]["path"]

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        simbologi_path = os.path.join(
            appdata,
            "SimbologiElevasiPersil.lyr"
        )

        # =========================
        # ADD REQUIRED FIELD
        # =========================
        field_names = [
            field.name.lower()
            for field in arcpy.ListFields(persil_path)
        ]

        if "elvasi" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "elvasi",
                "TEXT",
                field_length=50
            )

        if "s_elvasi" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "s_elvasi",
                "DOUBLE"
            )

        # =========================
        # CHECK SELECTION
        # =========================
        ada_seleksi = len(
            arcpy.Describe(persil).FIDSet
        )

        if ada_seleksi <= 0:

            messages.addWarningMessage(
                "Tidak ada persil yang dipilih."
            )
            return

        messages.addMessage(
            "Jumlah fitur terseleksi: {}".format(
                ada_seleksi
            )
        )

        # =========================
        # UPDATE
        # =========================
        with arcpy.da.UpdateCursor(
            persil,
            ["elvasi", "s_elvasi"]
        ) as cursor:

            for row in cursor:

                row[0] = elevasi
                row[1] = skor_elevasi

                cursor.updateRow(row)

        # =========================
        # APPLY SYMBOLOGY
        # =========================
        if arcpy.Exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                persil,
                simbologi_path
            )

        messages.addMessage(
            "Elevasi persil berhasil diperbarui."
        )