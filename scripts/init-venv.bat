@echo off

:: init-venv.bat
:: First version for initializing venv on Windows

:: Initialize the environment so that `doit` targets get working. Requires
:: `py` to be in your PATH.
:: On Linux, run `init-env.sh`.

echo.
echo ** Checking your python interpreter...
python --version

echo.
echo ** Removing existing virtualenv (if any)...
rmdir .venv /S/Q

echo.
echo ** Creating new virtualenv...
python -m venv .venv

echo.
echo ** Updating pip setuptools and wheel ...
.venv\Scripts\python -m pip install --index-url "https://adeartifactory1.de.festo.net/artifactory/api/pypi/pypi-python-remote/simple" -U pip setuptools wheel
echo ** Updating pip setuptools and wheel OK...
echo ** Installing requests ...
.venv\Scripts\pip install --index-url "https://adeartifactory1.de.festo.net/artifactory/api/pypi/pypi-python-remote/simple" requests
echo ** Installing requests OK...
echo ** Installing doit...
.venv\Scripts\pip install --index-url "https://adeartifactory1.de.festo.net/artifactory/api/pypi/pypi-python-remote/simple" doit=="0.33.1"
echo ** Installing doit OK...

echo.
echo ** Installing requirements...
.venv\Scripts\doit init

.venv\Scripts\pip install --index-url "https://adeartifactory1.de.festo.net/artifactory/api/pypi/pypi-python-remote/simple" jsonschema==3.2.0 --force-reinstall

echo.
echo Python virtual environment created which allows executing
echo 'doit' build targets. (More about 'doit' in the README.rst)
echo.
echo Location: .venv
echo Full path: %VIRTUAL_ENV%
echo.
echo Activate the environment:
echo .venv\Scripts\activate
echo.
echo All targets can be seen via
echo "X:\> doit list"
echo.
echo Enjoy! ;)
echo.
echo (And hey, take look at the README if you haven't done so yet.)

:: this one must be the last command as the script stops then :(
.venv\Scripts\activate.bat
