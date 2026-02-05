import arcpy, os, sys, requests, json

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    
persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)
persil_objek = os.path.join(dataset_path, "objek")
pembanding1 = "pembanding_1"
pembanding2 = "pembanding_2"
pembanding3 = "pembanding_3"

def main_loop(penilaian):
    list_pembanding = []
    pembanding = ''
    
    ada_seleksi = 0
    ada_seleksi = len(arcpy.Describe(persil).FIDSet)
    if ada_seleksi <= 0:
        sys.exit()
    
    rows = arcpy.da.SearchCursor (persil, 'IdBidang')
    for row in rows:
        list_pembanding.append(row[0])
        pembanding = pembanding + str(row[0]) + ';'
        count = 0

    for i in list_pembanding:
        count = count+1
        persil_i = "pembanding_{}".format(count)
        out_name = persil_i
        arcpy.MakeFeatureLayer_management(persil_path, persil_i, "OBJECTID = " + str(i))
        # arcpy.FeatureClassToFeatureClass_conversion(persil_i, dataset_path, out_name)

    if len(list_pembanding) == 3:
        objek = '';
        for rows in arcpy.da.SearchCursor(persil_path, ['IdBidang'], '"IdBidang" = ' + penilaian + ''):
            objek = rows[0]
        arcpy.MakeFeatureLayer_management(persil_path, "objek", "OBJECTID = " + str(objek))

    elif len(list_pembanding) < 3:
        arcpy.AddMessage('Data Pembanding Kurang Dari 3')
        arcpy.AddError('Data Pembanding Kurang Dari 3')
    else :
        arcpy.AddMessage('Data Pembanding Lebih Dari 3')
        arcpy.AddError('Data Pembanding Lebih Dari 3')

    persil_fields = [field.name for field in arcpy.ListFields(persil_path)]
    if "data_pembanding" not in persil_fields:
        arcpy.AddField_management(persil_path, "data_pembanding", "TEXT")
        
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Persil_Individual]

class Persil_Individual(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Hitung Individual"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        ##list
        list_tsi = []
        for rows in arcpy.SearchCursor(persil_path, where_clause = "perubahan = 'menyebar'"):
            list_tsi.append(rows.IdBidang)
        del rows
        
        param0 = arcpy.Parameter(
            displayName="ID Bidang Penilaian",
            name="penilaian",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param0.filter.type = "ValueList"
        list_tsi.sort()
        param0.filter.list = list_tsi
        
        params = [param0]
        return params

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
        penilaian = parameters[0].valueAsText
        main_loop(penilaian)

        rows = arcpy.UpdateCursor("objek")
        for row in rows:
            value_ls_tnh = row.getValue("ls_tnh")
            value_lb_dpn = row.getValue("lb_dpn")
            bentuk0 = row.getValue("s_bentuk")
            letak0 = row.getValue("s_letak")
            kls_jln0 = row.getValue("s_kls_jln")
            ls_tnh0 = row.getValue("ls_tnh_i")
            lb_dpn0 = row.getValue("lb_dpn_i")
            ls_tnh00 = row.getValue("ls_tnh")
            zonasi = row.getValue("s_zonasi")
            nama_zonasi = row.getValue("zonasi")
            rows.updateRow(row)
        del row, rows

        rows = arcpy.UpdateCursor(pembanding1)
        for row in rows:
            object_id1 = row.getValue("OBJECTID")
            value_ls_tnh = row.getValue("ls_tnh")
            value_lb_dpn = row.getValue("lb_dpn")
            nilai1 = row.getValue("NILAI_LAMA")
            ls_tnh1 = row.getValue("ls_tnh_i")
            ls_tnh11 = row.getValue("ls_tnh")
            lb_dpn1 = row.getValue("lb_dpn_i")
            bentuk1 = row.getValue("s_bentuk")
            letak1 = row.getValue("s_letak")
            kls_jln1 = row.getValue("s_kls_jln")
            zonasi1 = row.getValue("s_zonasi")
            nama_zonasi1 = row.getValue("zonasi")
            rows.updateRow(row)
        del row, rows

        rows = arcpy.UpdateCursor(pembanding2)
        for row in rows:
            object_id2 = row.getValue("OBJECTID")
            value_ls_tnh = row.getValue("ls_tnh")
            value_lb_dpn = row.getValue("lb_dpn")
            nilai2 = row.getValue("NILAI_LAMA")
            ls_tnh2 = row.getValue("ls_tnh_i")
            ls_tnh22 = row.getValue("ls_tnh")
            lb_dpn2 = row.getValue("lb_dpn_i")
            bentuk2 = row.getValue("s_bentuk")
            letak2 = row.getValue("s_letak")
            kls_jln2 = row.getValue("s_kls_jln")
            zonasi2 = row.getValue("s_zonasi")
            nama_zonasi2 = row.getValue("zonasi")
            rows.updateRow(row)
        del row, rows

        rows = arcpy.UpdateCursor(pembanding3)
        for row in rows:
            object_id3 = row.getValue("OBJECTID")
            value_ls_tnh = row.getValue("ls_tnh")
            value_lb_dpn = row.getValue("lb_dpn")
            nilai3 = row.getValue("NILAI_LAMA")
            ls_tnh3 = row.getValue("ls_tnh_i")
            ls_tnh33 = row.getValue("ls_tnh")
            lb_dpn3 = row.getValue("lb_dpn_i")
            bentuk3 = row.getValue("s_bentuk")
            letak3 = row.getValue("s_letak")
            kls_jln3 = row.getValue("s_kls_jln")
            zonasi3 = row.getValue("s_zonasi")
            nama_zonasi3 = row.getValue("zonasi")
            rows.updateRow(row)
        del row, rows

        #hitung individual
        #pembanding 1
        ls_tnh01 = (ls_tnh0 - ls_tnh1) * 0.5
        lb_dpn01 = (lb_dpn0 - lb_dpn1) * 1.5
        bentuk01 = (bentuk0 - bentuk1) * 1.5
        letak01 = (letak0 - letak1) * 1
        kls_jln01 = (kls_jln0 - kls_jln1) * 3
        persentase01 = ls_tnh01 + lb_dpn01 + bentuk01 + letak01 + kls_jln01 
        nilai01 = ((nilai1) * (100 + persentase01))/100
        #nilai01 = ((nilai1 / ls_tnh11) * (100 + persentase01))/100
        list_01 = [ls_tnh01 , lb_dpn01 , bentuk01 , letak01 , kls_jln01]
        nilai_nol01 = list_01.count(0)

        #pembanding 2
        ls_tnh02 = (ls_tnh0 - ls_tnh2) * 0.5
        lb_dpn02 = (lb_dpn0 - lb_dpn2) * 1.5
        bentuk02 = (bentuk0 - bentuk2) * 1.5
        letak02 = (letak0 - letak2) * 1
        kls_jln02 = (kls_jln0 - kls_jln2) * 3
        persentase02 = ls_tnh02 + lb_dpn02 + bentuk02 + letak02 + kls_jln02
        nilai02 = ((nilai2) * (100 + persentase02))/100
        #nilai02 = ((nilai2 / ls_tnh22) * (100 + persentase02))/100
        list_02 = [ls_tnh02 , lb_dpn02 , bentuk02 , letak02 , kls_jln02]
        nilai_nol02 = list_02.count(0)

        #pembanding 3
        ls_tnh03 = (ls_tnh0 - ls_tnh3) * 0.5
        lb_dpn03 = (lb_dpn0 - lb_dpn3) * 1.5
        bentuk03 = (bentuk0 - bentuk3) * 1.5
        letak03 = (letak0 - letak3) * 1
        kls_jln03 = (kls_jln0 - kls_jln3) * 3
        persentase03 = ls_tnh03 + lb_dpn03 + bentuk03 + letak03 + kls_jln03
        nilai03 = ((nilai3) * (100 + persentase03))/100
        #nilai03 = ((nilai3 / ls_tnh33) * (100 + persentase03))/100
        list_03 = [ls_tnh03 , lb_dpn03 , bentuk03 , letak03 , kls_jln03]
        nilai_nol03 = list_03.count(0)

        #input OBJECT ID dari 3 persil pembanding yang dipilih
        list_data_pembanding = str(object_id1) + " ; " + str(object_id2) + " ; " + str(object_id3)
            
        #hitung nilai
        r_bobot1 = (nilai_nol01 / (nilai_nol01 + nilai_nol02 + nilai_nol03)) * 100
        r_bobot2 = (nilai_nol02 / (nilai_nol01 + nilai_nol02 + nilai_nol03)) * 100
        r_bobot3 = (nilai_nol03 / (nilai_nol01 + nilai_nol02 + nilai_nol03)) * 100

        n_setelahbobot1 = (nilai01 * r_bobot1) / 100
        n_setelahbobot2 = (nilai02 * r_bobot2) / 100
        n_setelahbobot3 = (nilai03 * r_bobot3) / 100

        nilai_pasar = n_setelahbobot1 + n_setelahbobot2 + n_setelahbobot3

        nilai_baru = nilai_pasar
        #nilai_baru = nilai_pasar * ls_tnh00

        for row in arcpy.SearchCursor("objek"):
            if (zonasi) != zonasi1:
                arcpy.AddMessage('Data pembanding 1 tidak memiliki zonasi yang sama dengan data yang akan dinilai')
                arcpy.AddError('Data pembanding 1 tidak memiliki zonasi yang sama dengan data yang akan dinilai')
            elif (zonasi) != zonasi2:
                arcpy.AddMessage('Data pembanding 2 tidak memiliki zonasi yang sama dengan data yang akan dinilai')
                arcpy.AddError('Data pembanding 2 tidak memiliki zonasi yang sama dengan data yang akan dinilai')
            elif (zonasi) != zonasi3:
                arcpy.AddMessage('Data pembanding 3 tidak memiliki zonasi yang sama dengan data yang akan dinilai')
                arcpy.AddError('Data pembanding 3 tidak memiliki zonasi yang sama dengan data yang akan dinilai')
            elif (persentase01) > 10:
                arcpy.AddMessage('Data pembanding 1 memiliki persentase lebih besar dari 10%')
                arcpy.AddError('Data pembanding 1 memiliki persentase lebih besar dari 10%')
            elif (persentase02) > 10:
                arcpy.AddMessage('Data pembanding 2 memiliki persentase lebih besar dari 10%')
                arcpy.AddError('Data pembanding 2 memiliki persentase lebih besar dari 10%')
            elif (persentase03) > 10:
                arcpy.AddMessage('Data pembanding 3 memiliki persentase lebih besar dari 10%')
                arcpy.AddError('Data pembanding 3 memiliki persentase lebih besar dari 10%')
            else:
                rowsa = arcpy.UpdateCursor (persil_path, "IdBidang = " + str(row.IdBidang))
                for rowa in rowsa:
                    rowa.setValue ("data_pembanding", list_data_pembanding)
                    rowa.setValue ("NILAI_LAMA", nilai_baru)
                    rowa.setValue ("perubahan", "individual")
                    rowsa.updateRow(rowa)
            del row
        
        #arcpy.AddMessage (nilai_baru)
        arcpy.AddMessage("Data yang akan dinilai memiliki jenis zonasi: " + nama_zonasi)
        arcpy.AddMessage("Data pembanding 1 memiliki zonasi: " + str(nama_zonasi1) + ". Persentase penyesuaian: " + str(persentase01) + "%, dengan OBJECTID: " + str(object_id1))
        arcpy.AddMessage("Data pembanding 2 memiliki zonasi: " + str(nama_zonasi2) + ". Persentase penyesuaian: " + str(persentase02) + "%, dengan OBJECTID: " + str(object_id2))
        arcpy.AddMessage("Data pembanding 3 memiliki zonasi: " + str(nama_zonasi3) + ". Persentase penyesuaian: " + str(persentase03) + "%, dengan OBJECTID: " + str(object_id3))
        arcpy.CalculateField_management(persil_path, "IdBidang", '!OBJECTID!', "PYTHON3")
        

        return
