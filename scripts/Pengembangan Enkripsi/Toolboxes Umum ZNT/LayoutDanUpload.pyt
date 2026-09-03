import arcpy, requests, json, sys, os, datetime
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled" 
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.constant import PREFERRED_SERVER_KEY, PREFERRED_BERKAS_ID, CREDENTIAL_KEY, AUTH_KEY
from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils.system_utils import get_user_data, get_all_berkas_id, setup_user_data 
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
                      Upload_Layout_Ke_Sipenta]

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
            "Aturan Topologi yang digunakan adalah:\n"
            "1. Zona tidak boleh memiliki celah (gap) antar zona.\n"
            "2. Zona tidak boleh tumpang tindih (overlap) antar zona.\n"
            "3. Zona dengan kesalahan topologi akan ditampilkan pada peta.\n"
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

    def getParameterInfo(self):
        # Dropdown list Layout dari Project Aktif
        berkas_list = get_all_berkas_id()
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih'] 

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
            direction="Input")

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            berkas.value = preferred_berkas   
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        
        # Dropdown Parameter Peta
        param_peta = arcpy.Parameter(
            displayName="Parameter Peta",
            name="param_peta",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        
        # Daftar parameter sesuai request
        param_peta.filter.type = "ValueList"
        param_peta.filter.list = [
            'pembuatan_znt_peta_pdf_zona_awal_nilai_tanah',
            'pembuatan_znt_peta_pdf_sebaran_sampel',
            'pembuatan_znt_peta_pdf_standar_deviasi',
            'pembuatan_znt_peta_pdf_znt',
            'pembaruan_znt_peta_hasil_survei_batas_zona_pdf',
            'pembaruan_znt_peta_sebaran_sampel_nilai_tanah',
            'pembaruan_znt_peta_simpangan_baku_relatif',
            'pembaruan_znt_peta_zona_nilai_tanah',
            'pembuatan_nbt_peta_sebaran_sampel',
            'pembuatan_nbt_peta_nilai_bidang_tanah',
            'pembaruan_nbt_peta_sebaran_sampel',
            'pembaruan_nbt_peta_nilai_bidang_tanah'
        ]

        return [param_layout, berkas, param_peta]

    def updateParameters(self, parameters):
        # Otomatis mengambil daftar layout dari project ArcGIS Pro yang sedang dibuka
        if not parameters[0].altered:
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                layouts = [lyt.name for lyt in aprx.listLayouts()]
                parameters[0].filter.type = "ValueList"
                parameters[0].filter.list = layouts
            except Exception:
                pass

        if parameters[1].altered:
            value = parameters[1].valueAsText
            kode = value[:2]
            mapping_data = {
                '01': [
                    'Peta Zona Awal Nilai Tanah',
                    'Peta Sebaran Sampel',
                    'Peta Simpangan Baku Relatif',
                    'Peta Zona Nilai Tanah'
                ],
                '02': [
                    'Peta Hasil Survei Batas Zona',
                    'Peta Sebaran Sampel',
                    'Peta Simpangan Baku Relatif',
                    'Peta Zona Nilai Tanah'
                ],
                '03': [
                    'Peta Sebaran Sampel',
                    'Peta Nilai Bidang Tanah'
                ],
                
                '04': [
                    'Peta Sebaran Sampel',
                    'Peta Nilai Bidang Tanah'
                ]
            }
            list_param = mapping_data[kode]
            parameters[2].filter.list = list_param
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        layout_name = parameters[0].valueAsText
        no_berkas = parameters[1].valueAsText
        param_peta = parameters[2].valueAsText

        berkas_list = get_all_berkas_id()
        

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False

        user_data = get_user_data(CREDENTIAL_KEY)
        token = user_data.get(AUTH_KEY, None)

        # Mendapatkan objek layout
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        layout = aprx.listLayouts(layout_name)[0]

        # Menentukan path output PDF sementara (menggunakan scratch folder bawaan ArcGIS)
        scratch_folder = arcpy.env.scratchFolder
        pdf_filename = f"{layout_name.replace(' ', '_')}.pdf"
        pdf_path = os.path.join(scratch_folder, pdf_filename)

        # Proses Export
        arcpy.AddMessage(f"Mengekspor layout '{layout_name}' ke format PDF...")
        layout.exportToPDF(pdf_path)
        arcpy.AddMessage(f"Export berhasil: {pdf_path}")

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

        # Proses Upload (Sesuai parameter dari screenshot Postman/Insomnia)
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/upload/layout"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/upload/layout"
        url = prod_url if use_production else test_url

        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        payload_data = {
            "no_berkas": no_berkas,
            "param": param_upload
        }

        arcpy.AddMessage("Mengirim file PDF ke API SIPENTA...")
        
        try:
            with open(pdf_path, 'rb') as f:
                # Format multipart/form-data untuk file upload
                files = {'file': (pdf_filename, f, 'application/pdf')}
                
                # Mengirim request POST
                # verify=False dapat ditambahkan jika terdapat isu SSL certificate pada server belajar.atrbpn.go.id
                response = requests.post(url, headers=headers, data=payload_data, files=files) 

            # Evaluasi respon API
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    arcpy.AddMessage(f"SUKSES: {res_json.get('message', 'File berhasil diunggah!')}")
                else:
                    arcpy.AddError(f"GAGAL DARI SERVER: {response.text}")
            else:
                arcpy.AddError(f"HTTP ERROR {response.status_code}: {response.text}")
                
        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat menghubungi API: {str(e)}")

        return