# pytest-cqase
![versions](https://img.shields.io/pypi/pyversions/pybadges.svg)

This is a custom pytest plugin for TMS QASE.

Official pytest plugin: https://github.com/qase-tms/qase-python/tree/master/qase-pytest

API QASE: https://developers.qase.io/reference/

Guide: https://developers.qase.io/docs

### Installation

------------

You can install via pip
```
$ pip install pytest-cqase
```
or with poetry
```
$ poetry add -D pytest-cqase
```

### How to work

------------

First, create your project in QASE TMS and **get api token** from page https://app.qase.io/user/api/token (See guide).

Second, open project settings and **enable** the option  "Allow submitting results in bulk".

Configuration could be provided both by `pytest.ini`/`tox.ini` params
and using command-line arguments:

* Command-line args:
```
  --qase                Use Qase TMS
  --qase-api-token=QS_API_TOKEN
                        Api token for Qase TMS
  --qase-project=QS_PROJECT_CODE
                        Project code in Qase TMS
  --qase-testrun=QS_TESTRUN_ID
                        Testrun ID in Qase TMS
  --qase-complete-run   Complete run after all tests are finished
```

* INI file parameters:

```
  qs_enabled (bool):    default value for --qase
  qs_api_token (string):
                        default value for --qase-api-token
  qs_project_code (string):
                        default value for --qase-project
  qs_testrun_id (string):
                        default value for --qase-testrun
  qs_complete_run (bool):
                        default value for --qase-complete-run
```

### Link tests with test-cases

To link tests with test-cases in Qase TMS you should use predefined decorator:

```python
from pytest_cqase.plugin import qase

@qase.id(13)
def test_example_1():
    pass

@qase.id(14)
def test_example_2():
    pass
```

Each unique number can only be assigned once to the class or function being used. You could pass as much IDs as you need.

### Possible cases statuses

- PASSED - when test passed
- FAILED - when test failed with AssertionError
- BLOCKED - when test failed with any other exception
- SKIPPED - when test has been skipped

### Known issues

1. Tests use only bulk sending of results, do not forget to enable this option in the settings
2. To run parallel tests (xdist), do not use the option qs_complete_run
3. At the moment, the plugin does not support adding attachments.
4. Auto creation of test cases will be added in the future
