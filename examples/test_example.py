

# test a file on disk
from lxml import etree
from pywmdr.ats import WMDRTestSuite
from pywmdr.kpi import WMDRKeyPerformanceIndicators

exml = etree.parse('examples/wmdr_example_facility_0-2008-0-JFJ.xml')

# #exml = etree.parse('examples/ndacc_0-20008-0-ARO.xml')
# # test ATS
# ts = WMDRTestSuite(exml)
# ts.run_tests() 

kpi = WMDRKeyPerformanceIndicators(exml)
# evaluate single kpi
results = kpi.evaluate(20)
# evaluate all kpis
results_all = kpi.evaluate()

