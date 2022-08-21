import pathlib

import pytest
from cqase.client import QaseClient
from filelock import FileLock

from pytest_cqase.singltone_like import QaseObject


class qase:
    """Class with decorators for pytest"""

    @staticmethod
    def id(*ids):
        """ """
        return pytest.mark.qase(ids=ids)


class MoreThenOneCaseIdException(Exception):
    pass


class ProjectCodeException(Exception):
    pass


class BulkResultSendException(Exception):
    pass


class PyTestQasePlugin:
    def __init__(
        self,
        client: QaseClient,
        qs_project_code: str = None,
        qs_testrun_id: int = None,
        qs_new_run: bool = None,
        qs_complete_run: bool = None,
    ):
        self.client = client
        self.qase_object = QaseObject()
        self.meta_run_file = pathlib.Path("qaseio.runid")
        self.qs_project_code = self._check_project_code(qs_project_code)
        self.qs_testrun_id = qs_testrun_id
        self.qs_new_run = qs_new_run
        self.qs_complete_run = qs_complete_run

    QASE_MARKER = "qase"
    COMMENT = "Pytest Plugin Automation Run"
    TEST_RUN_TITLE = "Automation test run"
    TEST_STATUS = {
        "PASSED": "passed",
        "FAILED": "failed",
        "SKIPPED": "skipped",
        "BLOCKED": "blocked",
    }
    URL_RUN = "https://app.qase.io/run/{}/dashboard/{}"
    BATCH_BULK_COUNT = 2000

    @staticmethod
    def _check_project_code(project_code: str):
        if isinstance(project_code, str):
            return project_code
        raise ProjectCodeException(
            "Check your project code, it should be like 'TP, TEST, PJ'."
        )

    def _get_qase_ids(self, items) -> list:
        """
        get qase ids
        """
        testcase_ids = []
        for item in items:
            marker = item.get_closest_marker(self.QASE_MARKER)
            if marker:
                ids = [id_ for id_ in marker.kwargs.get("ids")]
                [testcase_ids.append(id_) for id_ in ids]
        return testcase_ids

    def _load_run_from_lock(self) -> int:
        """
        Get test id from file
        """
        if self.meta_run_file.exists():
            with open(self.meta_run_file, "r") as lock_file:
                try:
                    test_run_id = int(lock_file.read())
                    return test_run_id
                except ValueError:
                    pass

    def _create_file_lock(self, test_run_id: int):
        with open(self.meta_run_file, "w") as lock_file:
            lock_file.write(str(test_run_id))

    def _create_test_run(self, qase_ids: list) -> int:
        """
        create qase test run
        """
        if self.qs_testrun_id:
            return self.qs_testrun_id
        body = {"title": self.TEST_RUN_TITLE, "cases": qase_ids}
        res = self.client.runs.create(code=self.qs_project_code, body=body)
        return res.body.get("result").get("id")

    def _create_qase_results_object(self, testcase_ids):
        self.qase_object.create_test_ids_dict(testcase_ids)

    def _get_qase_id_from_report(self, item) -> None | int:
        # TODO may be same ids
        marks = item.own_markers
        qase_mark = list(mark for mark in marks if mark.name == self.QASE_MARKER)
        if len(qase_mark) > 0:
            return qase_mark[0].kwargs.get("ids")[0]
        raise MoreThenOneCaseIdException("More than one value added")

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items):
        with FileLock("qaseio.lock"):
            qase_ids: list = self._get_qase_ids(items)
            self._create_qase_results_object(qase_ids)
            test_run_id = self._load_run_from_lock()
            if test_run_id is None:
                test_run_id = self._create_test_run(qase_ids)
                self._create_file_lock(test_run_id)
            QaseObject().test_run_id = test_run_id
            print(
                f"Create new test run: "
                f"{self.URL_RUN.format(f'{self.qs_project_code}', test_run_id)}"
            )

    def _create_bulk_body(self) -> dict:
        results_send = []
        try:
            for key, value in self.qase_object.test_cases.items():
                if value.result != "untested":
                    results_send.append(
                        {
                            "case_id": value.qase_id,
                            "status": value.result,
                            "comment": value.description,
                            "stacktrace": value.stacktrace,
                            "time_ms": int(value.duration * 1000),
                        }
                    )
            return {"results": results_send}
        except AttributeError:
            pass

    def _send_bulk_results(self, body):
        count = 0
        chunks_len = len(body.get("results"))
        while count < chunks_len:
            results = body.get("results")[count : count + self.BATCH_BULK_COUNT]
            count = count + self.BATCH_BULK_COUNT
            response = self.client.results.bulk(
                code=self.qs_project_code,
                uuid=QaseObject().test_run_id,
                body={"results": results},
            )
            if response.status_code != 200:
                raise BulkResultSendException(
                    "Check your project settings in QASE ui and confirm bulk "
                    "results sends."
                )

    def _confirm_run_complete(self):
        if self.qs_complete_run:
            self.client.runs.complete(self.qs_project_code, self.qs_testrun_id)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        test_fn = item.obj
        if report.when != "teardown":
            description = self.COMMENT
            docstring = getattr(test_fn, "__doc__", None)
            qase_id = self._get_qase_id_from_report(item)
            result = report.outcome
            duration = report.duration
            if qase_id:
                if docstring:
                    description = "".join([self.COMMENT, docstring, report.caplog])
                self.qase_object.test_cases[qase_id].description = description
                self.qase_object.test_cases[qase_id].duration = duration
                if report.outcome == self.TEST_STATUS.get("FAILED"):
                    self.qase_object.test_cases[qase_id].result = result
                    stacktrace = report.longreprtext
                    self.qase_object.test_cases[qase_id].stacktrace = stacktrace
                    return
                if (
                    report.outcome == self.TEST_STATUS.get("SKIPPED")
                    and report.longrepr
                ):
                    self.qase_object.test_cases[qase_id].result = result
                    return
                if report.outcome == self.TEST_STATUS.get("SKIPPED"):
                    self.qase_object.test_cases[qase_id].result = result
                    return
                if report.outcome == self.TEST_STATUS.get("PASSED"):
                    if self.qase_object.test_cases[qase_id].result != "failed":
                        self.qase_object.test_cases[qase_id].result = result
                    return

    def pytest_sessionfinish(self):
        body = self._create_bulk_body()
        self._send_bulk_results(body=body)

        if self.meta_run_file.exists():
            self.meta_run_file.unlink()
