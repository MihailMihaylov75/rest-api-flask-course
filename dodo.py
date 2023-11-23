"""
dodo.py for the ui-testing-core project - these are `doit` targets definitions.

To avoid creating `__pycache__` directories, consider using `python -B`
or "PYTHONDONTWRITEBYTECODE=1" (e.g. on Windows).


`Doit` allows for teh full power of python and it syntax clarity and debugging
capabilities to be employed in defining build tasks.

More about `doit` on https://pydoit.org/.
"""
from typing import Dict

import os
import sys
import shutil
from os.path import dirname, exists, isdir
from posixpath import join as posix_join
from pathlib import Path
from functools import lru_cache

from doit.action import CmdAction

from scripts.dodolib.helpers import actions_of
from scripts.dodolib.fsutil import recursive_remove, find_repo_root
from scripts.dodolib.netutil import GeckoDownloader, ChromeDownloader

REPO_ROOT = Path(find_repo_root(os.getcwd()))
SRC_DIR = Path('src')
TEST_DIR = Path('tests')
VENV_ROOT = Path('.venv')
SCRIPTS_DIR = Path('scripts')
CONF_DIR = Path('conf')
DOCS_DIR = Path('docs')
TEMP_DIR = Path('.cache')
BUILD_DIR = Path('build')

UNIT_TEST_DIR = TEST_DIR / 'unit_tests'
OFFLINE_TEST_DIR = TEST_DIR / 'offline_tests'
ONLINE_TEST_DIR = TEST_DIR / 'online_tests'
DOCTREES_DIR = BUILD_DIR / 'doctrees'
DOCHTML_DIR = BUILD_DIR / 'dochtml'
DODOLIB_ROOT = SCRIPTS_DIR / 'dodolib'
DODOLIB_MODS_4TEST = ('_tests',)

PYLINT_ROOT_PKG = SRC_DIR
PY_VER = '.'.join(map(str, sys.version_info[:2]))
DOIT_DEP_FILE = DODOLIB_ROOT / 'doit.json'

PATH = os.environ['PATH']
ENVIRONMENT_NAME = os.environ.get('ENVIRONMENT_NAME')
LOCAL_FESTO_REPO = \
    "https://adeartifactory1.de.festo.net/artifactory/api/pypi/pypi-python-remote/simple"

# see https://pydoit.org/configuration.html
DOIT_CONFIG = {
    'verbosity': 1,
    'backend': 'json',  # mdb fails on Windows
    'dep_file': str(DOIT_DEP_FILE),
    'default_tasks': [
        # 'cov-term',  # let's see what would ne useful as a default target
    ],
}

# [1] Cannot keep doit dep file in TMP_DIR as data is removed while doit
#     is running during `clean-temp` task, which fails miserably.

if os.name == 'posix':
    VENV_BIN = VENV_ROOT / 'bin'
    PYTHON_BIN = VENV_BIN / 'python'
    PIP_BIN = VENV_BIN / 'pip'
    VENV_SITE_PACKAGES = VENV_ROOT / 'lib' / f'python{PY_VER}' / 'site-packages'
    NOOP = '/bin/true'
    ENV_QUOTE = '"'

elif os.name == 'nt':
    VENV_BIN = VENV_ROOT / 'Scripts'
    PYTHON_BIN = VENV_BIN / 'python.exe'
    PIP_BIN = VENV_BIN / 'pip.exe'
    VENV_SITE_PACKAGES = VENV_ROOT / 'Lib' / 'site-packages'
    NOOP = '(exit 0)'
    ENV_QUOTE = ''  # Env variables on Windows must NOT be quoted

else:
    print('ERROR: Unsupported OS:', os.name, '- exitting.', file=sys.stderr)
    sys.exit(3)

# By default store webdrivers into .vemv/bin (should be in PATH)
WEBDRIVER_DIR = VENV_BIN

# Create DOIT_DEP_FILE directory if not existent (avoid .gitkeep)
if not exists(dirname(DOIT_DEP_FILE)):
    os.mkdir(dirname(DOIT_DEP_FILE))


def _print(*args, **kw):
    """Alias for the builtin ``print()`` (``doit`` does not accept
    builtins as action functions).
    """
    print(*args, **kw)


def _osremove(*args, **kw):
    """Alias for the builtin ``os.remove()`` (see above)."""
    os.remove(*args, *kw)


@lru_cache()
def getenv() -> Dict[str, str]:
    """Return a dict with suitable OS environment variables to set
    during task executions.
    """
    envdict = dict(
        PYTHONPATH=(
            f'{REPO_ROOT}'
            f'{os.pathsep}{REPO_ROOT / SRC_DIR}'
            f'{os.pathsep}{REPO_ROOT / TEST_DIR}'
        ),
        PATH=PATH,
        FESTO_REPO_ROOT=os.environ.get('FESTO_REPO_ROOT', 'NOTSET'),
    )
    if str(VENV_BIN) not in PATH:
        venv_bin_path = str(REPO_ROOT / VENV_BIN)
        _PATH = os.pathsep.join((venv_bin_path, PATH))
        envdict.update(PATH=_PATH)

    return envdict


def with_env(command: str) -> CmdAction:
    """Return a CmdAction carrying given command with OS environment set."""
    # Skip setting env vars on Windows as command execution breaks raising:
    # `Fatal Python error: _Py_HashRandomization_Init:
    # failed to get random numbers to initialize Python`
    if os.name == 'nt':
        return CmdAction(command)

    return CmdAction(command, env=getenv())


def task_pylint() -> dict:
    """Run pylint checks."""
    return {
        'actions': [f'pylint {PYLINT_ROOT_PKG}'],
    }


def task_test_dodo() -> dict:
    """Run doit code (dodo) test suite."""
    modules = ' '.join(f'{DODOLIB_ROOT / mod}' for mod in DODOLIB_MODS_4TEST)
    # pytest doesn't like single backslashes on Windows:
    modules = modules.replace('\\', '/')
    return {
        'verbosity': 2,
        'basename': 'test-dodo',
        'actions': [
            f'{VENV_BIN / "pip"} install --index-url {LOCAL_FESTO_REPO} pyfakefs',
            with_env(f'pytest --no-cov {modules}'),
        ],
    }


def task_cov_html() -> dict:
    """Run tests and generate test coverage report in HTML format."""
    cwd_as_uri = Path(os.getcwd()).as_uri()
    report_url = posix_join(cwd_as_uri, TEMP_DIR, 'htmlcov', 'index.html')
    return {
        'verbosity': 2,
        'basename': 'cov-html',
        'actions': [
            with_env(
                f'pytest --cov={SRC_DIR} --cov-report=html {UNIT_TEST_DIR}'
            ),
            (_print, ['HTML report URL:', report_url, '\n']),
        ],
    }


def clean_temp() -> None:
    """Remove the temporary stuff."""
    for thedir in (TEMP_DIR, BUILD_DIR):
        if exists(thedir):
            print(f'Removing {thedir} ...')
            shutil.rmtree(thedir)


def task_clean_pycache() -> dict:
    """Remove any `__pycache__/` directories within the project tree.

    Note that this would always find the root `__pycache__` and
    `scripts/__pycache__` unless bytecode caching is suppressed, due to
    the Python interpreter importing `dodo.py` and `dodolib.py`.
    """
    return {
        'basename': 'clean-pycache',
        'actions': [
            (recursive_remove, [os.getcwd(), '**/__pycache__', isdir]),
        ],
    }


def task_clean_pytyest_cache() -> dict:
    """Remove any `.pytest_cache` directories within the project tree."""
    return {
        'basename': 'clean-pytest-cache',
        'actions': [
            (recursive_remove, [os.getcwd(), '**/.pytest_cache', isdir]),
        ],
    }


def task_clean_temp() -> dict:
    """Remove the cache directory containing intermittent stuff."""
    return {
        'basename': 'clean-temp',
        'actions': [
            (clean_temp,),
        ],
    }


def task_clean_all() -> dict:
    """Clean up all garbage."""
    return {
        'basename': 'clean-all',
        'actions': actions_of(
            task_clean_temp,
            task_clean_pycache,
            task_clean_pytyest_cache,
        ),
    }


def task_show_env() -> dict:
    """Dump OS environment variables ready to be evaluated."""
    # TODO: support Windows cmd.exe via 'set PYTHONPATH=' and proper path sep
    the_verb = 'set' if os.name == 'nt' else 'export'

    def print_envs(envs: Dict[str, str]) -> None:
        """Print environments"""
        for name, value in envs.items():
            quote = ENV_QUOTE
            print(f'{the_verb} {name}={quote}{value}{quote}')

    return {
        'verbosity': 2,
        'basename': 'show-env',
        'actions': [
            (print_envs, [getenv()]),
        ],
    }


def maybe_create_empty_venv_cmd() -> str:
    """Return a command string for creating a pyton virtualenv if one does not
    exist, otherwise return a shell No-Op.
    """
    if not PYTHON_BIN.exists():
        shutil.rmtree(VENV_ROOT)
        return f'python{PY_VER} -m venv {VENV_ROOT}'

    return NOOP


def task_venv_dev() -> dict:
    """Set (or update) project's virtual environment."""

    return {
        'basename': 'venv-dev',
        'actions': [
            maybe_create_empty_venv_cmd,
            with_env(f'{PYTHON_BIN} -m pip install --index-url {LOCAL_FESTO_REPO} -U pip setuptools wheel'),
            f'{PYTHON_BIN} {SCRIPTS_DIR / "extract_req.py"} -o requirements.txt',
            with_env(f'{PIP_BIN} install --index-url {LOCAL_FESTO_REPO} -Ur requirements.txt'),
            (_osremove, ['requirements.txt']),
        ]
    }


def task_init() -> dict:
    """Initialize environment after bootstrapping with `init-venv.sh`."""

    return {
        'actions': actions_of(
            task_clean_all,
            task_venv_dev,
        ),
    }
