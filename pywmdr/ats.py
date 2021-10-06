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

# abstract test suite as per WMO Metadata Representation version 1.0 http://def.wmo.int/wmdr/1.0

from io import BytesIO
import logging

import click

from pywmdr.util import (get_cli_common_options, get_codelists_from_rdf,
                         get_string_or_anchor_value, NAMESPACES,
                         nspath_eval, parse_wmdr, setup_logger,
                         urlopen_, validate_wmdr_xml)

LOGGER = logging.getLogger(__name__)

CODELIST_PREFIX = 'http://wis.wmo.int/2012/codelists/WMOCodeLists.xml' # Is it available for WMDR?


def msg(test_id: str, test_description: str) -> str:
    """
    Convenience function to print test props

    :param test_id: test suite identifier
    :param test_description: test suite identifier

    :returns: user-friendly string of test properties
    """

    requirement = test_id.split('test_requirement_')[-1].replace('_', '.')

    return f'Requirement {requirement}:\n    {test_description}'


def gen_test_id(test_id: str) -> str:
    """
    Convenience function to print test identifier as URI

    :param test_id: test suite identifier

    :returns: test identifier as URI
    """

    return f'http://wis.wmo.int/2012/metadata/conf/{test_id}'


class WMDRTestSuite:
    """Test suite for WMO Metadata Representation for WIGOS"""

    def __init__(self, exml):
        """
        initializer

        :param exml: `etree.ElementTree` object

        :returns: `pywcmp.ats.WMOCoreMetadataProfileTestSuite13`
        """

        self.test_id = None
        rtag = exml.getroot().tag
        if rtag != "{http://def.wmo.int/wmdr/1.0}WIGOSMetadataRecord":
            wigosmetadatarecord = exml.getroot().find('.//{http://def.wmo.int/wmdr/1.0}WIGOSMetadataRecord')
            if wigosmetadatarecord is None:
                raise RuntimeError('Does not look like a WMDR document!')
            exml._setroot(wigosmetadatarecord)
        self.exml = exml
        self.namespaces = self.exml.getroot().nsmap

        # generate dict of codelists
        self.codelists = get_codelists_from_rdf()

    def run_tests(self):
        """Convenience function to run all tests"""

        tests = ['1_1_1']

        error_stack = []
        for i in tests:
            test_name = f'test_requirement_{i}'
            try:
                getattr(self, test_name)()
            except AssertionError as err:
                message = f'ASSERTION ERROR: {err}'
                LOGGER.info(message)
                error_stack.append(message)
            except Exception as err:
                message = f'OTHER ERROR: {err}'
                LOGGER.info(message)
                error_stack.append(message)

        if len(error_stack) > 0:
            raise TestSuiteError('Invalid metadata', error_stack)

    def test_requirement_1_1_1(self):
        """Requirement 1.1.1: Each WIGOS Metadata record shall validate without error against the XML schemas defined in https://schemas.wmo.int/wmdr/"""
        self.test_id = gen_test_id('WMDR-xml-schema-validation')
        validate_wmdr_xml(self.exml)

    def _get_wmo_keyword_lists(self, code: str = 'WMO_CategoryCode') -> list:
        """
        Helper function to retrieve all keyword sets by code

        :param code: code list name (default: `WMO_CategoryCode`)

        :returns: `list` of keyword set by code
        """

        wmo_cats = []

        keywords_sets = self.exml.findall(nspath_eval('gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords'))

        for kwd in keywords_sets:  # find thesaurusname
            node = kwd.find(nspath_eval('gmd:thesaurusName/gmd:CI_Citation/gmd:title'))
            if node is not None:
                node2 = node.find(nspath_eval('gmx:Anchor'))
                if node2 is not None:  # search gmx:Anchor
                    value = node2.get(nspath_eval('xlink:href'))
                    if value == f'{CODELIST_PREFIX}#{code}':
                        wmo_cats.append(kwd)
                else:  # gmd:title should be code var
                    value = node.find(nspath_eval('gco:CharacterString'))
                    if value is not None and value.text == code:
                        wmo_cats.append(kwd)
        return wmo_cats

    def _get_keyword_values(self, keyword_nodes: list) -> list:
        values = []
        for keyword_node in keyword_nodes:
            anchor_node = keyword_node.find(nspath_eval('gmx:Anchor'))
            if anchor_node is not None:
                value = anchor_node.get(nspath_eval('xlink:href'))
                values.append(value)
            else:
                value_node = keyword_node.find(nspath_eval('gco:CharacterString'))
                if value_node is not None:
                    values.append(value_node.text)
        return values


class TestSuiteError(Exception):
    """custom exception handler"""
    def __init__(self, message, errors):
        """set error list/stack"""
        super(TestSuiteError, self).__init__(message)
        self.errors = errors


@click.group()
def ats():
    """abstract test suite"""
    pass


@click.command()
@click.pass_context
@get_cli_common_options
@click.option('--file', '-f', 'file_',
              type=click.Path(exists=True, resolve_path=True),
              help='Path to XML file')
@click.option('--url', '-u',
              help='URL of XML file')
def validate(ctx, file_, url, logfile, verbosity):
    """validate against the abstract test suite"""

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

    ts = WMDRTestSuite(exml)

    # run the tests
    try:
        ts.run_tests()
        click.echo('Success!')
    except TestSuiteError as err:
        msg = '\n'.join(err.errors)
        click.echo(msg)


ats.add_command(validate)
