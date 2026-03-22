def test_search_by_original_url(client):
    client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/blog",
            "custom_alias": "my-blog",
        },
    )

    response = client.get(
        "/links/search",
        params={"original_url": "https://example.com/blog"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["short_code"] == "my-blog"


def test_expired_history_contains_deleted_link(client, auth_headers):
    client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/private",
            "custom_alias": "history-link",
        },
        headers=auth_headers,
    )

    delete_response = client.delete(
        "/links/history-link",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200

    history_response = client.get(
        "/links/expired-history",
        headers=auth_headers,
    )

    assert history_response.status_code == 200
    data = history_response.json()
    assert len(data) == 1
    assert data[0]["short_code"] == "history-link"
    assert data[0]["archive_reason"] == "manual_delete"
