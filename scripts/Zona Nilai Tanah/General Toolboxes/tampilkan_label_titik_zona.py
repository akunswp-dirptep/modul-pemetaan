# ======================
# ENVIRONMENT SETTINGS
# ======================
import arcpy, sys

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap

# ======================
# MENDEKLARASIKAN NILAI DEFAULT
# ======================
titik_zona_dan_outlier_code = """def FindLabel([indeks_sampel], [Nomor_Entry], [nilai]):
    angka = float(str([nilai]).replace(',', '.'))
    rupiah = f"{int(round(angka)):,}".replace(",", ".")

    return (
        "<FNT size='7'>"
        "Indeks: " + str([indeks_sampel]) + "\\n"
        "Nomor Entry: " + str([Nomor_Entry]) + "\\n"
        "Rp " + rupiah +
        "</FNT>"
    )
    """

zona_layer_labelling_code = """ "<FNT size = '8'>" + ([NILBULAT_LAMA].replace(',', '.')).replace(' ', '') + "</FNT>" """

# ======================
# USER INPUT
# ======================
metode = arcpy.GetParameterAsText(0)

# ======================
# MAIN PROCESSING
# ======================
layname = []
for lay in m.listLayers():
    layname.append(lay.name)
    lay.showLabels = False

if metode == 'Zona Terpilih':     
    ada_seleksi = len(arcpy.Describe('Zona_Layer').FIDSet)
    if ada_seleksi <= 0:
        arcpy.AddError("Tidak ada fitur yang dipilih.")
        sys.exit(1)
    else:
        arcpy.AddMessage(f'Jumlah zona terpilih: {ada_seleksi}')
        list_object_id = []
        with arcpy.da.SearchCursor('Zona_Layer', ["OID@", "OBJECTID"]) as cursor:
            for oid, objectid in cursor:
                list_object_id.append(objectid)
        
        arcpy.AddMessage(f'Zona yang dipilih: {list_object_id}')
        ids = tuple(list_object_id)
        
        titik_zona_dan_outlier_code = """def FindLabel([indeks_sampel], [Nomor_Entry], [nilai], [FID_Zona_Layer]):
            angka = float(str([nilai]).replace(',', '.'))
            rupiah = f"{int(round(angka)):,}".replace(",", ".")
            if int([FID_Zona_Layer]) in """ + str(ids) + """:        
                return (
                    "<FNT size='7'>"
                    "Indeks: " + str([indeks_sampel]) + "\\n"
                    "Nomor Entry: " + str([Nomor_Entry]) + "\\n"
                    "Rp " + rupiah +
                    "</FNT>"
                )
            else:
                return ("")
        """
        zona_layer_labelling_code = """ ("<FNT size = '8'>" + ([NILBULAT_LAMA].replace(',', '.')).replace(' ', '') + "</FNT>" if  int([OBJECTID]) in {} else "") """.format(ids)


# Simbologi Zona Layer dan Titik Zona hanya muncul di Pembaruan
if "Zona_Layer" in layname:
    l3 = m.listLayers('Zona_Layer')[0]

    # show label
    l3.showLabels = True

    # Get CIM definition
    l_cim3 = l3.getDefinition('V3')
    lc3 = l_cim3.labelClasses[0]

    # Create a colour
    fillRGBColour = arcpy.cim.CreateCIMObjectFromClassName('CIMRGBColor', 'V3')
    fillRGBColour.values = [255,255,255, 100]

    # Create a fill
    solFill = arcpy.cim.CreateCIMObjectFromClassName('CIMSolidFill', 'V3')
    solFill.color = fillRGBColour
    solFill.enable = True
    solFill.colorlocked = False
    solFill.overprint = False

    # Create a polygon symbol and set its symbol layers
    sym = arcpy.cim.CreateCIMObjectFromClassName('CIMPolygonSymbol', 'V3')
    sym.symbolLayers = [solFill]
    lc3.textSymbol.symbol.haloSize = 1.5
    lc3.textSymbol.symbol.haloSymbol = sym

    # update expression language
    lc3.expressionEngine = 'Python'

    #update expression
    lc3.expression = zona_layer_labelling_code

    # Update CIM defintion
    l3.setDefinition(l_cim3)
    
    for lyr in m.listLayers("Zona_Layer"):
        lblClass = lyr.listLabelClasses()[0]
        lyr.showLabels = True


if "Titik_Zona" in layname:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    ltz = m.listLayers("Titik_Zona")[0]

    # Show labels
    ltz.showLabels = True

    # Get CIM definition
    l_cim2 = ltz.getDefinition('V3')
    lc2 = l_cim2.labelClasses[0]

    # Create halo colour
    fillRGBColour = arcpy.cim.CreateCIMObjectFromClassName('CIMRGBColor', 'V2')
    fillRGBColour.values = [255, 255, 255, 100]

    # Create halo fill
    solFill = arcpy.cim.CreateCIMObjectFromClassName('CIMSolidFill', 'V2')
    solFill.color = fillRGBColour
    solFill.enable = True

    # Create halo symbol
    sym = arcpy.cim.CreateCIMObjectFromClassName('CIMPolygonSymbol', 'V2')
    sym.symbolLayers = [solFill]

    # Set label engine to Python (Advanced)
    lc2.expressionEngine = 'Python'

    # === LABEL EXPRESSION ===
    lc2.expression = titik_zona_dan_outlier_code

    # Halo settings
    lc2.textSymbol.symbol.haloSize = 1.5
    lc2.textSymbol.symbol.haloSymbol = sym

    # Apply CIM
    ltz.setDefinition(l_cim2)

    aprx.save()
    del aprx