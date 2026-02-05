import arcpy, sys

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap

layname = []
for lay in m.listLayers():
    layname.append(lay.name)
    lay.showLabels = False

if "Titik_Sampel" in layname:
    l2 = m.listLayers('Titik_Sampel')[0]

    # show label
    l2.showLabels = True

    # Get CIM definition
    l_cim2 = l2.getDefinition('V3')

    lc2 = l_cim2.labelClasses[0]

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

    # Use Arcade expression (more robust in ArcGIS Pro 3.6)
    lc2.expressionEngine = 'Arcade'

    # Arcade expression: handle nulls and format with dot as thousand separator
    code = (
        "var v = $feature.nilai;\n"
        "if (IsEmpty(v) || v == null) { return ''; }\n"
        "return 'Rp ' + Replace(Text(v, '#,###'), ',', '.');"
    )
    lc2.expression = code

    # Update text symbol: size and color (black) and halo
    try:
        lc2.textSymbol.symbol.font.size = 8
    except Exception:
        pass
    try:
        black = arcpy.cim.CreateCIMObjectFromClassName('CIMRGBColor', 'V3')
        black.values = [0, 0, 0, 255]
        lc2.textSymbol.symbol.color = black
    except Exception:
        pass
    lc2.textSymbol.symbol.haloSize = 2
    lc2.textSymbol.symbol.haloSymbol = sym

    # Update CIM defintion
    l2.setDefinition(l_cim2)

    aprx.save()
    del aprx 

    
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
    lc3.expression = r'"{}" + {} +  "{}"'.format("<FNT size = '8'>", "([NILBULAT_LAMA].replace(',', '.')).replace(' ', '')", "</FNT>")

    # Update CIM defintion
    l3.setDefinition(l_cim3)
    
    for lyr in m.listLayers("Zona_Layer"):
        lblClass = lyr.listLabelClasses()[0]
        lyr.showLabels = True
