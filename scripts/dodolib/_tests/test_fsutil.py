"""
Unit tests for the .. module:: dodolib.fsutils module.
"""

import os
from os.path import exists, isdir
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem as FakeFs

from scripts.dodolib.fsutil import (
    unarchive,
    find_repo_root,
    find_glob,
    recursive_remove,
)
from . import (
    fake_fs,  # do not remove fake_fs - used via injection
    FSROOT,
    get_content,
    create_targz_file,
    create_zip_file,
)


def test_unarchive_targz(fake_fs: FakeFs):
    # pyfakefs doesn't seem to properly handle unarchiving
    # when the_dir is not empty :(
    the_dir = Path('')
    archive_path = create_targz_file(fake_fs, the_dir)
    assert exists(archive_path)
    assert not exists(the_dir / 'file-1.txt')
    assert not exists(the_dir / 'file-2.txt')
    unarchive(archive_path)
    assert exists(archive_path)
    assert exists(the_dir / 'file-1.txt')
    assert exists(the_dir / 'file-2.txt')
    assert get_content(the_dir / 'file-1.txt') == 'First test file\n'
    assert get_content(the_dir / 'file-2.txt') == 'Second test file\n'


def test_unarchive_zip(fake_fs: FakeFs):
    # pyfakefs doesn't seem to properly handle unarchiving
    # when the_dir is not empty :(
    the_dir = Path('')
    archive_path = create_zip_file(fake_fs, the_dir)
    assert exists(archive_path)
    assert not exists(the_dir / 'file-1.txt')
    assert not exists(the_dir / 'file-2.txt')
    unarchive(archive_path)
    assert exists(archive_path)
    assert exists(the_dir / 'file-1.txt')
    assert exists(the_dir / 'file-2.txt')
    assert get_content(the_dir / 'file-1.txt') == 'First test file\n'
    assert get_content(the_dir / 'file-2.txt') == 'Second test file\n'


def test_find_repo_root_success(fake_fs: FakeFs):
    the_path = FSROOT / 'rootdir' / 'project' / 'package' / 'sub_package'
    fake_fs.makedirs(the_path)
    fake_fs.makedirs(FSROOT / 'rootdir' / 'project' / '.git')
    expected = Path(os.sep) / 'rootdir' / 'project'
    assert find_repo_root(the_path) == str(expected)


def test_find_repo_root_no_gitdir_no_success(fake_fs: FakeFs):
    the_path = FSROOT / 'rootdir' / 'project' / 'package'
    fake_fs.makedirs(the_path)
    with pytest.raises(RuntimeError):
        find_repo_root(the_path)


def test_find_repo_root_below_gitdir_no_success(fake_fs: FakeFs):
    the_path = FSROOT / 'rootdir' / 'project' / 'package' / 'sub_package'
    fake_fs.makedirs(the_path)
    fake_fs.makedirs(the_path / '.git')
    start_path = Path(os.sep) / 'rootdir' / 'project'
    with pytest.raises(RuntimeError):
        find_repo_root(start_path)


def test_find_glob(fake_fs: FakeFs):
    fake_fs.create_dir(FSROOT / 'rootdir' / 'project' / 'package' / '__dir1__')
    fake_fs.create_dir(FSROOT / 'rootdir' / 'project' / '__dir22__')
    fake_fs.create_dir(FSROOT / 'rootdir' / '__dir3__')
    fake_fs.create_dir(FSROOT / '__dir4__')
    expected = [
        '__dir4__',
        str(Path('rootdir') / '__dir3__'),
        str(Path('rootdir') / 'project' / 'package' / '__dir1__'),
    ]
    assert list(find_glob(FSROOT, '**/__dir?__')) == expected


def test_recursive_remove(fake_fs: FakeFs):
    fake_fs.create_dir(FSROOT / 'rootdir' / 'project' / 'package' / '__dir1__')
    fake_fs.create_dir(FSROOT / 'rootdir' / 'project' / '__dir22__')
    fake_fs.create_dir(FSROOT / 'rootdir' / '__dir3__')
    fake_fs.create_dir(FSROOT / '__dir4__')
    does_qualify = lambda p: isdir(p) and p != '__dir3__'
    recursive_remove(FSROOT / 'rootdir' / 'project', '**/__dir?__', filter_fn=does_qualify)
    assert not exists(FSROOT / 'rootdir' / 'project' / 'package' / '__dir1__')  # removed
    assert exists(FSROOT / 'rootdir' / 'project' / '__dir22__')  # excluded by glob pattern
    assert exists(FSROOT / 'rootdir' / '__dir3__')  # excluded by filter
    assert exists(FSROOT / '__dir4__')  # excluded by start dir choice
