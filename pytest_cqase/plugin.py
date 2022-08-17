import pytest
from cqase.client import QaseClient

# start wright plugin
from pytest_cqase.singltone_like import QaseObject


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

    QASE_MARKER = 'qase'
    # qase_object = QaseObject()
    test_run_id = None
    COMMENT = "RUN FROM AUTOMATION TESTS"

    def get_qase_ids(self, items):
        """
        взять список ids из декоратора ids
        """
        testcase_ids = []
        for item in items:
            marker = item.get_closest_marker(self.QASE_MARKER)
            if marker:
                ids = [id_ for id_ in marker.kwargs.get("ids")]
                [testcase_ids.append(id_) for id_ in ids]
        return testcase_ids

    def create_test_run(self, qase_ids: list) -> int:
        """
        создать тест ран
        """
        body = {"title": "test run", "cases": qase_ids}
        res = self.client.runs.create(code="TP", body=body)
        return res.body.get("result").get("id")

    def create_qase_results_object(self, testcase_ids):
        self.qase_object.create_test_ids_dict(testcase_ids)

    def add_test_result(self):
        pass

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        qase_ids: list = self.get_qase_ids(items)
        self.create_qase_results_object(qase_ids)
        test_run_id = self.create_test_run(qase_ids)
        QaseObject().test_run_id = test_run_id
        pass

    def get_qase_id_from_report(self, item):
        # возможно несколько тест кейсов
        marks = item.own_markers
        qase_mark = list(mark for mark in marks if mark.name == 'qase')
        if len(qase_mark) > 0:
            return qase_mark[0].kwargs.get('ids')[0]
        return None

    results = {}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        # docstrings
        test_fn = item.obj
        if report.when != 'teardown':
            docstring = getattr(test_fn, '__doc__')
            qase_id = self.get_qase_id_from_report(item)
            # qase_object.test_cases[qase_id].stacktrace = "".join([docstring, report.caplog])
            result = report.outcome
            duration = report.duration
            if docstring:
                docstring = "".join([docstring, report.caplog])
            if report.outcome == 'failed':
                if qase_id:
                    stacktrace = report.longreprtext
                    self.qase_object.test_cases[qase_id].result = result
                    self.qase_object.test_cases[qase_id].stacktrace = stacktrace
                    self.qase_object.test_cases[qase_id].description = docstring
                    self.qase_object.test_cases[qase_id].duration = duration
                    return
            if report.outcome == 'skipped' and report.longrepr:
                if qase_id:
                    self.qase_object.test_cases[qase_id].result = result
                    self.qase_object.test_cases[qase_id].comment = docstring
                    self.qase_object.test_cases[qase_id].duration = duration
                    return
            if report.outcome == 'skipped':
                if qase_id:
                    self.qase_object.test_cases[qase_id].result = result
                    self.qase_object.test_cases[qase_id].comment = docstring
                    self.qase_object.test_cases[qase_id].duration = duration
                    return
            if report.outcome == 'passed':
                if qase_id:
                    if self.qase_object.test_cases[qase_id].result != 'failed':
                        self.qase_object.test_cases[qase_id].result = result
                    self.qase_object.test_cases[qase_id].description = docstring
                    self.qase_object.test_cases[qase_id].duration = duration
                    return

    def _create_bulk_body(self):
        results_send = []
        try:
            for key, value in self.qase_object.test_cases.items():
                if value.result != 'untested':
                    results_send.append(
                        {"case_id": value.qase_id, "status": value.result,
                         "comment": self.COMMENT, 'stacktrace': value.stacktrace,
                         "time_ms": int(value.duration * 1000),
                         "case": {
                             "description": value.description
                         }})
            return {'results': results_send}
        except AttributeError:
            pass
        pass

    def pytest_sessionfinish(self, session, exitstatus):
        body = self._create_bulk_body()
        res_bulk = self.client.results.bulk(code="TP", uuid=QaseObject().test_run_id,
                                       body=body)
        assert res_bulk