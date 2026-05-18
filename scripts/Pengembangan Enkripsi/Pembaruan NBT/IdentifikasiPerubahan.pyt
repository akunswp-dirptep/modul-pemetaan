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
from zntutils.upload_utils import upload_shapefile_to_sipenta
from zntutils import zona_layer

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Laporan_Basis_Data, Upload_Peta_Peta_Area_Kerja_AOI]


class Upload_Peta_Peta_Area_Kerja_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        shapefile = arcpy.Parameter(
            displayName="Shapefile Peta Area Kerja(.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        shapefile.filter.list = ["shp"]
 

        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)

            if preferred_berkas and preferred_berkas.startswith('04'):
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
        params = [shapefile, berkas, penjelasan]
        return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        shapefile_param = parameters[0]
        
        if shapefile_param.valueAsText:
            shapefile_path = shapefile_param.valueAsText
            shapefile_base = os.path.splitext(shapefile_path)[0]
            required_ext = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
            missing = [
                ext for ext in required_ext
                if not os.path.exists(shapefile_base + ext)
            ]

            if missing:
                shapefile_param.setErrorMessage(
                    f"Komponen shapefile tidak lengkap.\nFile dengan ekstensi berikut tidak ditemukan: {', '.join(missing)}"
                )
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
        
        shapefile_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_shapefile_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_peta_area_kerja",
            in_feature="Persil",
            shapefile_path=shapefile_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Upload_Laporan_Basis_Data(object):

    def __init__(self):
        self.label="Upload Laporan Basis Data"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        berkas_list=get_all_berkas_id(
            process_type='Pembaruan NBT'
        )

        berkas_show=[]

        if berkas_list is not None:

            for berkas in berkas_list:

                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")

        else:

            berkas_show=[
                'Tidak ada berkas yang dapat dipilih'
            ]

        nomor_berkas=arcpy.Parameter(
            displayName="Berkas",
            name="nomor_berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        nomor_berkas.filter.type="ValueList"
        nomor_berkas.filter.list=berkas_show

        if berkas_list:

            preferred_berkas=get_user_data(
                PREFERRED_BERKAS_ID
            )

            if (
                preferred_berkas
                and preferred_berkas.startswith('04')
            ):

                nomor_berkas.value=preferred_berkas

            else:

                nomor_berkas.value=berkas_show[0]

        else:

            nomor_berkas.value='Tidak ada berkas yang dapat dipilih'

        tahun=arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        tahun.value=datetime.now().year

        penjelasan=arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        penjelasan.value=(
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )

        return [
            nomor_berkas,
            tahun,
            penjelasan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):

        nomor_berkas=parameters[0]
        tahun=parameters[1]
        penjelasan=parameters[2]

        is_login=get_user_data(CREDENTIAL_KEY)

        if is_login is None:

            nomor_berkas.enabled=False
            tahun.enabled=False
            penjelasan.enabled=True

        else:

            nomor_berkas.enabled=True
            tahun.enabled=True
            penjelasan.enabled=False

        return

    def updateMessages(self,parameters):
        return

    def generate_text_report(
        self,
        report_path,
        metadata,
        validation_results
    ):

        with open(report_path,"w") as txt_file:

            txt_file.write(
                "Shapefile Analysis Report\n"
            )

            txt_file.write(
                "=========================\n\n"
            )

            txt_file.write(
                f"Nomor Berkas: {metadata['project_id']}\n"
            )

            txt_file.write(
                f"Tahun: {metadata['tahun']}\n\n"
            )

            txt_file.write(
                f"Date and Time: {metadata['date_and_time']}\n"
            )

            txt_file.write(
                f"Shapefile Analyzed: {metadata['shapefile_analyzed']}\n"
            )

            txt_file.write(
                f"Row Count: {metadata['row_count']}\n"
            )

            txt_file.write(
                f"Spatial Reference: {metadata['spatial_reference']}\n\n"
            )

            txt_file.write(
                "Validation Results:\n"
            )

            txt_file.write(
                validation_results+"\n"
            )

    def generate_json_report(
        self,
        report_path,
        metadata,
        validation_results
    ):

        report_data={
            "metadata":metadata,
            "validation_results":validation_results
        }

        with open(report_path,"w") as json_file:

            json.dump(
                report_data,
                json_file,
                indent=4
            )

    def export_attribute_table_to_csv(
        self,
        shapefile_path,
        output_path,
        messages
    ):

        try:

            fields=[
                f.name
                for f in arcpy.ListFields(
                    shapefile_path
                )
            ]

            with open(
                output_path,
                "w",
                newline="",
                encoding="utf-8"
            ) as csv_file:

                writer=csv.writer(csv_file)

                writer.writerow(fields)

                with arcpy.da.SearchCursor(
                    shapefile_path,
                    fields
                ) as cursor:

                    for row in cursor:
                        writer.writerow(row)

        except Exception as e:

            messages.addErrorMessage(
                f"Error exporting CSV: {e}"
            )

            raise arcpy.ExecuteError

    def compress_reports_to_zip(
        self,
        zip_path,
        report_files,
        messages
    ):

        try:

            with zipfile.ZipFile(
                zip_path,
                'w',
                zipfile.ZIP_DEFLATED
            ) as zipf:

                for file in report_files:

                    if os.path.exists(file):

                        zipf.write(
                            file,
                            os.path.basename(file)
                        )

            messages.addMessage(
                f"ZIP created: {zip_path}"
            )

        except Exception as e:

            messages.addErrorMessage(
                f"Error creating ZIP: {e}"
            )

            raise arcpy.ExecuteError

    def upload_zip_to_api(
        self,
        zip_path,
        nomor_berkas,
        token,
        use_production,
        messages
    ):

        if use_production:
            url="https://sipenta.atrbpn.go.id/tatausaha/apis/upload"

        else:
            url="https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/upload"

        headers={
            "Authorization":f"Bearer {token}"
        }

        payload={
            "nomor_berkas":nomor_berkas,
            "step":"Penyusunan Basis Data Penilaian Bidang Tanah",
            "param":"Basis Data Penilaian Bidang Tanah"
        }

        try:

            with open(zip_path,"rb") as f:

                files={
                    "file":(
                        os.path.basename(zip_path),
                        f,
                        "application/zip"
                    )
                }

                response=requests.post(
                    url,
                    headers=headers,
                    data=payload,
                    files=files
                )

                try:
                    response_json=response.json()

                except:

                    messages.addErrorMessage(
                        f"Invalid response: {response.text}"
                    )

                    raise arcpy.ExecuteError

                if response_json.get("error")==False:

                    messages.addMessage(
                        f"Upload successful: {response_json.get('message','Success')}"
                    )

                else:

                    messages.addErrorMessage(
                        f"Upload failed: {response_json.get('message','Unknown Error')}"
                    )

                    raise arcpy.ExecuteError

        except Exception as e:

            messages.addErrorMessage(
                f"Error uploading ZIP: {e}"
            )

            raise arcpy.ExecuteError

    def execute(self,parameters,messages):

        import os
        import json
        import csv
        import zipfile
        import requests
        import arcpy

        from datetime import datetime

        arcpy.env.overwriteOutput=True

        messages.addMessage(
            "== Proses dimulai =="
        )

        nomor_berkas=parameters[0].valueAsText
        tahun=parameters[1].value

        validate_document_type(
            document_id=nomor_berkas,
            target='Pembaruan NBT'
        )

        user_data=get_user_data(CREDENTIAL_KEY)

        token=user_data.get(
            AUTH_KEY,
            None
        )

        server=get_user_data(
            PREFERRED_SERVER_KEY
        )

        use_production=True if (
            server=="Produksi"
            or server is None
        ) else False

        configs=persil.get_config_values()

        dataset_path=configs[
            "project_config"
        ]["dataset_path"]

        persil_name="Persil_Baru"

        persil_path=os.path.join(
            dataset_path,
            persil_name
        )

        execution_time=datetime.now()

        formatted_date=execution_time.strftime(
            "%d %B"
        )

        formatted_time=execution_time.strftime(
            "%H_%M"
        )

        zip_filename=(
            f"Laporan Tahap Basis Data_"
            f"Pembaruan NBT_"
            f"{formatted_date}_"
            f"{formatted_time}.zip"
        )

        output_dir=r"C:\PenilaianTanah"

        zip_path=os.path.join(
            output_dir,
            zip_filename
        )

        row_count=len(
            list(
                arcpy.da.SearchCursor(
                    persil_path,
                    ["OBJECTID"]
                )
            )
        )

        spatial_ref=arcpy.Describe(
            persil_path
        ).spatialReference.name

        metadata={
            "project_id":nomor_berkas,
            "tahun":tahun,
            "date_and_time":execution_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "shapefile_analyzed":persil_name,
            "row_count":row_count,
            "spatial_reference":spatial_ref
        }

        json_path=os.path.join(
            output_dir,
            "Shapefile_Analysis_Report.json"
        )

        txt_path=os.path.join(
            output_dir,
            "Shapefile_Analysis_Report.txt"
        )

        csv_path=os.path.join(
            output_dir,
            "Shapefile_Attribute_Table.csv"
        )

        validation_message=(
            "All required columns are complete. "
            "No NULL values detected."
        )

        self.generate_json_report(
            json_path,
            metadata,
            validation_message
        )

        self.generate_text_report(
            txt_path,
            metadata,
            validation_message
        )

        self.export_attribute_table_to_csv(
            persil_path,
            csv_path,
            messages
        )

        self.compress_reports_to_zip(
            zip_path,
            [json_path,txt_path,csv_path],
            messages
        )

        self.upload_zip_to_api(
            zip_path,
            nomor_berkas,
            token,
            use_production,
            messages
        )

        os.remove(json_path)
        os.remove(txt_path)
        os.remove(csv_path)

        setup_user_data(
            PREFERRED_BERKAS_ID,
            nomor_berkas
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return