from qgis.utils import iface
import processing

alle_lag_name = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]

if 'Punkt tættest på skel' in alle_lag_name:
    lyr = QgsProject.instance().mapLayersByName('Punkt tættest på skel')[0]
    QgsProject.instance().removeMapLayer(lyr.id())

# Find bygninger of clicked feature
lyr_bygninger = QgsProject.instance().mapLayer('[% @layer_id %]')
bygning_feature = lyr_bygninger.getFeature([% $id %])
lyr_bygninger.selectByIds([bygning_feature.id()])

lyr_list = [f for f in QgsProject.instance().mapLayers().values() if 'jordstykke' in f.name().lower()]

jordstykke_lyr = lyr_list[0]
jordstykke_features = [f.id() for f in jordstykke_lyr.getFeatures() if f.geometry().intersects(bygning_feature.geometry())]
jordstykke_lyr.selectByIds(jordstykke_features)
if len(jordstykke_features) > 1:
    iface.messageBar().pushMessage('Hov!','Bygning krydser matrikelgrænse', level=Qgis.Warning, duration=10)

# Forbered bygningfeature
args = {
    'INPUT': QgsProcessingFeatureSourceDefinition('[% @layer_id %]', True),
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
b_line = processing.run('native:polygonstolines', args)['OUTPUT']
b_exploded = processing.run('native:explodelines', args)['OUTPUT']
b_vertices = processing.run('native:extractvertices', args)['OUTPUT']
fields = b_vertices.dataProvider().fields()
b_vertices.dataProvider().deleteAttributes([fields.lookupField('distance')])
b_vertices.updateFields()

# Forbered jordstykke
args = {
    'INPUT': QgsProcessingFeatureSourceDefinition(jordstykke_lyr.id(), True),
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
j_lines = processing.run("native:polygonstolines", args)['OUTPUT']

jordstykke_lyr.removeSelection()
lyr_bygninger.removeSelection()

alg_args = {
    'INPUT': b_vertices,
    'INPUT_2': j_lines,
    'OUTPUT': 'TEMPORARY_OUTPUT'
}

join_nearest = processing.run('native:joinbynearest', alg_args)['OUTPUT']
#QgsProject.instance().addMapLayer(join_nearest)

# Fjern dupletter
alg_args = {
    'INPUT': join_nearest,
    'FIELDS': ['distance','feature_x','feature_y','nearest_x','nearest_y'],
    'OUTPUT': 'TEMPORARY_OUTPUT'
}

duplicates_removed = processing.run('native:removeduplicatesbyattribute', alg_args)['OUTPUT']
#QgsProject.instance().addMapLayer(duplicates_removed)

# Lav en linjegeometri ud af punkterne
alg_args = {
    'INPUT': duplicates_removed,
    'OUTPUT_GEOMETRY': 1,
    'EXPRESSION': 'make_line(make_point( attribute(\'feature_x\') ,  attribute(\'feature_y\') ), make_point( attribute(\'nearest_x\') , attribute(\'nearest_y\') ))',
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
linje_geoms = processing.run('native:geometrybyexpression', alg_args)['OUTPUT']
#QgsProject.instance().addMapLayer(linje_geoms)

# auto incremental field til at finde det korteste i en bygning
alg_args = {
    'INPUT': linje_geoms,
    'FIELD_NAME': 'RANK',
    'START': 1,
    'GROUP_FIELDS': ['fid'],
    'OUTPUT': 'TEMPORARY_OUTPUT',
    'SORT_EXPRESSION': QgsExpression('\'distance\'').evaluate()
}
auto_inc = processing.run('native:addautoincrementalfield', alg_args)['OUTPUT']
#QgsProject.instance().addMapLayer(auto_inc)

# Find de korteste, som har fået RANK = 1 i auto inc
alg_args = {
    'INPUT': auto_inc,
    'FIELD': 'RANK',
    'VALUE': '1',
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
results = processing.run('native:extractbyattribute', alg_args)['OUTPUT']
results.setName('Punkt tættest på skel')
args = {
    'INPUT': results,
    'STYLE': 'Y:\\Arbejdsmappe\\Daníel Örn Árnason\\QGIS\\byg_skel\\nearest.qml'
}
processing.run('native:setlayerstyle', args)
QgsProject.instance().addMapLayer(results)
iface.setActiveLayer(lyr_bygninger)
