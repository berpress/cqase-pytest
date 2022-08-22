class Singleton(type):
    """
    Singleton class
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class QaseObject(metaclass=Singleton):
    def __init__(self, project_code=None, client=None):
        self.test_cases = None
        self.test_run_id = None
        self.current_id = None
        self.project_code = project_code
        self.client = client

    def create_test_ids_dict(self, test_cases) -> dict:
        t_cases = {}
        for test_case in test_cases:
            t_cases[test_case] = TestCase(test_case)
        self.test_cases = t_cases


class TestCase:
    def __init__(
        self,
        qase_id: int,
        comment: str = None,
        result: str = "untested",
        stacktrace: str = None,
        description: str = None,
    ):
        self.qase_id = qase_id
        self.result = result
        self.comment = comment
        self.stacktrace = stacktrace
        self.description = description
        self.duration = 0
        self.attachments = []
