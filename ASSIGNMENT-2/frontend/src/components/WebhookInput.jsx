/**
 * WebhookInput component - lets the user paste their webhook URL
 * (Webhook.site / Pipedream) and test it.
 *
 * @param {Object} props
 * @param {string} props.webhookUrl - Current webhook URL
 * @param {Function} props.onWebhookChange - Called when webhook URL changes
 */
import { useState } from "react";
import { testWebhook } from "../api/client";

export default function WebhookInput({ webhookUrl, onWebhookChange }) {
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState(null);

    const handleTest = async () => {
        if (!webhookUrl.trim()) {
            setTestResult({ success: false, message: "Please enter a webhook URL first." });
            return;
        }

        setTesting(true);
        setTestResult(null);
        try {
            const result = await testWebhook(webhookUrl.trim());
            setTestResult(result);
        } catch (err) {
            setTestResult({ success: false, message: `Error: ${err.message}` });
        } finally {
            setTesting(false);
        }
    };

    return (
        <div className="webhook-input">
            <div className="webhook-header">
                <span className="webhook-label">🔔 Notification Webhook</span>
                <span className="webhook-hint">
                    Paste your Webhook.site or Pipedream URL to receive booking confirmations
                </span>
            </div>
            <div className="webhook-row">
                <input
                    type="url"
                    className="webhook-field"
                    placeholder="https://webhook.site/your-unique-url"
                    value={webhookUrl}
                    onChange={(e) => onWebhookChange?.(e.target.value)}
                />
                <button
                    className="webhook-test-btn"
                    onClick={handleTest}
                    disabled={testing}
                >
                    {testing ? "Testing..." : "Test"}
                </button>
            </div>
            {testResult && (
                <div className={`webhook-result ${testResult.success ? "success" : "error"}`}>
                    {testResult.success ? "✅" : "❌"} {testResult.message}
                </div>
            )}
        </div>
    );
}
