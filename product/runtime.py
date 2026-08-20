from core.config import settings
from product.identity import IdentityStore
from product.personal_library import PersonalLibraryStore


def identity_store() -> IdentityStore:
    return IdentityStore(settings.PRODUCT_DB_PATH, settings.AUTH_TOKEN_TTL_HOURS)


def personal_library_store() -> PersonalLibraryStore:
    return PersonalLibraryStore(settings.PRODUCT_DB_PATH, settings.PERSONAL_LIBRARY_FILES_DIR)
