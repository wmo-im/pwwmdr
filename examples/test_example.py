

# test a file on disk
from lxml import etree
from pywmdr.ats import WMDRTestSuite
from pywmdr.kpi import WMDRKeyPerformanceIndicators

#exml = etree.parse('examples/wmdr_example_facility_0-2008-0-JFJ.xml')
# #exml = etree.parse('examples/ndacc_0-20008-0-ARO.xml')
#exml = etree.parse('examples/20210823_0-124-34001-160_edit.xml')
# exml = etree.parse('examples/438aafa4-4200-47c5-98fe-1e11a2346680.xml')
#exml = etree.parse('/home/leyden/pywmdr/pywmdr/examples/wmdr_example_equipment_catalogue.xml')

# # test ATS
# ts = WMDRTestSuite(exml)
# ts.run_tests() 

exml = etree.parse('examples/wmdr_example_facility_0-2008-0-JFJ_kpi_2-0_100.xml')
kpi = WMDRKeyPerformanceIndicators(exml)
#kpi.kpi_2004()
## evaluate single kpi
kpi.evaluate(20)
## evaluate all kpis
results_all = kpi.evaluate()

