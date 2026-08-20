from app.api import app


def test_memory_management_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert "/memory/maintenance/expire" in paths
    assert "/memory/{conversation_id}" in paths
    assert "/memory/{conversation_id}/conflicts" in paths
    assert "/memory/{conversation_id}/{memory_id}" in paths
