class RequestError(Exception):
    def __init__(self, status: int, *args):
        super().__init__(*args)

        self.status = status


class RateLimit(Exception):
    def __init__(self, timeout: float):
        super().__init__()
        self.timeout = timeout