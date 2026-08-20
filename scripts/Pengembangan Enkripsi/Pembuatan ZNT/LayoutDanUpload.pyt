import arcpy, os, json, sys

from datetime import datetime


arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


from zntutils.constant import PREFERRED_SERVER_KEY, PREFERRED_BERKAS_ID, CREDENTIAL_KEY, AUTH_KEY
from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import upload_shapefile_to_sipenta, upload_feature_layer_to_sipenta
from zntutils.system_utils import get_user_data, get_all_berkas_id, setup_user_data 
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
        self.label = "Upload Data Titik Sampel"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
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

        feature_layer = arcpy.Parameter(
            displayName="Titik Sampel (Feature Layer)",
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

        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]     
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        params = [feature_layer, berkas, penjelasan]
        return params


    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        feature_layer = parameters[0]
        berkas = parameters[1]
        penjelasan = parameters[2]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            feature_layer.enabled = False
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            feature_layer.enabled = True
            berkas.enabled = True
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

        return  

    def execute(self, parameters, messages):
        """The source code of the tool."""
        delete_topology_file()
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)
        configs = zonalayer.get_config_values()
        ts_path = os.path.join(configs['dataset_path'], 'Titik_Sampel')
        
        nilai_tanah_negatif_titik_sampel = zonalayer.validasi_nilai_tanah_negatif(ts_path, 'Titik_Sampel')
        if nilai_tanah_negatif_titik_sampel:
            for err in nilai_tanah_negatif_titik_sampel:
                arcpy.AddError(f'Terdapat Nilai Tanah Negatif pada layer Titik Sampel, Nomor Sampel: {err[0]} | Nilai Tanah/m2 : {err[1]}')
            return
        
        zona_pembuatan_kurang_dari_3_titik = zonalayer.validasi_zona_layer_min_3_titik_sampel(config_dan_paths=configs)
        if zona_pembuatan_kurang_dari_3_titik:
            for err in zona_pembuatan_kurang_dari_3_titik:
                arcpy.AddError(f"Pada Zona ini titik sampel kurang dari batas minimum (3 buah):{err}")
            return
        
        perbedaan_zona = zonalayer.validate_kesesuaian_zona(config_dan_paths=zonalayer.get_config_values())
        if perbedaan_zona:
            arcpy.AddError(perbedaan_zona)
            sys.exit(1)
            return

        smpbkrel_tidak_memenuhi_syarat = zonalayer.validate_simpangan_baku_relatif(config_dan_paths=configs)
        if smpbkrel_tidak_memenuhi_syarat == "Skala Kosong":
            arcpy.AddWarning("Peringatan: Data ini tidak memiliki informasi skala. Validasi persentase batas toleransi dilewati. Silakan perbarui data skala pada workspace untuk validasi penuh")
        elif smpbkrel_tidak_memenuhi_syarat != "Skala Kosong" and smpbkrel_tidak_memenuhi_syarat is not None:
            arcpy.AddError(f"{smpbkrel_tidak_memenuhi_syarat}")
            return 

        
        validate_document_type(berkas_value, target='Pembuatan ZNT')
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_peta_shp_sebaran_sampel",
            in_feature="Titik_Sampel",
            feature_layer=feature_layer,
            use_production=use_production)
        
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Simpangan_Baku_Relatif:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Data Simpangan Baku Relatif"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
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

        feature_layer = arcpy.Parameter(
            displayName="Zona Layer (Feature Layer)",
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

        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]     
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'

        
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        params = [feature_layer, berkas, penjelasan]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        feature_layer = parameters[0]
        berkas = parameters[1]
        penjelasan = parameters[2]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            feature_layer.enabled = False
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            feature_layer.enabled = True
            berkas.enabled = True
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

        return  

    def execute(self, parameters, messages):
        """The source code of the tool."""
        delete_topology_file()
        zonalayer.check_if_there_selected_field()
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)
        configs = zonalayer.get_config_values()
        ts_path = os.path.join(configs['dataset_path'], 'Titik_Sampel')

        duplikasi_nozn = zonalayer.validasi_duplikasi_nozn(config_dan_paths=configs)
        if duplikasi_nozn:
            for err in duplikasi_nozn:
                arcpy.AddError(f'Terdapat Duplikasi NOZN: {err}')
            return
        
        nilai_tanah_negatif_titik_sampel = zonalayer.validasi_nilai_tanah_negatif(ts_path, 'Titik_Sampel')
        if nilai_tanah_negatif_titik_sampel:
            for err in nilai_tanah_negatif_titik_sampel:
                arcpy.AddError(f'Terdapat Nilai Tanah Negatif pada layer Titik Sampel, Nomor Sampel: {err[0]} | Nilai Tanah/m2 : {err[1]}')
            return
        
        zona_pembuatan_kurang_dari_3_titik = zonalayer.validasi_zona_layer_min_3_titik_sampel(config_dan_paths=configs)
        if zona_pembuatan_kurang_dari_3_titik:
            for err in zona_pembuatan_kurang_dari_3_titik:
                arcpy.AddError(f"Pada Zona ini titik sampel kurang dari batas minimum (3 buah):{err}")
            return

        smpbkrel_tidak_memenuhi_syarat = zonalayer.validate_simpangan_baku_relatif(config_dan_paths=configs)
        if smpbkrel_tidak_memenuhi_syarat == "Skala Kosong":
            arcpy.AddWarning("Peringatan: Data ini tidak memiliki informasi skala. Validasi persentase batas toleransi dilewati. Silakan perbarui data skala pada workspace untuk validasi penuh")
        elif smpbkrel_tidak_memenuhi_syarat != "Skala Kosong" and smpbkrel_tidak_memenuhi_syarat is not None:
            arcpy.AddError(f"{smpbkrel_tidak_memenuhi_syarat}")
            return
        
        luas_zona_tidak_memenuhi_minimum = zonalayer.validate_luas_minimal_zona(config_dan_paths=configs)
        if luas_zona_tidak_memenuhi_minimum == "Skala Kosong":
            arcpy.AddWarning("Peringatan: Data ini tidak memiliki informasi skala. Validasi luas zona minimum dilewati. Silakan perbarui data skala pada workspace untuk validasi penuh")
        elif luas_zona_tidak_memenuhi_minimum != "Skala Kosong" and luas_zona_tidak_memenuhi_minimum is not None:
            arcpy.AddError(f"{luas_zona_tidak_memenuhi_minimum}")
            return      
          
        perbedaan_zona = zonalayer.validate_kesesuaian_zona(config_dan_paths=zonalayer.get_config_values())
        if perbedaan_zona:
            arcpy.AddError(perbedaan_zona)
            sys.exit(1)
            return
        validation_error = zonalayer.validate_zona_layer_before_upload(feature_layer)
        if validation_error:
            arcpy.AddError(validation_error)
            sys.exit(1)
            return

        
        validate_document_type(berkas_value, target='Pembuatan ZNT')
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_peta_shp_standar_deviasi",
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class Upload_Peta_Zona_Nilai_Tanah:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload Data Zona Nilai Tanah"
        self.description = ""

    def getParameterInfo(self):
        """Define parameter definitions"""
        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')
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

        feature_layer = arcpy.Parameter(
            displayName="Zona Layer (Feature Layer)",
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

        if berkas_list:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '01/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]     
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'

        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        params = [feature_layer, berkas, penjelasan]
        return params



    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        feature_layer = parameters[0]
        berkas = parameters[1]
        penjelasan = parameters[2]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            feature_layer.enabled = False
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            feature_layer.enabled = True
            berkas.enabled = True
            penjelasan.value = (
                "Pastikan data sudah benar sebelum diupload.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""


        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020

        return  

    def execute(self, parameters, messages):
        """The source code of the tool."""
        delete_topology_file()
        zonalayer.check_if_there_selected_field()
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembuatan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembuatan ZNT.")
            return
        
        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)
        configs = zonalayer.get_config_values()
        ts_path = os.path.join(configs['dataset_path'], 'Titik_Sampel')

        duplikasi_nozn = zonalayer.validasi_duplikasi_nozn(config_dan_paths=configs)
        if duplikasi_nozn:
            for err in duplikasi_nozn:
                arcpy.AddError(f'Terdapat Duplikasi NOZN: {err}')
            return
        
        nilai_tanah_negatif_titik_sampel = zonalayer.validasi_nilai_tanah_negatif(ts_path, 'Titik_Sampel')
        if nilai_tanah_negatif_titik_sampel:
            for err in nilai_tanah_negatif_titik_sampel:
                arcpy.AddError(f'Terdapat Nilai Tanah Negatif pada layer Titik Sampel, Nomor Sampel: {err[0]} | Nilai Tanah/m2 : {err[1]}')
            return
        
        smpbkrel_tidak_memenuhi_syarat = zonalayer.validate_simpangan_baku_relatif(config_dan_paths=configs)
        if smpbkrel_tidak_memenuhi_syarat == "Skala Kosong":
            arcpy.AddWarning("Peringatan: Data ini tidak memiliki informasi skala. Validasi persentase batas toleransi dilewati. Silakan perbarui data skala pada workspace untuk validasi penuh")
        elif smpbkrel_tidak_memenuhi_syarat != "Skala Kosong" and smpbkrel_tidak_memenuhi_syarat is not None:
            arcpy.AddError(f"{smpbkrel_tidak_memenuhi_syarat}")
            return

        luas_zona_tidak_memenuhi_minimum = zonalayer.validate_luas_minimal_zona(config_dan_paths=configs)
        if luas_zona_tidak_memenuhi_minimum == "Skala Kosong":
            arcpy.AddWarning("Peringatan: Data ini tidak memiliki informasi skala. Validasi luas zona minimum dilewati. Silakan perbarui data skala pada workspace untuk validasi penuh")
        elif luas_zona_tidak_memenuhi_minimum != "Skala Kosong" and luas_zona_tidak_memenuhi_minimum is not None:
            arcpy.AddError(f"{luas_zona_tidak_memenuhi_minimum}")
            return
        
        zona_pembuatan_kurang_dari_3_titik = zonalayer.validasi_zona_layer_min_3_titik_sampel(config_dan_paths=configs)
        if zona_pembuatan_kurang_dari_3_titik:
            for err in zona_pembuatan_kurang_dari_3_titik:
                arcpy.AddError(f"Pada Zona ini titik sampel kurang dari batas minimum (3 buah):{err}")
            return
        
        perbedaan_zona = zonalayer.validate_kesesuaian_zona(config_dan_paths=zonalayer.get_config_values())
        if perbedaan_zona:
            arcpy.AddError(perbedaan_zona)
            sys.exit(1)
            return
        
        validation_error = zonalayer.validate_zona_layer_before_upload(feature_layer)
        if validation_error:
            arcpy.AddError(validation_error)
            sys.exit(1)
            return
        
        validate_document_type(berkas_value, target='Pembuatan ZNT')
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembuatan_znt_peta_shp_znt",
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
