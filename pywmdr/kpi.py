# =================================================================
#
# Terms and Conditions of Use
#
# Unless otherwise noted, computer program source code of this
# distribution is covered under Crown Copyright, Government of
# Canada, and is distributed under the MIT License.
#
# The Canada wordmark and related graphics associated with this
# distribution are protected under trademark law and copyright law.
# No permission is granted to use them outside the parameters of
# the Government of Canada's corporate identity program. For
# more information, see
# http://www.tbs-sct.gc.ca/fip-pcim/index-eng.asp
#
# Copyright title to all 3rd party software distributed with this
# software is held by the respective copyright holders as noted in
# those files. Users are asked to read the 3rd Party Licenses
# referenced with those assets.
#
# Copyright (c) 2021 Government of Canada
# Copyright (c) 2020-2021 IBL Software Engineering spol. s r. o.
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

# WMO Core Metadata Profile Key Performance Indicators (KPIs)

from io import BytesIO
import json
import os
import logging
import re

from bs4 import BeautifulSoup
import click
# from spellchecker import SpellChecker

from pywmdr.ats import TestSuiteError, WMDRTestSuite
from pywmdr.util import (get_cli_common_options, get_keyword_info,
                         get_string_or_anchor_value, get_string_or_anchor_values,
                         nspath_eval, parse_time_position, parse_wmdr,
                         setup_logger, urlopen_, check_url, get_codelists_from_rdf, get_region) # get_codelists, 

LOGGER = logging.getLogger(__name__)

# round percentages to x decimal places
ROUND = 3

THISDIR = os.path.dirname(os.path.realpath(__file__))


class WMDRKeyPerformanceIndicators:
    """Key Performance Indicators for WMDR"""

    def __init__(self, exml):
        """
        initializer

        :param exml: `etree.ElementTree` object

        :returns: `pywmdr.kpi.WMDRKeyPerformanceIndicators`
        """

        self.exml = exml  # serialized already
        self.namespaces = self.exml.getroot().nsmap

        # remove empty (default) namespace to avoid exceptions in exml.xpath
        if None in self.namespaces:
            LOGGER.debug('Removing default (None) namespace. This XML is destined to fail.')
            none_namespace = self.namespaces[None]
            self.namespaces[none_namespace.split('/')[-1]] = none_namespace
            self.namespaces.pop(None)

        # add namespace that our Xpath searches depend on but that may not exist in certain documents
        if 'gmx' not in self.namespaces:
            self.namespaces['gmx'] = 'http://www.isotc211.org/2005/gmx'

        # generate dict of codelists
        self.codelists = get_codelists_from_rdf()

    @property
    def identifier(self):
        """
        Helper function to derive a metadata record identifier

        :returns: metadata record identifier
        """

#        xpath = '//gmd:fileIdentifier/gco:CharacterString/text()'
        xpath = '/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/gml:identifier/text()'
        matches = self.exml.xpath(xpath, namespaces=self.namespaces)
        if len(matches):
            return matches[0]
        else:
            return ""

    # def _check_spelling(self, text: str) -> list:
    #     """
    #     Helper function to spell check a string

    #     :returns: `list` of unknown / misspelled words
    #     """

    #     LOGGER.debug(f'Spellchecking {text}')
    #     spell = SpellChecker()

    #     dictionary = f'{THISDIR}/dictionary.txt'
    #     LOGGER.debug(f'Loading custom dictionary {dictionary}')
    #     spell.word_frequency.load_text_file(f'{dictionary}')

    #     return list(spell.unknown(spell.split_words(text)))

    def _get_link_lists(self) -> set:
        """
        Helper function to retrieve all link elements (gmx:Anchor, gmd:URL, ...)

        :returns: `set` containing strings (URLs)
        """

        links = []

        # add possibly missing namespace
        xpath_namespaces = self.namespaces
        if xpath_namespaces.get('gmx') is None:
            xpath_namespaces['gmx'] = 'http://www.isotc211.org/2005/gmx'
        if xpath_namespaces.get('xlink') is None:
            xpath_namespaces['xlink'] = 'http://www.w3.org/1999/xlink'

        xpaths = [
            '//gmd:URL/text()',
            '//gmx:Anchor/@xlink:href',
            '//gmd:CI_DateTypeCode/@codeList',
            '//gmd:graphicOverview/gmd:MD_BrowseGraphic/gmd:fileName/gco:CharacterString/text()'
        ]

        for xpath in xpaths:
            new_links = self.exml.xpath(xpath, namespaces=xpath_namespaces)
            LOGGER.debug(f'Found {len(new_links)} links with {xpath}')
            links += new_links

        return set(links)

    def kpi_10(self) -> tuple:
        """
        Implements KPI-1-0-00: WMDR compliance

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        name = 'KPI-1: WMDR Compliance'

        LOGGER.info(f'Running {name}')
        LOGGER.debug('Running ATS tests')
        ts = WMDRTestSuite(self.exml)

        total = 1
        comments = []

        # run the tests
        try:
            ts.run_tests()
            score = 1
        except TestSuiteError as err:
            score = total - len(err.errors)
            comments = err.errors

        return name, total, score, comments

    def kpi_20(self) -> tuple:
        """
        Implements KPI-2-0: Station characteristics

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 0
        score = 0
        comments = []
        name = 'KPI-2-0: station characteristics'
        LOGGER.info(f'Running {name}')

        # Rule 2-0-00: Coordinates
        stotal, sscore, scomments = self.kpi_2000()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 2-0-00: wmoRegion
        stotal, sscore, scomments = self.kpi_2001()
        total += stotal
        score += sscore
        comments = comments + scomments 

        return name, total, score, comments

    def kpi_2000(self):
        # Rule 2-0-00: Coordinates
        # 2-0-00-a: A geopositioning method is specified and not "unknown".
        total = 2 # len(self.exml.xpath('/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation',namespaces=self.namespaces))*2
        # NOTE: only first matching observingFacility is evaluated
        score = 0
        comments = []

        xpath = '/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation/wmdr:GeospatialLocation/wmdr:geopositioningMethod'

        LOGGER.debug(f'Rule: A geopositioning method is specified and not "unknown"')

        matches = self.exml.xpath(xpath, namespaces=self.namespaces)

        if not len(matches):
            LOGGER.debug("geopositioningMethod not found")
            comments.append("geopositioningMethod not found")
        else:
            m = matches[0]
            href = m.get('{http://www.w3.org/1999/xlink}href')
            if href:
                LOGGER.debug('href attribute of geopositioningMethod is present')
                score += 1

        LOGGER.debug(f'Rule: The begin position of valid period is specified.')

        xpath = '/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation/wmdr:GeospatialLocation/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'

        matches = self.exml.xpath(xpath, namespaces=self.namespaces)

        if not len(matches):
            LOGGER.debug("beginPosition not found")
            comments.append("beginPosition not found")
        else:
            m = matches[0]
            text = m.text
            if text:
                LOGGER.debug('beginPosition is specified')
                score += 1
        
        return total, score, comments
    
    def kpi_2001(self):
        # Rule 2-0-01: WMO Region
        # A WMO region (code list: http://codes.wmo.int/wmdr/WMORegion) is specified and it matches the coordinates.

        total = 1
        score = 0
        comments = []

        xpath = '/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/wmdr:wmoRegion'

        matches = self.exml.xpath(xpath, namespaces=self.namespaces)

        if not len(matches):
            LOGGER.debug("wmoRegion not found")
            comments.append("wmoRegion not found")
            return total, score, comments

        m = matches[0]
        if nspath_eval('xlink:href') in m.attrib and m.get(nspath_eval('xlink:href')) != "":
            wmoregion = m.get(nspath_eval('xlink:href'))
            getNotation = False
        elif m.text == "":
            LOGGER.debug("wmoRegion is empty")
            comments.append("wmoRegion is empty")
            return total, score, comments
        else:
            wmoregion = m.text
            getNotation = True

        print('found region %s' % wmoregion) # text}')

        if wmoregion not in self.codelists['WMORegion']:
            LOGGER.debug('wmoRegion not present in codelist')
            comments.append('wmoRegion not present in codelist')
            return total, score, comments

        ## get the coordinates
        xpath = '/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation/wmdr:GeospatialLocation/wmdr:geoLocation/gml:Point/gml:pos'
        match = self.exml.xpath(xpath,namespaces=self.namespaces)
        if not len(match):
            xpath = '/wmdr:WIGOSMetadataRecord/wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation/wmdr:GeospatialLocation/wmdr:geoLocation/gml:Point/gml:coordinates'
            match = self.exml.xpath(xpath,namespaces=self.namespaces)
            if not len(match):
                LOGGER.debug("Missing wmdr:geoLocation/gml:Point/gml:pos")
                comments.append("Missing wmdr:geoLocation/gml:Point/gml:pos")
            else:
                LOGGER.debug("gml:coordinates is deprecated. Use gml:pos")
                comments.append("gml:coordinates is deprecated. Use gml:pos")
            return total, score, comments

        coords = match[0].text.split(" ")
        
        if len(coords) < 2:
            LOGGER.debug("gml:pos is missing values")
            comments.append("gml:pos is missing values")
            return total, score, comments

        lon = float(coords[1])
        lat = float(coords[0])

        # check if region matches the coordinates
        region_from_pos = get_region(lon,lat,getNotation)
        print(coords,lon,lat,region_from_pos,wmoregion)
        if region_from_pos != wmoregion:
            LOGGER.debug("region doesnt match coordinates")
            comments.append("region doesnt match coordinates")
        else:
            score += 1
        return total, score, comments

    def evaluate(self, kpi: int = 0) -> dict:
        """
        Convenience function to run all tests

        :returns: `dict` of overall test report
        """

        known_kpis = [
            # 'kpi_10',
            'kpi_20',
        ]

        kpis_to_run = known_kpis

        if kpi != 0:
            selected_kpi = f'kpi_{kpi:02}'
            if selected_kpi not in known_kpis:
                msg = f'Invalid KPI number: {selected_kpi} is not in {known_kpis}'
                LOGGER.error(msg)
                raise ValueError(msg)
            else:
                kpis_to_run = [selected_kpi]

        LOGGER.info(f'Evaluating KPIs: {kpis_to_run}')

        results = {}

        for kpi in kpis_to_run:
            LOGGER.debug(f'Running {kpi}')
            result = getattr(self, kpi)()
            LOGGER.debug(f'Raw result: {result}')
            LOGGER.debug('Calculating result')
            try:
                percentage = round(float((result[2] / result[1]) * 100), ROUND)
            except ZeroDivisionError:
                percentage = None

            results[kpi] = {
                'name': result[0],
                'total': result[1],
                'score': result[2],
                'comments': result[3],
                'percentage': percentage
            }
            LOGGER.debug(f'{kpi}: {result[1]} / {result[2]} = {percentage}')

        # the summary only if more than one KPI was evaluated
        if len(kpis_to_run) > 1:
            LOGGER.debug('Calculating total results')
            results['summary'] = generate_summary(results)
            # this total summary needs extra elements
            results['summary']['identifier'] = self.identifier,
            overall_grade = 'F'
            # if results['kpi_1000']['percentage'] != 100:
            #     overall_grade = 'U'
            # else:
            overall_grade = calculate_grade(results['summary']['percentage'])
            results['summary']['grade'] = overall_grade

        return results


def generate_summary(results: dict) -> dict:
    """
    Genrerates a summary entry for given group of results

    :param results: results to generate the summary from
    """

    sum_total = sum(v['total'] for v in results.values())
    sum_score = sum(v['score'] for v in results.values())
    comments = {k: v['comments'] for k, v in results.items() if v['comments']}

    try:
        sum_percentage = round(float((sum_score / sum_total) * 100), ROUND)
    except ZeroDivisionError:
        sum_percentage = None

    summary = {
        'total': sum_total,
        'score': sum_score,
        'comments': comments,
        'percentage': sum_percentage,
    }

    return summary


def calculate_grade(percentage: float) -> str:
    """
    Calculates letter grade from numerical score

    :param percentage: float between 0-100
    """
    grade = 'F'

    if percentage is None:
        grade = None
    elif percentage > 100 or percentage < 0:
        raise ValueError('Invalid percentage')
    elif percentage >= 80:
        grade = 'A'
    elif percentage >= 65:
        grade = 'B'
    elif percentage >= 50:
        grade = 'C'
    elif percentage >= 35:
        grade = 'D'
    elif percentage >= 20:
        grade = 'E'

    return grade


def group_kpi_results(kpis_results: dict) -> dict:
    """
    Groups KPI results by category

    :param kpis_results: the results to be grouped
    """

    grouped_kpi_results = {}
    # grouped_kpi_results['mandatory'] = {k: kpis_results[k] for k in ['kpi_1000'] if kpis_results.get(k)}

    categories = {
        # "mandatory": [1000],
        "station_characteristics": [2000, 2001],    
        # "observations_measurements": [3000],
        # "station_contacts": [4000],
        # "bibliographic_references_and_documents": [5000],
        # "value_of_a_station_for_WIGOS": [6000]    
    }

    for key, kpis in categories.items():
        subset = {f'kpi_{k:04}': kpis_results[f'kpi_{k:04}'] for k in kpis}
        grouped_kpi_results[key] = subset
        grouped_kpi_results[key]['summary'] = generate_summary(subset)
    
    # copy the total summary as-is
    if kpis_results['summary']:
        grouped_kpi_results['summary'] = kpis_results['summary']

    return grouped_kpi_results


@click.group()
def kpi():
    """key performance indicators"""
    pass


@click.command()
@click.pass_context
@get_cli_common_options
@click.option('--file', '-f', 'file_',
              type=click.Path(exists=True, resolve_path=True),
              help='Path to XML file')
@click.option('--summary', '-s', is_flag=True, default=False,
              help='Provide summary of KPI test results')
@click.option('--group', '-g', is_flag=True, default=False,
              help='Group KPIs by into categories')
@click.option('--url', '-u', help='URL of XML file')
@click.option('--kpi', '-k', default=0, help='KPI to run, default is all')
def validate(ctx, file_, summary, group, url, kpi, logfile, verbosity):
    """run key performance indicators"""

    if file_ is None and url is None:
        raise click.UsageError('Missing --file or --url options')

    setup_logger(verbosity, logfile)

    if file_ is not None:
        content = file_
        msg = f'Validating file {file_}'
        LOGGER.info(msg)
        click.echo(msg)
    elif url is not None:
        content = BytesIO(urlopen_(url).read())

    try:
        exml = parse_wmdr(content)
    except Exception as err:
        raise click.ClickException(err)

    kpis = WMDRKeyPerformanceIndicators(exml)

    try:
        kpis_results = kpis.evaluate(kpi)
    except ValueError as err:
        raise click.UsageError(f'Invalid KPI {kpi}: {err}')

    if group and kpi == 0:
        kpis_results = group_kpi_results(kpis_results)

    if not summary or kpi != 0:
        click.echo(json.dumps(kpis_results, indent=4))
    else:
        click.echo(json.dumps(kpis_results['summary'], indent=4))


kpi.add_command(validate)
