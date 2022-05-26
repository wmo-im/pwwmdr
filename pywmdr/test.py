# test a file on disk
from lxml import etree
#from pywmdr.ats import WMDRTestSuite
from pywmdr.kpi import WMDRKeyPerformanceIndicators

# tests for validating the pywmdr tool

class Test:
    def __init__(self):
        pass

    tests = [
        "t_3300", "t_3300n", "t_3301", "t_3301n", "t_3302", "t_3302n"
    ]

    def t_3300(self):
        print("test kpi 3-3 rule 0 SamplingStrategy ok")
        exml = etree.parse('examples/wmdr_example_for_test.xml')
        kpi = WMDRKeyPerformanceIndicators(exml)
        dataGenerations = exml.xpath('./wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation/om:procedure/wmdr:Process/wmdr:deployment/wmdr:Deployment/wmdr:dataGeneration/wmdr:DataGeneration',namespaces=kpi.namespaces)
        results = kpi.kpi_3300(dataGenerations[0],1) # should return total 1, score 1 and no comments
        print(results)
        if results[0] == 1 and results[1] == 1 and not len(results[2]):
            print("Pass")
            return True
        else:
            print("Fail")
            return False

    def t_3300n(self):
        print("test kpi 3-3 rule 0 SamplingStrategy not in codelist")
        exml = etree.parse('examples/wmdr_example_for_test.xml')
        kpi = WMDRKeyPerformanceIndicators(exml)
        dataGenerations = exml.xpath('./wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation/om:procedure/wmdr:Process/wmdr:deployment/wmdr:Deployment/wmdr:dataGeneration/wmdr:DataGeneration',namespaces=kpi.namespaces)
        results = kpi.kpi_3300(dataGenerations[1],2) # should return total 1, score 0 and comments
        print(results)
        if results[0] == 1 and results[1] == 0 and len(results[2]):
            print("Pass")
            return True
        else:
            print("Fail")
            return False
    
    def t_3301(self):
        print("test kpi 3-3 rule 1 temporalSamplingInterval ok")
        exml = etree.parse('examples/wmdr_example_for_test.xml')
        kpi = WMDRKeyPerformanceIndicators(exml)
        dataGenerations = exml.xpath('./wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation/om:procedure/wmdr:Process/wmdr:deployment/wmdr:Deployment/wmdr:dataGeneration/wmdr:DataGeneration',namespaces=kpi.namespaces)
        results = kpi.kpi_3301(dataGenerations[0],1) # should return total 1, score 1 and no comments
        print(results)
        if results[0] == 1 and results[1] == 1 and len(results[2]) == 0:
            print("Pass")
            return True
        else:
            print("Fail")
            return False
    
    def t_3301n(self):
        print("test kpi 3-3 rule 1 temporalSamplingInterval not found")
        exml = etree.parse('examples/wmdr_example_for_test.xml')
        kpi = WMDRKeyPerformanceIndicators(exml)
        dataGenerations = exml.xpath('./wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation/om:procedure/wmdr:Process/wmdr:deployment/wmdr:Deployment/wmdr:dataGeneration/wmdr:DataGeneration',namespaces=kpi.namespaces)
        results = kpi.kpi_3301(dataGenerations[1],2) # should return total 1, score 0 and comments
        print(results)
        if results[0] == 1 and results[1] == 0 and len(results[2]) > 0:
            print("Pass")
            return True
        else:
            print("Fail")
            return False

    def t_3302(self):
        print("test kpi 3-3 rule 2 samplingTimePeriod ok")
        exml = etree.parse('examples/wmdr_example_for_test.xml')
        kpi = WMDRKeyPerformanceIndicators(exml)
        dataGenerations = exml.xpath('./wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation/om:procedure/wmdr:Process/wmdr:deployment/wmdr:Deployment/wmdr:dataGeneration/wmdr:DataGeneration',namespaces=kpi.namespaces)
        results = kpi.kpi_3302(dataGenerations[0],1) # should return total 1, score 1 and no comments
        print(results)
        if results[0] == 1 and results[1] == 1 and len(results[2]) == 0:
            print("Pass")
            return True
        else:
            print("Fail")
            return False
    
    def t_3302n(self):
        print("test kpi 3-3 rule 2 samplingTimePeriod not found")
        exml = etree.parse('examples/wmdr_example_for_test.xml')
        kpi = WMDRKeyPerformanceIndicators(exml)
        dataGenerations = exml.xpath('./wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation/om:procedure/wmdr:Process/wmdr:deployment/wmdr:Deployment/wmdr:dataGeneration/wmdr:DataGeneration',namespaces=kpi.namespaces)
        results = kpi.kpi_3302(dataGenerations[1],2) # should return total 1, score 0 and comments
        print(results)
        if results[0] == 1 and results[1] == 0 and len(results[2]) > 0:
            print("Pass")
            return True
        else:
            print("Fail")
            return False
        
    def run(self,test_id=None):
        if test_id:
            if test_id not in self.tests:
                raise Exception("invalid test_id")
            return getattr(self,test_id)()
        else:
            return [getattr(self,test_id)() for test_id in self.tests]

if __name__ == "__main__":
    test = Test()
    results = test.run()
    print(results)