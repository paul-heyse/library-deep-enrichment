# scikit-mine metadata compatibility

FCApy depends on scikit-mine 1.0.0. Its upstream metadata unconditionally requires
the `dataclasses` backport, whose latest release supports only Python 3.6. Python
3.14 supplies `dataclasses` in its standard library.

The retained wheel adds `python_version < "3.7"` to that dependency and identifies
the correction with local version `1.0.0+smartref.1`. All package code and license
bytes remain identical to the SHA-256-pinned upstream wheel. The provenance
receipt records both digests. No scientific algorithm or warning is patched.

Rebuild with `python vendor/rebuild_scikit_mine.py` from the tooling directory.
The script verifies upstream bytes before writing the deterministic wheel.
`uv.lock` selects this wheel explicitly; include it when distributing the tooling
source or preparing an offline dependency wheelhouse.
