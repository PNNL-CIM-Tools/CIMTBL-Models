"""Load .cimtbl model files under their declared profile and summarize them.

Usage: python -I check_cimtbl.py MASTER.cimtbl [...]   (in the cimtables environment)
Exits non-zero, with the offending file and line, on the first row that fails to load.
"""
import collections
import sys
import tempfile

from cimgraph.core.env_vars import get_cim_profile
from cimgraph.databases import XMLFile
from cimgraph.models import FeederModel

import cimtables


def check(path: str) -> None:
    # parse first: the file's `Profile =` selects the profile (CIMG_CIM_PROFILE)
    cimtables.parse_file(path)
    get_cim_profile.cache_clear()
    _, cim = get_cim_profile()
    network = FeederModel(connection=XMLFile(filename=tempfile.mktemp(suffix='.xml')),
                          container=cim.Feeder(mRID='_check_container'), distributed=False)
    rows = cimtables.load(path, network)
    identities = network.list_identities()
    counts = collections.Counter(identity['class'] for identity in identities)
    without_mrid = sum(1 for identity in identities if identity['mRID'] is None)
    print(f'{path}: {len(rows)} rows -> {len(identities)} objects '
          f'({without_mrid} Identity-only, keyed by identifier)')
    for cls_name, count in sorted(counts.items()):
        print(f'  {count:5d}  {cls_name}')


for model_path in sys.argv[1:]:
    check(model_path)
