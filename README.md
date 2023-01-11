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

### metrics

This command evaluates (all or selected) KPIS for all files matching a given path (accepts bash wildcards), saves the results as .json files and optionally computes statistics from the resulting scores, including percentiles and mean for each KPI and final score.

    $ pywmdr metrics --help
    Usage: pywmdr metrics [OPTIONS] {evaluate|metrics} PATH

    Options:
        -o, --output_dir PATH       Save the results onto this location
        -m, --compute_metrics PATH  Compute metrics and save the results onto this
                                    file
        -k, --kpi INTEGER           Compute selected kpi only
        -s, --skip_schema_eval      skip evaluation of schema (kpi 1-01)
        --help                      Show this message and exit.
example:

    pywmdr metrics evaluate "data/records/*.xml" -o data/evaluations
    pywmdr metrics metrics "data/evaluations/*.json" -m metrics.json

### harvest

This command can be used to bulk download wmdr metadata records from a OAI REST endpoint (defaults to OSCAR)

    $ pywmdr harvest --help
    Usage: pywmdr harvest [OPTIONS] {identifiers|records|record} OUTPUT

    Bulk download WMDR records from OAI web service

    ACTION is the action to perform. Options are

        - identifiers: request record identifiers.

        - records: request records.

        - record: request record by identifier"

    OUTPUT is the directory where to save results

    Options:
    -s, --set_spec TEXT         Retrieve only records with the specified setSpec
                                attribute
    -e, --endpoint TEXT         OAI web service endpoint
    -i, --identifier TEXT       Record identifier. Valid only for action=record
    -p, --metadata_prefix TEXT  Metadata prefix. Defaults to wmdr
    --help                      Show this message and exit.
Examples:

    pywmdr harvest records data/records -s airFixed
    pywmdr harvest record data/records -i 0-20000-0-15118
