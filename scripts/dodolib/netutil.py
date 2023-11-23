"""
Network-related utilities for the doit tool targets.
"""
import re
import subprocess
from typing import Any, Dict, Set
from abc import ABC, abstractmethod

import os
import platform
from collections import namedtuple
from os.path import dirname, isfile, join as pjoin
from posixpath import join as posix_join, sep as posix_sep
from urllib.error import URLError
from urllib.parse import urlunparse
from functools import lru_cache
from urllib.request import urlopen

import requests

from scripts.dodolib._types import PathT
from scripts.dodolib.fsutil import unarchive

DEFAULT_BUFFER_SIZE = 8 * 1024


def download_file(url, path: PathT, buffer_size: int = DEFAULT_BUFFER_SIZE):
    """Download a binary file with an HTTP GET request and store it
    at given filesystem full path location.

    :param url: the HTTP url to download the file from
    :param path: filesystem path location
    :param buffer_size: size of the buffer
    :return:
    """
    with requests.get(url, stream=True) as resp:
        resp.raise_for_status()  # raise HTTPError on status 4xx/5xx
        with open(path, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=buffer_size):
                if not chunk:
                    continue
                fd.write(chunk)


def substitute_keywords(template_dict: Dict[str, str], **kw) -> Dict[str, str]:
    """Return a new dict created out of ``template_dict`` after substituting
    any keywords found in its values using mapping given in ``kw``.

    :param template_dict: the original dict with values with potential keywords
                          (e.g. {'call_message': 'please call {name}'})
    :param kw: keyword -> substitution value map (e.g. dict(name='Alissa'))
    :return: new dict with complete substitution (e.g. {'call_message': 'please call Alissa'})
    """
    return {name: value.format(**kw) for name, value in template_dict.items()}


class DriverDownloader(ABC):
    """Interface for driver-downloader implementations."""

    attrnames: Set[str] = set()  # must override in sub-classes

    def _check_attributes(self, args):
        """Raise TypeError if argument names are not a sub-set of
        ``attr names``."""
        passed_names = set(args.keys())
        if not (passed_names <= self.attrnames):
            raise TypeError(f'Unknown argument(s): {",".join(passed_names - self.attrnames)}')

    def configure(self, **kwargs: Any) -> None:
        """Configure downloader"""
        self._check_attributes(kwargs)
        for name, value in kwargs.items():
            setattr(self, name, value)

    @abstractmethod
    def basename(self, uname=None) -> str:
        """Return the base name of the file to be downloaded."""

    @abstractmethod
    def go(self, target_dir: PathT) -> None:
        """Do the actual download storing the driver into given ``target_dir``."""


class GeckoDownloader(DriverDownloader):
    """Downloader for the geckodriver (for Firefox)."""

    # Download URL broken into urlparse parts
    WEBDRIVER_GECKO_URL_PARTS = {
        'scheme': 'https',
        'netloc': 'github.com',
        'path': '/mozilla/geckodriver/releases',
    }

    # Mapping platform.uname().system + '-' + platform.uname().machine
    # to downloadable drivers files' suffixes, e.g. 'geckodriver-v0.29.0-linux64.tar.gz'
    # or 'geckodriver-v0.29.0-win32.zip'
    WEBDRIVER_GECKO_FILE_SUFFIX_MAP = {
        'Linux-x86_64': 'linux64.tar.gz',
        'Linux-x86': 'linux32.tar.gz',
        'Windows-AMD64': 'win64.zip',
        'Windows-x86': 'win32.zip',
    }

    attrnames = {'directory', 'version'}
    UrlParts = namedtuple('UrlParts', 'scheme netloc path params query fragment')

    def __init__(self):
        super().__init__()
        self.directory: str = '/tmp'
        self.version: str = 'latest'

    @property
    def basename(self, uname=None) -> str:
        """Get basename."""
        uname = platform.uname()
        suffix = self.WEBDRIVER_GECKO_FILE_SUFFIX_MAP[uname.system + '-' + uname.machine]
        return f'geckodriver-v{self.version}-{suffix}'

    @property
    def main_url(self) -> str:
        """Return the main download URL as defined in `WEBDRIVER_GECKO_URL_PARTS`."""
        parts_kw = substitute_keywords(self.WEBDRIVER_GECKO_URL_PARTS, version=self.version)
        parts_kw.update(dict(params='', query='', fragment=''))  # needed by urlunparse()
        return urlunparse(self.UrlParts(**parts_kw))

    @lru_cache(maxsize=1)
    def get_latest_version(self):
        """Get latest geckodriver version."""
        latest_url = posix_join(self.main_url, 'latest')
        resp = requests.get(latest_url, allow_redirects=False)
        assert resp.status_code == 302, f'Expected status code 302, got {resp.status_code}'
        return resp.headers['location'].strip().rsplit(posix_sep)[-1].lstrip('v')

    def _save_version_file(self, fullpath: PathT) -> None:
        """Save geckodriver version."""
        with open(pjoin(dirname(fullpath), 'version'), 'w') as fd:
            print('geckodriver ', self.version, sep='', file=fd)

    def go(self, target_dir: PathT = None) -> None:
        """Download geckodriver.exe"""
        if self.version == 'latest':
            self.version = self.get_latest_version()
            print('geckodriver latest version:', self.version)

        download_url = posix_join(self.main_url, 'download', f'v{self.version}', self.basename)
        fullpath = pjoin(self.directory, self.basename)
        download_file(download_url, fullpath)
        assert isfile(fullpath), f'FAILED downloading {download_url} into {fullpath}'
        unarchive(fullpath)
        os.remove(fullpath)
        self._save_version_file(fullpath)


class ChromeDownloader(DriverDownloader):
    """Downloader for the chrome."""

    WEBDRIVER_CHROME_FILE_SUFFIX_MAP = {
        'Linux-x86_64': 'linux64.zip',
        'Linux-x86': 'linux64.zip',
        'Windows-AMD64': 'win32.zip',
        'Windows-x86': 'win32.zip',
    }

    attrnames = {'directory', 'version'}

    CHROME_BASE_DOWNLOAD_URL = "https://chromedriver.storage.googleapis.com"
    LATEST_RELEASE_URL = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"

    def __init__(self):
        super().__init__()
        self.directory: str = '/tmp'

    @property
    def basename(self, uname=None) -> str:
        """Get basename."""
        uname = platform.uname()
        suffix = self.WEBDRIVER_CHROME_FILE_SUFFIX_MAP[uname.system + '-' + uname.machine]
        return f'chromedriver_{suffix}'

    @staticmethod
    def get_chrome_version():
        """
        :return: the version of chrome installed on client
        """
        if platform.system() == 'linux':
            with subprocess.Popen(['chromium-browser', '--version'],
                                  stdout=subprocess.PIPE) as proc:
                version = proc.stdout.read().decode('utf-8').replace('Chromium', '').strip()
                version = version.replace('Google Chrome', '').strip()
        elif platform.system() == 'Windows':
            process = subprocess.Popen(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v',
                 'version'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
            )
            version = process.communicate()[0].decode('UTF-8').strip().split()[-1]
        else:
            return
        chrome_ver_reg = re.compile(r'\d+\.\d+\.\d+')
        version = chrome_ver_reg.search(version).group()
        return version

    def get_latest_release_for_version(self, version=None):
        """
        Searches for the latest release (complete version string) for a given major `version`. If `version` is None
        the latest release is returned.
        :param version: Major version number or None
        :return: Latest release for given version
        """
        release_url = self.LATEST_RELEASE_URL + '_{}'.format(version)
        try:
            response = urlopen(release_url)
            if response.getcode() != 200:
                raise URLError('Not Found')
            return response.read().decode('utf-8').strip()
        except URLError:
            raise RuntimeError('Failed to find release information: {}'.format(release_url))

    def get_chromedriver_url(self, version):
        """
        Generates the download URL for current platform , architecture and the given version.
        Supports Linux, MacOS and Windows.
        :param version: chromedriver version string
        :return: Download URL for chromedriver
        """
        return self.CHROME_BASE_DOWNLOAD_URL + '/' + version + '/' + self.basename

    def go(self, target_dir: PathT = None) -> None:
        """Download chrome.exe"""
        chrome_version = self.get_chrome_version()
        latest_stable_release = self.get_latest_release_for_version(chrome_version)
        download_url = self.get_chromedriver_url(latest_stable_release)
        fullpath = pjoin(self.directory, self.basename)
        download_file(download_url, fullpath)
        assert isfile(fullpath), f'FAILED downloading {download_url} into {fullpath}'
        unarchive(fullpath)
        os.remove(fullpath)
        print('chromedriver version {}'.format(latest_stable_release))
