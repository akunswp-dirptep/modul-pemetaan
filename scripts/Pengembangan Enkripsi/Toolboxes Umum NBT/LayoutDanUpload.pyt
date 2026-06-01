import arcpy, os, sys, requests, json, datetime

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"
arcpy.env.overwriteOutput = True

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


from nbtutils import persil

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tampilkan_Simbologi_Persil]


class Tampilkan_Simbologi_Persil(object):
    """Tool untuk menampilkan simbologi pada layer Persil_Layer"""
    def __init__(self):
        self.label = "Tampilkan Simbologi Persil"
        self.description = "Tool untuk menampilkan simbologi pada layer Persil_Layer berdasarkan atribut yang dipilih."

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",    
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk menampilkan simbologi pada\n"
            "Persil_Layer.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )

        pilihan_atribut = arcpy.Parameter(
            displayName="Pilih Atribut untuk Simbologi",
            name="pilihan_atribut",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pilihan_atribut.filter.type = "ValueList"
        pilihan_atribut.filter.list = ['Bentuk', 'Letak', 'Kelas Jalan', 'Lebar Jalan', 'Lebar Depan', 'Tipe Hak', 'Zonasi']
        pilihan_atribut.value = 'Bentuk'

        pilihan_simbologi = arcpy.Parameter(
            displayName="Pilih Simbologi",
            name="pilihan_simbologi",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pilihan_simbologi.filter.type = "ValueList"
        pilihan_simbologi.filter.list = ['Hanya Atribut', 'Dengan Status Pembaruan']
        pilihan_simbologi.value = 'Hanya Atribut'
        
        output_bp = arcpy.Parameter(
            name="Bentuk_Persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, pilihan_atribut, pilihan_simbologi, output_bp]

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool untuk menampilkan simbologi pada layer Persil_Layer"""
        config_paths = persil.get_config_values()

        dataset_path = config_paths['project_config']['dataset_path']
        persil_path = os.path.join(dataset_path, 'Persil_Layer')
        pilihan_atribut = parameters[1].valueAsText
        pilihan_simbologi = parameters[2].valueAsText
        mapping_simbology = {
            'Bentuk': ['Simbologi_Bentuk_Persil.lyrx', 'Simbologi_Bentuk_Persil_Dan_Status_Pembaruan.lyrx'],
            'Letak': ['Simbologi_Letak_Persil.lyrx', 'Simbologi_Letak_Persil_Dan_Status_Pembaruan.lyrx'],
            'Kelas Jalan': ['Simbologi_Kelas_Jalan.lyrx', 'Simbologi_Kelas_Jalan_Dan_Status_Pembaruan.lyrx'],
            'Lebar Jalan': ['Simbologi_Lebar_Jalan.lyrx', 'Simbologi_Lebar_Jalan_Dan_Status_Pembaruan.lyrx'],
            'Lebar Depan': ['Simbologi_Lebar_Depan.lyrx', 'Simbologi_Lebar_Depan_Dan_Status_Pembaruan.lyrx'],
            'Tipe Hak': ['Simbologi_Tipe_Hak.lyrx', 'Simbologi_Tipe_Hak_Dan_Status_Pembaruan.lyrx'],
            'Zonasi': ['Simbologi_Zonasi.lyrx', 'Simbologi_Zonasi_Dan_Status_Pembaruan.lyrx']
        }

        simbology_path = mapping_simbology.get(pilihan_atribut, [None])[0] if pilihan_simbologi == 'Hanya Atribut' else mapping_simbology.get(pilihan_atribut, [None])[1]

        arcpy.management.MakeFeatureLayer(persil_path, "Persil_Layer")
        arcpy.management.ApplySymbologyFromLayer("Persil_Layer", simbology_path)

        arcpy.SetParameter(3, "Persil_Layer")
