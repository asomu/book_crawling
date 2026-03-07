from __future__ import annotations


class CrawlError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LoginFailedError(CrawlError):
    def __init__(self, message: str = "Yes24 login failed.") -> None:
        super().__init__("login_failed", message)


class AdultVerificationRequiredError(CrawlError):
    def __init__(self, message: str = "Adult verification is required for this book.") -> None:
        super().__init__("adult_verification_required", message)


class SearchNoResultError(CrawlError):
    def __init__(self, message: str = "No matching search result was found.") -> None:
        super().__init__("search_no_result", message)


class DetailPageNotFoundError(CrawlError):
    def __init__(self, message: str = "Detail page or detailed image was not found.") -> None:
        super().__init__("detail_page_not_found", message)


class SelectorChangedError(CrawlError):
    def __init__(self, message: str = "The page structure changed and a selector failed.") -> None:
        super().__init__("selector_changed", message)


class ImageDownloadFailedError(CrawlError):
    def __init__(self, message: str = "Unable to download an image asset.") -> None:
        super().__init__("image_download_failed", message)


class ImageTransformFailedError(CrawlError):
    def __init__(self, message: str = "Unable to transform an image asset.") -> None:
        super().__init__("image_transform_failed", message)


class StorageFailedError(CrawlError):
    def __init__(self, message: str = "Unable to persist a file or record.") -> None:
        super().__init__("storage_failed", message)
