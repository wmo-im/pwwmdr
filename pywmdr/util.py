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

import logging
import os
import ssl
import sys
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
from urllib.error import URLError
from urllib.request import urlopen
from geopandas import read_file as gpd_read_file
from shapely.geometry import Point
import glob
import re
import validators
import pytz

from lxml import etree

LOGGER = logging.getLogger(__name__)

NAMESPACES = {
    'gco': 'http://www.isotc211.org/2005/gco',
    'gmd': 'http://www.isotc211.org/2005/gmd',
    'gml': 'http://www.opengis.net/gml/3.2',
    'gmx': 'http://www.isotc211.org/2005/gmx',
    'om': 'http://www.opengis.net/om/2.0',
    'wmdr': 'http://def.wmo.int/wmdr/1.0',
    'xlink': 'http://www.w3.org/1999/xlink',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'dct':   'http://purl.org/dc/terms/',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
}


def get_cli_common_options(function):
    """
    Define common CLI options
    """

    import click
    function = click.option('--verbosity', '-v',
                            type=click.Choice(
                                ['ERROR', 'WARNING', 'INFO', 'DEBUG']),
                            help='Verbosity')(function)
    function = click.option('--log', '-l', 'logfile',
                            type=click.Path(writable=True, dir_okay=False),
                            help='Log file')(function)
    return function


# def get_codelists():
#     """
#     Helper function to assemble dict of ISO and WMO codelists

#     :param authority: code list authority (iso or wmo)

#     :returns: `dict` of ISO and WMO codelists

#     """

#     codelists = {}
#     userdir = get_userdir()

#     codelist_files = {
#         'iso': f'{userdir}/schema/resources/Codelist/gmxCodelists.xml',
#         'wmo': f'{userdir}{os.sep}WMOCodeLists.xml'
#     }

#     for key, value in codelist_files.items():
#         codelists[key] = {}
#         xml = etree.parse(value)
#         for cld in xml.xpath('gmx:codelistItem/gmx:CodeListDictionary', namespaces=NAMESPACES):
#             identifier = cld.get(nspath_eval('gml:id'))
#             codelists[key][identifier] = []
#             for centry in cld.findall(nspath_eval('gmx:codeEntry/gmx:CodeDefinition/gml:identifier')):
#                 codelists[key][identifier].append(centry.text)

#     return codelists

def get_codelists_from_rdf():
    """
    Helper function to assemble dict of WMO codelists from RDF XML files

    :returns: `dict` of WMO codelists

    """

    codelists = {}
    userdir = get_userdir()

    codelist_files = {}

    surface_cover_scheme_map = {
        'SurfaceCoverGlob2009': 'globCover2009',
        'SurfaceCoverIGBP': 'igbp',
        'SurfaceCoverLAI': 'laifpar',
        'SurfaceCoverLCCS': 'lccs',
        'SurfaceCoverNPP': 'npp',
        'SurfaceCoverPFT': 'pft',
        'SurfaceCoverUMD': 'umd'
    }

    listing = glob.glob(f'{userdir}/schema/resources/Codelist/*.rdf')
    for file in listing:
        key = re.sub('\.rdf$','',os.path.basename(file))
        if key in surface_cover_scheme_map.keys():
            codelist_files[surface_cover_scheme_map[key]] = file
        else:
            codelist_files[key] = file

    # codelist_files = {
    #     'WMORegion': f'{userdir}/schema/resources/Codelist/WMORegion.rdf',
    #     'GeopositioningMethod': f'{userdir}/schema/resources/Codelist/GeopositioningMethod.rdf',
    # }

    for key, value in codelist_files.items():
        codelists[key] = []
        xml = etree.parse(value)
        container = xml.getroot()[0]
        # for notation in container.findall(nspath_eval('skos:member/skos:Concept/skos:notation')):
        #     codelists[key].append(notation.text)
        for concept in container.findall(nspath_eval('skos:member/skos:Concept')):
            codelists[key].append(concept.get(nspath_eval('rdf:about')))
            codelists[key].append(concept.find(nspath_eval('skos:notation')).text)

    # add time zones from pytz package
        codelists["TimeZone"] = pytz.all_timezones

    return codelists


def get_string_or_anchor_value(parent) -> list:
    """
    Returns list of strings (texts) from CharacterString or Anchor child elements of the given element

    :param parent : The element to check
    """
    values = []
    value_elements = parent.findall(nspath_eval('gco:CharacterString')) + parent.findall(nspath_eval('gmx:Anchor'))
    for element in value_elements:
        values.append(element.text)
    return values


def get_string_or_anchor_values(parent_elements: list) -> list:
    """
    Returns list of strings (texts) from CharacterString or Anchor child elements of given parent_elements

    :param parent_elements : List of parent elements of the CharacterString or Anchor to read.
    """
    values = []
    for parent in parent_elements:
        values += get_string_or_anchor_value(parent)
    return values


def get_keyword_info(main_keyword_element) -> tuple:
    """
    Returns tuple with keywords, type value(s) and thesaurus(es) for given "MD_Keywords" element

    :param main_keyword_element : The element to check
    """

    keywords = main_keyword_element.findall(nspath_eval('gmd:keyword'))
    type_element = get_codelist_values(main_keyword_element.findall(nspath_eval('gmd:type/gmd:MD_KeywordTypeCode')))
    thesauruses = main_keyword_element.findall(nspath_eval('gmd:thesaurusName/gmd:CI_Citation/gmd:title'))
    return keywords, type_element, thesauruses


def get_codelist_values(elements: list) -> list:
    """
    Returns list of code list values as strings for all elements (except the ones with no value)
    The value can be in the element attribute or text node.

    :param elements : The elements to check
    """
    values = []
    for element in elements:
        value = element.get('codeListValue')
        if value is None:
            value = element.text
        if value is not None:
            values.append(value)
    return values


def parse_time_position(element) -> datetime:
    """
    Returns datetime extracted from the given GML element or None if parsing failed.
    The parsing is rather benevolent here to allow mixing of "Zulu" and "naive" time strings (and other oddities),
    in the hope that all meteorological data refer to UTC.

    :param element : XML / GML element (e.g. gml:beginPosition)
    """
    indeterminate_pos = element.get('indeterminatePosition')
    if indeterminate_pos is not None:
        if indeterminate_pos in ["now", "unknown"]:
            return datetime.now(timezone.utc)
        elif indeterminate_pos == "before":
            return datetime.now(timezone.utc) - timedelta(hours=24)
        elif indeterminate_pos == "after":
            return datetime.now(timezone.utc) + timedelta(hours=24)
        else:
            LOGGER.debug(f'Time point has unexpected value of indeterminatePosition: {indeterminate_pos}')
    elif element.text is not None:
        text_to_parse = element.text
        if text_to_parse.endswith('Z'):
            text_to_parse = text_to_parse[0:-1]
        dtg = parse(text_to_parse, fuzzy=True, ignoretz=True).replace(tzinfo=timezone.utc)
        return dtg
    return None


def get_userdir() -> str:
    """
    Helper function to get userdir

    :returns: user's home directory
    """

    return f'{os.path.expanduser("~")}{os.sep}.pywmdr'


def nspath_eval(xpath: str) -> str:
    """
    Return an etree friendly xpath based expanding namespace
    into namespace URIs

    :param xpath: xpath string with namespace prefixes

    :returns: etree friendly xpath
    """

    out = []
    for chunk in xpath.split('/'):
        if ':' in chunk:
            namespace, element = chunk.split(':')
            out.append(f'{{{NAMESPACES[namespace]}}}{element}')
        else:
            out.append(chunk)
    return '/'.join(out)


def setup_logger(loglevel: str = None, logfile: str = None):
    """
    Setup logging

    :param loglevel: logging level
    :param logfile: logfile location

    :returns: void (creates logging instance)
    """

    if loglevel is None and logfile is None:  # no logging
        return

    if loglevel is None and logfile is not None:
        loglevel = 'INFO'

    log_format = \
        '[%(asctime)s] %(levelname)s - %(message)s'
    date_format = '%Y-%m-%dT%H:%M:%SZ'

    loglevels = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET,
    }

    loglevel = loglevels[loglevel]

    if logfile is not None:  # log to file
        logging.basicConfig(level=loglevel, datefmt=date_format,
                            format=log_format, filename=logfile)
    elif loglevel is not None:  # log to stdout
        logging.basicConfig(level=loglevel, datefmt=date_format,
                            format=log_format, stream=sys.stdout)
        LOGGER.debug('Logging initialized')


def urlopen_(url: str):
    """
    Helper function for downloading a URL

    :param url: URL to download

    :returns: `http.client.HTTPResponse`
    """

    try:
        response = urlopen(url)
    except (ssl.SSLError, URLError) as err:
        LOGGER.warning(err)
        LOGGER.warning('Creating unverified context')
        context = ssl._create_unverified_context()

        response = urlopen(url, context=context)

    return response


def check_url(url: str, check_ssl: bool) -> dict:
    """
    Helper function to check link (URL) accessibility

    :param url: The URL to check
    :param check_ssl: Whether the SSL/TLS layer verification shall be made

    :returns: `dict` with details about the link
    """

    response = None
    result = {
        'mime-type': None,
        'url-original': url
    }

    try:
        if check_ssl is False:
            LOGGER.debug('Creating unverified context')
            result['ssl'] = False
            context = ssl._create_unverified_context()
            response = urlopen(url, context=context)
        else:
            response = urlopen(url)
    except (ssl.SSLError, URLError, ValueError) as err:
        LOGGER.debug(err)

    if response is None and check_ssl is True:
        return check_url(url, False)

    if response is not None:
        result['url-resolved'] = response.url
        if response.status > 300:
            LOGGER.debug(f'Request failed: {response}')
        result['accessible'] = response.status < 300
        result['mime-type'] = response.headers.get_content_type()
        if response.url.startswith("https") and check_ssl is True:
            result['ssl'] = True
    else:
        result['accessible'] = False
    return result


def validate_wmdr_xml(xml):
    """
    Perform XML Schema validation of WMDR Metadata

    :param xml: file or string of XML

    :returns: `bool` of whether XML validates WMDR schema
    """

    userdir = get_userdir()
    if not os.path.exists(userdir):
        raise IOError(f'{userdir} does not exist')
    if isinstance(xml, str):
        xml = etree.fromstring(xml)
    xsd = os.path.join(userdir, 'wmdr.xsd')
    LOGGER.debug(f'Validating {xml} against schema {xsd}')
    schema = etree.XMLSchema(etree.parse(xsd))
    schema.assertValid(xml)


def parse_wmdr(content):
    """
    Parse a buffer into an etree ElementTree

    :param content: str of xml content

    :returns: `lxml.etree._ElementTree` object of WMDR
    """

    try:
        exml = etree.parse(content)
    except etree.XMLSyntaxError as err:
        LOGGER.error(err)
        raise RuntimeError('Syntax error')

    root_tag = exml.getroot().tag

    if root_tag != '{http://def.wmo.int/wmdr/1.0}WIGOSMetadataRecord' and root_tag != '{http://def.wmo.int/wmdr/2017}WIGOSMetadataRecord':
        raise RuntimeError('Does not look like a WMDR document!')

    return exml

def get_coordinates(self):
    xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation/wmdr:GeospatialLocation/wmdr:geoLocation/gml:Point/gml:pos'
    match = self.exml.xpath(xpath,namespaces=self.namespaces)
    if not len(match):
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation/wmdr:GeospatialLocation/wmdr:geoLocation/gml:Point/gml:coordinates'
        match = self.exml.xpath(xpath,namespaces=self.namespaces)
        if not len(match):
            raise ValueError("Missing wmdr:geoLocation/gml:Point/gml:pos")
        else:
            raise ValueError("gml:coordinates is deprecated. Use gml:pos")
        return

    coords = match[0].text.split(" ")
    
    if len(coords) < 2:
        raise ValueError("gml:pos is missing values")
        return

    lon = float(coords[1])
    lat = float(coords[0])
    return lon, lat


def get_region(lon,lat,getNotation=False):

    userdir = get_userdir()
    regions_geojson_file = f'{userdir}/schema/resources/maps/WMO_regions.json'
    regions = gpd_read_file(regions_geojson_file)

    st0 = Point(lon,lat)

    region = None
    st_bounds = st0.bounds
    if st_bounds[1] < -60:
        if getNotation:
            region = "antarctica"
        else:
            region = "http://codes.wmo.int/wmdr/WMORegion/antarctica"
    else:
        for i in range(0,len(regions.geometry)):
            if st0.within(regions.geometry[i]):
                # print("is within region %s" % regions.notation[i])
                if getNotation:
                    region = regions.notation[i]
                else:
                    region = regions.code[i]
    
    return region

def is_within_timezone(lon,lat,tzid):
    userdir = get_userdir()
    timezones_geojson_file = f'{userdir}/schema/resources/maps/timezones.json'
    timezones = gpd_read_file(timezones_geojson_file)
    l = [timezones.tzid[i] for i in range(0,len(timezones.tzid))]
    if tzid not in l:
        raise ValueError('timezone not found in code list')
        return
    i = l.index(tzid)
    geometry = timezones.geometry[i]
    st0 = Point(lon,lat)
    if st0.within(geometry):
        return True
    else:
        raise ValueError('coordinates dont match timezone')

def validate_url(url):
    return validators.url(url)

def get_href_and_validate(exml,xpath,namespaces,codelist,element_name):
    # finds reference and validates against codelist
    # returns score, comments, value
    score = 0
    comments = []
    value = None

    matches = exml.xpath(xpath,namespaces=namespaces)

    if not len(matches):
        LOGGER.debug("%s not found" % element_name)
        comments.append("%s not found" % element_name)
    else:
        m = matches[0]
        value = m.get('{http://www.w3.org/1999/xlink}href')
        if not value:
            LOGGER.debug('%s href not found' % element_name)
            comments.append('%s href not found'  % element_name)
        else:
            if value not in codelist:
                LOGGER.debug('%s not present in codelist' % element_name)
                comments.append('%s not present in codelist' % element_name)
            else:
                if value.split("/")[-1].lower() == 'unknown' or value.split("/")[-1].lower() == 'inapplicable':
                    LOGGER.debug('%s is unknown or inapplicable' % element_name)
                    comments.append('%s is unknown or inapplicable' % element_name)
                else:
                    LOGGER.debug('Found %s "%s"' % (element_name, value))
                    score += 1
    
    return score, comments, value

def get_text_and_validate(exml,xpath,namespaces,type="integer",element_name="element",min_length=1,codelist=None,get_only_first_match=True):
    # finds and validates matches of provided xpath 
    # returns score, comments, value
    comments = []
    matches = exml.xpath(xpath,namespaces=namespaces)
    if not len(matches):
        LOGGER.debug("%s not found" % element_name)
        comments.append("%s not found" % element_name)
    else:
        text = matches[0].text

        if(get_only_first_match):
            return validate_text(text,type,element_name,min_length,codelist)
        else:   # validates all matches and returns average score
            sum = 0
            count = 0
            value = []
            for match in matches:
                text = match.text
                sscore, scomments, svalue = validate_text(text,type,element_name,min_length,codelist) 
                sum += sscore
                comments = comments + scomments
                count = count + 1
                value.append(svalue)
            score = sum/count 
            return score, comments, value

def validate_text(text,type="integer",element_name="element",min_length=1,codelist=None):
    score = 0
    comments = []
    value = None
    if type == "integer":
        try:
            value = int(text)
        except ValueError:
            LOGGER.debug("%s is not a valid integer" % element_name)
            comments.append("%s is not a valid integer" % element_name)
        else:
            LOGGER.debug('Found %s "%s"' % (element_name, value))
            score += 1
    elif type == "string":
        try:
            value = str(text)
        except ValueError:
            LOGGER.debug("%s is not a valid string" % element_name)
            comments.append("%s is not a valid string" % element_name)
        else:
            if len(value) < min_length:
                LOGGER.debug("%s is shorter than minimum length" % element_name)
                comments.append("%s is shorter than minimum length" % element_name)
            else:   
                if codelist:
                    if value not in codelist:
                        LOGGER.debug('%s not present in codelist' % element_name)
                        comments.append('%s not present in codelist' % element_name)
                    else:
                        if value.lower() == 'unknown' or value.lower() == 'inapplicable':
                            LOGGER.debug('%s is unknown or inapplicable' % element_name)
                            comments.append('%s is unknown or inapplicable' % element_name)
                        else:
                            LOGGER.debug('Found %s "%s"' % (element_name, value))
                            score += 1
                else:
                    LOGGER.debug('Found %s "%s"' % (element_name, value))
                    score += 1
    elif type == "url":
        try:
            value = str(text)
        except ValueError:
            LOGGER.debug("%s is not a valid string" % element_name)
            comments.append("%s is not a valid string" % element_name)
        else:
            if not validators.url(value):
                if not validators.url('https://%s' % value):
                    LOGGER.debug("%s is not a valid URL" % element_name)
                    comments.append("%s is not a valid URL" % element_name)
                else:
                    LOGGER.debug('Found %s "%s"' % (element_name, value))
                    score += 1
            else:  
                LOGGER.debug('Found %s "%s"' % (element_name, value))
                score += 1
    elif type == "datetime":
        try:
            value = datetime.fromisoformat(re.sub('Z$','+00:00',text))
        except ValueError:
            LOGGER.debug("%s is not a valid date" % element_name)
            comments.append("%s is not a valid date" % element_name)
        else:
            LOGGER.debug('Found %s "%s"' % (element_name, value))
            score += 1
    elif type == "href":
        value = str(text)
        if value not in codelist:
                LOGGER.debug('%s not present in codelist' % element_name)
                comments.append('%s not present in codelist' % element_name)
        else:
            if value.split("/")[-1].lower() == 'unknown' or value.split("/")[-1].lower() == 'inapplicable':
                LOGGER.debug('%s is unknown or inapplicable' % element_name)
                comments.append('%s is unknown or inapplicable' % element_name)
            else:
                LOGGER.debug('Found %s "%s"' % (element_name, value))
                score += 1
    else:
        raise RuntimeError("invalid type: %s" % type)
    
    return score, comments, value
