from datetime import datetime
import sys
import uuid
import arcpy, os, json

from zntutils.constant import NAMA_PROVINSI, KAB_KOTA

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Workspace"
        self.alias = "toolbox_workspace"

        # List of tool classes associated with this toolbox
        self.tools = [Buat_Workspace]


class Buat_Workspace:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Buat Workspace"
        self.description = "Tool untuk menyimpan konfigurasi workspace"

    def getParameterInfo(self):
        """Define the tool parameters."""
        
        coordinate_system = arcpy.Parameter(
            displayName="Referensi Sistem Koordinat",
            name="coordinate_system",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        
        workspace_folder = arcpy.Parameter(
            displayName="Workspace",
            name="workspace_folder",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        provinsi = arcpy.Parameter(
            displayName="Provinsi",
            name="provinsi",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        provinsi.filter.type = "ValueList"
        provinsi.filter.list = NAMA_PROVINSI

        kab_kota = arcpy.Parameter(
            displayName="Kabupaten/Kota",
            name="kab_kota",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        tahun_penilaian = arcpy.Parameter(
            displayName="Tahun Penilaian",
            name="tahun_penilaian",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        tahun_penilaian.value = current_year()

        feature_layer = arcpy.Parameter(
            name="feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        return [coordinate_system, workspace_folder, provinsi, kab_kota, tahun_penilaian, feature_layer]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        prov = parameters[2].valueAsText  # parameter Provinsi
        kab = parameters[3]               # parameter Kab/Kota

        if prov:
            kab.filter.type = "ValueList"
            kab.filter.list = KAB_KOTA.get(prov, [])
        else:
            kab.filter.list = []


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """
        Fungsi ini digunakan untuk membuat sebuah workspace geodatabase baru untuk analisis zona nilai tanah.
        
        Kondisi yang harus dipenuhi:
        1. Terbentuk sebuah folder baru di lokasi yang dipilih yang didalamnya terdapat gedatabase dengan nama "ZoneNilaiTanah.gdb", config.json, dan dataset dengan nama "znt_ds".
        2. Sistem koordinat yang digunakan haruslah DGN_1995_Indonesia_TM-3_Zone_X (dimana X adalah zona koordinat yang sesuai dengan lokasi studi).
        3. Path workspace yang dipilih haruslah valid dan dapat diakses.
        4. Nama provinsi dan kabupaten/kota haruslah valid dan sesuai dengan daftar yang tersedia.
        """
        coord = parameters[0].valueAsText
        ws_path = parameters[1].valueAsText 
        WADMPR = parameters[2].valueAsText
        WADMKK = parameters[3].valueAsText
        THNNILAI = parameters[4].valueAsText

        gdbname = "ZoneNilaiTanah.gdb"

        local_conf_path = os.path.join(ws_path, "config.json")

        gdb_path = os.path.join(ws_path, gdbname)
        dataset_name = 'znt_ds'
        dataset_path = os.path.join(gdb_path, dataset_name)

        id = str(uuid.uuid4())

        # Koordinat harus TM-3
        if coord is None or 'DGN_1995_Indonesia_TM-3_Zone' not in coord.strip():
            arcpy.AddError( "Proyeksi Sistem Koordinat harus DGN_1995_Indonesia_TM-3 ")
            sys.exit(1)

        # Membuat data konfigurasi dalam format dictionary
        config_data = {
            "id": id,
            "ws_path": ws_path,
            "dataset_path": dataset_path,
            "WADMPR": WADMPR,
            "WADMKK": WADMKK,
            "THNNILAI": THNNILAI,
            "coord": coord,
            "gdb_path": gdb_path
        }

        with open(local_conf_path, 'w') as f:
            json.dump(config_data, f, indent=4)

        if arcpy.Exists(gdb_path):
            arcpy.management.Delete(gdb_path)

        arcpy.management.CreateFileGDB(ws_path, gdbname)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_name, coord)
        ds_path = os.path.join(gdb_path, dataset_name)
        layer_path = os.path.join(ds_path, "Zona_Layer")

        arcpy.management.CreateFeatureclass(
            out_path=ds_path,
            out_name="Zona_Layer",
            geometry_type="POLYGON",
            spatial_reference=coord

        )
        
        double_field = [
                        "NILAIZN",
                        "SMPBAKU",
                        "SMPBKREL" 
                    ]
        long_field = ["NILMIN",
                    "NILMAX",
                    "NOZONE"
                    ]
        text_field = ["WADMPR",
                    "WADMKK",
                    ]


        for field in double_field:
            arcpy.management.AddField(layer_path, field, "DOUBLE", field_is_nullable="NULLABLE")

        for field in long_field:
            arcpy.management.AddField(layer_path, field, "LONG", field_is_nullable="NULLABLE")

        for field in text_field:
            arcpy.management.AddField(layer_path, field, "TEXT", field_is_nullable="NULLABLE")

        arcpy.SetParameter(5, layer_path)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Import_Workspace:

    def __init__(self):

        self.label = "Import Workspace"
        self.description = "Tool untuk mengimpor workspace data ZNT."
    
    def getParameterInfo(self):
        return

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True
