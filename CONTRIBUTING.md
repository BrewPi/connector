

# Test Coverage

New code is required to have unit tests providing 95% test coverage or more.


# PEP8

Contributions are required to conform to PEP8. We use flake8 to test these.

# Checking Requirements

Before committing, you can check the requirements by running `tox` in the root folder. This runs some of the tests
performed by the CI build.

## Setting up Local Development for simpler PEP8 compliance

- install flake8 into your python environment
```pip install flake8```
- [optional] integrate PEP8 into your IDE


### Adding Flake8 to PyCharm

These are outline instructions - for details on configuring external tools see
 -

- Add an external tool with these options:
  - Name: `flake8`
  - Program: `flake8`
  - Parameters: `--doctests --count --max-line-length=120 --format=pylint $FilePath$`
  - Working directory: `$ProjectFileDir$`
  - Add an external tool output filter:
    - `$FILE_PATH$\:$LINE$:\.*`