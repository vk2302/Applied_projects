def test_register_user_success(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert "id" in data
    assert "created_at" in data


def test_register_user_duplicate_email(client):
    client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "12345678",
        },
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"


def test_login_success(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
