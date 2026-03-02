import arcpy, requests, json, sys, os, re
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled" 
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document



class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Cek_Topologi,
                      Tampilkan_Simbologi_Pembagian_Kelas, 
                      Tampilkan_Simpangan_Baku_Relatif,
                      Tampilkan_Sebaran_Titik_Sampel,
                      Tampilkan_Sebaran_Titik_Sampel_Dan_Titik_Zona,
                      Tampilkan_Jenis_Penggunaan_Pada_Zona]

class Cek_Topologi(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Cek Topologi Zona Layer"
        self.description = ""
        self.canRunInBackground = False

        
    def getParameterInfo(self):
        """Define parameter definitions"""
       
        znt_layer = arcpy.Parameter(
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
            "Tool ini mengecek topologi pada zona layer.\n"

        )

        return [znt_layer, penjelasan]


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

        config_dan_paths =zonalayer.get_config_values()

        # Mengambil nilai konfigurasi
        dataset_path = config_dan_paths['dataset_path']  # Path dataset utama
        lay_main = os.path.join(dataset_path, "Zona_Layer")
        topo_name = 'Zona_Layer_Topology'
        topologi_path = os.path.join(dataset_path, topo_name)

        if arcpy.Exists(topologi_path):
            arcpy.management.Delete(topologi_path)
        arcpy.management.CreateTopology(dataset_path, topo_name)
        arcpy.management.AddFeatureClassToTopology(topologi_path, lay_main, 1, 1)
        arcpy.management.AddRuleToTopology(topologi_path, "Must Not Have Gaps (Area)", lay_main)
        arcpy.management.AddRuleToTopology(topologi_path, "Must Not Overlap (Area)", lay_main)
        arcpy.management.ValidateTopology(topologi_path)
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        current_map = aprx.activeMap
        current_map.addDataFromPath(topologi_path)
        return



class Tampilkan_Simbologi_Pembagian_Kelas(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Simbologi Pembagian Kelas"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        pilih_metode = arcpy.Parameter(
            displayName="Pilih Metode Klasifikasi",
            name="metode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pilih_metode.filter.type = "ValueList"
        pilih_metode.filter.list = ["Natural Breaks", "Kuantil", "Equal Interval"]
        
        znt_layer = arcpy.Parameter(
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
            "Tool ini menampilkan pembagian kelas\n"
            "pada zona layer.\n"
            "\n"
        ) 
        return [pilih_metode, znt_layer, penjelasan]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        metode = parameters[0].valueAsText

        config_dan_paths = zonalayer.get_config_values()
        zl_path = os.path.join(config_dan_paths["dataset_path"], "Zona_Layer")
        quantile_sim_path = os.path.join(config_dan_paths["symbology_folder"], "Model_Pewarnaan_ZNT_8_Kelas_Rapermen.lyrx")
        nb_sim_path = os.path.join(config_dan_paths["symbology_folder"], "Simbologi_Natural_Breaks.lyrx")
        equal_interval_sim_path = os.path.join(config_dan_paths["symbology_folder"], "Simbologi_Equal_Interval.lyrx")

        if metode == "Natural Breaks":
            sim_path = nb_sim_path
        elif metode == "Kuantil":
            sim_path = quantile_sim_path
        elif metode == "Equal Interval":
            sim_path = equal_interval_sim_path

        arcpy.AddMessage(f"Metode klasifikasi yang dipilih: {metode}")
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.SetParameter(1, "Zona_Layer")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Tampilkan_Simpangan_Baku_Relatif(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Simpangan Baku Relatif"
        self.description = ""
        self.canRunInBackground = False

        

    def getParameterInfo(self):
        """Define parameter definitions"""
       
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


        return [znt_layer, penjelasan]


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

        config_dan_paths =zonalayer.get_config_values()


        # Mengambil nilai konfigurasi
        dataset_path = config_dan_paths['dataset_path']  # Path dataset utama



        zl_path = os.path.join(dataset_path, "Zona_Layer")
        if not arcpy.Exists(zl_path):
            arcpy.AddError('Zona Layer tidak ditemukan')
            sys.exit(1)

        symbology_folder = config_dan_paths['symbology_folder']
        sim_path = os.path.join(symbology_folder, "Model_Pewarnaan_Simpangan_Baku_Relatif_ZNT.lyrx")
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.SetParameter(0, "Zona_Layer")

        return

class Tampilkan_Sebaran_Titik_Sampel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Sebaran Titik Sampel"
        self.description = ""
        self.canRunInBackground = False

        
    def getParameterInfo(self):
        """Define parameter definitions"""
       
        znt_layer = arcpy.Parameter(
            name="znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        ts_layer = arcpy.Parameter(
            name="ts_layer",
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
            "Tool ini menampilkan sebaran titik sampel\n"
            "pada zona layer.\n"
            "\n"

        )

        return [znt_layer, ts_layer, penjelasan]


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

        config_dan_paths =zonalayer.get_config_values()


        # Mengambil nilai konfigurasi
        dataset_path = config_dan_paths['dataset_path']  # Path dataset utama
        symbology_folder = config_dan_paths['symbology_folder']
        zl_path = os.path.join(dataset_path, "Zona_Layer")
        ts_path = os.path.join(dataset_path, "Titik_Sampel")

        sim_path_zl = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Pada_Zona.lyrx")
        sim_path_ts = os.path.join(symbology_folder, "Simbologi_Persebaran_Titik_Sampel.lyrx")


        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path_zl)
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", sim_path_ts)
        arcpy.SetParameter(0, "Zona_Layer")
        arcpy.SetParameter(1, "Titik_Sampel")

        return

class Tampilkan_Sebaran_Titik_Sampel_Dan_Titik_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Sebaran Titik Sampel dan Titik Zona"
        self.description = ""
        self.canRunInBackground = False

        
    def getParameterInfo(self):
        """Define parameter definitions"""
       
        znt_layer = arcpy.Parameter(
            name="znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        ts_layer = arcpy.Parameter(
            name="ts_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        tz_layer = arcpy.Parameter(
            name="tz_layer",
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
            "Tool ini menampilkan sebaran titik sampel\n"
            "pada zona layer.\n"
            "\n"

        )

        return [znt_layer, ts_layer, tz_layer, penjelasan]


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

        config_dan_paths =zonalayer.get_config_values()


        # Mengambil nilai konfigurasi
        dataset_path = config_dan_paths['dataset_path']  # Path dataset utama
        symbology_folder = config_dan_paths['symbology_folder']
        zl_path = os.path.join(dataset_path, "Zona_Layer")
        ts_path = os.path.join(dataset_path, "Titik_Sampel")
        tz_path = os.path.join(dataset_path, "Titik_Zona")
        sim_path_zl = os.path.join(symbology_folder, "Simbologi_Peruntukan_Zona_Layer.lyrx")
        sim_path_ts = os.path.join(symbology_folder, "Simbologi_Persebaran_Titik_Sampel.lyrx")
        sim_path_tz = os.path.join(symbology_folder, "Simbologi_Persebaran_Titik_Zona.lyrx")

        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
        arcpy.management.MakeFeatureLayer(tz_path, "Titik_Zona")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path_zl)
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", sim_path_ts)
        arcpy.management.ApplySymbologyFromLayer("Titik_Zona", sim_path_tz)
        arcpy.SetParameter(0, "Zona_Layer")
        arcpy.SetParameter(1, "Titik_Sampel")
        arcpy.SetParameter(2, "Titik_Zona")
        return

class Tampilkan_Jenis_Penggunaan_Pada_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Jenis Penggunaan pada Zona"
        self.description = ""
        self.canRunInBackground = False

        
    def getParameterInfo(self):
        """Define parameter definitions"""
       
        znt_layer = arcpy.Parameter(
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
            "Tool ini menampilkan jenis penggunaan\n"
            "pada zona layer.\n"
            "\n"

        )

        return [znt_layer, penjelasan]


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

        config_dan_paths =zonalayer.get_config_values()


        # Mengambil nilai konfigurasi
        dataset_path = config_dan_paths['dataset_path']  # Path dataset utama
        symbology_folder = config_dan_paths['symbology_folder']
        zl_path = os.path.join(dataset_path, "Zona_Layer")

        zl_path = os.path.join(dataset_path, "Zona_Layer")
        sim_path = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Pada_Zona.lyrx")


        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.SetParameter(0, "Zona_Layer")


        return

