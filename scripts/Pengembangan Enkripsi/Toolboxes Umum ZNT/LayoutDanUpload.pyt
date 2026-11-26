import arcpy, requests, json, sys, os, datetime, tempfile, gc
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled" 
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.constant import PREFERRED_SERVER_KEY, PREFERRED_BERKAS_ID, CREDENTIAL_KEY, AUTH_KEY, PROJECT_CONFIG_FILE_NAME
from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils.system_utils import get_user_data, get_all_berkas_id, setup_user_data , clear_user_data, get_all_config
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
                      Tampilkan_Jenis_Penggunaan_Pada_Zona,
                      Tampilkan_Jenis_Penggunaan_Dengan_Transparansi_Pada_Zona,
                      Upload_Layout_Ke_Sipenta,
                      Tambah_Kotak_TTE,
                      Unduh_Data_Nearby]

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
            datatype="GPTopologyLayer", 
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
            "Aturan Topologi yang digunakan adalah:\n"
            "1. Zona tidak boleh memiliki celah (gap) antar zona.\n"
            "2. Zona tidak boleh tumpang tindih (overlap) antar zona.\n"
            "3. Zona dengan kesalahan topologi akan ditampilkan pada peta.\n"
            "\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )

        return [znt_layer, penjelasan]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        config_dan_paths = zonalayer.get_config_values()

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

        arcpy.SetParameter(0, topologi_path)
        
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
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementrian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
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
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementrian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)

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
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementrian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)


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
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementrian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)

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
        if not arcpy.Exists(ts_path) or not arcpy.Exists(tz_path):
            arcpy.AddError('layer titik sampel atau titik zona tidak ditemukan')
            sys.exit(1)
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
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementrian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)

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

class Tampilkan_Jenis_Penggunaan_Dengan_Transparansi_Pada_Zona(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Simbologi Mengecek Jenis Zona"
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
            "dengan transparansi pada zona layer.\n"
            "\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan\n"
            "Kementrian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)

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
        sim_path = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Dengan_Transparansi.lyrx")


        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.SetParameter(0, "Zona_Layer")


        return

class Upload_Layout_Ke_Sipenta(object):
    
    def __init__(self):
        self.label = "Upload Hasil Layout ke Sipenta"
        self.description = "Eksport layout dari ArcGIS Pro ke PDF dan otomatis kirim ke SIPENTA."
        self.canRunInBackground = False
        self.previous_berkas = None

    def getParameterInfo(self):
        berkas_list = get_all_berkas_id()
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ["Tidak ada berkas yang dapat dipilih"]
        else:
            berkas_show = ["Tidak ada berkas yang dapat dipilih"] 

        param_layout = arcpy.Parameter(
            displayName="Pilih Layout",
            name="layout_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            berkas.value = preferred_berkas   
        else:
            berkas.value = "Tidak ada berkas yang dapat dipilih"
        
        param_peta = arcpy.Parameter(

            displayName="Jenis Layout Peta",
            name="param_peta",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_peta.filter.type = "ValueList"
        # Set default awal saat pertama kali dibuka
        param_peta.filter.list = ["Pilih Berkas Terlebih Dahulu"]
        

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            f"Tahun: {datetime.datetime.now().year}\n"
        )
        
        return [param_layout, berkas, param_peta, penjelasan]

    def updateParameters(self, parameters):
        param_layout = parameters[0]
        berkas = parameters[1]
        param_peta = parameters[2]
        penjelasan = parameters[3]
        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            param_layout.enabled = False
            berkas.enabled = False
            param_peta.enabled = False
            penjelasan.enabled = True
            penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            f"Tahun: {datetime.datetime.now().year}\n"
        )
            return 
        else:
            penjelasan.value = (
                "Pastikan layout sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                f"Tahun: {datetime.datetime.now().year}\n"
            )

            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                layouts = [lyt.name for lyt in aprx.listLayouts()]
                param_layout.filter.type = "ValueList"
                
                if len(layouts) > 0:
                    param_layout.filter.list = layouts
                else:
                    param_layout.filter.list = ['Tidak ada Layout yang dapat dipilih']
            except Exception:
                param_layout.filter.type = "ValueList"
                param_layout.filter.list = ['Tidak ada Layout yang dapat dipilih']

            value = berkas.valueAsText

            if value and value != "Tidak ada berkas yang dapat dipilih" and value.strip() != "":
                
                kode = value[:2]
                mapping_data = {
                    "01": ["Peta Zona Awal Nilai Tanah", "Peta Sebaran Sampel", "Peta Simpangan Baku Relatif", "Peta Zona Nilai Tanah"],
                    "02": ["Peta Hasil Survei Batas Zona", "Peta Sebaran Sampel", "Peta Simpangan Baku Relatif", "Peta Zona Nilai Tanah"],
                    "03": ["Peta Sebaran Sampel", "Peta Nilai Bidang Tanah"],
                    "04": ["Peta Sebaran Sampel", "Peta Nilai Bidang Tanah"],
                }

                if kode in mapping_data:
                    param_peta.filter.list = mapping_data[kode]
                else:
                    param_peta.filter.list = ["Jenis peta tidak ditemukan"]

        return

    def updateMessages(self, parameters):
        # Jika nilai parameter layout adalah pesan kosong, cegah tool berjalan
        if parameters[0].valueAsText == 'Tidak ada Layout yang dapat dipilih':
            parameters[0].setErrorMessage("Harap buat layout terlebih dahulu di dalam project ini.")
        return
    
    def execute(self, parameters, messages):
        layout_name = parameters[0].valueAsText
        no_berkas = parameters[1].valueAsText
        param_peta = parameters[2].valueAsText
        
        berkas_list = get_all_berkas_id()
        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid.")
            return

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False

        user_data = get_user_data(CREDENTIAL_KEY)
        token = user_data.get(AUTH_KEY, None)

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        layout = aprx.listLayouts(layout_name)[0]
        nama_layout_template_item = "Template_Item"
        pagx_file_path = r"C:\PenilaianTanah\template\zona nilai tanah\Layout Standardisasi\6. Template Sistem\Template_Item.pagx"
        template_layouts = aprx.listLayouts(nama_layout_template_item)
        if not template_layouts:
            try:
                aprx.importDocument(pagx_file_path)
                arcpy.AddMessage(f"Layout '{nama_layout_template_item}' otomatis diimpor dari file .pagx.")
                template_layouts = aprx.listLayouts(nama_layout_template_item)
            except Exception as e:
                arcpy.AddError(f"{e}")
                return
            
        template_lyt = template_layouts[0]
        tte_template_items = template_lyt.listElements("TEXT_ELEMENT", "Template_TTE")
        blank_template_items = template_lyt.listElements("TEXT_ELEMENT", "Blank_TTE")
        if not tte_template_items:
            arcpy.AddError('Template TTE Tidak ditemukan')
            raise arcpy.ExecuteError

        tte_template_item = tte_template_items[0]
        blank_template_item = blank_template_items[0]

        cim_version = 'V3' if aprx.documentVersion.startswith('3') else 'V2'
        spesimen_tte = self.check_tte_box(layout_name)

        scratch_folder = arcpy.env.scratchFolder
        pdf_filename = f"{layout_name.replace(' ', '_')}.pdf"
        pdf_path = os.path.join(scratch_folder, pdf_filename)
        elements = layout.listElements("TEXT_ELEMENT", "TTE_*")

        for el in elements:
            cim_new = el.getDefinition(cim_version)
            cim_template = blank_template_item.getDefinition(cim_version)
            
            new_shape = cim_new.graphic.shape
            new_text = cim_new.graphic.text
            

            cim_new.graphic = cim_template.graphic
            
            cim_new.graphic.shape = new_shape
            cim_new.graphic.text = new_text
            
            el.setDefinition(cim_new)

        
        arcpy.AddMessage(f"Mengekspor layout '{layout_name}' ke format PDF...")
        layout.exportToPDF(pdf_path)
        arcpy.AddMessage(f"Export berhasil: {pdf_path}")
        elements_to_restore = layout.listElements("TEXT_ELEMENT", "TTE_*")
        for el in elements_to_restore:
            cim_new = el.getDefinition(cim_version)
            cim_template = tte_template_item.getDefinition(cim_version)
            
            new_shape = cim_new.graphic.shape
            new_text = cim_new.graphic.text
            

            cim_new.graphic = cim_template.graphic
            
            cim_new.graphic.shape = new_shape
            cim_new.graphic.text = new_text
            
            el.setDefinition(cim_new)

        kode = no_berkas[:2]
        kode_param = kode + '-' + param_peta

        mapping_param = {
            '01-Peta Zona Awal Nilai Tanah' : 'pembuatan_znt_peta_pdf_zona_awal_nilai_tanah',
            '01-Peta Sebaran Sampel' : 'pembuatan_znt_peta_pdf_sebaran_sampel',
            '01-Peta Simpangan Baku Relatif' : 'pembuatan_znt_peta_pdf_standar_deviasi',
            '01-Peta Zona Nilai Tanah' : 'pembuatan_znt_peta_pdf_znt',
            '02-Peta Hasil Survei Batas Zona' : 'pembaruan_znt_peta_hasil_survei_batas_zona_pdf',
            '02-Peta Sebaran Sampel' : 'pembaruan_znt_peta_sebaran_sampel_nilai_tanah',
            '02-Peta Simpangan Baku Relatif' : 'pembaruan_znt_peta_simpangan_baku_relatif',
            '02-Peta Zona Nilai Tanah' : 'pembaruan_znt_peta_zona_nilai_tanah',
            '03-Peta Sebaran Sampel' : 'pembuatan_nbt_peta_sebaran_sampel',
            '03-Peta Nilai Bidang Tanah' :  'pembuatan_nbt_peta_nilai_bidang_tanah',
            '04-Peta Sebaran Sampel' : 'pembaruan_nbt_peta_sebaran_sampel',
            '04-Peta Nilai Bidang Tanah' : 'pembaruan_nbt_peta_nilai_bidang_tanah'
        }

        param_upload = mapping_param[kode_param]
        if not param_upload:
            arcpy.AddError(f"Mapping parameter untuk {kode_param} tidak ditemukan.")
            return
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/upload/layout"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/upload/layout"
        url = prod_url if use_production else test_url

        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        payload_data = {
            "no_berkas": no_berkas,
            "param": param_upload,
            'spesimen': str(spesimen_tte).replace("'", '"')
        }

        arcpy.AddMessage("Mengirim file PDF ke API SIPENTA...")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (pdf_filename, f, 'application/pdf')}
                response = requests.post(url, headers=headers, data=payload_data, files=files) 

            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    arcpy.AddMessage(f"SUKSES: {res_json.get('message', 'File berhasil diunggah!')}")
                else:
                    arcpy.AddError(f"GAGAL DARI SERVER: {response.text}")

            elif response.status_code == 403:
                try:
                    error_json = response.json()
                    message = error_json.get("message", "")
                except ValueError:
                    message = ""
                    
                if "expired" in message.lower():
                    clear_user_data() 
                    arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
                elif "Berkas tidak bisa di upload pada tahapan ini" in message:
                    arcpy.AddError("Data tidak dapat diupload karena posisi berkas di SIPENTA sudah bergeser atau tidak berada pada tahap tempat data seharusnya diunggah.")
                else:
                    error_message = message if message else "Periksa hak akses atau token."
                    arcpy.AddError(f"Akses ditolak (403). Pesan: {error_message}")

            else:
                arcpy.AddError(f"HTTP ERROR {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Gagal menghubungi server API: {str(e)}")
        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan sistem: {str(e)}")
        return

    def check_tte_box(self, layout_name):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        layout = aprx.listLayouts(layout_name)[0] 

        spesimen_list = []
        urutan = 1

        layout_width = layout.pageWidth
        layout_height = layout.pageHeight
        
        if layout_width > layout_height:
            a0_width_pt = 3370.39
            a0_height_pt = 2383.94
        else:
            a0_width_pt = 2383.94
            a0_height_pt = 3370.39

        scale_x = a0_width_pt / layout_width
        scale_y = a0_height_pt / layout_height

        elements = layout.listElements("TEXT_ELEMENT", "TTE_*")
        for el in elements:
            try:
                id_spesimen = int(el.name.split("_")[1])
                role = el.name.split("_")[2]
                
                # 1. Catat koordinat dan ukuran aslinya terlebih dahulu agar spesimen_list tidak berubah
                x_scaled = el.elementPositionX * scale_x
                y_scaled = el.elementPositionY * scale_y
                width_scaled = el.elementWidth * scale_x
                height_scaled = el.elementHeight * scale_y
                
                y_scaled = a0_height_pt - y_scaled - height_scaled + height_scaled
                
                spesimen = {
                    "id_spesimen": id_spesimen,
                    "urutan": 1 if role == 'pembuat' else 2,
                    "position": {
                        "x": round(x_scaled, 2),
                        "y": round(y_scaled, 2),
                        "width": round(width_scaled, 2),
                        "height": round(height_scaled, 2) 
                    }
                }
                spesimen_list.append(spesimen)
                urutan += 1

            except (IndexError, ValueError):
                continue

        return spesimen_list
    
class Tambah_Kotak_TTE(object):
   
    def __init__(self):
        self.label = "Tambah Kotak TTE"
        self.description = "Membuat kotak placeholder TTE di Layout aktif"
        self.canRunInBackground = False

    def getParameterInfo(self):
        berkas_list = get_all_berkas_id()
        berkas_show = []
        
        if berkas_list:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ["Tidak ada berkas yang dapat dipilih"]
        else:
            berkas_show = ["Tidak ada berkas yang dapat dipilih"] 

        param_layout = arcpy.Parameter(
            displayName="Pilih Layout",
            name="layout_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
            
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            param_layout.filter.list = [lyt.name for lyt in aprx.listLayouts()]
        except Exception:
            param_layout.filter.list = []

        param_berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_berkas.filter.type = "ValueList"
        param_berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            param_berkas.value = preferred_berkas   
        else:
            param_berkas.value = "Tidak ada berkas yang dapat dipilih"

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            f"Tahun: {datetime.datetime.now().year}\n"
        )
        return [param_layout, param_berkas, penjelasan]
    
    def updateParameters(self, parameters):
        param_layout = parameters[0]
        berkas = parameters[1]
        penjelasan = parameters[2]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            param_layout.enabled = False
            berkas.enabled = False
            penjelasan.enabled = False
            return 
        else:
            penjelasan.value = (
                "Pastikan spesimen TTE sudah ditambahkan di SIPENTA.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                f"Tahun: {datetime.datetime.now().year}\n"
            )
            
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                layouts = [lyt.name for lyt in aprx.listLayouts()]
                param_layout.filter.type = "ValueList"
                
                if len(layouts) > 0:
                    param_layout.filter.list = layouts
                else:
                    param_layout.filter.list = ['Tidak ada Layout yang dapat dipilih']
            except Exception:
                param_layout.filter.type = "ValueList"
                param_layout.filter.list = ['Tidak ada Layout yang dapat dipilih']
        return
    
    def updateMessages(self, parameters):
        if parameters[0].valueAsText == 'Tidak ada Layout yang dapat dipilih':
            parameters[0].setErrorMessage("Harap buat layout terlebih dahulu di dalam project ini.")
        return
    
    def execute(self, parameters, messages):
        layout_name = parameters[0].valueAsText
        berkas = parameters[1].valueAsText

        list_ttd = []
        try:
            user_data = get_user_data(CREDENTIAL_KEY)
            token = user_data.get(AUTH_KEY, None) if user_data else None
            server = get_user_data(PREFERRED_SERVER_KEY)
            use_production = True if server == "Produksi" or server is None else False
                        
            if token:
                api_data = self.call_tte_api(token, berkas, use_production)
                            
                if api_data and "data" in api_data:
                    unique_ttd = {}
                    for f in api_data["data"]:
                        nama = f.get("nama")
                        if nama not in unique_ttd:
                            unique_ttd[nama] = f
                    
                    if unique_ttd:
                        list_ttd = list(unique_ttd.values())
                    else:
                        arcpy.AddError('Tidak ditemukan spesimen tandatangan untuk berkas yang dipilih')
                        raise arcpy.ExecuteError
                else:
                    arcpy.AddError('Data API tidak valid atau tidak menemukan spesimen.')
                    raise arcpy.ExecuteError
        except Exception as e:
            arcpy.AddError(f'Terdapat kendala: {str(e)}')
            raise arcpy.ExecuteError

        # Hapus kotak TTE yang lama
        self.hapus_elemen_tte(layout_name)
        
        # Ambil Layout aktif
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        lyt = aprx.listLayouts(layout_name)[0]
        
        # Cari elemen teks "TTD 1" dan "TTD 2" di layout
        ttd1_els = lyt.listElements("TEXT_ELEMENT", "TTD 1")
        ttd2_els = lyt.listElements("TEXT_ELEMENT", "TTD 2")
        
        ttd1_el = ttd1_els[0] if ttd1_els else None
        ttd2_el = ttd2_els[0] if ttd2_els else None

        for data_tte in list_ttd:
            role = str(data_tte.get('sebagai', '')).lower()
            jabatan = data_tte.get('jabatan', 'Tanpa Jabatan')
            nama = data_tte.get('nama', 'Tanpa Nama')
            nip = data_tte.get('nip', '0')
            
            # Jika rolenya mengandung kata 'pemebuat' dan kotak TTD 1 ditemukan
            if 'pembuat' in role and ttd1_el:
                teks_ttd1 = f"UNTUK PEMBUATANNYA,\n{jabatan.upper()}\n\n\n\n\n\n\n{nama}\nNIP {nip}"
                ttd1_el.text = teks_ttd1
                
                # Buat kotak TTE tepat di posisi TTD 1
                self.create_tte_text_box_at_position(data_tte, ttd1_el, layout_name)
                
            # Jika rolenya mengandung kata 'pemanfaat' dan kotak TTD 2 ditemukan
            elif 'pemanfaat' in role and ttd2_el:
                kab_kota = self.get_kab_kota()
                teks_ttd2 = f"{kab_kota},\nUNTUK PEMANFAATANNYA,\n{jabatan.upper()}\n\n\n\n\n\n\n{nama}\nNIP. {nip}"
                ttd2_el.text = teks_ttd2
                
                # Buat kotak TTE tepat di posisi TTD 2
                self.create_tte_text_box_at_position(data_tte, ttd2_el, layout_name)
            else:
                arcpy.AddWarning(f"Role '{role}' tidak cocok dengan 'pembuat' atau 'pemanfaat', atau elemen teks TTD 1/TTD 2 tidak ditemukan di layout[cite: 1].")
                
        return

    def create_tte_text_box_at_position(self, data_tte, target_text_el, layout_name):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        lyt = aprx.listLayouts(layout_name)[0]
        nama_layout_template_item = "Template_Item"
        pagx_file_path = r"C:\PenilaianTanah\template\zona nilai tanah\Layout Standardisasi\6. Template Sistem\Template_Item.pagx"
        
        template_layouts = aprx.listLayouts(nama_layout_template_item)
        if not template_layouts:
            try:
                aprx.importDocument(pagx_file_path)
                arcpy.AddMessage(f"Layout '{nama_layout_template_item}' otomatis diimpor dari file .pagx.")
                template_layouts = aprx.listLayouts(nama_layout_template_item)
            except Exception as e:
                arcpy.AddError(f"{e}")
                raise arcpy.ExecuteError
                
        template_lyt = template_layouts[0]
        tte_template_items = template_lyt.listElements("TEXT_ELEMENT", "Template_TTE")
        if not tte_template_items:
            arcpy.AddError('Template TTE Tidak ditemukan')
            raise arcpy.ExecuteError

        tte_template_item = tte_template_items[0]
        cim_version = 'V3' if aprx.documentVersion.startswith('3') else 'V2'

        # Menentukan posisi berdasarkan elemen teks TTD
        width, height = 6.9, 2.3
        x_base = target_text_el.elementPositionX
        y_base = target_text_el.elementPositionY
        
        # Menyejajarkan posisi X dengan teks TTD
        x_initial = x_base - 3.75
        y_initial = y_base + 1.0 

        arr = arcpy.Array([
            arcpy.Point(x_initial, y_initial),
            arcpy.Point(x_initial, y_initial + height),
            arcpy.Point(x_initial + width, y_initial + height),
            arcpy.Point(x_initial + width, y_initial),
            arcpy.Point(x_initial, y_initial),
        ])
        polygon_geom = arcpy.Polygon(arr)
        
        id_spesimen = data_tte.get('id_spesimen', '0')
        nama = data_tte.get('nama', 'Tanpa Nama')
        jabatan = data_tte.get('jabatan', 'Tanpa Jabatan')
        role = str(data_tte.get('sebagai', '')).lower()
        
        element_name = f"TTE_{id_spesimen}_{role}"
        display_text = f"[Placeholder TTE]\n\n{jabatan}\n"
        
        try:
            new_text_el = aprx.createTextElement(lyt, polygon_geom, 'POLYGON', display_text, name=element_name)
            
            cim_new = new_text_el.getDefinition(cim_version)
            cim_template = tte_template_item.getDefinition(cim_version)
            
            new_shape = cim_new.graphic.shape
            new_text = cim_new.graphic.text
            
            cim_new.graphic = cim_template.graphic
            cim_new.graphic.shape = new_shape
            cim_new.graphic.text = new_text
            
            new_text_el.setDefinition(cim_new)
            arcpy.AddMessage(f"Berhasil! Kotak TTE untuk {nama} ditambahkan pada posisinya.")
            
        except AttributeError as e:
            arcpy.AddError(f"Detail Error : {str(e)}")
            raise arcpy.ExecuteError
            
        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat membuat kotak: {str(e)}")
            raise arcpy.ExecuteError
            
    def call_tte_api(self, token, nomor_berkas, use_production=True):

        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/spesimen?no_berkas={nomor_berkas}"
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/spesimen?no_berkas={nomor_berkas}"
    
        url = prod_url if use_production else test_url

        try:
            # Mengambil data dari API
            arcpy.AddMessage("Mengambil data Spesimen TTE...")
            headers = {
                    "Authorization": f"Bearer {token}"
                }
            response = requests.get(url, headers=headers, timeout=60)  
            response.raise_for_status()
            
            data = response.json()
            if not data:
                arcpy.AddError('Server Tidak mengirimkan Apapun')
                raise arcpy.ExecuteError

            return data
            
        except requests.exceptions.HTTPError as e:
            response = e.response
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                message = ""

            if response.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                raise Exception("Token Anda kadaluarsa, silakan login ulang.")
            
            if response.status_code == 404 and message:
                arcpy.AddError(message)
                raise arcpy.ExecuteError

            elif response.status_code == 403:
                raise Exception("Akses ditolak (403). Periksa hak akses atau token.")
            else:
                raise Exception(f"HTTP Error: {e}")
        
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "NameResolutionError" in error_msg or "getaddrinfo failed" in error_msg or "Max retries exceeded" in error_msg:
                raise Exception("Koneksi terputus, silakan cek jaringan internet Anda dan coba lagi.")
            else:
                raise Exception(f"Error koneksi ke server: {error_msg}")
                
        except json.JSONDecodeError as e:
            raise Exception(f"Error ketika mengubah respon API ke JSON: {str(e)}")

    def hapus_elemen_tte(self, layout_name):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        lyt = aprx.listLayouts(layout_name)[0]
        semua_elemen = lyt.listElements()
        jumlah_dihapus = 0
        
        for el in semua_elemen:

            if el.name and "TTE_" in el.name:
                try:

                    if hasattr(lyt, 'deleteElement'):
                        lyt.deleteElement(el)
                    elif hasattr(el, 'delete'):
                        el.delete()
                    else:
                        el.visible = False
                        el.elementPositionX = -9999
                        el.elementPositionY = -9999
                    
                    jumlah_dihapus += 1
                    arcpy.AddMessage(f"Elemen '{el.name}' berhasil dihilangkan.")
                    
                except Exception as e:
                    arcpy.AddWarning(f"Gagal memproses elemen {el.name}: {str(e)}")
                    
        return jumlah_dihapus

    def get_kab_kota(self):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap
        
        zona_layers = []
        for layer in active_map.listLayers():
            if layer.name == 'Zona_Layer':
                zona_layers.append(layer)
        
        if len(zona_layers) == 0:
            arcpy.AddMessage('Tidak ditemukan Kab/Kota valid')
            return 'KAB/KOTA'
        elif len(zona_layers) > 1:
            arcpy.AddMessage('Tidak ditemukan Kab/Kota valid')
            return 'KAB/KOTA'
        else:
            zona_layer = zona_layers[0]
            if not arcpy.Exists(zona_layer):
                arcpy.AddMessage('Tidak ditemukan Kab/Kota valid')
                return 'KAB/KOTA'
            
            try:
                if hasattr(zona_layer, 'dataSource'):
                    layer_path = zona_layer.dataSource
                    ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(layer_path)))  
                    new_config_path = os.path.join(ws_dir, PROJECT_CONFIG_FILE_NAME)  
                    configs = None
                    if arcpy.Exists(new_config_path):
                        configs = get_all_config(new_config_path)  

                    # Validasi path GDB
                    if configs['ws_path'] != ws_dir:
                        arcpy.AddMessage('Tidak ditemukan Kab/Kota valid')
                        return 'KAB/KOTA'

                    kota =  configs.get('WADMKK')
                    return kota
                else:
                    arcpy.AddMessage('Tidak ditemukan Kab/Kota valid')
                    return 'KAB/KOTA'
                    
            except Exception as e:
                arcpy.AddMessage('Tidak ditemukan Kab/Kota valid')
                return 'KAB/KOTA'

class Unduh_Data_Nearby(object):
    def __init__(self):
        self.label = "Unduh Data Nearby"
        self.description = (
            "Tool untuk mengunduh data pemetaan nearby (Data Terkini & Data Lampau) "
            "dari server Sipenta berdasarkan Nomor Berkas dan menyimpannya ke dalam "
            "Geodatabase Zona Layer (ZoneNilaiTanah.gdb)."
        )
        self.canRunInBackground = True

    def getParameterInfo(self):
        berkas_list = get_all_berkas_id()
        berkas_show = [f"{b[0]}" for b in berkas_list] if berkas_list else []
        if not berkas_show:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        # Parameter 0: Nomor Berkas
        nomor_berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="nomor_berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        nomor_berkas.filter.type = "ValueList"
        nomor_berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            nomor_berkas.value = preferred_berkas if preferred_berkas in berkas_show else berkas_show[0]
        else:
            nomor_berkas.value = 'Tidak ada berkas yang dapat dipilih'

        # Parameter 1: Target Feature Dataset
        target_dataset = arcpy.Parameter(
            displayName="Target Feature Dataset",
            name="target_dataset",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Input"
        )
        default_ds = self._detect_active_znt_dataset()
        if default_ds and arcpy.Exists(default_ds):
            target_dataset.value = default_ds

        # Parameter 2: Output Feature Class (Derived)
        output_nearby_fcs = arcpy.Parameter(
            displayName="Feature Class Hasil Nearby",
            name="output_nearby_fcs",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
            multiValue=True
        )

        # Parameter 3: Penjelasan / Informasi Tools
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = self._get_info_text(is_logged_in=False)

        return [nomor_berkas, target_dataset, output_nearby_fcs, penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        nomor_berkas = parameters[0]
        target_dataset = parameters[1]
        penjelasan = parameters[3]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            nomor_berkas.enabled = False
            target_dataset.enabled = False
            penjelasan.enabled = True
            penjelasan.value = self._get_info_text(is_logged_in=False)
        else:
            nomor_berkas.enabled = True
            target_dataset.enabled = True
            penjelasan.enabled = True
            penjelasan.value = self._get_info_text(is_logged_in=True)

            if not target_dataset.valueAsText:
                default_ds = self._detect_active_znt_dataset()
                if default_ds and arcpy.Exists(default_ds):
                    target_dataset.value = default_ds

    def updateMessages(self, parameters):
        nomor_berkas = parameters[0]
        target_dataset = parameters[1]

        if nomor_berkas.valueAsText == 'Tidak ada berkas yang dapat dipilih':
            nomor_berkas.setErrorMessage(
                "Tidak ada nomor berkas yang tersedia. Silakan periksa akun atau sinkronisasi berkas Anda."
            )

        if target_dataset.valueAsText:
            ds_path = target_dataset.valueAsText
            if "zonenilaitanah.gdb" not in ds_path.lower() and not ds_path.lower().endswith(".gdb"):
                target_dataset.setWarningMessage(
                    "Disarankan memilih Feature Dataset 'znt_ds' di dalam ZoneNilaiTanah.gdb."
                )

    def execute(self, parameters, messages):
        nomor_berkas = parameters[0].valueAsText
        target_dataset = parameters[1].valueAsText

        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        token = user_data.get(AUTH_KEY, None)
        if not token:
            arcpy.AddError("Token autentikasi tidak ditemukan. Silakan login ulang.")
            return

        if not nomor_berkas or nomor_berkas == 'Tidak ada berkas yang dapat dipilih':
            arcpy.AddError("Nomor berkas tidak valid.")
            return

        if not arcpy.Exists(target_dataset):
            arcpy.AddError(f"Target Feature Dataset tidak ditemukan: {target_dataset}")
            return

        used_names = self._get_existing_fc_names(target_dataset)

        arcpy.AddMessage(f"Memulai proses unduh data nearby untuk Nomor Berkas: {nomor_berkas}")
        arcpy.AddMessage(f"Lokasi penyimpanan: {target_dataset}")

        nearby_fc_paths = self._fetch_and_convert_nearby(
            no_berkas=nomor_berkas,
            token=token,
            output_dataset=target_dataset,
            used_names=used_names
        )

        gc.collect()
        try:
            arcpy.management.ClearWorkspaceCache()
        except Exception:
            pass

        if nearby_fc_paths:
            arcpy.AddMessage(f"Berhasil menyimpan {len(nearby_fc_paths)} layer ke GDB Zona Layer:")
            for fc in nearby_fc_paths:
                arcpy.AddMessage(f"  - {fc}")

            self._add_layers_safely_to_map(nearby_fc_paths)
            arcpy.SetParameter(2, nearby_fc_paths)
            arcpy.AddMessage("Proses selesai. Silakan centang layer pada panel Contents untuk menampilkannya.")
        else:
            arcpy.AddWarning("Tidak ada layer nearby yang berhasil diunduh atau dikonversi.")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _add_layers_safely_to_map(self, fc_paths):
        """Menambahkan layer ke peta aktif dalam kondisi uncheck (visible=False) agar ringan."""
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap
            if active_map is None:
                return

            for fc_path in fc_paths:
                fc_name = os.path.basename(fc_path)
                for existing_lyr in active_map.listLayers(fc_name):
                    active_map.removeLayer(existing_lyr)

                lyr = active_map.addDataFromPath(fc_path)
                if lyr is not None:
                    lyr.visible = False
        except Exception as e:
            arcpy.AddWarning(f"Layer tersimpan di GDB, namun gagal ditambahkan otomatis ke TOC: {e}")

    def _get_info_text(self, is_logged_in=False):
        status_msg = (
            "FUNGSI TOOLS:\n"
            "Mengunduh data pemetaan sekitar (Nearby) dari server Sipenta "
            "berdasarkan Nomor Berkas yang dipilih, lalu menyimpannya ke dalam "
            "Feature Dataset GDB Zona Layer (ZoneNilaiTanah.gdb\\znt_ds):\n"
            "1. Nearby_Data_Terkini (data berkas terkini)\n"
            "2. Nearby_Data_Lampau (data historis/dashboard)\n"
        )
        if not is_logged_in:
            header = "⚠️ Login terlebih dahulu untuk mengakses fitur ini.\n\n"
        else:
            header = "✅ Siap digunakan. Pilih Nomor Berkas dan pastikan Target GDB mengarah ke znt_ds.\n\n"

        footer = (
            "\nDirektorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            f"Tahun: {datetime.datetime.now().year}"
        )
        return header + status_msg + footer

    def _get_pemetaan_base_url(self):
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server in ["Produksi", None] else False
        if use_production:
            return "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan"
        return "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan"

    def _detect_active_znt_dataset(self):
        """Mencoba mendeteksi path ZoneNilaiTanah.gdb\\znt_ds dari project ArcGIS Pro yang sedang terbuka."""
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            candidate_folders = [aprx.homeFolder] + [
                fc.get("connectionString") for fc in aprx.folderConnections if fc.get("connectionString")
            ]
            for folder in candidate_folders:
                if not folder or not os.path.exists(folder):
                    continue
                config_file = os.path.join(folder, PROJECT_CONFIG_FILE_NAME)
                if os.path.exists(config_file):
                    cfg = get_all_config(config_file)
                    if isinstance(cfg, dict) and cfg.get("dataset_path"):
                        if arcpy.Exists(cfg["dataset_path"]):
                            return cfg["dataset_path"]

                ds_candidate = os.path.join(folder, "ZoneNilaiTanah.gdb", "znt_ds")
                if arcpy.Exists(ds_candidate):
                    return ds_candidate
        except Exception:
            pass
        return None

    def _get_existing_fc_names(self, target_dataset):
        """Mengambil semua nama Feature Class di dalam GDB induk agar nama baru tidak bentrok."""
        used = set()
        try:
            desc = arcpy.Describe(target_dataset)
            gdb_path = os.path.dirname(target_dataset) if desc.dataType == "FeatureDataset" else target_dataset

            arcpy.env.workspace = gdb_path
            for fc in arcpy.ListFeatureClasses() or []:
                used.add(fc.lower())
            for ds in arcpy.ListDatasets("", "Feature") or []:
                for fc in arcpy.ListFeatureClasses("", "", ds) or []:
                    used.add(fc.lower())
        except Exception:
            pass
        return used

    def _fetch_and_convert_nearby(self, no_berkas, token, output_dataset, used_names):
        arcpy.AddMessage(
            f"Mengambil data nearby untuk nomor berkas '{no_berkas}' "
            f"(mohon tunggu, ukuran data bisa cukup besar)..."
        )

        api_url = f"{self._get_pemetaan_base_url()}/nearby"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        params = {"no_berkas": no_berkas}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=(30, 300))
            response.raise_for_status()

            raw_text = response.text.strip()
            if not raw_text:
                arcpy.AddWarning(
                    f"Server mengembalikan respons kosong (HTTP {response.status_code}) "
                    f"dari URL: {response.url}"
                )
                return []

            try:
                json_data = response.json()
            except ValueError:
                preview = raw_text[:300].replace("\n", " ")
                arcpy.AddWarning(
                    f"Respons server bukan JSON yang valid (HTTP {response.status_code}). "
                    f"URL: {response.url} | Isi respons: {preview}"
                )
                return []

            if not json_data.get("success"):
                msg = json_data.get("message", "Gagal mengambil data nearby dari server.")
                arcpy.AddWarning(f"Data nearby untuk berkas '{no_berkas}' gagal diambil: {msg}")
                return []

            nearby_data = json_data.get("data") or {}
            geojson_berkas = nearby_data.get("geojson_berkas") or nearby_data.get("berkas")
            geojson_dashboard = nearby_data.get("geojson_dashboard") or nearby_data.get("dashboard")

            nearby_fc_paths = []

            if geojson_berkas:
                nearby_fc_paths.extend(
                    self._convert_geojson_to_fc(
                        geojson_data=geojson_berkas,
                        base_label="Nearby_Data_Terkini",
                        output_dataset=output_dataset,
                        used_names=used_names,
                        fallback_index=1,
                        log_title=f"Nearby Berkas ({no_berkas})"
                    )
                )
            else:
                arcpy.AddWarning(f"Tidak ditemukan geojson_berkas pada data nearby '{no_berkas}'.")

            if geojson_dashboard:
                nearby_fc_paths.extend(
                    self._convert_geojson_to_fc(
                        geojson_data=geojson_dashboard,
                        base_label="Nearby_Data_Lampau",
                        output_dataset=output_dataset,
                        used_names=used_names,
                        fallback_index=2,
                        log_title=f"Nearby Dashboard ({no_berkas})"
                    )
                )
            else:
                arcpy.AddWarning(f"Tidak ditemukan geojson_dashboard pada data nearby '{no_berkas}'.")

            return nearby_fc_paths

        except requests.exceptions.HTTPError as e:
            resp = e.response
            message = ""
            try:
                message = resp.json().get("message", "")
            except Exception:
                message = resp.text[:200] if resp is not None else ""
            status_code = resp.status_code if resp is not None else "Unknown"
            if status_code == 403 and "expired" in message.lower():
                clear_user_data()
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            else:
                arcpy.AddWarning(
                    f"Gagal mengambil data nearby untuk berkas '{no_berkas}' "
                    f"(HTTP {status_code}): {message or str(e)}"
                )
            return []
        except Exception as e:
            arcpy.AddWarning(
                f"Terjadi kesalahan saat mengunduh/mengonversi data nearby '{no_berkas}': {str(e)}"
            )
            return []

    def _convert_geojson_to_fc(
        self,
        geojson_data,
        base_label,
        output_dataset,
        used_names,
        fallback_index=1,
        log_title=""
    ):
        created_fcs = []
        if isinstance(geojson_data, str):
            try:
                geojson_obj = json.loads(geojson_data)
            except json.JSONDecodeError:
                arcpy.AddWarning(f"[{log_title}] Format GeoJSON tidak valid.")
                return []
        elif isinstance(geojson_data, dict):
            geojson_obj = geojson_data
        else:
            arcpy.AddWarning(f"[{log_title}] Tipe data GeoJSON tidak dikenali.")
            return []

        features = geojson_obj.get("features", [])
        if not features:
            arcpy.AddWarning(f"[{log_title}] Data GeoJSON kosong (0 fitur).")
            return []

        grouped_features = {}
        for feat in features:
            geom = feat.get("geometry") or {}
            gtype = geom.get("type", "Unknown")
            if gtype in ("Polygon", "MultiPolygon"):
                key = "Polygon"
            elif gtype in ("Point", "MultiPoint"):
                key = "Point"
            elif gtype in ("LineString", "MultiLineString"):
                key = "Polyline"
            else:
                continue
            grouped_features.setdefault(key, []).append(feat)

        if not grouped_features:
            arcpy.AddWarning(f"[{log_title}] Tidak ada fitur dengan geometri valid.")
            return []

        target_sr = None
        try:
            target_sr = arcpy.Describe(output_dataset).spatialReference
        except Exception:
            pass

        multi_geom = len(grouped_features) > 1

        for geom_type, feats in grouped_features.items():
            fc_base = f"{base_label}_{geom_type}" if multi_geom else base_label
            fc_name = self._generate_unique_fc_name(fc_base, used_names, fallback_index)
            out_fc_path = os.path.join(output_dataset, fc_name)

            temp_geojson = None
            try:
                sub_geojson = {
                    "type": "FeatureCollection",
                    "features": feats
                }
                if "crs" in geojson_obj:
                    sub_geojson["crs"] = geojson_obj["crs"]

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".geojson", delete=False, encoding="utf-8"
                ) as tmp:
                    json.dump(sub_geojson, tmp)
                    temp_geojson = tmp.name

                del sub_geojson

                arcpy.AddMessage(f"[{log_title}] Mengonversi {len(feats)} fitur ({geom_type}) -> {fc_name}...")

                with arcpy.EnvManager(outputCoordinateSystem=target_sr):
                    arcpy.conversion.JSONToFeatures(
                        in_json_file=temp_geojson,
                        out_features=out_fc_path,
                        geometry_type=geom_type.upper()
                    )

                try:
                    arcpy.management.AddSpatialIndex(out_fc_path)
                except Exception:
                    pass

                used_names.add(fc_name.lower())
                created_fcs.append(out_fc_path)

            except Exception as e:
                arcpy.AddWarning(f"[{log_title}] Gagal mengonversi {fc_name}: {str(e)}")
            finally:
                if temp_geojson and os.path.exists(temp_geojson):
                    try:
                        os.remove(temp_geojson)
                    except Exception:
                        pass

        del geojson_obj, features, grouped_features
        gc.collect()

        return created_fcs

    def _generate_unique_fc_name(self, base_name, used_names, fallback_index=1):
        """Menghasilkan nama Feature Class yang valid di GDB dan tidak bentrok dengan yang sudah ada."""
        clean_name = arcpy.ValidateTableName(base_name)
        if clean_name.lower() not in used_names:
            return clean_name

        counter = fallback_index
        while True:
            candidate = f"{clean_name}_{counter}"
            if candidate.lower() not in used_names:
                return candidate
            counter += 1