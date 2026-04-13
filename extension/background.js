// background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'sync_spec') {
        handleSync('http://localhost:8000/api/specs/sync', request.data, sendResponse);
        return true; // Keep channel open for async response
    }

    if (request.action === 'sync_defect') {
        handleSync('http://localhost:8000/api/defects/sync', [request.data], sendResponse);
        return true;
    }
});

async function handleSync(url, data, sendResponse) {
    try {
        // In production, fetch JWT token from chrome.storage.local
        const { qa_hub_token } = await chrome.storage.local.get(['qa_hub_token']);

        if (!qa_hub_token) {
            console.warn("No QA HUB Token found. Please login via extension popup.");
            sendResponse({ success: false, error: "Not authenticated" });
            return;
        }

        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${qa_hub_token}`
            },
            body: JSON.stringify(data)
        });

        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'Sync failed');

        sendResponse({ success: true, data: result });
    } catch (error) {
        console.error('Sync error:', error);
        sendResponse({ success: false, error: error.message });
    }
}
