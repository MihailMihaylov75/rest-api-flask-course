"""
Filesystem related utilities/helpers for the doit tool targets.
"""

from typing import Generator

import os
from functools import lru_cache
from os.path import (
    abspath,
    normpath,
    isdir,
    splitext,
    dirname,
    basename,
    join as pjoin,
)
from shutil import rmtree
from glob import glob

from scripts.dodolib._types import PathT, FilterFuncT


def unarchive(fullpath: PathT) -> None:
    """Unarchive given full path into its directory considering
    the archive format.

    :param fullpath: the full path of the original archive
    :raises: RuntimeError if arhive type is not supported
    """
    ext = splitext(fullpath)[1]
    if str(fullpath).endswith('.tar.gz') or ext == '.tgz':
        import tarfile

        with tarfile.open(fullpath, 'r:gz') as tar_arch:
            tar_arch.extractall(dirname(fullpath))
        return

    if ext == '.zip':
        import zipfile

        with zipfile.ZipFile(fullpath, 'r') as zip_arch:
            zip_arch.extractall(dirname(fullpath))
        return

    msg = f'Cannot unarchive file {basename(fullpath)} of type {ext!s}'
    raise RuntimeError(msg)


def _anyone(path: PathT):
    return True  # any path is accepted


def find_glob(
    root_dir: PathT, pattern: str, filter_fn: FilterFuncT = _anyone
) -> Generator[str, None, None]:
    """Yield a sequence of all files or directories matching given glob
    pattern.

    :param root_dir: str or Path - the root directory to start looking into
    :param pattern: str - the glob pattern for files and dirs to match
    :param filter_fn: callable - a boolean filtering function
    :return: yield a sequence of strings with path names relative to
             `root_dir`.
    """
    old_cwd = os.getcwd()

    try:
        os.chdir(root_dir)
        for path in glob(pattern, recursive=True):
            if filter_fn(path):
                yield path
    finally:
        os.chdir(old_cwd)


def recursive_remove(root_dir: PathT, pattern: str, filter_fn: FilterFuncT = _anyone) -> None:
    """Remove all filesystem objects matching glob `pattern`, found
    recursively within `root_dir` for which `filter_fn()` returns True.

    :param root_dir: str or Path - the root directory to start looking into
    :param pattern: str - the glob pattern for files and dirs to match
    :param filter_fn: callable - a boolean filtering function
    :return: None
    """
    for path in find_glob(root_dir, pattern, filter_fn=filter_fn):
        rmtree(path)


@lru_cache(maxsize=1)
def find_repo_root(start_dir: PathT = None) -> str:
    """Find and return the first git repo root directory within given `start_dir`.

    :param start_dir:
    :return: the repo root absolute path
    :raises: RuntimeError if repo root not found
    """
    start_dir = start_dir if start_dir else os.getcwd()
    curr_dir = abspath(normpath(start_dir))

    def _isdir(short_path):
        return isdir(pjoin(curr_dir, short_path))

    while curr_dir:
        sub_dirs = {path for path in os.listdir(curr_dir) if _isdir(path)}
        if '.git' in sub_dirs:
            return curr_dir
        curr_dir = curr_dir.rsplit(os.sep, 1)[0]

    raise RuntimeError(f'Cannot find git repo within {start_dir!r}')
