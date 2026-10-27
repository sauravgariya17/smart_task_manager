
const API_BASE = "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);

let token = sessionStorage.getItem("access_token");
let authMode = "login";
let editingTaskId = null;
let currentOffset = 0;
const pageSize = 5;
let currentTotal = 0;
let searchTimer;

function showMessage(id, message, success = false) {
    const element = $(id);
    element.textContent = message;
    element.classList.toggle("success", success);
}

async function apiRequest(path, options = {}) {
    const headers = { ...(options.headers || {}) };

    if (options.body) {
        headers["Content-Type"] = "application/json";
    }

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    let response;

    try {
        response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers,
        });
    } catch {
        throw new Error(
            "Cannot reach the backend. Check that FastAPI is running."
        );
    }

    if (response.status === 204) {
        return null;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
            ? detail.map((item) => item.msg).join(", ")
            : detail || "The request failed.";

        throw new Error(message);
    }

    return data;
}

function setAuthMode(mode) {
    authMode = mode;
    const registering = mode === "register";

    $("login-tab").classList.toggle("active", !registering);
    $("register-tab").classList.toggle("active", registering);
    $("name-group").classList.toggle("hidden", !registering);
    $("name").required = registering;

    $("auth-title").textContent = registering
        ? "Create your account"
        : "Welcome back";

    $("auth-subtitle").textContent = registering
        ? "Start organizing your tasks today."
        : "Enter your details to continue.";

    $("auth-submit").textContent = registering
        ? "Create account"
        : "Log in";

    $("password").autocomplete = registering
        ? "new-password"
        : "current-password";

    showMessage("auth-message", "");
}

function showDashboard(isLoggedIn) {
    $("auth-section").classList.toggle("hidden", isLoggedIn);
    $("dashboard-section").classList.toggle("hidden", !isLoggedIn);
}

$("login-tab").addEventListener("click", () => setAuthMode("login"));
$("register-tab").addEventListener("click", () => setAuthMode("register"));

$("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = $("auth-submit");
    submitButton.disabled = true;
    showMessage("auth-message", "");

    try {
        const email = $("email").value.trim();
        const password = $("password").value;

        if (authMode === "register") {
            const name = $("name").value.trim();

            await apiRequest("/auth/register", {
                method: "POST",
                body: JSON.stringify({ name, email, password }),
            });

            setAuthMode("login");
            $("email").value = email;
            $("password").value = password;

            showMessage(
                "auth-message",
                "Account created. You can now log in.",
                true
            );
            return;
        }

        const result = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });

        token = result.access_token;
        sessionStorage.setItem("access_token", token);

        await apiRequest("/auth/me");
        showDashboard(true);
        currentOffset = 0;
        await refreshDashboard();
    } catch (error) {
        token = null;
        sessionStorage.removeItem("access_token");
        showMessage("auth-message", error.message);
    } finally {
        submitButton.disabled = false;
    }
});

$("logout-btn").addEventListener("click", () => {
    token = null;
    sessionStorage.removeItem("access_token");
    editingTaskId = null;
    $("task-form").reset();
    resetEditMode();
    showDashboard(false);
    setAuthMode("login");
    showMessage("auth-message", "You have logged out.", true);
});

function getFilters() {
    const params = new URLSearchParams();
    const search = $("search-input").value.trim();
    const status = $("status-filter").value;
    const priority = $("priority-filter").value;
    const [sortBy, order] = $("sort-filter").value.split(":");

    if (search) params.set("search", search);
    if (status !== "") params.set("is_completed", status);
    if (priority) params.set("priority", priority);

    params.set("sort_by", sortBy);
    params.set("order", order);
    params.set("limit", String(pageSize));
    params.set("offset", String(currentOffset));

    return params;
}

async function loadTasks() {
    $("list-message").textContent = "Loading tasks...";
    $("task-list").replaceChildren();

    try {
        const params = getFilters();

        // The backend returns an object with items, total, limit,
        // offset and has_more, not a plain array.
        const result = await apiRequest(`/tasks?${params.toString()}`);

        currentTotal = result.total;
        $("page-info").textContent = result.total === 0
            ? "No tasks"
            : `Showing ${result.offset + 1}–${
                result.offset + result.items.length
              } of ${result.total}`;

        $("prev-btn").disabled = currentOffset === 0;
        $("next-btn").disabled = !result.has_more;

        $("list-message").textContent = result.items.length
            ? ""
            : "No tasks match these filters. Try creating a task.";

        result.items.forEach(renderTask);
    } catch (error) {
        $("list-message").textContent = error.message;

        if (
            error.message.includes("token") ||
            error.message.includes("authentication")
        ) {
            token = null;
            sessionStorage.removeItem("access_token");
            showDashboard(false);
        }
    }
}

function renderTask(task) {
    const card = document.createElement("article");
    card.className = "task-card";

    const top = document.createElement("div");
    top.className = "task-top";

    const title = document.createElement("h3");
    title.className = "task-title";
    if (task.is_completed) title.classList.add("completed");
    title.textContent = task.title;

    const priority = document.createElement("span");
    priority.className = `priority ${task.priority}`;
    priority.textContent = task.priority;

    top.append(title, priority);
    card.append(top);

    if (task.description) {
        const description = document.createElement("p");
        description.className = "task-description";
        description.textContent = task.description;
        card.append(description);
    }

    const actions = document.createElement("div");
    actions.className = "task-actions";

    const completeButton = document.createElement("button");
    completeButton.className = "btn secondary";
    completeButton.textContent = task.is_completed
        ? "Mark pending"
        : "Complete";

    completeButton.addEventListener("click", async () => {
        await updateTask(task.id, {
            is_completed: !task.is_completed,
        });
    });

    const editButton = document.createElement("button");
    editButton.className = "btn secondary";
    editButton.textContent = "Edit";

    editButton.addEventListener("click", () => beginEdit(task));

    const deleteButton = document.createElement("button");
    deleteButton.className = "btn secondary";
    deleteButton.textContent = "Delete";

    deleteButton.addEventListener("click", async () => {
        if (!window.confirm(`Delete "${task.title}"?`)) return;

        try {
            await apiRequest(`/tasks/${task.id}`, {
                method: "DELETE",
            });

            showMessage("task-message", "Task deleted.", true);
            await refreshDashboard();
        } catch (error) {
            showMessage("task-message", error.message);
        }
    });

    actions.append(completeButton, editButton, deleteButton);
    card.append(actions);
    $("task-list").append(card);
}

async function updateTask(id, updates) {
    try {
        await apiRequest(`/tasks/${id}`, {
            method: "PATCH",
            body: JSON.stringify(updates),
        });

        showMessage("task-message", "Task updated.", true);
        await refreshDashboard();
    } catch (error) {
        showMessage("task-message", error.message);
    }
}

function beginEdit(task) {
    editingTaskId = task.id;
    $("task-title").value = task.title;
    $("task-description").value = task.description || "";
    $("task-priority").value = task.priority;
    $("task-form-title").textContent = "Edit task";
    $("save-task-btn").textContent = "Save changes";
    $("cancel-edit-btn").classList.remove("hidden");

    $("task-title").focus();
    $("task-form").scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetEditMode() {
    editingTaskId = null;
    $("task-form-title").textContent = "Create a task";
    $("save-task-btn").textContent = "Add task";
    $("cancel-edit-btn").classList.add("hidden");
}

$("cancel-edit-btn").addEventListener("click", () => {
    $("task-form").reset();
    resetEditMode();
    showMessage("task-message", "");
});

$("task-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    const title = $("task-title").value.trim();

    if (!title) {
        showMessage("task-message", "Please enter a task title.");
        return;
    }

    const payload = {
        title,
        description: $("task-description").value.trim() || null,
        priority: $("task-priority").value,
    };

    const button = $("save-task-btn");
    button.disabled = true;

    try {
        if (editingTaskId !== null) {
            await apiRequest(`/tasks/${editingTaskId}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });
            showMessage("task-message", "Task updated successfully.", true);
        } else {
            await apiRequest("/tasks", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            showMessage("task-message", "Task created successfully.", true);
        }

        $("task-form").reset();
        resetEditMode();
        currentOffset = 0;
        await refreshDashboard();
    } catch (error) {
        showMessage("task-message", error.message);
    } finally {
        button.disabled = false;
    }
});

async function loadStats() {
    const stats = await apiRequest("/tasks/stats");

    $("total-stat").textContent = stats.total_tasks;
    $("completed-stat").textContent = stats.completed_tasks;
    $("pending-stat").textContent = stats.pending_tasks;
    $("high-stat").textContent = stats.high_priority_tasks;
}

async function refreshDashboard() {
    try {
        await Promise.all([loadStats(), loadTasks()]);
    } catch (error) {
        showMessage("task-message", error.message);
    }
}

$("refresh-btn").addEventListener("click", refreshDashboard);

["status-filter", "priority-filter", "sort-filter"].forEach((id) => {
    $(id).addEventListener("change", () => {
        currentOffset = 0;
        loadTasks();
    });
});

$("search-input").addEventListener("input", () => {
    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
        currentOffset = 0;
        loadTasks();
    }, 300);
});

$("prev-btn").addEventListener("click", () => {
    currentOffset = Math.max(0, currentOffset - pageSize);
    loadTasks();
});

$("next-btn").addEventListener("click", () => {
    if (currentOffset + pageSize < currentTotal) {
        currentOffset += pageSize;
        loadTasks();
    }
});

async function checkBackend() {
    try {
        await apiRequest("/health");
        $("connection-status").textContent = "API connected";
    } catch {
        $("connection-status").textContent = "API unavailable";
    }
}

async function initialize() {
    await checkBackend();

    if (token) {
        try {
            await apiRequest("/auth/me");
            showDashboard(true);
            await refreshDashboard();
            return;
        } catch {
            token = null;
            sessionStorage.removeItem("access_token");
        }
    }

    showDashboard(false);
}

initialize();
