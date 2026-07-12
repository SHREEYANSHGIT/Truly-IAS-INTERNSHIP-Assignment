/**
 * ChatInput component - modern text input with circular send button.
 *
 * @param {Object} props
 * @param {string} props.value - Current input value
 * @param {Function} props.onChange - Called when input changes
 * @param {Function} props.onSend - Called when user sends (Enter or button)
 * @param {boolean} props.disabled - Whether input is disabled (during loading)
 */
import { useState, useRef, useEffect } from "react";

export default function ChatInput({ value, onChange, onSend, disabled }) {
    const [localValue, setLocalValue] = useState(value || "");
    const textareaRef = useRef(null);

    // Sync external value
    useEffect(() => {
        if (value !== undefined && value !== localValue) {
            setLocalValue(value);
        }
    }, [value]);

    // Auto-resize textarea
    useEffect(() => {
        const el = textareaRef.current;
        if (el) {
            el.style.height = "auto";
            el.style.height = Math.min(el.scrollHeight, 120) + "px";
        }
    }, [localValue]);

    const handleChange = (e) => {
        setLocalValue(e.target.value);
        onChange?.(e.target.value);
    };

    const handleSend = () => {
        if (localValue.trim() && !disabled) {
            onSend?.(localValue.trim());
            setLocalValue("");
            onChange?.("");
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-input">
            <div className="chat-input-inner">
                <textarea
                    ref={textareaRef}
                    className="chat-textarea"
                    placeholder="Type your message... (e.g. 'Book tomorrow at 3pm')"
                    value={localValue}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    rows={1}
                />
                <button
                    className="chat-send-btn"
                    onClick={handleSend}
                    disabled={disabled || !localValue.trim()}
                    title="Send message"
                >
                    <svg
                        className="chat-send-icon"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    );
}
