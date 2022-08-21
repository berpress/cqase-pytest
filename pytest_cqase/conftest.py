from cqase.client import QaseClient

from pytest_cqase.plugin import PyTestQasePlugin


def get_option_ini(config, name):
    ret = config.getoption(name)  # 'default' arg won't work as expected
    if ret in (None, False):
        ret = config.getini(name)
    return ret


def pytest_addoption(parser):
    group = parser.getgroup("qase")

    def add_option_ini(option, dest, default=None, type=None, **kwargs):
        parser.addini(
            dest,
            default=default,
            type=type,
            help="default value for " + option,
        )
        group.addoption(option, dest=dest, **kwargs)

    add_option_ini(
        "--qase",
        "qs_enabled",
        default=False,
        type="bool",
        help="Use Qase TMS",
        action="store_true",
    )
    add_option_ini(
        "--qase-api-token",
        "qs_api_token",
        help="Api token for Qase TMS",
    )
    add_option_ini(
        "--qase-project",
        "qs_project_code",
        help="Project code in Qase TMS",
    )
    add_option_ini(
        "--qase-testrun",
        "qs_testrun_id",
        default=None,
        help="Testrun ID in Qase TMS",
    )
    add_option_ini(
        "--qase-testplan",
        "qs_testplan_id",
        default=None,
        help="Testplan ID in Qase TMS",
    )
    add_option_ini(
        "--qase-complete-run",
        "qs_complete_run",
        default=False,
        type="bool",
        help="Complete run after all tests are finished",
        action="store_true",
    )


def pytest_configure(config):
    qs_enabled = get_option_ini(config, "qs_enabled")
    if qs_enabled:
        qs_api_token = get_option_ini(config, "qs_api_token")
        qs_project_code = get_option_ini(config, "qs_project_code")
        qs_testrun_id = get_option_ini(config, "qs_testrun_id")
        qs_complete_run = get_option_ini(config, "qs_complete_run")

        client = QaseClient(
            api_token=qs_api_token,
        )

        config.pluginmanager.register(
            PyTestQasePlugin(
                client=client,
                qs_project_code=qs_project_code,
                qs_testrun_id=qs_testrun_id,
                qs_complete_run=qs_complete_run,
            ),
            name="qase-pytest",
        )
