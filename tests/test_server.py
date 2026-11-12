import json
from unittest import mock

from sure_mcp_server.server import create_tag, delete_tag, merge_categories

PER_PAGE = 100


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status_code = status
        self.text = json.dumps(payload)
        self.headers = {"content-type": "application/json"}

    def json(self):
        return json.loads(self.text)


class FakeClient:
    def __init__(self):
        self.get_calls = []
        self.patch_calls = []
        self.post_calls = []
        self.delete_calls = []
        self._total = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, path, params=None):
        self.get_calls.append((path, params or {}))
        if path == "/api/v1/transactions":
            remaining = self._total - len(self.patch_calls)
            page_count = min(remaining, PER_PAGE)
            return FakeResponse(
                {"transactions": [{"id": f"txn-{i}"} for i in range(page_count)]}
            )
        if path == "/api/v1/tags":
            return FakeResponse([])
        return FakeResponse({})

    def patch(self, path, json=None):
        self.patch_calls.append((path, json))
        return FakeResponse({"id": path.rsplit("/", 1)[-1]})

    def post(self, path, json=None):
        self.post_calls.append((path, json))
        return FakeResponse({"id": "tag-1", "name": json["tag"]["name"]})

    def delete(self, path):
        self.delete_calls.append(path)
        return FakeResponse({"message": "Tag deleted successfully"})


@mock.patch("sure_mcp_server.server.get_client")
def test_merge_categories_moves_more_than_one_page(get_client):
    client = FakeClient()
    client._total = 230
    get_client.return_value = client

    result = json.loads(merge_categories("cat-from", "cat-into"))

    assert result["message"] == "Moved 230 transactions"
    assert len(client.patch_calls) == 230

    txn_gets = [params["page"] for path, params in client.get_calls if path == "/api/v1/transactions"]
    assert txn_gets == [1, 1, 1]


@mock.patch("sure_mcp_server.server.get_client")
def test_merge_categories_stops_when_page_empties(get_client):
    client = FakeClient()
    client._total = 105
    get_client.return_value = client

    result = json.loads(merge_categories("cat-from", "cat-into"))

    assert result["message"] == "Moved 105 transactions"
    assert len(client.patch_calls) == 105


@mock.patch("sure_mcp_server.server.get_client")
def test_create_and_delete_tag_round_trip(get_client):
    client = FakeClient()
    get_client.return_value = client

    created = json.loads(create_tag("Test Tag"))
    assert created["id"] == "tag-1"
    assert client.post_calls == [("/api/v1/tags", {"tag": {"name": "Test Tag"}})]

    deleted = json.loads(delete_tag("tag-1"))
    assert deleted["message"] == "Tag deleted successfully"
    assert client.delete_calls == ["/api/v1/tags/tag-1"]