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

import click

from pywmdr.ats import ats
from pywmdr.kpi import kpi
from pywmdr.harvest import harvest
from pywmdr.metrics import metrics

__version__ = '0.1.dev0'


@click.group()
@click.version_option(version=__version__)
def cli():
    pass


cli.add_command(ats)
cli.add_command(kpi)
cli.add_command(harvest)
cli.add_command(metrics)