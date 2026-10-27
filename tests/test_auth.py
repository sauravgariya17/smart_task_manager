
def register_user(client, email="testuser@example.com"):
    return client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "Test-Password-123!",
        },
    )


def login_user(client, email="testuser@example.com"):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "Test-Password-123!",
        },
    )


def test_register_user(client):
    response = register_user(client)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert "password" not in data
    assert "hashed_password" not in data


def test_duplicate_registration(client):
    register_user(client)

    response = register_user(client)

    assert response.status_code == 409


def test_login_success(client):
    register_user(client)

    response = login_user(client)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_wrong_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "Wrong-Password-123!",
        },
    )

    assert response.status_code == 401


def test_protected_profile_requires_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_protected_profile_with_token(client):
    register_user(client)
    login_response = login_user(client)
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "testuser@example.com"
    assert "hashed_password" not in response.json()
