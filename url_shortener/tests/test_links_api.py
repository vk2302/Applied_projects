def test_create_short_link_success(client):
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/page"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://example.com/page"
    assert "short_code" in data
    assert "short_url" in data
    assert data["click_count"] == 0
    assert data["owner_id"] is None


def test_create_short_link_with_custom_alias(client):
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/blog",
            "custom_alias": "my-blog",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "my-blog"
    assert data["is_custom"] is True


def test_create_short_link_duplicate_custom_alias(client):
    client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/blog",
            "custom_alias": "my-blog",
        },
    )

    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/other",
            "custom_alias": "my-blog",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "custom_alias is already taken"


def test_create_short_link_invalid_url(client):
    response = client.post(
        "/links/shorten",
        json={"original_url": "not-a-valid-url"},
    )

    assert response.status_code == 422


def test_create_owned_link_with_auth(client, auth_headers):
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/private",
            "custom_alias": "owned-link",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["owner_id"] == 1


def test_get_link_stats(client):
    create_response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/page"},
    )
    short_code = create_response.json()["short_code"]

    response = client.get(f"/links/{short_code}/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["click_count"] == 0
    assert data["last_accessed_at"] is None


def test_redirect_increments_click_count(client):
    create_response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/page"},
    )
    short_code = create_response.json()["short_code"]

    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "https://example.com/page"

    stats_response = client.get(f"/links/{short_code}/stats")
    stats_data = stats_response.json()

    assert stats_data["click_count"] == 1
    assert stats_data["last_accessed_at"] is not None


def test_update_owned_link_success(client, auth_headers):
    create_response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/old",
            "custom_alias": "my-owned-link",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    response = client.put(
        "/links/my-owned-link",
        json={"original_url": "https://example.com/new"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "my-owned-link"
    assert data["original_url"] == "https://example.com/new"


def test_update_link_without_auth_forbidden(client):
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/old", "custom_alias": "public-link"},
    )

    response = client.put(
        "/links/public-link",
        json={"original_url": "https://example.com/new"},
    )

    assert response.status_code == 401


def test_delete_owned_link_success(client, auth_headers):
    create_response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/old",
            "custom_alias": "to-delete",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    delete_response = client.delete(
        "/links/to-delete",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200

    stats_response = client.get("/links/to-delete/stats")
    assert stats_response.status_code == 404

def test_create_project_success(client, auth_headers):
    response = client.post(
        "/projects",
        json={"name": "marketing"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "marketing"


def test_list_projects(client, auth_headers):
    client.post(
        "/projects",
        json={"name": "marketing"},
        headers=auth_headers,
    )

    response = client.get(
        "/projects",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "marketing"
