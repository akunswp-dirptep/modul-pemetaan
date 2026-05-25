from datetime import datetime
import json
import sys
import arcpy, os, requests, zipfile, csv

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import constant, persil
from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_feature_layer_to_sipenta


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Hitung_Jarak_Fasilitas, Upload_Basis_Data, Hitung_Resiko_Persil]


class Hitung_Jarak_Fasilitas(object):

    def __init__(self):
        self.label="Hitung Jarak Fasilitas"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type):

        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in field_names:
            arcpy.management.AddField(feature_class,field_name,field_type)

    def execute(self,parameters,messages):

        messages.addMessage("== Proses mulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]
        dataset_fasilitas_path=configs["fasilitas_config"]["dataset_path"]
        jaringanjalan_nd_path=configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        nd_path=configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]

        persil_nama="Persil_Layer"
        persil_path=os.path.join(dataset_path,persil_nama)

        persil_layer_centroid="Persil_Layer_Centroid"
        persil_layer_centroid_path=os.path.join(dataset_path,persil_layer_centroid)

        dataset_template_path=os.path.dirname(jaringanjalan_nd_path)

        self.delete_if_exists(persil_layer_centroid)
        self.delete_if_exists(persil_layer_centroid_path)

        messages.addMessage("== Membuat centroid persil ==")

        arcpy.management.FeatureToPoint(
            persil_path,
            persil_layer_centroid_path,
            "INSIDE"
        )

        messages.addMessage("== Persiapan network analyst ==")

        outNALayerName="hasil_na"
        impedance_attribute="P_Jalan"

        arcpy.env.workspace=dataset_fasilitas_path
        list_fc=arcpy.ListFeatureClasses()

        if not list_fc:
            messages.addWarningMessage("== Tidak ada fasilitas ditemukan ==")
            return

        for fc in list_fc:
            fasilitas=fc
            fasilitas_path=os.path.join(dataset_fasilitas_path,fasilitas)
            namafield='JK'+ os.path.splitext(fasilitas)[0]
            arcpy.AddMessage(namafield)

            messages.addMessage(f"== Hitung jarak fasilitas: {fasilitas} ==")

            hasilNAObject=arcpy.na.MakeClosestFacilityLayer(
                nd_path,
                outNALayerName,
                impedance_attribute,
                "TRAVEL_FROM",
                default_number_facilities_to_find=1
            )

            outNALayer=hasilNAObject.getOutput(0)

            arcpy.na.AddLocations(
                outNALayer,
                "Incidents",
                persil_layer_centroid_path
            )

            arcpy.na.AddLocations(
                outNALayer,
                "Facilities",
                fasilitas_path
            )

            arcpy.na.Solve(outNALayer)
            aprx=arcpy.mp.ArcGISProject("CURRENT")
            m=aprx.activeMap
            m.addLayer(outNALayer)

            incident_path=os.path.join(dataset_template_path,f"incident_{fasilitas}")
            route_path=os.path.join(dataset_template_path,f"route_{fasilitas}")
            temp_join=os.path.join(dataset_template_path,"temp_join1")

            self.delete_if_exists(incident_path)
            self.delete_if_exists(route_path)
            self.delete_if_exists(temp_join)

            messages.addMessage("== Export hasil network analyst ==")

            for lyr in outNALayer.listLayers():

                if lyr.isGroupLayer:
                    continue

                if lyr.name=="Incidents":

                    arcpy.management.CopyFeatures(
                        lyr,
                        incident_path
                    )

                elif lyr.name=="Routes":

                    arcpy.management.CopyFeatures(
                        lyr,
                        route_path
                    )

            messages.addMessage("== Join route ==")

            arcpy.management.JoinField(
                incident_path,
                "OBJECTID",
                route_path,
                "IncidentID",
                ["Total_P_Jalan"]
            )

            messages.addMessage("== Spatial join ==")

            field_mapping=(
                f'IdBidang "IdBidang" true true false 4 Long 0 0 ,First,#,{persil_path},IdBidang,-1,-1;'
                f'Total_P_Jalan "Total_P_Jalan" true true false 8 Double 0 0 ,First,#,{incident_path},Total_P_Jalan,-1,-1'
            )

            arcpy.analysis.SpatialJoin(
                persil_path,
                incident_path,
                temp_join,
                "JOIN_ONE_TO_ONE",
                "KEEP_ALL",
                field_mapping,
                "INTERSECT"
            )

            self.add_field_if_not_exists(
                persil_path,
                namafield,
                "DOUBLE"
            )

            arcpy.management.JoinField(
                persil_path,
                "IdBidang",
                temp_join,
                "IdBidang",
                ["Total_P_Jalan"]
            )

            arcpy.management.CalculateField(
                persil_path,
                namafield,
                "!Total_P_Jalan!",
                "PYTHON3"
            )

            try:
                arcpy.management.DeleteField(persil_path,"Total_P_Jalan")
            except:
                pass

        self.delete_if_exists(persil_nama)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_nama
        )

        parameters[0].value=persil_nama

        messages.addMessage("== Proses selesai ==")
        return

class Upload_Basis_Data(object):
    def __init__(self):
        self.label = "Upload Basis Data"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        fl = arcpy.Parameter(
            displayName="Persil_Layer (Feature Layer)",
            name="fl",
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
        if berkas_list and can_show > 0:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '04/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]           
        elif berkas_list and can_show == 0:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
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
        params = [fl, berkas, penjelasan]
        return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   
    
    def updateParameters(self, parameters):
            """Modify the values and properties of parameters before internal
            validation is performed.  This method is called whenever a parameter
            has been changed."""

            shapefile_path = parameters[0]
            berkas = parameters[1]
            penjelasan = parameters[2]

            is_login = get_user_data(CREDENTIAL_KEY)

            if is_login is None:
                shapefile_path.enabled = False
                berkas.enabled = False
                penjelasan.enabled = True
            else:
                shapefile_path.enabled = True
                berkas.enabled = True
                penjelasan.enabled = False
            
            return
   
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan NBT.")
            return
        
        fl_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_basis_data_penilaian_bidang_tanah",
            in_feature="Persil_Layer",
            feature_layer=fl_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Hitung_Resiko_Persil(object):

    def __init__(self):

        self.label = "Hitung Resiko Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type="SHORT"
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses mulai =="
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        datasetresiko_path = (
            configs["resiko_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil = (
            "Persil_Layer"
        )

        persil_path = os.path.join(
            dataset_path,
            persil
        )

        persilcentroid = (
            "PersilCentroidUpdate"
        )

        persilcentroid_path = os.path.join(
            dataset_path,
            persilcentroid
        )

        # =================================================
        # PERSIAPAN
        # =================================================

        messages.addMessage(
            "== Persiapan =="
        )

        self.delete_if_exists(
            persilcentroid
        )

        self.delete_if_exists(
            persilcentroid_path
        )

        # =================================================
        # CREATE CENTROID
        # =================================================

        arcpy.management.FeatureToPoint(
            persil_path,
            persilcentroid_path,
            "INSIDE"
        )

        # =================================================
        # LIST RESIKO
        # =================================================

        arcpy.env.workspace = (
            datasetresiko_path
        )

        list_fc = arcpy.ListFeatureClasses(
            "*"
        )

        if not list_fc:

            messages.addWarningMessage(
                "== Tidak ada layer resiko ditemukan =="
            )

            return

        # =================================================
        # LOOP RESIKO
        # =================================================

        for fc in list_fc:

            resiko = fc

            resiko_path = os.path.join(
                datasetresiko_path,
                resiko
            )

            namafield = (
                fc.replace(" ", "")[:7]
            )

            messages.addMessage(
                f"== Cari persil dalam resiko: {resiko} =="
            )

            # =============================================
            # VALIDASI FIELD
            # =============================================

            self.add_field_if_not_exists(
                persil_path,
                namafield,
                "SHORT"
            )

            # =============================================
            # RESET VALUE
            # =============================================

            arcpy.management.CalculateField(
                persil_path,
                namafield,
                "0",
                "PYTHON3"
            )

            # =============================================
            # TEMP LAYER
            # =============================================

            temp_lyr = "temp"

            self.delete_if_exists(
                temp_lyr
            )

            arcpy.management.MakeFeatureLayer(
                persil_path,
                temp_lyr
            )

            # =============================================
            # SELECT BY LOCATION
            # =============================================

            arcpy.management.SelectLayerByLocation(
                temp_lyr,
                "INTERSECT",
                resiko_path
            )

            # =============================================
            # UPDATE VALUE
            # =============================================

            arcpy.management.CalculateField(
                temp_lyr,
                namafield,
                "1",
                "PYTHON3"
            )

            # =============================================
            # CLEAN TEMP
            # =============================================

            self.delete_if_exists(
                temp_lyr
            )

        # =================================================
        # REFRESH OUTPUT
        # =================================================

        self.delete_if_exists(
            persil
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return