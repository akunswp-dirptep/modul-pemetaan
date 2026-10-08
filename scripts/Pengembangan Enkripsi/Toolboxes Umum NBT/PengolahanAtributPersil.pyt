import arcpy, os, sys
from collections import Counter

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
        self.tools = [Pengisian_WADMKC_WADMKD_Otomatis,
                      Pengisian_WADMKC_WADMKD_Manual]



class Pengisian_WADMKC_WADMKD_Otomatis(object):
    def __init__(self):
        self.label = "Isi WADMKC & WADMKD Secara Otomatis"
        self.description = "Mengisi atribut WADMKC dan WADMKD yang Null berdasarkan 3 bidang terdekat, mengupdate status_per, dan perubahan."
        self.canRunInBackground = False

    def getParameterInfo(self):
        

        output_data = arcpy.Parameter(
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_data]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Memulai proses otomatisasi WADMKC & WADMKD ==")

        persil_layer = 'Persil_Layer'
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        peta_aktif = aprx.activeMap
        if peta_aktif is None:
            arcpy.AddError('Tidak ditemukan peta aktif pada project ini')
            return

        daftar_layer = peta_aktif.listLayers(persil_layer)

        if len(daftar_layer)  == 0:
            arcpy.AddError(f'Layer {persil_layer} tidak ditemukan.')
            return

        elif len(daftar_layer) > 1:
            jumlah_layer = len(daftar_layer)
            arcpy.AddError(f'Ditemukan {jumlah_layer} Layer {persil_layer}. Hanya boleh ada 1 {persil_layer}')
            return
        layer_diinginkan = daftar_layer[0]
        if layer_diinginkan.isBroken:
            arcpy.AddError(f"Peringatan: Layer '{persil_layer}' ditemukan, tetapi sumber datanya terputus (broken)!")
            return

        input_layer = layer_diinginkan                                              
        required_fields = ["WADMKC", "WADMKD"]
        existing_fields = {f.name.upper(): f.name for f in arcpy.ListFields(input_layer)}
        missing_fields = [f for f in required_fields if f.upper() not in existing_fields]

        if missing_fields:
            messages.addErrorMessage(f"Field berikut tidak ditemukan pada layer: {', '.join(missing_fields)}")
            raise arcpy.ExecuteError

        has_status = "STATUS_PER" in existing_fields or "STATUS_PERUBAHAN" in existing_fields
        has_perubahan = "PERUBAHAN" in existing_fields
        
        status_field_name = existing_fields.get("STATUS_PER", existing_fields.get("STATUS_PERUBAHAN", ""))
        perubahan_field_name = existing_fields.get("PERUBAHAN", "")

        target_fields = ["WADMKC", "WADMKD"]
        
        for target_field in target_fields:
            messages.addMessage(f"== Memproses field {target_field} ==")
            
            valid_layer = f"memory_valid_{target_field}"
            null_layer = f"memory_null_{target_field}"
            
            where_valid = f"{target_field} IS NOT NULL AND {target_field} <> '' AND {target_field} <> ' '"
            where_null = f"{target_field} IS NULL OR {target_field} = '' OR {target_field} = ' '"
            
            arcpy.management.MakeFeatureLayer(input_layer, valid_layer, where_valid)
            arcpy.management.MakeFeatureLayer(input_layer, null_layer, where_null)
            
            count_valid = int(arcpy.management.GetCount(valid_layer)[0])
            count_null = int(arcpy.management.GetCount(null_layer)[0])
            
            if count_null == 0:
                messages.addMessage(f"Tidak ada bidang yang {target_field}-nya kosong. Lanjut ke proses berikutnya.")
                arcpy.management.Delete(valid_layer)
                arcpy.management.Delete(null_layer)
                continue
                
            if count_valid == 0:
                messages.addErrorMessage(f"Tidak ada satupun bidang dengan {target_field} valid untuk referensi")
                arcpy.management.Delete(valid_layer)
                arcpy.management.Delete(null_layer)
                continue
                
            messages.addMessage(f"Ditemukan {count_null} bidang kosong dan {count_valid} bidang referensi untuk {target_field}")
            
            near_table = r"memory\near_table_result"
            if arcpy.Exists(near_table):
                arcpy.management.Delete(near_table)
                
            arcpy.analysis.GenerateNearTable(
                in_features=null_layer, 
                near_features=valid_layer, 
                out_table=near_table, 
                closest="ALL", 
                closest_count=3, 
                method="PLANAR"
            )
            
            valid_dict = {}
            with arcpy.da.SearchCursor(valid_layer, ["OID@", target_field]) as sc:
                for row in sc:
                    valid_dict[row[0]] = row[1]
                    
            null_neighbors = {}
            with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as sc:
                for row in sc:
                    in_fid = row[0]   
                    near_fid = row[1] 
                    
                    val = valid_dict.get(near_fid)
                    if val is not None:
                        if in_fid not in null_neighbors:
                            null_neighbors[in_fid] = []
                        null_neighbors[in_fid].append(val)
                        
            messages.addMessage(f"== Memperbarui bidang kosong untuk {target_field}... ==")
            
            # Menyusun field yang akan diupdate secara dinamis
            update_fields = ["OID@", target_field]
            if has_status: update_fields.append(status_field_name)
            if has_perubahan: update_fields.append(perubahan_field_name)
            
            updated_count = 0
            with arcpy.da.UpdateCursor(null_layer, update_fields) as uc:
                for row in uc:
                    oid = row[0]
                    if oid in null_neighbors:
                        val_list = null_neighbors[oid]
                        
                        if val_list:
                           
                            most_common_val = Counter(val_list).most_common(1)[0][0]
                            row[1] = most_common_val
                            
                            if has_status:
                                row[update_fields.index(status_field_name)] = "update"
                            if has_perubahan:
                                row[update_fields.index(perubahan_field_name)] = "menyebar"
                                
                            uc.updateRow(row)
                            updated_count += 1
                            
            messages.addMessage(f"Selesai. Berhasil memperbarui {updated_count} bidang untuk {target_field}.")
            
            arcpy.management.Delete(valid_layer)
            arcpy.management.Delete(null_layer)
            arcpy.management.Delete(near_table)
            
        
        arcpy.SetParameter(0, input_layer)
        return

class Pengisian_WADMKC_WADMKD_Manual(object):
    def __init__(self):
        self.label = "Isi WADMKC & WADMKD Secara Manual"
        self.description = "Mengisi atribut WADMKC dan WADMKD secara manual HANYA pada bidang (feature) yang sedang terpilih (selected) pada Persil_Layer."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param_wadmkc = arcpy.Parameter(
            name="wadmkc_value",
            displayName="Nilai WADMKC (Kecamatan)",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        param_wadmkd = arcpy.Parameter(
            name="wadmkd_value",
            displayName="Nilai WADMKD (Desa/Kelurahan)",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        return [param_wadmkc, param_wadmkd]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Memulai proses update manual WADMKC & WADMKD ==")

        wadmkc_val = parameters[0].valueAsText
        wadmkd_val = parameters[1].valueAsText

        if not wadmkc_val and not wadmkd_val:
            arcpy.AddError("Anda harus memasukkan minimal satu nilai (WADMKC atau WADMKD).")
            return

        input_layer = persil.is_persil_layer_comply()
        layer_name = 'Persil_Layer'

        desc = arcpy.Describe(layer_name)
        if not desc.FIDSet:
            arcpy.AddError('Tidak ada feature yang dipilih di Persil_Layer. Silakan Select fitur terlebih dahulu.')
            return 
        
        selected_features_count = len(desc.FIDSet.split(";"))
        messages.addMessage(f"Ditemukan {selected_features_count} bidang yang terpilih dan akan di-update.")
        existing_fields = {f.name.upper(): f.name for f in arcpy.ListFields(input_layer)}
        
        update_fields = []
        if wadmkc_val:
            if "WADMKC" not in existing_fields:
                arcpy.AddError("Field WADMKC tidak ditemukan pada layer.")
                return
            update_fields.append("WADMKC")
            
        if wadmkd_val:
            if "WADMKD" not in existing_fields:
                arcpy.AddError("Field WADMKD tidak ditemukan pada layer.")
                return
            update_fields.append("WADMKD")

        has_status = "STATUS_PER" in existing_fields or "STATUS_PERUBAHAN" in existing_fields
        has_perubahan = "PERUBAHAN" in existing_fields
        
        status_field_name = existing_fields.get("STATUS_PER", existing_fields.get("STATUS_PERUBAHAN", ""))
        perubahan_field_name = existing_fields.get("PERUBAHAN", "")

        if has_status: update_fields.append(status_field_name)
        if has_perubahan: update_fields.append(perubahan_field_name)

        updated_count = 0
        
        with arcpy.da.UpdateCursor(layer_name, update_fields) as uc:
            for row in uc:
                
                if wadmkc_val:
                    row[update_fields.index("WADMKC")] = wadmkc_val
                if wadmkd_val:
                    row[update_fields.index("WADMKD")] = wadmkd_val
                
                if has_status:
                    row[update_fields.index(status_field_name)] = "update"
                if has_perubahan:
                    row[update_fields.index(perubahan_field_name)] = "menyebar"
                    
                uc.updateRow(row)
                updated_count += 1

        messages.addMessage(f"Selesai! Berhasil meng-update {updated_count} bidang pada Persil_Layer")
        return