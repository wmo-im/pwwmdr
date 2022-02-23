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

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import os
import logging
# import re
# import pytz
# import datetime
# from bs4 import BeautifulSoup
import click
# from spellchecker import SpellChecker

from pywmdr.ats import TestSuiteError, WMDRTestSuite
from pywmdr.util import (get_cli_common_options, get_keyword_info,
                         get_string_or_anchor_value, get_string_or_anchor_values,
                         nspath_eval, parse_time_position, parse_wmdr,
                         setup_logger, urlopen_, check_url, get_codelists_from_rdf,
                         get_region, get_coordinates, is_within_timezone, 
                         validate_url, get_href_and_validate, get_text_and_validate, 
                         validate_text) # get_codelists, 

logging.basicConfig(level=logging.DEBUG)
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
        # serialized already
        rtag = exml.getroot().tag
        if rtag != "{http://def.wmo.int/wmdr/1.0}WIGOSMetadataRecord":
            wigosmetadatarecord = exml.getroot().find('.//{http://def.wmo.int/wmdr/1.0}WIGOSMetadataRecord')
            if wigosmetadatarecord is None:
                if rtag != '{http://def.wmo.int/wmdr/2017}WIGOSMetadataRecord':
                    wigosmetadatarecord = exml.getroot().find('{http://def.wmo.int/wmdr/2017}WIGOSMetadataRecord')
                    if wigosmetadatarecord is None:
                        raise RuntimeError('Does not look like a WMDR document!')
                    else:
                        exml._setroot(wigosmetadatarecord)
                LOGGER.debug("Warning: document is wmdr/2017 (1.0RC9)!")
                self.version = "1.0RC9"
            else:
                exml._setroot(wigosmetadatarecord)
                self.version = "1.0"
        self.exml = exml
        self.namespaces = self.exml.getroot().nsmap
        # remove empty (default) namespace to avoid exceptions in exml.xpath
        if None in self.namespaces:
            LOGGER.debug('Removing default (None) namespace. This XML is destined to fail.')
            none_namespace = self.namespaces[None]
            prefix = none_namespace.split('/')[-1]
            if prefix:
                self.namespaces[prefix] = none_namespace
            else:
                self.namespaces["default"] = none_namespace
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
        xpath = './wmdr:facility/wmdr:ObservingFacility/gml:identifier/text()'
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

        # Rule 2-0-01: wmoRegion
        stotal, sscore, scomments = self.kpi_2001()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 2-0-02: timeZone
        stotal, sscore, scomments = self.kpi_2002()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 2-0-03: Supervising organization
        stotal, sscore, scomments = self.kpi_2003()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 2-0-04: Station URL
        stotal, sscore, scomments = self.kpi_2004()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 2-0-05: Other link (URL)
        stotal, sscore, scomments = self.kpi_2005()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-06: site description
        stotal, sscore, scomments = self.kpi_2006()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-07: climate zone
        stotal, sscore, scomments = self.kpi_2007()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-08: Predominant surface cover
        stotal, sscore, scomments = self.kpi_2008()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-09: surface roughness
        stotal, sscore, scomments = self.kpi_2009()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-10: topography or bathymetry
        stotal, sscore, scomments = self.kpi_2010()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-11: population
        stotal, sscore, scomments = self.kpi_2011()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-12: Station / platform event logbook
        stotal, sscore, scomments = self.kpi_2012()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 2-0-13: Territory/Country 
        stotal, sscore, scomments = self.kpi_2013()
        total += stotal
        score += sscore
        comments = comments + scomments

        return name, total, score, comments

    def kpi_2000(self):
        # Rule 2-0-00: Coordinates
        # 2-0-00-a: A geopositioning method is specified and not "unknown".
        # NOTE: in case of multiple matches the average score is returned
        total = 2 
        score = 0
        comments = []

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:geospatialLocation'
        matches = self.exml.xpath(xpath,namespaces=self.namespaces)
        if not len(matches):
            LOGGER.debug('geospatialLocation not found')
            comments.append('geospatialLocation not found')
        else:
            sum = 0
            count = 0
            for geospatialLocation in matches:
                count = count + 2

                ## Rule 2-0-00-a: A geopositioning method is specified and not "unknown"
                xpath = './wmdr:GeospatialLocation/wmdr:geopositioningMethod'
                sscore, scomments, value = get_href_and_validate(geospatialLocation,xpath,self.namespaces,self.codelists["GeopositioningMethod"],"geopositioning method")
                sum += sscore
                comments = comments + scomments

                ## Rule 2-0-00-b: The begin position of valid period is specified
                xpath = './wmdr:GeospatialLocation/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
                sscore, scomments, value = get_text_and_validate(geospatialLocation,xpath,self.namespaces,type="datetime",element_name="valid period of geospatial location")
                sum += sscore
                comments = comments + scomments
            score = sum / count * total
        return total, score, comments
    
    def kpi_2001(self):
        # Rule 2-0-01: WMO Region
        # A WMO region (code list: http://codes.wmo.int/wmdr/WMORegion) is specified and it matches the coordinates.

        total = 1
        score = 0
        comments = []
        getNotation = False

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:wmoRegion'

        sscore, scomments, wmoregion = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["WMORegion"],"wmo region")

        if not wmoregion:
            getNotation = True
            sscore, scomments, wmoregion = get_text_and_validate(self.exml,xpath,self.namespaces,type="string",element_name="wmo region",codelist=self.codelists["WMORegion"])
        
        if not wmoregion:
            return total, score, comments
        
        ## get the coordinates
        lon, lat = (None, None)
        try:
            lon, lat = get_coordinates(self)
        except ValueError as e:
            LOGGER.debug(str(e))
            comments.append(str(e))
            return total, score, comments
        
        # check if region matches the coordinates
        region_from_pos = get_region(lon,lat,getNotation)
        # print(coords,lon,lat,region_from_pos,wmoregion)
        if region_from_pos != wmoregion:
            LOGGER.debug("region doesnt match coordinates")
            comments.append("region doesnt match coordinates")
        else:
            score += 1
        
        return total, score, comments

    def kpi_2002(self):
        ## rule 2-0-02 Timezone
        total = 2
        score = 0
        comments = []
        
        ## 2-0-02-a: A time zone is specified and it matches the coordinates.
        # NOTE: timeZoneType code list seems to be missing. Using pytz.all_timezones instead
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:timeZone/wmdr:TimeZone/wmdr:timeZone'

        sscore, scomments, time_zone = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["TimeZone"],"time zone")

        if not time_zone:
            comments = comments + scomments
        else:
            ## get the coordinates
            lon, lat = (None, None)
            try:
                lon, lat = get_coordinates(self)
            except ValueError as e:
                LOGGER.debug(str(e))
                comments.append(str(e))
            else:
                try:
                    is_within_timezone(lon,lat,time_zone)
                except ValueError as e:
                    LOGGER.debug(str(e))
                    comments.append(str(e))
                else:
                    score += 1
        
        ## 2-0-02-b: The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:timeZone/wmdr:TimeZone/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
        
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of time zone")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_2003(self):
        # Rule 2-0-03: Supervising organization
        # "wmdr:responsibleParty"
        
        total = 2
        score = 0
        comments = []
        
        # Rule 2-0-03-a: A supervising organization is specified and not "unknown".
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:responsibleParty/wmdr:ResponsibleParty/wmdr:responsibleParty/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString'
        
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="string", element_name="supervising organization")
        score += sscore
        comments = comments + scomments
        
        
        # Rule 2-0-03-b: The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:responsibleParty/wmdr:ResponsibleParty/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'

        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of supervising organization")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_2004(self):
        # Rule 2-0-04: Station URL
        # URL is provided and valid.
        xpath = "./wmdr:facility/wmdr:ObservingFacility/wmdr:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL"
        total = 1
        score = 0
        comments = []

        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="url", element_name="facility URL")
        score += sscore
        comments = comments + scomments
        
        return total, score, comments

    def kpi_2005(self):
        # Rule 2-0-05: Other link (URL)
        # At least one other link is provided and all URLs are valid.

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL'


        total = 1
        score = 0
        comments = []

        matches = self.exml.xpath(xpath,namespaces=self.namespaces)

        if len(matches) <= 1:
            LOGGER.debug("Other links are missing")
            comments.append("Other links are missing")
        else:
            matches.pop()
            all_valid = True
            for m in matches:
                valid = validate_url(m.text)
                if valid==False:
                    all_valid = False
            if all_valid==False:
                LOGGER.debug("At least one of other links is invalid")
                comments.append("At least one of other links is invalid")
            else:
                score += 1
        
        return total, score, comments
    
    def kpi_2006(self):
        # Rule 2-0-06: Site description wmdr:description
        total = 2
        score = 0
        comments = []

        # Rule 2-0-06-a: Site description is provided.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:description/wmdr:Description/wmdr:description'
        
        sscore, scomments, site_description = get_text_and_validate(self.exml, xpath, self.namespaces, type="string", element_name="site description")
        score += sscore
        comments = comments + scomments

        if not site_description:
            return total, score, comments      

        # Rule 2-0-06-b: Requirement for minimum length is fulfilled.
        # NOTE: can't fine minimum length requirement in documentation. Set at 300 chars

        if len(site_description) < 300:
            LOGGER.debug("Site description is shorter than required (300 chars)")
            comments.append("Site description is shorter than required (300 chars)")
        else:              
            score += 1

        return total, score, comments

    def kpi_2007(self):
        # 2-0-07 Climate zone wmdr:climateZone
        total = 2
        score = 0
        comments = []

        # Rule 2-0-07-a:  A climate zone (code list: http://codes.wmo.int/wmdr/ClimateZone) is specified.

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:climateZone/wmdr:ClimateZone/wmdr:climateZone'
        
        sscore, scomments, value = get_href_and_validate(self.exml, xpath, self.namespaces, self.codelists["ClimateZone"], "climate zone")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-07-b: The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:climateZone/wmdr:ClimateZone/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'

        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of climate zone")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_2008(self):
        # Rule 2-0-08: Predominant surface cover wmdr:surfaceCover
        total = 2
        score = 0
        comments = []
        
        # Rule 2-0-08-a: A surface cover classification scheme (code list: http://codes.wmo.int/wmdr/SurfaceCoverClassification) and the surface cover (code lists: http://codes.wmo.int/wmdr/SurfaceCoverXXXX) are specifed and not "unknown".

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:surfaceCover/wmdr:SurfaceCover/wmdr:surfaceCoverClassification'

        sscore, scomments, surface_cover_scheme = get_href_and_validate(self.exml, xpath, self.namespaces, self.codelists["SurfaceCoverClassification"], "surface cover classification")
        
        if not surface_cover_scheme:
            comments = comments + scomments
        else:
            surface_cover_scheme = surface_cover_scheme.split("/")[-1].lower()
            if surface_cover_scheme not in self.codelists:
                LOGGER.debug('codelist not found for surface cover classification scheme')
                comments.append('codelist not found for surface cover classification scheme')
            else:
                xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:surfaceCover/wmdr:SurfaceCover/wmdr:surfaceCover'

                sscore, scomments, surface_cover = get_href_and_validate(self.exml, xpath, self.namespaces, self.codelists[surface_cover_scheme], "surface cover")
                score += sscore
                comments = comments + scomments
         
        # Rule 2-0-08-b: The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:surfaceCover/wmdr:SurfaceCover/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
        
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of surface cover")
        score += sscore
        comments = comments + scomments

        return total, score, comments
    
    def kpi_2009(self):
        # Rule 2-0-09 Surface roughness wmdr:surfaceRoughness
        total = 2
        score = 0
        comments = []

        # Rule 2-0-09-a: The Surface roughness (code list: http://codes.wmo.int/wmdr/SurfaceRoughnessDavenport) is specified and not "unknown".
        
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:surfaceRoughness/wmdr:SurfaceRoughness/wmdr:surfaceRoughness'
        
        sscore, scomments, surface_roughness = get_href_and_validate(self.exml, xpath, self.namespaces, self.codelists["SurfaceRoughnessDavenport"],"surface roughness")
        score += sscore
        comments = comments + scomments
        matches = self.exml.xpath(xpath,namespaces=self.namespaces)

        # Rule 2-0-09-b: The begin position of valid period is specified.

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:surfaceRoughness/wmdr:SurfaceRoughness/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
        
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of surface roughness")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_2010(self):
        # Rule 2-0-10 Topography or bathymetry wmdr:topographyBathymetry 
        total = 5
        score = 0
        comments = []

        # Rule 2-0-10-a: The local topography (based on Speight 2009) (code list: http://codes.wmo.int/wmdr/LocalTopography ) is specified and not "unknown".
        xpath = "./wmdr:facility/wmdr:ObservingFacility/wmdr:topographyBathymetry/wmdr:TopographyBathymetry/wmdr:localTopography"

        sscore, scomments, value = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["LocalTopography"],"local topography")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-10-b: The relative elevation is specified and not "unknown".
        xpath = "./wmdr:facility/wmdr:ObservingFacility/wmdr:topographyBathymetry/wmdr:TopographyBathymetry/wmdr:relativeElevation"

        sscore, scomments, value = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["RelativeElevation"],"relative elevation")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-10-c: The Topographic context (based on Hammond 1954) (code list: http://codes.wmo.int/wmdr/TopographicContext ) is specified and not "unknown".
        xpath = "./wmdr:facility/wmdr:ObservingFacility/wmdr:topographyBathymetry/wmdr:TopographyBathymetry/wmdr:topographicContext"

        sscore, scomments, value = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["TopographicContext"],"topographic context")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-10-d: Altitude/depth (code list: http://codes.wmo.int/wmdr/AltitudeOrDepth) is specified and not "unknown".
        xpath = "./wmdr:facility/wmdr:ObservingFacility/wmdr:topographyBathymetry/wmdr:TopographyBathymetry/wmdr:altitudeOrDepth"

        sscore, scomments, value = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["AltitudeOrDepth"],"altitude or depth")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-10-e: The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:topographyBathymetry/wmdr:TopographyBathymetry/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
        
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of topography or bathymetry")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_2011(self):
        # Rule 2-0-11 Population wmdr:population
        total = 3
        score = 0
        comments = []

        # Rule 2-0-11-a: Values for population in 10 km range is added.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:population/wmdr:Population/wmdr:population10km'
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="integer", element_name="population10km")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-11-b: Values for population in 50 km range is added.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:population/wmdr:Population/wmdr:population50km'
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="integer", element_name="population50km")
        score += sscore
        comments = comments + scomments

        # Rule 2-0-11-c: The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:population/wmdr:Population/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
        sscore, scomments, value = get_text_and_validate(self.exml,xpath,self.namespaces,type="datetime",element_name="valid period of population")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_2012(self):
        # Rule 2-0-12 Station / platform event logbook wmdr:facilityLog
        total = 5
        score = 0
        comments = []

        xpath = "./wmdr:facility/wmdr:ObservingFacility/wmdr:facilityLog/wmdr:FacilityLog/wmdr:logEntry"
        matches = self.exml.xpath(xpath,namespaces=self.namespaces)
        if not len(matches):
            LOGGER.debug("logEntry not found")
            comments.append("logEntry not found")
        else:
            sum = 0
            count = 0
            value = []
            for logEntry in matches:
                count = count + 5
                
                # Rule 2-0-12-a: A date is added (range or single day).
                element_name = "valid period of reported event"
                # xpath = './wmdr:EventReport/wmdr:datetime'
                xpath = './wmdr:EventReport/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
                matches = logEntry.xpath(xpath,namespaces=self.namespaces)
                if not len(matches):
                    LOGGER.debug("%s not found" % element_name)
                    comments.append("%s not found" % element_name)
                else:
                    text = matches[0].text
                    sscore, scomments, svalue = validate_text(text,"datetime",element_name) 
                    sum += sscore
                    comments = comments + scomments
                    value.append(svalue)

                # Rule 2-0-12-b: The event is specified and not "unknown".
                xpath = './wmdr:EventReport/wmdr:typeOfEvent'
                element_name = "type of event"
                matches = logEntry.xpath(xpath,namespaces=self.namespaces)
                if not len(matches):
                    LOGGER.debug("%s not found" % element_name)
                    comments.append("%s not found" % element_name)
                else:
                    text = matches[0].get('{http://www.w3.org/1999/xlink}href')
                    sscore, scomments, svalue = validate_text(text,"href",element_name,codelist=self.codelists["EventAtFacility"])
                    sum += sscore
                    comments = comments + scomments
                    value.append(svalue)

                # Rule 2-0-12-c: A description is provided.
                xpath = './wmdr:EventReport/wmdr:description'
                element_name = "event description"
                matches = logEntry.xpath(xpath,namespaces=self.namespaces)
                if not len(matches):
                    LOGGER.debug("%s not found" % element_name)
                    comments.append("%s not found" % element_name)
                else:
                    text = matches[0].text
                    sscore, scomments, svalue = validate_text(text,"string",element_name,min_length=100)
                    sum += sscore
                    comments = comments + scomments
                    value.append(svalue)

                # 2-0-12-d: The author is named.
                xpath = './wmdr:EventReport/wmdr:author'
                element_name = "author of log entry"
                matches = logEntry.xpath(xpath,namespaces=self.namespaces)
                if not len(matches):
                    LOGGER.debug("%s not found" % element_name)
                    comments.append("%s not found" % element_name)
                else:
                    text = matches[0].text
                    sscore, scomments, svalue = validate_text(text,"string",element_name)
                    sum += sscore
                    comments = comments + scomments
                    value.append(svalue)

                # 2-0-12-e: The event has an online reference.
                xpath = './wmdr:EventReport/wmdr:documentationURL'
                element_name = "documentation URL of log entry"
                matches = logEntry.xpath(xpath,namespaces=self.namespaces)
                if not len(matches):
                    LOGGER.debug("%s not found" % element_name)
                    comments.append("%s not found" % element_name)
                else:
                    text = matches[0].text
                    sscore, scomments, svalue = validate_text(text,"url",element_name)
                    sum += sscore
                    comments = comments + scomments
                    value.append(svalue)

            score = sum / count * total
            # print("sum: %d, count: %s, score: %03f" % (sum, count, score))
        return total, score, comments

    def kpi_2013(self):
        # Rule 2-0-13 Territory/Country wmdr:territory
        total = 2
        score = 0
        comments = []

        # rule 2-0-13-a: A territory or country is specified and not "unknown".
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:territory/wmdr:Territory/wmdr:territoryName'
        
        sscore, scomments, value = get_href_and_validate(self.exml,xpath,self.namespaces,self.codelists["TerritoryName"],"territory name")
        score += sscore
        comments = comments + scomments
        
        # Rule 2-0-13-b The begin position of valid period is specified.
        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:territory/wmdr:Territory/wmdr:validPeriod/gml:TimePeriod/gml:beginPosition'
        sscore, scomments, value = get_text_and_validate(self.exml, xpath, self.namespaces, type="datetime", element_name="valid period of territory")
        score += sscore
        comments = comments + scomments

        return total, score, comments

    def kpi_21(self) -> tuple:
        """
        Implements KPI-2-1: Station characteristics (OSCAR/Surface)

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 5
        score = 0
        comments = []
        name = 'KPI-2-1: station characteristics (OSCAR/Surface)'
        LOGGER.info(f'Running {name}')

        # rule 2-1-00 Station photo gallery
        # The station has 1-2 photos -> 1
        # The station has 3-5 photos -> 2
        # The station has more than 5 photos -> 3
        
        # TODO

        # rule 2-1-01 Station photo
        # The added direction of view is not "unknown" -> 1
        # The angle of view (focal length) is specified -> 1

        # TODO

        return name, total, score, comments

    def kpi_30(self) -> tuple:
        """
        Implements KPI-3-0: 

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 0 
        score = 0
        comments = []

        name = 'KPI-3-0: Observations/measurements - Basic information'

        LOGGER.info(f'Running {name}')
        
        oms_xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:observation/wmdr:ObservingCapability/wmdr:observation/om:OM_Observation'
        print(oms_xpath)

        oms = self.exml.xpath(oms_xpath, namespaces=self.namespaces)
        total += 2*len(oms)

        LOGGER.info(f'Running ID: 3-0-00 Geometry')

        LOGGER.debug(f'Rule: Geometry (code list: http://codes.wmo.int/wmdr/Geometry) is not specified as "unknown". ')

        if len(oms) > 0:
            for om in oms:
                om_type = om.find(nspath_eval('om:type'))
                if om_type is not None:
                    href = om_type.get('{http://www.w3.org/1999/xlink}href')
                    geom_code_url = href.rsplit('/',1)[0]
                    geom_type = href.rsplit('/',1)[-1]
                    if geom_code_url == 'http://codes.wmo.int/wmdr/Geometry':
                        if geom_type != 'unknown':
                            result = check_url(href, False)
                            if result['accessible']:
                                score += 1
                                LOGGER.debug('Geometry type not unknown found for OM_Observation')
                                comments.append('Geometry type %s found for OM_Observation' % geom_type)
                            else:
                                LOGGER.debug(f'Geometry type %s is not in code list'  % geom_type)
                                comments.append(f'Geometry type %s is not in code list'  % geom_type)
                        else:
                            LOGGER.debug("Geometry type uses 'unknown' code")
                            comments.append("Geometry type uses 'unknown' code")
                    else:
                        LOGGER.debug("Geometry type does not use http://codes.wmo.int/wmdr/Geometry")
                        comments.append("Geometry type does not use http://codes.wmo.int/wmdr/Geometry")
                else:
                    LOGGER.debug("Geometry type not found for OM_Observation")
                    comments.append("Geometry type not found for OM_Observation")
        else:
            LOGGER.debug("No OM_Observation found")

        LOGGER.info(f'Running ID: 3-0-01 Deployments')

        LOGGER.debug(f'Rule: The observation/measurement has at least one deployment.')

        if len(oms) > 0:
            for om in oms:
                deployments = om.findall(nspath_eval('./om:procedure/wmdr:Process/wmdr:deployment'))
                n_deployments = len(deployments)
                print(n_deployments)
                if n_deployments > 0:
                    for deployment in deployments:
                        if deployment is not None:
                            score += 1/n_deployments
                            print(score)
                            LOGGER.debug('Deployment found for OM_Observation')
                            comments.append('Deployment found for OM_Observation')
                else:
                    LOGGER.debug("Deployment not found for OM_Observation")
                    comments.append("Deployment not found for OM_Observation")
        else:
            LOGGER.debug("No OM_Observation found")


        return name, total, score, comments

    def kpi_31(self) -> tuple:
        """
        Implements KPI-3-1: Deployment

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """
        #TODO implement single kpi functions 

        total = 0
        score = 0
        comments = []
        #empty function now
        comments.append('Not implemented yet')
        name = 'KPI-3-1: Deployment'
        LOGGER.info(f'Running {name}')

        # Rule 3-1-00: Source of observation
        stotal, sscore, scomments = self.kpi_3100()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 3-1-01: Distance from reference surface 
        stotal, sscore, scomments = self.kpi_3101()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 3-1-02: Type of reference surface 
        stotal, sscore, scomments = self.kpi_3102()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 3-1-03: Application area(s)
        stotal, sscore, scomments = self.kpi_3103()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 3-1-04: Exposure of instrument
        stotal, sscore, scomments = self.kpi_3104()
        total += stotal
        score += sscore
        comments = comments + scomments 

        # Rule 3-1-05: Configuration of instrument 
        stotal, sscore, scomments = self.kpi_3105()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-06: Representativeness of observation
        stotal, sscore, scomments = self.kpi_3106()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-07: Measurement leader / principal investigator
        stotal, sscore, scomments = self.kpi_3107()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-08: Organization
        stotal, sscore, scomments = self.kpi_3108()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-09: Near Real Time 
        stotal, sscore, scomments = self.kpi_3109()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-10: 
        stotal, sscore, scomments = self.kpi_3110()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-11: Data URL
        stotal, sscore, scomments = self.kpi_3111()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-12: Data communication method
        stotal, sscore, scomments = self.kpi_3112()
        total += stotal
        score += sscore
        comments = comments + scomments

        # Rule 3-1-13: Instrument QA/QC schedule
        stotal, sscore, scomments = self.kpi_3113()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-14: Maintenance schedule 
        stotal, sscore, scomments = self.kpi_3114()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-15: Instrument details
        stotal, sscore, scomments = self.kpi_3115()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-16: 
        stotal, sscore, scomments = self.kpi_3116()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-17: Coordinates
        stotal, sscore, scomments = self.kpi_3117()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-18: Instrument operating status
        stotal, sscore, scomments = self.kpi_3118()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-19: Firmware version
        stotal, sscore, scomments = self.kpi_3119()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-20: Observable range
        stotal, sscore, scomments = self.kpi_3120()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-21: Uncertainty
        stotal, sscore, scomments = self.kpi_3121()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-22: Drift per unit time
        stotal, sscore, scomments = self.kpi_3122()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-23: Specification URL 
        stotal, sscore, scomments = self.kpi_3123()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-24: Uncertainty evaluation procedure 
        stotal, sscore, scomments = self.kpi_3124()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-25: Observation frequency and polarization 
        stotal, sscore, scomments = self.kpi_3125()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-26: Telecommunication frequency 
        stotal, sscore, scomments = self.kpi_3126()
        total += stotal
        score += sscore
        comments = comments + scomments
        
        # Rule 3-1-27: Data generation
        stotal, sscore, scomments = self.kpi_3127()
        total += stotal
        score += sscore
        comments = comments + scomments

        return name, total, score, comments

    def kpi_3100(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3101(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3102(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3103(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3104(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3105(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3106(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3107(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3108(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3109(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3110(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3111(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3112(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3113(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3114(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3115(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3116(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3117(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3118(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3119(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3120(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3121(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3122(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3123(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3124(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3125(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3126(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_3127(self):
        total = 1
        score = 0
        comments = []

        return total, score, comments

    def kpi_40(self) -> tuple:
        """
        Implements KPI-4-0: Station contacts

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """
        total = 1
        score = 0
        comments = []

        name = 'KPI-4-0: Station contacts'

        LOGGER.info(f'Running {name}')

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:responsibleParty'

        LOGGER.info(f'Running ID: 4-0-00 Number of station contacts')

        LOGGER.debug(f'Rule: Station has at least on contact person.')

        matches = self.exml.xpath(xpath, namespaces=self.namespaces)

        if not len(matches):
            LOGGER.debug("responsibleParty not found")
            comments.append("responsibleParty not found")
        else:
            score += 1
            LOGGER.debug(f'responsibleParty specified')
            comments.append(f'responsibleParty specified')

        return name, total, score, comments

    def kpi_41(self) -> tuple:
        """
        Implements KPI-4-1: Station contact - individual

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 0 
        score = 0
        comments = []

        name = 'KPI-4-1: Station contact - individual'

        LOGGER.info(f'Running {name}')

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:responsibleParty'

        responsibleParties = self.exml.xpath(xpath, namespaces=self.namespaces)
        print(len(responsibleParties))
        total += 5*len(responsibleParties)


        if len(responsibleParties) > 0:
            responsiblePartyRecord = 1 
            for responsibleParty in responsibleParties:
                address = responsibleParty.find(nspath_eval('wmdr:ResponsibleParty/wmdr:responsibleParty/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString'))
                postal_code = responsibleParty.find(nspath_eval('wmdr:ResponsibleParty/wmdr:responsibleParty/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString'))
                country = responsibleParty.find(nspath_eval('wmdr:ResponsibleParty/wmdr:responsibleParty/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString'))
                phone = responsibleParty.find(nspath_eval('wmdr:ResponsibleParty/wmdr:responsibleParty/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString'))
                contact_url = responsibleParty.find(nspath_eval('wmdr:ResponsibleParty/wmdr:responsibleParty/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL'))
                LOGGER.info(f'Running ID: 4-1-00 Address')
                if address is not None:
                    score += 1
                    LOGGER.debug('Station contact %s address found' % responsiblePartyRecord)
                    comments.append('Station contact %s address found' % responsiblePartyRecord)
                else:
                    LOGGER.debug("Station contact %s address not found" % responsiblePartyRecord)
                    comments.append("Station contact %s address not found" % responsiblePartyRecord)
                LOGGER.info(f'Running ID: 4-1-01 Postal code')
                if postal_code is not None:
                    score += 1
                    LOGGER.debug('Station contact %s postal code found' % responsiblePartyRecord)
                    comments.append('Station contact %s postal code found' % responsiblePartyRecord)
                else:
                    LOGGER.debug("Station contact %s postal code not found" % responsiblePartyRecord)
                    comments.append("Station contact %s postal code not found" % responsiblePartyRecord)
                LOGGER.info(f'Running ID: 4-1-02 Country')
                if country is not None:
                    score += 1
                    LOGGER.debug('Station contact %s country found' % responsiblePartyRecord)
                    comments.append('Station contact %s country found' % responsiblePartyRecord)
                else:
                    LOGGER.debug("Station contact %s country not found" % responsiblePartyRecord)
                    comments.append("Station contact %s country not found" % responsiblePartyRecord)
                LOGGER.info(f'Running ID: 4-1-03 Phone (main & other)')
                if phone is not None:
                    score += 1
                    LOGGER.debug('Station contact %s phone found' % responsiblePartyRecord)
                    comments.append('Station contact %s phone found' % responsiblePartyRecord)
                else:
                    LOGGER.debug("Station contact %s phone not found" % responsiblePartyRecord)
                    comments.append("Station contact %s phone not found" % responsiblePartyRecord)
                LOGGER.info(f'Running ID: 4-1-04 Contact URL')
                if contact_url is not None:
                    result = check_url(contact_url.text, False)
                    if result['accessible']:
                        score += 1
                        LOGGER.debug("Station contact %s URL found and valid" % responsiblePartyRecord)
                        comments.append("Station contact %s URL found and valid" % responsiblePartyRecord)
                    else:
                        LOGGER.debug(f'Station contact %s URL not not accessible: {contact_url.text}' % responsiblePartyRecord)
                        comments.append(f'Station contact %s URL not accessible: {contact_url.text}' % responsiblePartyRecord)
                else:
                    LOGGER.debug("Station contact %s URL not found" % responsiblePartyRecord)
                    comments.append("Station contact %s URL not found" % responsiblePartyRecord)
                responsiblePartyRecord += 1 
        else:
            LOGGER.debug("No responsibleParty found")
            comments.append("No responsibleParty found")

        return name, total, score, comments

    def kpi_50(self) -> tuple:
        """
        Implements KPI-5-0: Bibliographic references and Documents (OSCAR/Surface)

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 2
        score = 0
        comments = []
        name = 'KPI-5-0: Bibliographic references and Documents (OSCAR/Surface)'
        LOGGER.info(f'Running {name}')

        # Rule 5-0-00 Reference. Station record has at least one reference.
        
        # TODO

        # Rule 5-0-01 5-0-01 Source. Reference contains a valid URL or DOI or a document.

        # TODO

        return name, total, score, comments

    def kpi_60(self) -> tuple:
        """
        Implements KPI-6-0: Value of a station for WIGOS

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 8
        score = 0
        previous_score = 0
        comments = []
        name = 'KPI-6-0: Value of a station for WIGOS'
        LOGGER.info(f'Running {name}')

        # Rule   
        # 2 - 3 program affiliations (score: 1)
        # 3 - 5 program affiliations (score: 2)
        # More than 5 program affiliations (score: 3)

        xpath = './wmdr:facility/wmdr:ObservingFacility/wmdr:programAffiliation/wmdr:ProgramAffiliation/wmdr:programAffiliation'
        element_name = "program affiliation"
        matches = self.exml.xpath(xpath,namespaces=self.namespaces)
        if(not len(matches)):
            LOGGER.debug("%s not found" % element_name)
            comments.append("%s not found" % element_name)
        else:
            programs = set()
            for match in matches:
                href = match.get('{http://www.w3.org/1999/xlink}href')
                # NOTE should codelist matching be case-sensitive? probably NOT! 
                sscore, scomments, svalue = validate_text(href,"href",element_name,codelist=self.codelists["ProgramAffiliation"])
                comments = comments + scomments
                if(svalue):
                    programs.add(svalue)
            if len(programs) > 5:
                score += 3
            elif len(programs) > 3:
                LOGGER.debug("found 4-5 %s (goal >5)" % element_name)
                comments.append("found 4-5 %s (goal >5)" % element_name)
                score += 2
            elif len(programs) > 1:
                LOGGER.debug("found 2-3 %s (goal >5)" % element_name)
                comments.append("found 2-3 %s (goal >5)" % element_name)
                score += 1
            else:
                LOGGER.debug("found 0-1 %s (goal >5)" % element_name)
                comments.append("found 0-1 %s (goal >5)" % element_name)
        
        LOGGER.debug("rule 6-0-00, score: %s, goal %s" % (score-previous_score,3))
        previous_score = score
        # Rule 6-0-01 Observations / measurements
        # 2 - 5 observations (score: 1)
        # 5 - 10 observations (score: 2)
        # More than 10 observations (score: 3)

        xpath = '//wmdr:observation/wmdr:ObservingCapability/wmdr:observation'
        element_name = "observation"
        matches = self.exml.xpath(xpath,namespaces=self.namespaces)
        if(not len(matches)):
            LOGGER.debug("%s not found" % element_name)
            comments.append("%s not found" % element_name)
        else:
            if len(matches) > 10:
                score += 3
            elif len(matches) > 5:
                LOGGER.debug("found 6-10 %s (goal >10)" % element_name)
                comments.append("found 6-10 %s (goal >10)" % element_name)
                score += 2
            elif len(matches) > 1:
                LOGGER.debug("found 2-5 %s (goal >10)" % element_name)
                comments.append("found 2-5 %s (goal >10)" % element_name)
                score += 1
            else:
                LOGGER.debug("found 1 %s (goal >10)" % element_name)
                comments.append("found 1 %s (goal >10)" % element_name)

        LOGGER.debug("rule 6-0-01, score: %s, goal %s" % (score-previous_score,3))
        previous_score = score

        # Rule 6-0-02 Application area(s). Deployment has more than one application area.
        # 1 (for each deployment)
        
        xpath = '//wmdr:deployment/wmdr:Deployment'
        element_name = "deployment"
        deployments = self.exml.xpath(xpath,namespaces=self.namespaces)
        if(not len(deployments)):
            LOGGER.debug("%s not found" % element_name)
            comments.append("%s not found" % element_name)
        else:
            sub_score = 0
            for deployment in deployments:
                xpath = 'wmdr:applicationArea'
                element_name = "application area"
                matches = deployment.xpath(xpath,namespaces=self.namespaces)
                if(not len(matches)):
                    LOGGER.debug("%s not found" % element_name)
                    comments.append("%s not found" % element_name)
                else:
                    application_areas = set()
                    count = 0
                    for match in matches:
                        count = count + 1
                        text = match.get('{http://www.w3.org/1999/xlink}href')
                        sscore, scomments, svalue = validate_text(text,"href",element_name,codelist=self.codelists["ApplicationArea"])
                        comments = comments + scomments
                        if(svalue):
                            application_areas.add(svalue)
                    if len(application_areas) < 2:
                        LOGGER.debug("found 0-1 valid %s (goal >1)" % element_name)
                        comments.append("found 0-1 valid %s (goal >1)" % element_name)
                    else:
                        sub_score += 1
            score += sub_score / len(deployments)

        LOGGER.debug("rule 6-0-04, score: %s, goal %s" % (score-previous_score,1))
        previous_score = score

        # Rule 6-0-03 Near real time availability. Data are available for near real time. 
        # 1 (for each deployment) 
        # NOTE missing criteria for what is considered near real time, using 24 hours
        time_interval = timedelta(days=1)

        xpath = '//wmdr:deployment/wmdr:Deployment/wmdr:validPeriod/gml:TimePeriod/gml:endPosition'
        element_name = "end position of deployment valid period"
        matches = self.exml.xpath(xpath,namespaces=self.namespaces)
        if(not len(matches)):
            LOGGER.debug("%s not found" % element_name)
            comments.append("%s not found" % element_name)
        else:
            sum = 0
            count = 0
            for match in matches:
                count = count + 1
                text = match.text
                sscore, scomments, svalue = validate_text(text,"datetime",element_name)
                comments = comments + scomments
                if svalue:
                    if svalue + time_interval < datetime.now(timezone.utc):
                        LOGGER.debug("deployment is not real time")
                        comments.append("deployment is not real time")
                    else:
                        sum = sum + 1
            score += sum / count * 1

        LOGGER.debug("rule 6-0-04, score: %s, goal %s" % (score-previous_score,1))

        return name, total, score, comments
    
    def kpi_61(self):
        """
        Implements KPI-6-1: Maintenance of a station record. Timeliness of data implementation rules

        :returns: `tuple` of KPI name, achieved score, total score, and comments
        """

        total = 1
        score = 0
        comments = []
        name = 'KPI-6-1: Maintenance of a station record'
        LOGGER.info(f'Running {name}')

        # TODO as defined by Oscar/surface

        return name, total, score, comments

    #### END OF KPIS ####

    def evaluate(self, kpi: int = 0) -> dict:
        """
        Convenience function to run all tests

        :returns: `dict` of overall test report
        """

        known_kpis = [
            'kpi_10',
            'kpi_20',
            'kpi_30',
            'kpi_31',
            'kpi_40',
            'kpi_41',
            'kpi_60'
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
            if results['kpi_10']['percentage'] != 100:
                overall_grade = 'U'
            else:
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
        "station_characteristics": [20, 21],    
        "observations_measurements": [30],
        "station_contacts": [40, 41],
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
