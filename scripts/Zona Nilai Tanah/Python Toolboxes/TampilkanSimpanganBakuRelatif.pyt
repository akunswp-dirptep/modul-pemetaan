import arcpy, os, json, sys
from penilaiantanahutils.document import get_credentials as _get_creds_for_flag
from penilaiantanahutils import zonalayer

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Tampilkan Simpangan Baku Relatif"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Tampilkan_Simpangan_Baku_Relatif]


class Tampilkan_Simpangan_Baku_Relatif(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Simpangan Baku Relatif"
        self.description = ""
        self.canRunInBackground = False
        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        

    def getParameterInfo(self):
        """Define parameter definitions"""
        pilih_layer = arcpy.Parameter(
            displayName="Pilih Zona Layer",
            name="metode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        znt_layer = arcpy.Parameter(
            displayName="Zona Layer dengan Simpangan Baku Relatif",
            name="znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Tool ini menampilkan nilai Simpangan Baku Relatif\n"
            "pada zona layer.\n"
            "\n"
            "Aturan Nilai Simpangan Baku Relatif adalah:\n"
            "1. Nilai Simpangan Bakru Relatif tidak boleh\n"
            "   Lebih besar daripada 25%.\n"
            "2. Nilai Simpangan Baku Relatif tidak boleh\n"
            "   bernilai null.\n"
            "3. Zona dengan Nilai Simpangan Baku Relatif\n"
            "   bernilai null tidak akan ditampilkan.\n"
            "\n"
        )

        pilih_layer.filter.type = "ValueList"
        pilih_layer.filter.list = ["Utama", 'Preview']

        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))

        if self.operatorGIS:
            return [pilih_layer, znt_layer, penjelasan]
        else:
            return [penjelasan, znt_layer]


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        pilihan = parameters[0].valueAsText if self.operatorGIS else 'Utama'

        # ======================
        # PATH CONFIGURATION
        # ======================

        # Konfigurasi Path Aplikasi
        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
        ui_folder =  os.path.join(appdata, "ui")
        symbology_folder = os.path.join(ui_folder, "symbology")
        # Konfigurasi Path Project
        zl_path = zonalayer.is_zona_layer_comply()  # Memeriksa dan mendapatkan path Zona Layer
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Mendapatkan direktori workspace
        config_path = os.path.join(ws_dir, "config.json")  # Path file konfigurasi
        configs = None
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)  # Memuat konfigurasi dari file JSON


        # Mengambil nilai konfigurasi
        dataset_path = configs['dataset_path']  # Path dataset utama


        if pilihan == 'Utama':
            zl_path = os.path.join(dataset_path, "Zona_Layer")
            if not arcpy.Exists(zl_path):
                arcpy.AddError('Zona Layer tidak ditemukan')
                sys.exit(1)
            sim_path = os.path.join(symbology_folder, "Model_Pewarnaan_Simpangan_Baku_Relatif_ZNT.lyrx")

            arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
            arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
            arcpy.SetParameter(1, "Zona_Layer")

        elif pilihan == 'Preview':
            zl_path = os.path.join(dataset_path, "Zona_Layer_Preview")
            if not arcpy.Exists(zl_path):
                arcpy.AddError('Preview tidak ditemukan')
                sys.exit(1)
            sim_path = os.path.join(symbology_folder, "Model_Pewarnaan_Simpangan_Baku_Relatif_ZNT_Preview.lyrx")

            arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer_Preview")
            arcpy.management.ApplySymbologyFromLayer("Zona_Layer_Preview", sim_path)
            arcpy.SetParameter(1, "Zona_Layer_Preview")

        return
