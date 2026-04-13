// content.js - Scrapes Redmine DOM

function scrapeDefect() {
    // Assuming standard Redmine DOM structure for an Issue
    const redmine_id_element = document.querySelector('h2');
    const title_element = document.querySelector('.subject h3');
    const status_element = document.querySelector('.status.attribute .value');
    const priority_element = document.querySelector('.priority.attribute .value'); // Using priority as severity

    // Custom field for 'Model ID' if it exists
    const model_element = document.querySelector('.cf_12.attribute .value'); // Example custom field ID

    if (!redmine_id_element || !title_element || !status_element) return null;

    const text_id = redmine_id_element.innerText.match(/#(\d+)/);
    const redmine_id = text_id ? parseInt(text_id[1]) : 0;

    return {
        redmine_id: redmine_id,
        title: title_element.innerText.trim(),
        status: status_element.innerText.trim().toLowerCase(),
        severity: priority_element ? priority_element.innerText.trim().toLowerCase() : 'normal',
        model_id: model_element ? model_element.innerText.trim() : 'Unknown'
    };
}

function scrapeSpec() {
    // Assuming standard Redmine Wiki page
    const title_element = document.querySelector('.title, h1');
    const content_element = document.querySelector('.wiki.wiki-page');
    // Usually Redmine shows version in history tab or bottom, assume we scrape it or use timestamp
    const version_element = document.querySelector('a[href*="/diff/"]');

    if (!title_element || !content_element) return null;

    let version_number = 1;
    if (version_element) {
        // e.g., "Version 3"
        const match = version_element.innerText.match(/\d+/);
        if (match) version_number = parseInt(match[0]);
    }

    return {
        title: title_element.innerText.trim(),
        language: 'English', // Auto-detect or default
        content: content_element.innerText,
        version_number: version_number
    };
}

// Inject a Sync Button into Redmine UI
function injectSyncButton() {
    const header = document.querySelector('#content h2');
    if (!header) return;

    const btn = document.createElement('button');
    btn.innerText = 'Sync to QA HUB';
    btn.style.marginLeft = '10px';
    btn.style.padding = '4px 8px';
    btn.style.background = '#3498db';
    btn.style.color = 'white';
    btn.style.border = 'none';
    btn.style.borderRadius = '3px';
    btn.style.cursor = 'pointer';

    btn.onclick = () => {
        btn.innerText = 'Syncing...';
        const isDefect = window.location.href.includes('/issues/');
        const isSpec = window.location.href.includes('/wiki/');

        let payload = null;
        let action = '';

        if (isDefect) {
            payload = scrapeDefect();
            action = 'sync_defect';
        } else if (isSpec) {
            payload = scrapeSpec();
            action = 'sync_spec';
        }

        if (payload) {
            chrome.runtime.sendMessage({ action: action, data: payload }, (response) => {
                if (response && response.success) {
                    btn.innerText = 'Synced ✓';
                    btn.style.background = '#2ecc71';
                } else {
                    btn.innerText = 'Sync Failed ✖';
                    btn.style.background = '#e74c3c';
                    console.error("Sync failed:", response?.error);
                }
                setTimeout(() => { btn.innerText = 'Sync to QA HUB'; btn.style.background = '#3498db'; }, 3000);
            });
        } else {
            console.error("Could not scrape data from this page");
            btn.innerText = 'Error Scrape ✖';
            btn.style.background = '#e74c3c';
        }
    };

    header.appendChild(btn);
}

// Initialize
window.addEventListener('load', injectSyncButton);
