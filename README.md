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
python3 -m ensurepip
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
>>> exml = etree.parse('examples/serafina.xml')
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

## Additional tools

### metrics.py

This program evaluates (all or selected) KPIS for all files matching a given path (accepts bash wildcards), saves the results as .json files and optionally computes statistics from the resulting scores, including percentiles and mean for each KPI and final score.

    $ python3 metrics.py --help
    usage: metrics.py [-h] [-o OUTPUT_DIR] [-m METRICS] [-k KPI] {evaluate,metrics} path

    Bulk evaluate WMDR KPIs. Compute metrics

    positional arguments:
    {evaluate,metrics}    action to perform: evaluate, metrics
    path                  path where to read wmdr files

    optional arguments:
    -h, --help            show this help message and exit
    -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                            optional. Save the results onto this location
    -m METRICS, --metrics METRICS
                            optional. Compute metrics and save the results onto this file
    -k KPI, --kpi KPI     optional. Compute selected kpi only

example:

    python3 metrics.py evaluate "data/records/*.xml" -o data/evaluations
    python3 metrics.py metrics "data/evaluations/*.json" -m metrics.json

### harvest_oai.py

This programs can be used to bulk download wmdr metadata records from a OAI REST endpoint (defaults to OSCAR)

    $ python3 harvest_oai.py --help
    usage: harvest_oai.py [-h] [-s SET_SPEC] [-e ENDPOINT] [-i IDENTIFIER]
                        {identifiers,records,record} output

    Bulk download WMDR records from OAI web service

    positional arguments:
    {identifiers,records,record}
                            action to perform.
                            - identifiers: request
                            record identifiers.
                            - records: request records.
                            - record: request record by identifier
    output                directory where to save results

    optional arguments:
    -h, --help            show this help message and exit
    -s SET_SPEC, --set_spec SET_SPEC
                            optional. Retrieve only records with the specified setSpec attribute
    -e ENDPOINT, --endpoint ENDPOINT
                            optional. OAI web service endpoint
    -i IDENTIFIER, --identifier IDENTIFIER
                            Record identifier. Valid only for action=record

Examples:

    python3 harvest_oai.py records data/records -s airFixed
    python3 harvest_oai.py record data/records -i 0-20000-0-15118