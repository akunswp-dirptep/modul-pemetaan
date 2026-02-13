import arcpy
# Helper: Get selected OIDs from layer
def get_selected_oids(layer):
    desc = arcpy.Describe(layer)
    if hasattr(desc, "FIDSet") and desc.FIDSet:
        return list(map(int, desc.FIDSet.replace(";", ",").split(",")))
    return []

# Fungsi ini mengidentifikasi field yang ada di source tapi tidak ada di target
def get_missing_fields(source_layer, target_layer):
    # Mendapatkan semua field yang editable dari source (kecuali Shape)
    source_fields = [f for f in arcpy.ListFields(source_layer) if f.editable and f.name != "Shape"]
    # Mendapatkan nama semua field dari target
    target_field_names = [f.name for f in arcpy.ListFields(target_layer)]
    # Return field yang ada di source tapi tidak ada di target
    return [f for f in source_fields if f.name not in target_field_names]

# Fungsi ini mencari field yang bisa diedit dan ada di kedua layer (kecuali field Shape)
def get_common_fields(source_layer, target_layer):
    # Mendapatkan semua field yang editable dari source (kecuali Shape)
    source_fields = [f for f in arcpy.ListFields(source_layer) if f.editable and f.name != "Shape"]
    # Mendapatkan nama semua field dari target
    target_fields = [f.name for f in arcpy.ListFields(target_layer)]
    # Return hanya field yang ada di kedua layer
    return [f.name for f in source_fields if f.name in target_fields]

def add_symbology():
    
    # Mendapatkan project ArcGIS yang sedang aktif
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    # Mendapatkan peta aktif dalam project
    m = aprx.activeMap

    # List untuk menyimpan nama semua layer yang ada di peta
    layname = []

    # Loop melalui semua layer dalam peta aktif
    for lay in m.listLayers():
        layname.append(lay.name)  # Menyimpan nama layer ke list
        lay.showLabels = False    # Mematikan label untuk semua layer

    # ======================
    # MENGATUR SIMBOL UNTUK LAYER "Titik_Sampel"
    # ======================
    if "Titik_Sampel" in layname:
        # Mendapatkan layer Titik_Sampel (layer pertama dengan nama tersebut)
        lyr = m.listLayers('Titik_Sampel')[0]

        # Memastikan layer adalah feature layer (bukan group layer atau lainnya)
        if lyr.isFeatureLayer:
            sym = lyr.symbology  # Mendapatkan objek simbologi layer
            
            # Memeriksa apakah layer memiliki renderer
            if hasattr(sym, 'renderer'):
                # Memeriksa apakah renderer adalah SimpleRenderer (simbol tunggal)
                if sym.renderer.type == 'SimpleRenderer':
                    # Mengaplikasikan simbol segitiga dari gallery simbol
                    sym.renderer.symbol.applySymbolFromGallery("Triangle 3")
                    
                    # Mengaplikasikan perubahan simbologi kembali ke layer
                    lyr.symbology = sym

    # ======================
    # MENGATUR SIMBOL UNTUK LAYER "Titik_Zona"
    # ======================
    if "Titik_Zona" in layname:
        # Mendapatkan layer Titik_Zona
        lyr = m.listLayers('Titik_Zona')[0]

        if lyr.isFeatureLayer:
            sym = lyr.symbology
            
            if hasattr(sym, 'renderer'):
                if sym.renderer.type == 'SimpleRenderer': 
                    # Mengatur warna simbol: Kuning transparan [R, G, B, Transparency]
                    sym.renderer.symbol.color = {'RGB' : [255, 255, 0, 100]}
                    # Mengatur ukuran simbol menjadi 7 points
                    sym.renderer.symbol.size = 7
                    
                    # Mengaplikasikan perubahan ke layer
                    lyr.symbology = sym

    # ======================
    # MENGATUR SIMBOL UNTUK LAYER "Titik_Sampel_Individual"
    # ======================
    if "Titik_Sampel_Individual" in layname:
        # Mendapatkan layer Titik_Sampel_Individual
        lyr = m.listLayers('Titik_Sampel_Individual')[0]

        if lyr.isFeatureLayer:
            sym = lyr.symbology
            
            if hasattr(sym, 'renderer'):
                if sym.renderer.type == 'SimpleRenderer':
                    # Mengaplikasikan simbol segitiga yang berbeda dari gallery
                    sym.renderer.symbol.applySymbolFromGallery("Triangle 1")
                    
                    # Mengaplikasikan perubahan ke layer
                    lyr.symbology = sym

    # Menyimpan perubahan pada project ArcGIS
    aprx.save()
    # Membersihkan memory dengan menghapus objek project
    del aprx
