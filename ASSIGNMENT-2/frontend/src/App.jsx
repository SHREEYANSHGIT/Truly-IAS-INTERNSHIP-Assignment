/**
 * App component - top-level layout.
 * Manages authentication state, thread_id state, webhook URL state, and message list.
 * Shows the Login screen when the user is not authenticated.
 */
import { useEffect, useState, useCallback } from "react";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import WebhookInput from "./components/WebhookInput";
import Login from "./components/Login";
import {
    sendMessage,
    getHistory,
    createThread,
    getUserThreads,
    isAuthenticated,
    getEmail,
    logout,
} from "./api/client";

export default function App() {
    const [authed, setAuthed] = useState(isAuthenticated());
    const [userEmail, setUserEmail] = useState(getEmail());
    const [threadId, setThreadId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [webhookUrl, setWebhookUrl] = useState("");
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [threads, setThreads] = useState([]);
    const [threadPreviews, setThreadPreviews] = useState({});
    const [loadingThread, setLoadingThread] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false);

    // Load all user threads from the backend
    const loadThreads = useCallback(async () => {
        try {
            const data = await getUserThreads();
            const threadList = data.threads || [];
            setThreads(threadList);

            // Load a preview (first user message) for each thread
            const previews = {};
            for (const tid of threadList) {
                try {
                    const hist = await getHistory(tid);
                    const firstUserMsg = (hist.messages || []).find(
                        (m) => m.role === "user"
                    );
                    previews[tid] = firstUserMsg
                        ? firstUserMsg.content.slice(0, 50)
                        : "New conversation";
                } catch {
                    previews[tid] = "Conversation";
                }
            }
            setThreadPreviews(previews);
        } catch (err) {
            // Silently fail — threads sidebar is non-critical
            console.error("Failed to load threads:", err);
        }
    }, []);

    // Initialize thread when authenticated — reuse from localStorage or create new
    useEffect(() => {
        if (!authed) return;

        const storedWebhook = localStorage.getItem("webhook_url");
        if (storedWebhook) setWebhookUrl(storedWebhook);

        loadThreads();

        const stored = localStorage.getItem("thread_id");
        if (stored) {
            setThreadId(stored);
            getHistory(stored)
                .then((data) => {
                    if (data.messages && data.messages.length > 0) {
                        setMessages(data.messages);
                    }
                })
                .catch(() => {
                    initNewThread();
                });
        } else {
            initNewThread();
        }
    }, [authed, loadThreads]);

    const initNewThread = useCallback(async () => {
        try {
            const data = await createThread();
            setThreadId(data.thread_id);
            localStorage.setItem("thread_id", data.thread_id);
        } catch (err) {
            setError(`Failed to create conversation thread: ${err.message}`);
        }
    }, []);

    const handleWebhookChange = (value) => {
        setWebhookUrl(value);
        localStorage.setItem("webhook_url", value);
    };

    const handleSend = async (text) => {
        if (!threadId || loading) return;

        const userMsg = { role: "user", content: text };
        setMessages((prev) => [...prev, userMsg]);
        setLoading(true);
        setError(null);

        try {
            const response = await sendMessage(threadId, text, webhookUrl);
            const assistantMsg = {
                role: "assistant",
                content: response.reply,
                name: response.pending_booking ? "booking" : "triage",
            };
            setMessages((prev) => [...prev, assistantMsg]);
            // Refresh thread previews so the sidebar shows the latest message
            loadThreads();
        } catch (err) {
            if (err.message.includes("Session expired")) {
                handleLogout();
                return;
            }
            setError(`Failed to send message: ${err.message}`);
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: `⚠️ Error: ${err.message}. Please try again.`,
                    name: "triage",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = () => {
        setMessages([]);
        localStorage.removeItem("thread_id");
        initNewThread().then(() => loadThreads());
    };

    const handleSelectThread = async (tid) => {
        if (tid === threadId || loadingThread) return;
        setSidebarOpen(false);
        setLoadingThread(true);
        setError(null);
        try {
            const data = await getHistory(tid);
            setThreadId(tid);
            setMessages(data.messages || []);
            localStorage.setItem("thread_id", tid);
        } catch (err) {
            if (err.message.includes("Session expired")) {
                handleLogout();
                return;
            }
            setError(`Failed to load conversation: ${err.message}`);
        } finally {
            setLoadingThread(false);
        }
    };

    const handleLogout = async () => {
        await logout();
        setAuthed(false);
        setUserEmail(null);
        setMessages([]);
        setThreadId(null);
        localStorage.removeItem("thread_id");
    };

    const handleAuthSuccess = () => {
        setAuthed(true);
        setUserEmail(getEmail());
    };

    // Show login screen if not authenticated
    if (!authed) {
        return <Login onAuthSuccess={handleAuthSuccess} />;
    }

    return (
        <div className="app">
            <header className="app-header">
                <button
                    className="sidebar-toggle"
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                    title="Toggle sidebar"
                    aria-label="Toggle sidebar"
                >
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
                <h1>📅 Scheduling Assistant</h1>
                <div className="header-actions">
                    {userEmail && (
                        <span className="user-email" title={userEmail}>
                            {userEmail}
                        </span>
                    )}
                    <button className="new-chat-btn" onClick={handleNewChat} title="Start a new conversation">
                        ✨ <span className="btn-label">New Chat</span>
                    </button>
                    <button className="logout-btn" onClick={handleLogout} title="Logout">
                        Logout
                    </button>
                </div>
            </header>

            <div className="app-body">
                {sidebarOpen && (
                    <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
                )}
                <aside className={`app-sidebar ${sidebarOpen ? "open" : ""}`}>
                    <WebhookInput
                        webhookUrl={webhookUrl}
                        onWebhookChange={handleWebhookChange}
                    />
                    <div className="chat-history">
                        <h3>💬 Chat History</h3>
                        {threads.length === 0 && (
                            <p className="no-threads">No previous conversations</p>
                        )}
                        <ul className="thread-list">
                            {threads.map((tid) => (
                                <li key={tid}>
                                    <button
                                        className={`thread-item ${tid === threadId ? "active" : ""}`}
                                        onClick={() => handleSelectThread(tid)}
                                        disabled={loadingThread}
                                        title={threadPreviews[tid] || "Conversation"}
                                    >
                                        <span className="thread-preview">
                                            {threadPreviews[tid] || "Conversation"}
                                        </span>
                                        <span className="thread-id-short">
                                            {tid.slice(0, 8)}…
                                        </span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="sidebar-info">
                        <h3>How it works</h3>
                        <ul>
                            <li><strong>Triage Agent</strong> (Groq) routes your message</li>
                            <li><strong>Booking Specialist</strong> (Gemini + Groq fallback) handles bookings</li>
                            <li>Dates like "tomorrow" are resolved automatically</li>
                            <li>Bookings are saved to your account ({userEmail})</li>
                            <li>Click a chat above to resume it</li>
                        </ul>
                    </div>
                </aside>

                <main className="app-chat">
                    {loadingThread && (
                        <div className="loading-overlay">
                            <div className="loading-spinner"></div>
                        </div>
                    )}
                    <ChatWindow messages={messages} loading={loading} onSuggestion={handleSend} />
                    <ChatInput
                        value={inputValue}
                        onChange={setInputValue}
                        onSend={handleSend}
                        disabled={loading || !threadId}
                    />
                </main>
            </div>

            {error && <div className="app-error">{error}</div>}
        </div>
    );
}
