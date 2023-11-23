"""
Common test helpers
"""
import os
import tarfile
import zipfile
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem as FakeFs
from pyfakefs.fake_filesystem_unittest import Patcher

from scripts.dodolib._types import PathT

FSROOT = Path(os.sep)


@pytest.fixture
def fake_fs():
    """Yield FakeFilesystem object to allow for tests which do not touch
    the real fs. (`pytest` has a `pyfakefs` plugin injecting a ready
    FakeFs as `fs` but we prefer to have an explicit feature for clarity.)
    """
    patcher = Patcher(use_cache=False)  # use_cache=False, allow_root_user=False
    patcher.setUp()
    yield patcher.fs
    patcher.tearDown()


def get_content(fullpath: PathT) -> str:
    """Return content of text file with given full path."""
    with open(fullpath, 'r') as fd:
        return fd.read()


def _create_two_files(fake_fs: FakeFs, the_dir: Path):
    first_filepath = the_dir / 'file-1.txt'
    second_filepath = the_dir / 'file-2.txt'
    fake_fs.create_file(first_filepath, contents='First test file\n')
    fake_fs.create_file(second_filepath, contents='Second test file\n')
    return first_filepath, second_filepath


def create_targz_file(fake_fs: FakeFs, the_dir: Path = '') -> PathT:
    first_filepath, second_filepath = _create_two_files(fake_fs, the_dir)
    archive_path = the_dir / 'sample.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as mytar:
        mytar.add(first_filepath)
        mytar.add(second_filepath)
    os.remove(first_filepath)
    os.remove(second_filepath)
    return archive_path


def create_zip_file(fake_fs: FakeFs, the_dir: Path = '') -> PathT:
    first_filepath, second_filepath = _create_two_files(fake_fs, the_dir)
    archive_path = the_dir / 'sample.zip'
    with zipfile.ZipFile(archive_path, 'a') as myzip:
        myzip.write(first_filepath)
        myzip.write(second_filepath)
    os.remove(first_filepath)
    os.remove(second_filepath)
    return archive_path
