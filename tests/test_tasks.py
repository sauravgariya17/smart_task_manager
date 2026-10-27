
def create_account_and_get_token(client, email):
    registration = client.post(
        "/auth/register",
        json={
            "name": "Task Tester",
            "email": email,
            "password": "Test-Password-123!",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "Test-Password-123!",
        },
    )
    assert login.status_code == 200

    return login.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_tasks(client):
    token = create_account_and_get_token(
        client, "owner@example.com"
    )
    headers = auth_headers(token)

    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Learn Pytest",
            "description": "Write API tests",
            "priority": "high",
        },
    )

    assert created.status_code == 201
    assert created.json()["title"] == "Learn Pytest"

    listed = client.get("/tasks", headers=headers)

    assert listed.status_code == 200
    data = listed.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Learn Pytest"


def test_update_and_delete_task(client):
    token = create_account_and_get_token(
        client, "crud@example.com"
    )
    headers = auth_headers(token)

    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Temporary task", "priority": "medium"},
    )
    task_id = created.json()["id"]

    updated = client.patch(
        f"/tasks/{task_id}",
        headers=headers,
        json={"is_completed": True},
    )

    assert updated.status_code == 200
    assert updated.json()["is_completed"] is True
    assert updated.json()["title"] == "Temporary task"

    deleted = client.delete(
        f"/tasks/{task_id}",
        headers=headers,
    )

    assert deleted.status_code == 204


def test_user_cannot_access_another_users_task(client):
    first_token = create_account_and_get_token(
        client, "first@example.com"
    )
    second_token = create_account_and_get_token(
        client, "second@example.com"
    )

    created = client.post(
        "/tasks",
        headers=auth_headers(first_token),
        json={
            "title": "Private task",
            "priority": "high",
        },
    )
    task_id = created.json()["id"]

    second_headers = auth_headers(second_token)

    # The second user must not see the first user's task.
    listing = client.get("/tasks", headers=second_headers)
    assert listing.status_code == 200
    assert listing.json()["items"] == []

    # The second user must not update or delete it.
    update = client.patch(
        f"/tasks/{task_id}",
        headers=second_headers,
        json={"title": "Unauthorized change"},
    )
    assert update.status_code == 404

    delete = client.delete(
        f"/tasks/{task_id}",
        headers=second_headers,
    )
    assert delete.status_code == 404

    # The original owner still has the unchanged task.
    owner_list = client.get(
        "/tasks",
        headers=auth_headers(first_token),
    )
    assert owner_list.json()["items"][0]["title"] == "Private task"


def test_task_filters_pagination_and_stats(client):
    token = create_account_and_get_token(
        client, "filters@example.com"
    )
    headers = auth_headers(token)

    tasks = [
        {"title": "FastAPI basics", "priority": "high"},
        {"title": "Python practice", "priority": "low"},
        {"title": "FastAPI testing", "priority": "high"},
    ]

    for task in tasks:
        response = client.post(
            "/tasks",
            headers=headers,
            json=task,
        )
        assert response.status_code == 201

    # Complete one of the high-priority tasks.
    task_list = client.get("/tasks", headers=headers).json()
    first_task_id = task_list["items"][0]["id"]

    updated = client.patch(
        f"/tasks/{first_task_id}",
        headers=headers,
        json={"is_completed": True},
    )
    assert updated.status_code == 200

    filtered = client.get(
        "/tasks",
        headers=headers,
        params={
            "priority": "high",
            "search": "fastapi",
            "limit": 1,
            "offset": 0,
        },
    )

    assert filtered.status_code == 200
    result = filtered.json()
    assert result["total"] == 2
    assert len(result["items"]) == 1
    assert result["has_more"] is True

    stats = client.get("/tasks/stats", headers=headers)

    assert stats.status_code == 200
    stats_data = stats.json()
    assert stats_data["total_tasks"] == 3
    assert stats_data["completed_tasks"] == 1
    assert stats_data["pending_tasks"] == 2
    assert stats_data["high_priority_tasks"] == 2
