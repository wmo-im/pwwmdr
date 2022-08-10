# pywmdr

This is a python implementation of the WIGOS Metadata Representation Key Performance Indicators (WMDR KPIs).

## Installation

### From source

Install latest development version.

```bash
python3 -m venv pywmdr
cd pywmdr
. bin/activate
git clone https://github.com/wmo-im/pywmdr.git
cd pywmdr
pip3 install -r requirements.txt
python3 setup.py build
python3 setup.py install
```
## Running 
From command line:
```bash
# fetch version
pywmdr --version

# abstract test suite

# validate metadata against abstract test suite (file on disk)
pywmdr ats validate --file /path/to/file.xml
# validate metadata against abstract test suite (URL)
pywmdr ats validate --url http://example.org/path/to/file.xml

# adjust debugging messages (CRITICAL, ERROR, WARNING, INFO, DEBUG) to stdout
pywmdr ats validate --url http://example.org/path/to/file.xml --verbosity DEBUG

# write results to logfile
pywmdr ats validate --url http://example.org/path/to/file.xml --verbosity DEBUG --logfile /tmp/foo.txt

# key performance indicators

# all key performance indicators at once # note: running KPIs automatically runs the ats
pywmdr kpi validate --url http://example.org/path/to/file.xml --verbosity DEBUG

# all key performance indicators at once, in summary
pywmdr kpi validate --url http://example.org/path/to/file.xml --verbosity DEBUG --summary

# all key performance indicators at once, with scoring rubric grouping
pywmdr kpi validate --url http://example.org/path/to/file.xml --verbosity DEBUG --group

# selected key performance indicator
pywmdr kpi validate --kpi 20 -f /path/to/file.xml -v INFO
```
Using the API:
```pycon
>>> # test a file on disk
>>> from lxml import etree
>>> from pywmdr.ats import WMDRTestSuite
>>> exml = etree.parse('examples/ndacc_0-20008-0-ARO.xml')
>>> # test ATS
>>> ts = WMDRTestSuite(exml)
>>> ts.run_tests() 
>>> # test a URL
>>> from urllib2 import urlopen
>>> from StringIO import StringIO
>>> content = StringIO(urlopen('http://....').read())
>>> exml = etree.parse(content)
>>> ts = WMDRTestSuite(exml)
>>> ts.run_tests()  # raises ValueError error stack on exception
>>> # handle ats.TestSuiteError
>>> # ats.TestSuiteError.errors is a list of errors
>>> try:
...    ts.run_tests()
... except ats.TestSuiteError as err:
...    print('\n'.join(err.errors))
>>> ...
>>> # test KPI
>>> from pywcmp.kpi import WMDRKeyPerformanceIndicators
>>> kpis = WMDRKeyPerformanceIndicators(exml)
>>> results = kpis.evaluate()
>>> results['summary']
>>> # scoring rubric
>>> grouped = group_kpi_results(results)
```

KPI definitions being developed on this branch: https://github.com/wmo-im/wmdr/tree/issue42
