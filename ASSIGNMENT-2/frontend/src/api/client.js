/**
 * API client for communicating with the FastAPI backend.
 * Base URL is read from VITE_API_URL env var.
 * Auth token is stored in localStorage and sent as Bearer header.
 */

const BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

const TOKEN_KEY = "scheduling_assistant_token";
const EMAIL_KEY = "scheduling_assistant_email";

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function getEmail() {
    return localStorage.getItem(EMAIL_KEY);
}

export function setAuth(token, email) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(EMAIL_KEY, email);
}

export function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
}

export function isAuthenticated() {
    return !!getToken();
}

/**
 * Build headers with auth token.
 */
function authHeaders(extra = {}) {
    const token = getToken();
    const headers = { "Content-Type": "application/json", ...extra };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

/**
 * Register a new user account.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<Object>} - { token, email }
 */
export async function register(email, password) {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `Registration failed (${response.status}). The backend may be starting up.`);
    }

    setAuth(data.token, data.email);
    return data;
}

/**
 * Login an existing user.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<Object>} - { token, email }
 */
export async function login(email, password) {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `Login failed (${response.status}). The backend may be starting up.`);
    }

    setAuth(data.token, data.email);
    return data;
}

/**
 * Logout the current user.
 */
export async function logout() {
    try {
        await fetch(`${BASE_URL}/api/logout`, {
            method: "POST",
            headers: authHeaders(),
        });
    } catch (e) {
        // Ignore errors on logout
    }
    clearAuth();
}

// ---------------------------------------------------------------------------
// Chat API (authenticated)
// ---------------------------------------------------------------------------

/**
 * Send a chat message to the backend.
 * @param {string} threadId - Conversation thread ID
 * @param {string} message - User message
 * @param {string|null} webhookUrl - Optional user-provided webhook URL
 * @returns {Promise<Object>} - { thread_id, reply, pending_booking }
 */
export async function sendMessage(threadId, message, webhookUrl) {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/chat`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({
                thread_id: threadId,
                message: message,
                webhook_url: webhookUrl || null,
            }),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    if (response.status === 401) {
        clearAuth();
        throw new Error("Session expired. Please login again.");
    }

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Chat request failed (${response.status}). The backend may be starting up.`);
    }

    return response.json().catch(() => ({}));
}

/**
 * Retrieve conversation history for a thread.
 * @param {string} threadId - Conversation thread ID
 * @returns {Promise<Object>} - { thread_id, messages }
 */
export async function getHistory(threadId) {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/history/${threadId}`, {
            headers: authHeaders(),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    if (response.status === 401) {
        clearAuth();
        throw new Error("Session expired. Please login again.");
    }

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `History request failed (${response.status}). The backend may be starting up.`);
    }

    return response.json().catch(() => ({ thread_id: threadId, messages: [] }));
}

/**
 * Create a new conversation thread.
 * @returns {Promise<Object>} - { thread_id }
 */
export async function createThread() {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/thread`, {
            method: "POST",
            headers: authHeaders(),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    if (response.status === 401) {
        clearAuth();
        throw new Error("Session expired. Please login again.");
    }

    if (!response.ok) {
        throw new Error(`Thread creation failed (${response.status}). The backend may be starting up.`);
    }

    return response.json().catch(() => ({ thread_id: crypto.randomUUID() }));
}

/**
 * List all conversation threads for the authenticated user.
 * @returns {Promise<Object>} - { email, threads }
 */
export async function getUserThreads() {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/threads`, {
            headers: authHeaders(),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    if (response.status === 401) {
        clearAuth();
        throw new Error("Session expired. Please login again.");
    }

    if (!response.ok) {
        throw new Error(`Failed to list threads (${response.status}). The backend may be starting up.`);
    }

    return response.json().catch(() => ({ email: "", threads: [] }));
}

/**
 * Test a webhook URL by sending a test payload.
 * @param {string} webhookUrl - The webhook URL to test
 * @returns {Promise<Object>} - { success, message }
 */
export async function testWebhook(webhookUrl) {
    let response;
    try {
        response = await fetch(`${BASE_URL}/api/test-webhook`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({ webhook_url: webhookUrl }),
        });
    } catch (e) {
        throw new Error("Cannot reach the server. The backend may be starting up. Please wait a moment and try again.");
    }

    if (response.status === 401) {
        clearAuth();
        throw new Error("Session expired. Please login again.");
    }

    if (!response.ok) {
        throw new Error(`Webhook test failed (${response.status}). The backend may be starting up.`);
    }

    return response.json().catch(() => ({ success: false, message: "Empty response from server." }));
}
