import logging
import pathlib

import pytest
from cqase.client import QaseClient
from filelock import FileLock

# start wright plugin
from pytest_cqase.singltone_like import QaseObject

logger = logging.getLogger("qase")

class qase:
    """Class with decorators for pytest"""

    @staticmethod
    def id(*ids):
        """
        """
        return pytest.mark.qase(ids=ids)


class PyTestQasePlugin:
    def __init__(self, client: QaseClient):
        self.client = client
        self.qase_object = QaseObject()
        self.meta_run_file = pathlib.Path("qaseio.runid")
        self.url = "https://app.qase.io/run/{}/dashboard/{}"

    QASE_MARKER = 'qase'
    test_run_id = None
    COMMENT = "Pytest Plugin Automation Run"
    TEST_STATUS = {
        "PASSED": 'passed',
        "FAILED": 'failed',
        "SKIPPED": 'skipped',
        "BLOCKED": 'blocked',
    }

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

    def load_run_from_lock(self):
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
        body = {"title": "test run", "cases": qase_ids}
        res = self.client.runs.create(code="TP", body=body)
        return res.body.get("result").get("id")

    def create_qase_results_object(self, testcase_ids):
        self.qase_object.create_test_ids_dict(testcase_ids)

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items):
        with FileLock("qaseio.lock"):
            qase_ids: list = self._get_qase_ids(items)
            self.create_qase_results_object(qase_ids)
            test_run_id = self.load_run_from_lock()
            if test_run_id is None:
                test_run_id = self._create_test_run(qase_ids)
                self._create_file_lock(test_run_id)
            QaseObject().test_run_id = test_run_id
            logger.info(f"Create new test run: {self.url.format('TP', test_run_id)}")

    def _get_qase_id_from_report(self, item) -> int:
        # TODO may be same ids
        marks = item.own_markers
        qase_mark = list(mark for mark in marks if mark.name == self.QASE_MARKER)
        if len(qase_mark) > 0:
            return qase_mark[0].kwargs.get('ids')[0]
        return -1

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        test_fn = item.obj
        if report.when != 'teardown':
            description = self.COMMENT
            docstring = getattr(test_fn, '__doc__', None)
            qase_id = self._get_qase_id_from_report(item)
            result = report.outcome
            duration = report.duration
            if qase_id:
                if docstring:
                    description = "".join([self.COMMENT, docstring, report.caplog])
                self.qase_object.test_cases[qase_id].description = description
                self.qase_object.test_cases[qase_id].duration = duration
                if report.outcome == self.TEST_STATUS.get('FAILED'):
                    self.qase_object.test_cases[qase_id].result = result
                    stacktrace = report.longreprtext
                    self.qase_object.test_cases[qase_id].stacktrace = stacktrace
                    return
                if report.outcome == self.TEST_STATUS.get(
                        'SKIPPED') and report.longrepr:
                    self.qase_object.test_cases[qase_id].result = result
                    return
                if report.outcome == self.TEST_STATUS.get('SKIPPED'):
                    self.qase_object.test_cases[qase_id].result = result
                    return
                if report.outcome == self.TEST_STATUS.get('PASSED'):
                    if self.qase_object.test_cases[qase_id].result != 'failed':
                        self.qase_object.test_cases[qase_id].result = result
                    return

    def _create_bulk_body(self):
        results_send = []
        try:
            for key, value in self.qase_object.test_cases.items():
                if value.result != 'untested':
                    results_send.append(
                        {"case_id": value.qase_id, "status": value.result,
                         "comment": value.description,
                         'stacktrace': value.stacktrace,
                         "time_ms": int(value.duration * 1000),
                         })
            return {'results': results_send}
        except AttributeError:
            pass

    def pytest_sessionfinish(self, session, exitstatus):
        body = self._create_bulk_body()
        res_bulk = self.client.results.bulk(code="TP", uuid=QaseObject().test_run_id,
                                            body=body)
        assert res_bulk
