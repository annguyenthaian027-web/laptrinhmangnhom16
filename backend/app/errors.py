"""Lỗi dùng chung, trả về theo định dạng {"error": ..., "code": ...} trong docs/api.md."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
