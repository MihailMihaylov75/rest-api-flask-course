"""
Generate requirements.txt out of a ``pyproject.toml``.
"""
from typing import Generator, Callable

import sys
import argparse

DEFAULT_INFILE = 'pyproject.toml'
DEFAULT_OUTFILE = 'stdout'


class DepExtractor:
    """Collect dependency information from ``pyproject.toml`` and generate
    ``requirements.txt`` style output appropriate for ``pip install -r``."""

    def __init__(self):
        self._in_dep_section = False
        self._deps = list()

    def process(self, line: str) -> None:
        """Parse a line from input file collecting any dependency information."""
        if not line.strip() and self._in_dep_section:
            self._in_dep_section = False

        elif 'dependencies]' in line:
            self._in_dep_section = True

        elif self._in_dep_section:
            if 'python' not in line.split():  # skip python itself ;)
                self._deps.append(line.strip())

    def deps(self) -> Generator[str, None, None]:
        """Return a generator yielding all dependencies, one per yield."""

        def strip_extra(input: str) -> str:
            """Return given extra after cleaning it up of surrounding characters."""
            input = input.strip(",")
            input = input.strip("[]")
            input = input.strip("'")
            return input

        for line in self._deps:
            extras = ''
            if 'extras' in line:
                extras = f'[{strip_extra(line.split()[4])}]'
            yield line.split()[0] + extras


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Extract requirements from pyproject.toml.')
    parser.add_argument(
        '-i', '--input-file',
        action='store',
        default='pyproject.toml',
        help='the file to read dependencies from (default: %(default)s)',
    )
    parser.add_argument(
        '-o', '--output-file',
        action='store',
        default='stdout',
        help='the file to write extracted dependencies to (default: %(default)s)',
    )
    args = parser.parse_args(argv)
    return args


def suitable_open_fn(filename: str, inout: str) -> Callable:
    if inout == 'out' and filename in ('stdout', '-'):
        return lambda *args: sys.stdout
    if inout == 'in' and filename in ('stdin', '-'):
        return lambda *args: sys.stdin
    return open


def _main(argv: list) -> int:
    args = parse_args(argv)
    infile = args.input_file
    outfile = args.output_file

    extractor = DepExtractor()
    with suitable_open_fn(infile, inout='in')(infile, 'r') as fd:
        for line in fd.readlines():
            extractor.process(line)

    with suitable_open_fn(outfile, inout='out')(outfile, 'w') as fd:
        for line in extractor.deps():
            print(line, file=fd)

    return 0


def main(argv: list):
    # try:
    return _main(argv)

    # except FileNotFoundError as err:
    #     print('Cannot find file:', str(err))
    # except Exception as err:
    #     print('ERROR: Unexpected exception:', type(err).__name__, str(err))
    #     return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
