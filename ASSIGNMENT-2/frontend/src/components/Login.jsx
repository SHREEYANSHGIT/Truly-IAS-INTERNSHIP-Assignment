/**
 * Login/Register component.
 * Shows a stunning glassmorphism form to login or register with email and password.
 */
import { useState } from "react";
import { login, register } from "../api/client";

export default function Login({ onAuthSuccess }) {
    const [mode, setMode] = useState("login"); // "login" or "register"
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!email || !password) {
            setError("Please enter both email and password.");
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const authFn = mode === "login" ? login : register;
            await authFn(email, password);
            onAuthSuccess();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const switchMode = () => {
        setMode(mode === "login" ? "register" : "login");
        setError(null);
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <div className="login-logo">📅</div>
                    <h1>Scheduling Assistant</h1>
                    <p>
                        {mode === "login"
                            ? "Welcome back! Sign in to continue."
                            : "Create an account to get started."}
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label htmlFor="email">
                            <span>✉️</span> Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@example.com"
                            autoComplete="email"
                            disabled={loading}
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">
                            <span>🔒</span> Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="At least 6 characters"
                            autoComplete={mode === "login" ? "current-password" : "new-password"}
                            disabled={loading}
                        />
                    </div>

                    {error && <div className="login-error">{error}</div>}

                    <button type="submit" className="login-btn" disabled={loading}>
                        {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
                    </button>
                </form>

                <div className="login-switch">
                    {mode === "login" ? (
                        <span>
                            Don't have an account?{" "}
                            <button onClick={switchMode} className="link-btn">
                                Register
                            </button>
                        </span>
                    ) : (
                        <span>
                            Already have an account?{" "}
                            <button onClick={switchMode} className="link-btn">
                                Sign In
                            </button>
                        </span>
                    )}
                </div>

                <div className="login-footer">
                    <div className="login-footer-badges">
                        <span className="footer-badge">LangGraph</span>
                        <span className="footer-badge">Groq</span>
                        <span className="footer-badge">Gemini</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
