/**
 * MessageBubble component - renders a single message with markdown support.
 *
 * @param {Object} props
 * @param {string} props.role - "user" or "assistant"
 * @param {string} props.content - The message text (may contain markdown)
 * @param {string} [props.name] - Agent name (e.g. "triage" or "booking")
 */
import ReactMarkdown from "react-markdown";

export default function MessageBubble({ role, content, name }) {
    const isUser = role === "user";

    return (
        <div className={`message-bubble ${isUser ? "message-user" : "message-assistant"}`}>
            <div className="message-avatar">
                {isUser ? "👤" : "🤖"}
            </div>
            <div className="message-content">
                {!isUser && name && (
                    <div className="message-agent-name">
                        {name === "triage" ? "Triage Agent" : "Booking Specialist"}
                    </div>
                )}
                <div className="message-text">
                    <ReactMarkdown>{content}</ReactMarkdown>
                </div>
            </div>
        </div>
    );
}
