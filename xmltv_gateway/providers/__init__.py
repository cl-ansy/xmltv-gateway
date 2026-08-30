"""Provider registry.

A provider returns XMLTV bytes or raises, and reads its config from the
environment. Add one by writing a module beside this file and listing it here.
"""

from . import hdhomerun

PROVIDERS = {
    "hdhomerun": hdhomerun.fetch,
}
