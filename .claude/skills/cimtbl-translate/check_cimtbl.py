"""Load .cimtbl model files under their declared profile and model scope and summarize them.

Usage: python -I check_cimtbl.py MASTER.cimtbl [...]   (in the cimtables environment)
Exits non-zero, with the offending file and line, on the first row that fails to load.
"""
import collections
import sys

from cimgraph.core import get_model_authority, get_model_name

import cimtables


def check(path: str) -> None:
    # The file's Profile =, Authority = and Model = select the profile and model scope
    network = cimtables.load_model(path)
    identities = network.list_identities()
    counts = collections.Counter(identity['class'] for identity in identities)
    without_mrid = sum(1 for identity in identities if identity['mRID'] is None)
    container = network.container.mRID if network.container is not None else None
    print(f'{path}: {len(identities)} objects ({without_mrid} Identity-only, keyed by identifier)')
    print(f'  profile {network.cim.__name__}, authority {get_model_authority()!r}, '
          f'model {get_model_name()!r}, container {container!r}')
    for cls_name, count in sorted(counts.items()):
        print(f'  {count:5d}  {cls_name}')


for model_path in sys.argv[1:]:
    check(model_path)
