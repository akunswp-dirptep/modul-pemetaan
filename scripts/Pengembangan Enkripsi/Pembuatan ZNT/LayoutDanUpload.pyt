import arcpy, os, json, sys

from datetime import datetime


arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import main_upload
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id
from zntutils.constant import USER_DATA_KEY, NIK_KEY, PREFERRED_SERVER_KEY, YEAR_KEY
from zntutils import zona_layer as zonalayer

#Helper Functions
def is_internal():
    try:
        return bool(get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        # return True
    except Exception:
        return False

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

def delete_topology_file():
    config_dan_paths = zonalayer.get_config_values()
    topology_path = os.path.join(config_dan_paths['dataset_path'], 'Zona_Layer_Topology')
    if arcpy.Exists(topology_path):
        arcpy.management.Delete(topology_path)
        
class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Peta_Sebaran_Sampel, 
                      Upload_Peta_Simpangan_Baku_Relatif, 
                      Upload_Peta_Zona_Nilai_Tanah]


class Upload_Peta_Sebaran_Sampel:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Sebaran Sampel"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        is_login = get_user_data(USER_DATA_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = [f"{berkas[0]} - {berkas[1]}" for berkas in berkas_list] if berkas_list else ['Tidak ada berkas yang dapat dipilih']

        feature_class = arcpy.Parameter(
            displayName="Titik Sampel (Feature Class)",
            name="feature_layer",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input")
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        berkas.value = berkas_show[0] if berkas_list else 'Tidak ada berkas yang dapat dipilih'
        
        penjelasan = arcpy.Parameter(
            displayName="Anda Belum Login Sebagai Pemeta Nilai Tanah",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu pada menu Login Pemeta Nilai Tanah.\n"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(current_year()))
        

        if is_login:
            params = [feature_class, berkas]
            return params
        else:
            return [penjelasan]


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
        delete_topology_file()
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_class = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        username = get_user_data(NIK_KEY)
        tahun = get_user_data(YEAR_KEY)


        project_id = berkas_value.split(" - ")[0]
        arcpy.AddMessage(f"Berkas yang dipilih: {project_id}")

        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Peta Sebaran Sampel", "Analisis dan Pengolahan Data", "Titik_Sampel", tahun, "ZNT", feature_class, use_production)

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Simpangan_Baku_Relatif:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Simpangan Baku Relatif"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        is_login = get_user_data(USER_DATA_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = [f"{berkas[0]} - {berkas[1]}" for berkas in berkas_list] if berkas_list else ['Tidak ada berkas yang dapat dipilih']

        feature_class = arcpy.Parameter(
            displayName="Zona Layer (Feature Class)",
            name="feature_layer",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input")
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        berkas.value = berkas_show[0] if berkas_list else 'Tidak ada berkas yang dapat dipilih'
        
        penjelasan = arcpy.Parameter(
            displayName="Anda Belum Login Sebagai Pemeta Nilai Tanah",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu pada menu Login Pemeta Nilai Tanah.\n"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(current_year()))
        

        if is_login:
            params = [feature_class, berkas]
            return params
        else:
            return [penjelasan]

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
        delete_topology_file()
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_class = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        username = get_user_data(NIK_KEY)
        tahun = get_user_data(YEAR_KEY)


        project_id = berkas_value.split(" - ")[0]
        arcpy.AddMessage(f"Berkas yang dipilih: {project_id}")


        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Peta Standar Deviasi", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
 
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Zona_Nilai_Tanah:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Peta Zona Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        is_login = get_user_data(USER_DATA_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
        berkas_show = [f"{berkas[0]} - {berkas[1]}" for berkas in berkas_list] if berkas_list else ['Tidak ada berkas yang dapat dipilih']

        feature_class = arcpy.Parameter(
            displayName="Zona Layer (Feature Class)",
            name="feature_layer",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input")
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        berkas.value = berkas_show[0] if berkas_list else 'Tidak ada berkas yang dapat dipilih'
        
        penjelasan = arcpy.Parameter(
            displayName="Anda Belum Login Sebagai Pemeta Nilai Tanah",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu pada menu Login Pemeta Nilai Tanah.\n"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(current_year()))
        

        if is_login:
            params = [feature_class, berkas]
            return params
        else:
            return [penjelasan]


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


        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020

        return  

    def execute(self, parameters, messages):
        """The source code of the tool."""
        delete_topology_file()
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_class = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        username = get_user_data(NIK_KEY)
        tahun = get_user_data(YEAR_KEY)


        project_id = berkas_value.split(" - ")[0]
        arcpy.AddMessage(f"Berkas yang dipilih: {project_id}")


        
        validate_document_type(project_id, target='Pembuatan ZNT')
        main_upload(project_id, username, "Peta Zona Nilai Tanah", "Analisis dan Pengolahan Data", "Zona_Layer", tahun, "ZNT", feature_class, use_production)
 

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
