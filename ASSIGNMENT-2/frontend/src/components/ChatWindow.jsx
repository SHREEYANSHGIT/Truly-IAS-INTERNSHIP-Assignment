/**
 * ChatWindow component - scrollable message list with enhanced empty state.
 *
 * @param {Object} props
 * @param {Array} props.messages - Array of {role, content, name} objects
 * @param {boolean} props.loading - Whether the assistant is generating a response
 * @param {Function} [props.onSuggestion] - Called when a suggestion chip is clicked
 */
import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

const SUGGESTIONS = [
    "📅 Book tomorrow at 3pm",
    "🔍 Check availability for today",
    "📋 List my bookings",
    "❌ Cancel my last booking",
];

export default function ChatWindow({ messages, loading, onSuggestion }) {
    const bottomRef = useRef(null);

    // Auto-scroll to the bottom when new messages arrive
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    return (
        <div className="chat-window">
            {messages.length === 0 && !loading && (
                <div className="chat-empty">
                    <div className="chat-empty-icon">📅</div>
                    <p className="chat-empty-title">Welcome to the Scheduling Assistant!</p>
                    <p className="chat-empty-subtitle">
                        I can help you book appointments, check availability, list your bookings,
                        and even cancel or reschedule — all through natural conversation.
                    </p>
                    <div className="chat-empty-suggestions">
                        {SUGGESTIONS.map((suggestion) => (
                            <button
                                key={suggestion}
                                className="suggestion-chip"
                                onClick={() => onSuggestion?.(suggestion.replace(/^[^\s]+\s/, ""))}
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            )}
            {messages.map((msg, index) => (
                <MessageBubble
                    key={index}
                    role={msg.role}
                    content={msg.content}
                    name={msg.name}
                />
            ))}
            {loading && (
                <div className="message-bubble message-assistant">
                    <div className="message-avatar">🤖</div>
                    <div className="message-content">
                        <div className="message-typing">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            )}
            <div ref={bottomRef} />
        </div>
    );
}
