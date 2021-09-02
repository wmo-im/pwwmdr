

# test a file on disk
from lxml import etree
from pywmdr.ats import WMDRTestSuite
#exml = etree.parse('examples/ndacc_0-20008-0-ARO.xml')
exml = etree.parse('examples/wmdr_example_facility_0-2008-0-JFJ.xml')
# test ATS
ts = WMDRTestSuite(exml)
ts.run_tests() 

from pywmdr.kpi import WMDRKeyPerformanceIndicators
kpi = WMDRKeyPerformanceIndicators(exml)
# evaluate single kpi
results = kpi.evaluate(2000)
# evaluate all kpis
results_all = kpi.evaluate()