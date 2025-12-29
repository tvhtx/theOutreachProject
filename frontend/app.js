/**
 * Outreach Dashboard - Fully Integrated Frontend
 * Connects to the Python backend and manages all UI interactions
 */

// ========================================
// Configuration & State
// ========================================

const API_BASE = 'http://localhost:5000/api';
const USE_MOCK_DATA = false; // Set to true to disable API calls and use simulation mode

const AppState = {
    contacts: [],
    logs: [],
    drafts: [],
    config: {},
    currentSection: 'dashboard',
    campaignRunning: false,
    sendDelay: { min: 15, max: 45 }, // Delay between emails in seconds
    stats: {
        emailsSent: 0,
        totalContacts: 0,
        pendingDrafts: 0,
        successRate: 0
    }
};

// ========================================
// DOM Elements
// ========================================

const elements = {
    // Navigation
    navItems: document.querySelectorAll('.nav-item'),
    pageTitle: document.getElementById('pageTitle'),
    pageSubtitle: document.getElementById('pageSubtitle'),

    // Sections
    sections: {
        dashboard: document.getElementById('dashboardSection'),
        contacts: document.getElementById('contactsSection'),
        campaigns: document.getElementById('campaignsSection'),
        drafts: document.getElementById('draftsSection'),
        logs: document.getElementById('logsSection'),
        settings: document.getElementById('settingsSection')
    },

    // Stats
    statEmailsSent: document.getElementById('statEmailsSent'),
    statTotalContacts: document.getElementById('statTotalContacts'),
    statPendingDrafts: document.getElementById('statPendingDrafts'),
    statSuccessRate: document.getElementById('statSuccessRate'),

    // Dashboard
    dryRunBtn: document.getElementById('dryRunBtn'),
    sendBtn: document.getElementById('sendBtn'),
    limitSlider: document.getElementById('limitSlider'),
    limitValue: document.getElementById('limitValue'),
    activityList: document.getElementById('activityList'),

    // Contacts
    contactsTableBody: document.getElementById('contactsTableBody'),
    contactsCount: document.getElementById('contactsCount'),
    importContactsBtn: document.getElementById('importContactsBtn'),
    addContactBtn: document.getElementById('addContactBtn'),

    // Campaigns
    campaignProgress: document.getElementById('campaignProgress'),
    campaignSent: document.getElementById('campaignSent'),
    campaignPending: document.getElementById('campaignPending'),
    campaignErrors: document.getElementById('campaignErrors'),
    campaignStartTime: document.getElementById('campaignStartTime'),
    startCampaignBtn: document.getElementById('startCampaignBtn'),
    stopCampaignBtn: document.getElementById('stopCampaignBtn'),

    // Drafts
    draftsGrid: document.getElementById('draftsGrid'),
    draftsCount: document.getElementById('draftsCount'),
    refreshDraftsBtn: document.getElementById('refreshDraftsBtn'),
    sendAllDraftsBtn: document.getElementById('sendAllDraftsBtn'),

    // Logs
    logsTableBody: document.getElementById('logsTableBody'),
    logsFilter: document.getElementById('logsFilter'),
    exportLogsBtn: document.getElementById('exportLogsBtn'),

    // Settings
    settingsName: document.getElementById('settingsName'),
    settingsEmail: document.getElementById('settingsEmail'),
    settingsSchool: document.getElementById('settingsSchool'),
    settingsMajor: document.getElementById('settingsMajor'),
    settingsPitch: document.getElementById('settingsPitch'),
    settingsGoal: document.getElementById('settingsGoal'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),

    // Modal
    modalOverlay: document.getElementById('modalOverlay'),
    modalClose: document.getElementById('modalClose'),
    modalCancel: document.getElementById('modalCancel'),
    modalConfirm: document.getElementById('modalConfirm'),
    modalTitle: document.getElementById('modalTitle'),
    modalMessage: document.getElementById('modalMessage'),
    modalNote: document.getElementById('modalNote'),
    modalConfirmText: document.getElementById('modalConfirmText'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),

    // Loading
    loadingOverlay: document.getElementById('loadingOverlay'),

    // Search
    globalSearch: document.getElementById('globalSearch'),

    // User
    userName: document.getElementById('userName'),
    userAvatar: document.getElementById('userAvatar')
};

// ========================================
// Mock Data (for development without backend)
// ========================================

const mockContacts = [
    { firstName: 'Tarun', lastName: 'Aitharaju', company: 'Goldman Sachs', email: 'tarun.aitharaju@gs.com', jobTitle: 'Full Stack Engineer', status: 'sent' },
    { firstName: 'Fijurrahman', lastName: 'Amanulla', company: 'Goldman Sachs', email: 'fijurrahman.amanulla@gs.com', jobTitle: 'AWS Data Engineer', status: 'pending' },
    { firstName: 'James', lastName: 'Bellucci', company: 'Goldman Sachs', email: 'james.bellucci@gs.com', jobTitle: 'Software Engineer', status: 'pending' },
    { firstName: 'Fady', lastName: 'Samuel', company: 'Goldman Sachs', email: 'fady.samuel@gs.com', jobTitle: 'AI Engineer', status: 'draft' },
    { firstName: 'Harry', lastName: 'Ketikidis', company: 'Goldman Sachs', email: 'harry.ketikidis@gs.com', jobTitle: 'Data Center Engineer', status: 'sent' },
    { firstName: 'Tianyi', lastName: 'Xie', company: 'Goldman Sachs', email: 'tianyi.xie@gs.com', jobTitle: 'Quantitative Engineer', status: 'sent' },
    { firstName: 'Chelsey', lastName: 'Swilik', company: 'Goldman Sachs', email: 'chelsey.swilik@gs.com', jobTitle: 'Software Engineer', status: 'pending' },
    { firstName: 'Maxim', lastName: 'Zaigraev', company: 'Goldman Sachs', email: 'maxim.zaigraev@gs.com', jobTitle: 'Network Engineer', status: 'error' },
];

const mockLogs = [
    { timestamp: '2025-12-23T22:30:00', email: 'tarun.aitharaju@gs.com', company: 'Goldman Sachs', status: 'SENT', subject: 'Interest in Full Stack Engineering', error: '' },
    { timestamp: '2025-12-23T22:15:00', email: 'harry.ketikidis@gs.com', company: 'Goldman Sachs', status: 'SENT', subject: 'Data Center Engineering Opportunity', error: '' },
    { timestamp: '2025-12-23T22:00:00', email: 'tianyi.xie@gs.com', company: 'Goldman Sachs', status: 'SENT', subject: 'Quantitative Engineering Discussion', error: '' },
    { timestamp: '2025-12-23T21:45:00', email: 'fady.samuel@gs.com', company: 'Goldman Sachs', status: 'DRY_RUN', subject: 'AI Engineering at Goldman', error: '' },
    { timestamp: '2025-12-23T21:30:00', email: 'maxim.zaigraev@gs.com', company: 'Goldman Sachs', status: 'ERROR', subject: 'N/A', error: 'Connection timeout' },
];

const mockDrafts = [
    {
        recipient: 'Fady Samuel',
        email: 'fady.samuel@gs.com',
        subject: 'Interest in AI Engineering at Goldman Sachs',
        preview: 'Hi Fady, I\'m Taylor, an ECE student at Baylor University. As the Electrical & Data Acquisition lead on our Baja SAE team...',
        body: `Hi Fady,

I'm Taylor, an Electrical & Computer Engineering student at Baylor University. I lead the Electrical & Data Acquisition team for our Baja SAE project, which has given me a lot of hands-on experience with embedded systems and working with real-time data.

I came across your profile and was genuinely curious about your path into AI engineering at Goldman Sachs. The intersection of AI and finance is something I find really compelling, and I'd love to hear how you ended up in this space and what the day-to-day looks like.

I'm not reaching out about a job or anything like that—just hoping to learn from someone who's doing the kind of work I'm interested in. If you ever have 15 minutes for a quick call, I'd really appreciate the chance to pick your brain.

Best,
Taylor Van Horn
Lead Electrical Engineer | Baylor SAE Baja Racing Team
Baylor University | Rogers School of Engineering
B.S. Electrical & Computer Engineering, Class of 2027
taylorv0323@gmail.com | (832) 728-6936`,
        date: '2 hours ago'
    },
    {
        recipient: 'James Bellucci',
        email: 'james.bellucci@gs.com',
        subject: 'Quick question about your software engineering journey',
        preview: 'Hi James, I noticed your work as a Software Engineer at Goldman Sachs. I\'d love to learn about your journey into...',
        body: `Hi James,

I'm Taylor, a junior studying Electrical & Computer Engineering at Baylor. I run the electrical and data systems side of our Baja SAE racing team, which has gotten me really interested in software beyond just the embedded stuff I work with day-to-day.

I saw that you're a Software Engineer at Goldman Sachs, and I was curious how you got into that world. I'm trying to figure out where I want to take my career, and talking to people who are actually doing the work seems way more useful than just reading job descriptions.

If you're open to it, I'd love to grab 15 minutes sometime to hear about your experience. No pressure at all if you're too busy—I know how it goes.

Best,
Taylor Van Horn
Lead Electrical Engineer | Baylor SAE Baja Racing Team
Baylor University | Rogers School of Engineering
B.S. Electrical & Computer Engineering, Class of 2027
taylorv0323@gmail.com | (832) 728-6936`,
        date: '3 hours ago'
    },
    {
        recipient: 'Fijurrahman Amanulla',
        email: 'fijurrahman.amanulla@gs.com',
        subject: 'Curious about AWS & data engineering',
        preview: 'Hi Fijurrahman, Your background in AWS and Databricks caught my attention. As someone interested in data-driven design...',
        body: `Hi Fijurrahman,

I'm Taylor—I study ECE at Baylor and lead the data acquisition work for our Baja SAE team. We deal with a lot of sensor data and I've been getting more interested in how this kind of thing works at a larger scale, especially in cloud environments.

Your background with AWS and Databricks caught my eye. I'd be curious to hear how you think about building data systems and what led you down that path. I'm still figuring out what direction I want to go after school, and it sounds like you've built some interesting expertise.

Would you be open to a short call sometime? Even just 10-15 minutes would be really helpful. Totally understand if you're slammed though.

Best,
Taylor Van Horn
Lead Electrical Engineer | Baylor SAE Baja Racing Team
Baylor University | Rogers School of Engineering
B.S. Electrical & Computer Engineering, Class of 2027
taylorv0323@gmail.com | (832) 728-6936`,
        date: '4 hours ago'
    },
];

const mockConfig = {
    your_name: 'Taylor Van Horn',
    your_email: 'taylorv0323@gmail.com',
    your_school: 'Baylor University',
    your_major: 'Electrical & Computer Engineering',
    your_pitch: 'I\'m an ECE student working on Baja SAE as Electrical & Data Acquisition lead, interested in embedded systems, hardware engineering, IT systems, and data-driven design.',
    target_goal: 'explore potential internships, mentorship, or short conversations about your path and team.'
};

// ========================================
// Initialization
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    showLoading();

    try {
        // Load data
        await loadAllData();

        // Set up event listeners
        setupNavigation();
        setupDashboardEvents();
        setupContactsEvents();
        setupCampaignsEvents();
        setupDraftsEvents();
        setupLogsEvents();
        setupSettingsEvents();
        setupModalEvents();
        setupSearchEvents();

        // Render initial view
        updateStats();
        renderContacts();
        renderLogs();
        renderDrafts();
        renderRecentActivity();
        populateSettings();

        hideLoading();
        showToast('success', 'Ready', 'Dashboard loaded successfully');
    } catch (error) {
        hideLoading();
        showToast('error', 'Error', 'Failed to load data');
        console.error('Init error:', error);
    }
}

// ========================================
// Data Loading
// ========================================

// Path to contacts CSV file (relative to frontend folder)
const CONTACTS_CSV_PATH = '../outreach_proj/contacts.csv';
const LOGS_CSV_PATH = '../outreach_proj/logs.csv';
const CONFIG_JSON_PATH = '../outreach_proj/config.json';

async function loadAllData() {
    // Always try to load from actual files first
    try {
        // Load contacts from CSV
        const contactsLoaded = await loadContactsFromCSV();

        // Load config from JSON
        const configLoaded = await loadConfigFromJSON();

        // Load logs from CSV (if exists)
        const logsLoaded = await loadLogsFromCSV();

        // Use mock drafts for now (drafts are generated, not stored)
        AppState.drafts = mockDrafts;

        if (contactsLoaded) {
            console.log(`Loaded ${AppState.contacts.length} contacts from CSV`);
        }
    } catch (error) {
        console.error('Error loading data:', error);
        // Fall back to mock data if file loading fails
        if (AppState.contacts.length === 0) {
            AppState.contacts = mockContacts;
        }
        AppState.logs = AppState.logs.length > 0 ? AppState.logs : mockLogs;
        AppState.config = AppState.config.your_name ? AppState.config : mockConfig;
        AppState.drafts = mockDrafts;
    }
}

// Parse CSV text into array of objects
function parseCSV(csvText) {
    // Remove BOM if present
    if (csvText.charCodeAt(0) === 0xFEFF) {
        csvText = csvText.slice(1);
    }

    const lines = csvText.trim().split(/\r?\n/);
    if (lines.length < 2) return [];

    // Parse header row
    const headers = parseCSVLine(lines[0]);

    // Parse data rows
    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        const values = parseCSVLine(line);
        const row = {};

        headers.forEach((header, index) => {
            row[header.trim()] = (values[index] || '').trim();
        });

        data.push(row);
    }

    return data;
}

// Parse a single CSV line handling quoted values
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    result.push(current);

    return result;
}

async function loadContactsFromCSV() {
    try {
        const response = await fetch(CONTACTS_CSV_PATH);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const csvText = await response.text();
        const rawContacts = parseCSV(csvText);

        // Map CSV columns to our contact format - include ALL contacts
        AppState.contacts = rawContacts
            .filter(row => row['First Name'] || row['Last Name']) // Only filter completely empty rows
            .map(row => ({
                firstName: row['First Name'] || '',
                lastName: row['Last Name'] || '',
                company: row['Company'] || '',
                email: row['Email Address'] || '',
                jobTitle: row['Job Title'] || '',
                city: row['Business City'] || '',
                state: row['Business State'] || '',
                status: row['Email Address'] && row['Email Address'].trim() ? 'pending' : 'no-email'
            }));

        // Check logs to update contact statuses
        updateContactStatusesFromLogs();

        return true;
    } catch (error) {
        console.warn('Could not load contacts.csv:', error.message);
        return false;
    }
}

async function loadLogsFromCSV() {
    try {
        const response = await fetch(LOGS_CSV_PATH);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const csvText = await response.text();
        const rawLogs = parseCSV(csvText);

        // Map CSV columns to our log format
        AppState.logs = rawLogs.map(row => ({
            timestamp: row['Timestamp'] || '',
            email: row['Email'] || '',
            company: row['Company'] || '',
            status: row['Status'] || '',
            subject: row['Subject'] || '',
            error: row['Error'] || ''
        }));

        return true;
    } catch (error) {
        console.warn('Could not load logs.csv:', error.message);
        AppState.logs = [];
        return false;
    }
}

async function loadConfigFromJSON() {
    try {
        const response = await fetch(CONFIG_JSON_PATH);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        AppState.config = await response.json();
        return true;
    } catch (error) {
        console.warn('Could not load config.json:', error.message);
        AppState.config = mockConfig;
        return false;
    }
}

// Update contact statuses based on log entries
function updateContactStatusesFromLogs() {
    const contactedEmails = new Map();

    // Build map of email -> status from logs
    AppState.logs.forEach(log => {
        const email = (log.email || '').toLowerCase();
        const status = (log.status || '').toUpperCase();

        if (email && (status === 'SENT' || status === 'DRY_RUN' || status === 'ERROR')) {
            // Use the most recent status
            if (!contactedEmails.has(email)) {
                contactedEmails.set(email, status === 'SENT' ? 'sent' : status === 'ERROR' ? 'error' : 'draft');
            }
        }
    });

    // Update contact statuses
    AppState.contacts.forEach(contact => {
        const email = (contact.email || '').toLowerCase();
        if (contactedEmails.has(email)) {
            contact.status = contactedEmails.get(email);
        }
    });
}

// ========================================
// Navigation
// ========================================

function setupNavigation() {
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            navigateTo(section);
        });
    });

    // Handle panel links
    document.querySelectorAll('.panel-link[data-section]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.section);
        });
    });
}

function navigateTo(section) {
    // Update nav items
    elements.navItems.forEach(nav => {
        nav.classList.toggle('active', nav.dataset.section === section);
    });

    // Update sections
    Object.keys(elements.sections).forEach(key => {
        elements.sections[key].classList.toggle('active', key === section);
    });

    // Update header
    updatePageHeader(section);

    AppState.currentSection = section;
}

function updatePageHeader(section) {
    const headers = {
        dashboard: { title: 'Dashboard', subtitle: 'Monitor your outreach campaigns' },
        contacts: { title: 'Contacts', subtitle: 'Manage your contact list' },
        campaigns: { title: 'Campaigns', subtitle: 'Track email campaign progress' },
        drafts: { title: 'Drafts', subtitle: 'Review generated email drafts' },
        logs: { title: 'Activity Logs', subtitle: 'View all email activity history' },
        settings: { title: 'Settings', subtitle: 'Configure your preferences' }
    };

    const header = headers[section] || headers.dashboard;
    elements.pageTitle.textContent = header.title;
    elements.pageSubtitle.textContent = header.subtitle;
}

// ========================================
// Stats
// ========================================

function updateStats() {
    const sent = AppState.logs.filter(l => l.status === 'SENT').length;
    const total = AppState.contacts.length;
    const drafts = AppState.drafts.length;
    const errors = AppState.logs.filter(l => l.status === 'ERROR').length;
    const successRate = sent > 0 ? Math.round((sent / (sent + errors)) * 100) : 0;

    AppState.stats = { emailsSent: sent, totalContacts: total, pendingDrafts: drafts, successRate };

    animateValue(elements.statEmailsSent, sent);
    animateValue(elements.statTotalContacts, total);
    animateValue(elements.statPendingDrafts, drafts);
    elements.statSuccessRate.textContent = `${successRate}%`;

    // Update campaign stats
    const pending = AppState.contacts.filter(c => c.status === 'pending').length;
    elements.campaignSent.textContent = sent;
    elements.campaignPending.textContent = pending;
    elements.campaignErrors.textContent = errors;
}

function animateValue(element, target) {
    const start = parseInt(element.textContent) || 0;
    const duration = 500;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const value = Math.floor(start + (target - start) * easeOutQuart(progress));
        element.textContent = value;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function easeOutQuart(x) {
    return 1 - Math.pow(1 - x, 4);
}

// ========================================
// Dashboard Events
// ========================================

function setupDashboardEvents() {
    // Slider
    elements.limitSlider.addEventListener('input', (e) => {
        elements.limitValue.textContent = e.target.value;
    });

    // Delay selector
    const delaySelect = document.getElementById('delaySelect');
    if (delaySelect) {
        delaySelect.addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            switch (value) {
                case 15:
                    AppState.sendDelay = { min: 15, max: 45 };
                    break;
                case 30:
                    AppState.sendDelay = { min: 30, max: 60 };
                    break;
                case 60:
                    AppState.sendDelay = { min: 60, max: 120 };
                    break;
            }
            showToast('info', 'Delay Updated', `Delay set to ${AppState.sendDelay.min}-${AppState.sendDelay.max} seconds`);
        });
    }

    // Dry Run
    elements.dryRunBtn.addEventListener('click', () => {
        const limit = elements.limitSlider.value;
        showModal(
            'Start Dry Run',
            `Generate ${limit} email draft(s) without sending?`,
            'Drafts will be saved for review.',
            'Generate Drafts',
            () => runDryRun(limit)
        );
    });

    // Send Campaign
    elements.sendBtn.addEventListener('click', () => {
        const limit = elements.limitSlider.value;
        showModal(
            'Send Campaign',
            `Send ${limit} email(s) to pending contacts?`,
            `Delay: ${AppState.sendDelay.min}-${AppState.sendDelay.max}s between emails. This action cannot be undone.`,
            'Send Emails',
            () => runCampaign(limit)
        );
    });
}

async function runDryRun(limit) {
    showLoading();
    showToast('info', 'Dry Run Started', `Generating ${limit} drafts...`);

    try {
        // Try to use the backend API
        const response = await fetch(`${API_BASE}/dry-run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ limit: parseInt(limit) })
        });

        if (response.ok) {
            const data = await response.json();

            if (data.drafts && data.drafts.length > 0) {
                // Count successful drafts (without errors)
                const successfulDrafts = data.drafts.filter(d => !d.error && d.body);

                if (successfulDrafts.length > 0) {
                    // Add drafts to state
                    successfulDrafts.forEach(draft => {
                        AppState.drafts.unshift({
                            recipient: draft.recipient,
                            email: draft.email,
                            subject: draft.subject,
                            preview: draft.preview,
                            body: draft.body,
                            date: 'Just now'
                        });

                        // Update contact status
                        const contact = AppState.contacts.find(c => c.email.toLowerCase() === draft.email.toLowerCase());
                        if (contact) {
                            contact.status = 'draft';
                        }

                        addActivity('draft', `Draft created for ${draft.recipient}`, 'Just now');
                    });

                    updateStats();
                    renderDrafts();
                    renderContacts();
                    renderRecentActivity();
                    hideLoading();
                    showToast('success', 'Dry Run Complete', `Generated ${successfulDrafts.length} draft(s) via API`);
                    return;
                } else {
                    // All drafts had errors, fall back to simulation
                    console.log('API returned only errors, falling back to simulation');
                }
            } else if (data.message) {
                hideLoading();
                showToast('info', 'No New Contacts', data.message);
                return;
            }
        }
    } catch (error) {
        console.log('API not available, using simulation mode:', error.message);
    }

    // Fallback to simulation if API is not available
    const pending = AppState.contacts.filter(c => c.status === 'pending').slice(0, limit);

    for (let i = 0; i < pending.length; i++) {
        await delay(500);
        const contact = pending[i];

        // Create draft with full body - natural conversational tone + professional signature
        const draft = {
            recipient: `${contact.firstName} ${contact.lastName}`,
            email: contact.email,
            subject: `Interest in ${contact.jobTitle} at ${contact.company}`,
            preview: `Hi ${contact.firstName}, I'm Taylor, an ECE student at Baylor University...`,
            body: `Hi ${contact.firstName},

I'm Taylor, a junior studying Electrical & Computer Engineering at Baylor. I run the electrical and data systems for our Baja SAE racing team, which has given me a lot of hands-on experience beyond just coursework.

I came across your profile and was curious about your work as a ${contact.jobTitle} at ${contact.company}. It sounds like the kind of role I could see myself in down the road, and I'd love to hear a bit about how you got there and what the work is actually like.

I'm not reaching out about job opportunities or anything—just trying to learn from people who are doing interesting work in the field. If you ever have 10-15 minutes for a quick chat, I'd really appreciate it. No worries if not, I know everyone's busy.

Best,
Taylor Van Horn
Lead Electrical Engineer | Baylor SAE Baja Racing Team
Baylor University | Rogers School of Engineering
B.S. Electrical & Computer Engineering, Class of 2027
taylorv0323@gmail.com | (832) 728-6936`,
            date: 'Just now'
        };

        AppState.drafts.unshift(draft);
        contact.status = 'draft';

        // Add to activity
        addActivity('draft', `Draft created for ${contact.firstName} ${contact.lastName}`, 'Just now');
    }

    updateStats();
    renderDrafts();
    renderContacts();
    renderRecentActivity();
    hideLoading();
    showToast('success', 'Dry Run Complete', `Generated ${pending.length} draft(s) (simulation)`);
}

async function runCampaign(limit) {
    showLoading();
    showToast('info', 'Campaign Started', `Sending ${limit} emails...`);

    try {
        // Try to use the backend API
        const response = await fetch(`${API_BASE}/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ limit: parseInt(limit) })
        });

        if (response.ok) {
            const data = await response.json();

            if (data.sent && data.sent.length > 0) {
                let sentCount = 0;
                let errorCount = 0;

                data.sent.forEach(result => {
                    const contact = AppState.contacts.find(c => c.email.toLowerCase() === result.email.toLowerCase());

                    if (result.status === 'sent') {
                        sentCount++;
                        if (contact) contact.status = 'sent';

                        AppState.logs.unshift({
                            timestamp: new Date().toISOString(),
                            email: result.email,
                            company: result.company,
                            status: 'SENT',
                            subject: result.subject,
                            error: ''
                        });
                        addActivity('sent', `Email sent to ${result.recipient}`, 'Just now');
                    } else {
                        errorCount++;
                        if (contact) contact.status = 'error';

                        AppState.logs.unshift({
                            timestamp: new Date().toISOString(),
                            email: result.email,
                            company: result.company || '',
                            status: 'ERROR',
                            subject: 'N/A',
                            error: result.error || 'Unknown error'
                        });
                        addActivity('error', `Failed to send to ${result.recipient}`, 'Just now');
                    }

                    // Remove from drafts if exists
                    const draftIdx = AppState.drafts.findIndex(d => d.email.toLowerCase() === result.email.toLowerCase());
                    if (draftIdx !== -1) {
                        AppState.drafts.splice(draftIdx, 1);
                    }
                });

                const progress = 100;
                elements.campaignProgress.style.width = `${progress}%`;

                updateStats();
                renderContacts();
                renderLogs();
                renderDrafts();
                renderRecentActivity();
                hideLoading();
                showToast('success', 'Campaign Complete', `Sent ${sentCount}/${data.sent.length} emails via API`);
                return;
            } else {
                hideLoading();
                showToast('info', 'No New Contacts', data.message || 'All contacts have been processed');
                return;
            }
        }
    } catch (error) {
        console.log('API not available, using simulation mode:', error.message);
    }

    // Fallback to simulation if API is not available
    const pending = AppState.contacts.filter(c => c.status === 'pending' || c.status === 'draft').slice(0, limit);
    let sent = 0;

    for (let i = 0; i < pending.length; i++) {
        await delay(800);
        const contact = pending[i];

        // Simulate sending (90% success rate)
        const success = Math.random() > 0.1;

        if (success) {
            contact.status = 'sent';
            AppState.logs.unshift({
                timestamp: new Date().toISOString(),
                email: contact.email,
                company: contact.company,
                status: 'SENT',
                subject: `Interest in ${contact.jobTitle}`,
                error: ''
            });
            addActivity('sent', `Email sent to ${contact.firstName} ${contact.lastName}`, 'Just now');
            sent++;
        } else {
            contact.status = 'error';
            AppState.logs.unshift({
                timestamp: new Date().toISOString(),
                email: contact.email,
                company: contact.company,
                status: 'ERROR',
                subject: 'N/A',
                error: 'Connection failed'
            });
            addActivity('error', `Failed to send to ${contact.firstName} ${contact.lastName}`, 'Just now');
        }

        // Update progress
        const progress = ((i + 1) / pending.length) * 100;
        elements.campaignProgress.style.width = `${progress}%`;
    }

    updateStats();
    renderContacts();
    renderLogs();
    renderRecentActivity();
    hideLoading();
    showToast('success', 'Campaign Complete', `Sent ${sent}/${pending.length} emails (simulation)`);
}

// ========================================
// Recent Activity
// ========================================

function renderRecentActivity() {
    const recentLogs = AppState.logs.slice(0, 5);

    if (recentLogs.length === 0) {
        elements.activityList.innerHTML = `
            <div class="empty-state">
                <p>No recent activity</p>
            </div>
        `;
        return;
    }

    elements.activityList.innerHTML = recentLogs.map(log => {
        const statusClass = log.status === 'SENT' ? 'sent' : log.status === 'ERROR' ? 'error' : 'draft';
        const statusLabel = log.status === 'SENT' ? 'Sent' : log.status === 'ERROR' ? 'Error' : 'Draft';
        const icon = getStatusIcon(log.status);
        const name = log.email.split('@')[0].split('.').map(capitalize).join(' ');
        const time = formatTime(log.timestamp);

        return `
            <div class="activity-item">
                <div class="activity-icon ${statusClass}">${icon}</div>
                <div class="activity-info">
                    <span class="activity-title">${log.status === 'SENT' ? 'Sent to' : log.status === 'ERROR' ? 'Failed:' : 'Draft for'} ${name}</span>
                    <span class="activity-meta">${log.company} • ${time}</span>
                </div>
                <span class="activity-badge ${statusClass.toLowerCase()}">${statusLabel}</span>
            </div>
        `;
    }).join('');
}

function addActivity(type, title, time) {
    const icon = getStatusIcon(type.toUpperCase());
    const statusClass = type === 'sent' ? 'sent' : type === 'error' ? 'error' : 'draft';
    const statusLabel = type === 'sent' ? 'Sent' : type === 'error' ? 'Error' : 'Draft';

    const item = document.createElement('div');
    item.className = 'activity-item';
    item.style.animation = 'slideIn 0.3s ease';
    item.innerHTML = `
        <div class="activity-icon ${statusClass}">${icon}</div>
        <div class="activity-info">
            <span class="activity-title">${title}</span>
            <span class="activity-meta">${time}</span>
        </div>
        <span class="activity-badge ${statusClass}">${statusLabel}</span>
    `;

    elements.activityList.insertBefore(item, elements.activityList.firstChild);

    // Keep only 5 items
    while (elements.activityList.children.length > 5) {
        elements.activityList.removeChild(elements.activityList.lastChild);
    }
}

function getStatusIcon(status) {
    if (status === 'SENT' || status === 'sent') {
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (status === 'ERROR' || status === 'error') {
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else {
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
    }
}

// ========================================
// Contacts
// ========================================

// Add Contact Modal Elements
const addContactModal = document.getElementById('addContactModal');
const addContactClose = document.getElementById('addContactClose');
const addContactCancelBtn = document.getElementById('addContactCancelBtn');
const addContactSaveBtn = document.getElementById('addContactSaveBtn');
const csvFileInput = document.getElementById('csvFileInput');

function setupContactsEvents() {
    // Import CSV button
    elements.importContactsBtn.addEventListener('click', () => {
        csvFileInput.click();
    });

    // CSV file input change handler
    csvFileInput.addEventListener('change', handleCSVImport);

    // Add Contact button - open modal
    elements.addContactBtn.addEventListener('click', openAddContactModal);

    // Add Contact modal events
    if (addContactClose) {
        addContactClose.addEventListener('click', closeAddContactModal);
    }
    if (addContactCancelBtn) {
        addContactCancelBtn.addEventListener('click', closeAddContactModal);
    }
    if (addContactSaveBtn) {
        addContactSaveBtn.addEventListener('click', saveNewContact);
    }
    if (addContactModal) {
        addContactModal.addEventListener('click', (e) => {
            if (e.target === addContactModal) closeAddContactModal();
        });
    }
}

function openAddContactModal() {
    // Clear form
    document.getElementById('newContactFirstName').value = '';
    document.getElementById('newContactLastName').value = '';
    document.getElementById('newContactEmail').value = '';
    document.getElementById('newContactCompany').value = 'Goldman Sachs';
    document.getElementById('newContactJobTitle').value = '';

    addContactModal.classList.add('active');
}

function closeAddContactModal() {
    addContactModal.classList.remove('active');
}

async function saveNewContact() {
    const firstName = document.getElementById('newContactFirstName').value.trim();
    const lastName = document.getElementById('newContactLastName').value.trim();
    const email = document.getElementById('newContactEmail').value.trim();
    const company = document.getElementById('newContactCompany').value.trim();
    const jobTitle = document.getElementById('newContactJobTitle').value.trim();

    if (!firstName || !lastName) {
        showToast('error', 'Required Fields', 'First name and last name are required');
        return;
    }

    // Validate email format if provided
    if (email && !isValidEmail(email)) {
        showToast('error', 'Invalid Email', 'Please enter a valid email address');
        return;
    }

    // Check for duplicate email locally first
    if (email && AppState.contacts.some(c => c.email.toLowerCase() === email.toLowerCase())) {
        showToast('error', 'Duplicate Email', 'A contact with this email already exists');
        return;
    }

    const newContact = {
        firstName,
        lastName,
        email,
        company,
        jobTitle,
        city: '',
        state: '',
        status: email ? 'pending' : 'no-email'
    };

    showLoading();

    try {
        // Try to persist to backend
        const response = await fetch(`${API_BASE}/contacts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newContact)
        });

        if (response.ok) {
            AppState.contacts.unshift(newContact);
            updateStats();
            renderContacts();
            closeAddContactModal();
            hideLoading();
            showToast('success', 'Contact Added', `${firstName} ${lastName} has been saved`);
        } else {
            const data = await response.json();
            hideLoading();
            showToast('error', 'Error', data.error || 'Failed to add contact');
        }
    } catch (error) {
        console.log('API not available, saving locally only:', error.message);

        // Fallback: add to local state only
        AppState.contacts.unshift(newContact);
        updateStats();
        renderContacts();
        closeAddContactModal();
        hideLoading();
        showToast('success', 'Contact Added', `${firstName} ${lastName} added (local only)`);
    }
}

// Email validation helper
function isValidEmail(email) {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return pattern.test(email);
}

async function handleCSVImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    showLoading();

    try {
        const text = await file.text();
        const rawContacts = parseCSV(text);

        let imported = 0;
        let skipped = 0;

        rawContacts.forEach(row => {
            const firstName = row['First Name'] || '';
            const lastName = row['Last Name'] || '';
            const email = row['Email Address'] || '';

            if (!firstName && !lastName) {
                skipped++;
                return;
            }

            // Check for duplicate email
            if (email && AppState.contacts.some(c => c.email.toLowerCase() === email.toLowerCase())) {
                skipped++;
                return;
            }

            AppState.contacts.push({
                firstName,
                lastName,
                company: row['Company'] || '',
                email,
                jobTitle: row['Job Title'] || '',
                city: row['Business City'] || '',
                state: row['Business State'] || '',
                status: email ? 'pending' : 'no-email'
            });
            imported++;
        });

        updateStats();
        renderContacts();
        hideLoading();
        showToast('success', 'Import Complete', `Imported ${imported} contacts (${skipped} skipped)`);
    } catch (error) {
        hideLoading();
        showToast('error', 'Import Failed', 'Could not read the CSV file');
        console.error('CSV import error:', error);
    }

    // Reset file input
    csvFileInput.value = '';
}

function renderContacts(filter = '') {
    let contacts = AppState.contacts;

    if (filter) {
        const search = filter.toLowerCase();
        contacts = contacts.filter(c =>
            c.firstName.toLowerCase().includes(search) ||
            c.lastName.toLowerCase().includes(search) ||
            c.email.toLowerCase().includes(search) ||
            c.company.toLowerCase().includes(search)
        );
    }

    elements.contactsCount.textContent = `${contacts.length} contact${contacts.length !== 1 ? 's' : ''}`;

    if (contacts.length === 0) {
        elements.contactsTableBody.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                    </svg>
                </div>
                <h3>No contacts found</h3>
                <p>Import a CSV or add contacts manually</p>
            </div>
        `;
        return;
    }

    elements.contactsTableBody.innerHTML = contacts.map((contact, index) => {
        const initials = `${(contact.firstName[0] || '?')}${(contact.lastName[0] || '?')}`;
        const statusClass = contact.status || 'pending';
        const statusLabel = contact.status === 'no-email' ? 'No Email' : capitalize(contact.status || 'pending');
        const emailDisplay = contact.email || '(no email)';
        const hasEmail = contact.email && contact.email.trim();

        // Find actual index in AppState.contacts for delete
        const actualIndex = AppState.contacts.indexOf(contact);

        return `
            <div class="table-row">
                <div class="contact-cell">
                    <div class="contact-avatar">${initials}</div>
                    <span class="contact-name">${contact.firstName} ${contact.lastName}</span>
                </div>
                <span class="contact-email ${!hasEmail ? 'no-email-text' : ''}">${emailDisplay}</span>
                <span class="contact-company">${contact.company}</span>
                <span class="contact-status ${statusClass}">${statusLabel}</span>
                <div class="contact-actions">
                    ${hasEmail ? `
                    <button title="Send" onclick="sendToContact('${contact.email}')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z"/>
                        </svg>
                    </button>
                    ` : ''}
                    <button title="Delete" onclick="deleteContact(${actualIndex})" class="delete-btn">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6l-2 14H7L5 6"/>
                            <path d="M10 11v6M14 11v6"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Delete contact
window.deleteContact = function (index) {
    const contact = AppState.contacts[index];
    if (!contact) return;

    showModal(
        'Delete Contact',
        `Delete ${contact.firstName} ${contact.lastName}?`,
        'This action cannot be undone.',
        'Delete',
        async () => {
            showLoading();

            try {
                // Try to persist deletion to backend
                if (contact.email) {
                    const response = await fetch(`${API_BASE}/contacts/${encodeURIComponent(contact.email)}`, {
                        method: 'DELETE'
                    });

                    if (!response.ok) {
                        const data = await response.json();
                        console.log('Backend delete failed:', data.error);
                    }
                }
            } catch (error) {
                console.log('API not available, deleting locally only:', error.message);
            }

            // Always remove from local state
            AppState.contacts.splice(index, 1);
            updateStats();
            renderContacts();
            hideLoading();
            showToast('info', 'Contact Deleted', `${contact.firstName} ${contact.lastName} removed`);
        }
    );
};

// Global functions for contact actions
window.viewContact = function (email) {
    const contact = AppState.contacts.find(c => c.email === email);
    if (contact) {
        showToast('info', 'Contact Details', `${contact.firstName} ${contact.lastName} - ${contact.jobTitle}`);
    }
};

window.sendToContact = async function (email) {
    const contact = AppState.contacts.find(c => c.email === email);
    if (!contact) return;

    showModal(
        'Send Email',
        `Send personalized email to ${contact.firstName} ${contact.lastName}?`,
        `Email: ${email}`,
        'Send Email',
        async () => {
            showLoading();

            try {
                // Try to use the backend API
                const response = await fetch(`${API_BASE}/send`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, limit: 1 })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.sent && data.sent.length > 0) {
                        const result = data.sent[0];
                        if (result.status === 'sent') {
                            contact.status = 'sent';
                            AppState.logs.unshift({
                                timestamp: new Date().toISOString(),
                                email: contact.email,
                                company: contact.company,
                                status: 'SENT',
                                subject: result.subject || `Interest in ${contact.jobTitle}`,
                                error: ''
                            });
                            addActivity('sent', `Email sent to ${contact.firstName} ${contact.lastName}`, 'Just now');
                            hideLoading();
                            showToast('success', 'Email Sent', `Successfully sent to ${contact.firstName} via API`);
                        } else {
                            contact.status = 'error';
                            AppState.logs.unshift({
                                timestamp: new Date().toISOString(),
                                email: contact.email,
                                company: contact.company,
                                status: 'ERROR',
                                subject: 'N/A',
                                error: result.error || 'Unknown error'
                            });
                            addActivity('error', `Failed to send to ${contact.firstName}`, 'Just now');
                            hideLoading();
                            showToast('error', 'Send Failed', result.error || 'Unknown error');
                        }
                    } else {
                        hideLoading();
                        showToast('info', 'Already Processed', data.message || 'Contact already processed');
                    }
                } else {
                    throw new Error('API request failed');
                }
            } catch (error) {
                console.log('API not available, using simulation:', error.message);

                // Fallback to simulation
                await delay(1000);
                contact.status = 'sent';
                AppState.logs.unshift({
                    timestamp: new Date().toISOString(),
                    email: contact.email,
                    company: contact.company,
                    status: 'SENT',
                    subject: `Interest in ${contact.jobTitle}`,
                    error: ''
                });
                addActivity('sent', `Email sent to ${contact.firstName} ${contact.lastName}`, 'Just now');
                hideLoading();
                showToast('success', 'Email Sent', `Successfully sent to ${contact.firstName} (simulation)`);
            }

            updateStats();
            renderContacts();
            renderLogs();
            renderRecentActivity();
        }
    );
};

// ========================================
// Campaigns
// ========================================

function setupCampaignsEvents() {
    elements.startCampaignBtn.addEventListener('click', () => {
        const pending = AppState.contacts.filter(c => c.status === 'pending' || c.status === 'draft').length;
        if (pending === 0) {
            showToast('warning', 'No Pending', 'No pending contacts to send emails to');
            return;
        }

        showModal(
            'Start Campaign',
            `Start sending to ${pending} pending contact(s)?`,
            'Emails will be sent with delays to avoid spam filters.',
            'Start Campaign',
            () => startCampaign()
        );
    });

    elements.stopCampaignBtn.addEventListener('click', () => {
        AppState.campaignRunning = false;
        elements.stopCampaignBtn.style.opacity = '0.5';
        elements.stopCampaignBtn.style.pointerEvents = 'none';
        elements.startCampaignBtn.style.opacity = '1';
        elements.startCampaignBtn.style.pointerEvents = 'auto';
        showToast('info', 'Campaign Paused', 'Campaign has been stopped');
    });
}

async function startCampaign() {
    AppState.campaignRunning = true;
    elements.startCampaignBtn.style.opacity = '0.5';
    elements.startCampaignBtn.style.pointerEvents = 'none';
    elements.stopCampaignBtn.style.opacity = '1';
    elements.stopCampaignBtn.style.pointerEvents = 'auto';
    elements.campaignStartTime.textContent = new Date().toLocaleTimeString();

    const pending = AppState.contacts.filter(c => c.status === 'pending' || c.status === 'draft');

    for (let i = 0; i < pending.length && AppState.campaignRunning; i++) {
        const contact = pending[i];

        // Simulate sending
        await delay(1500);

        if (!AppState.campaignRunning) break;

        const success = Math.random() > 0.1;
        contact.status = success ? 'sent' : 'error';

        AppState.logs.unshift({
            timestamp: new Date().toISOString(),
            email: contact.email,
            company: contact.company,
            status: success ? 'SENT' : 'ERROR',
            subject: success ? `Interest in ${contact.jobTitle}` : 'N/A',
            error: success ? '' : 'Connection failed'
        });

        // Update progress
        const progress = ((i + 1) / pending.length) * 100;
        elements.campaignProgress.style.width = `${progress}%`;

        updateStats();
        renderContacts();
        renderRecentActivity();
    }

    AppState.campaignRunning = false;
    elements.startCampaignBtn.style.opacity = '1';
    elements.startCampaignBtn.style.pointerEvents = 'auto';
    elements.stopCampaignBtn.style.opacity = '0.5';
    elements.stopCampaignBtn.style.pointerEvents = 'none';

    renderLogs();
    showToast('success', 'Campaign Complete', 'All emails have been processed');
}

// ========================================
// Drafts
// ========================================

// Draft detail modal elements
let currentDraftIndex = null;
const draftDetailOverlay = document.getElementById('draftDetailOverlay');
const draftDetailClose = document.getElementById('draftDetailClose');
const draftDetailAvatar = document.getElementById('draftDetailAvatar');
const draftDetailName = document.getElementById('draftDetailName');
const draftDetailEmail = document.getElementById('draftDetailEmail');
const draftDetailTo = document.getElementById('draftDetailTo');
const draftDetailSubject = document.getElementById('draftDetailSubject');
const draftDetailBody = document.getElementById('draftDetailBody');
const draftDetailEdit = document.getElementById('draftDetailEdit');
const draftDetailSend = document.getElementById('draftDetailSend');

function setupDraftsEvents() {
    elements.refreshDraftsBtn.addEventListener('click', () => {
        showToast('info', 'Refreshing', 'Loading drafts...');
        renderDrafts();
    });

    elements.sendAllDraftsBtn.addEventListener('click', () => {
        if (AppState.drafts.length === 0) {
            showToast('warning', 'No Drafts', 'No drafts to send');
            return;
        }

        showModal(
            'Send All Drafts',
            `Send ${AppState.drafts.length} draft email(s)?`,
            'All drafts will be sent to their recipients.',
            'Send All',
            () => sendAllDrafts()
        );
    });

    // Draft detail modal events
    if (draftDetailClose) {
        draftDetailClose.addEventListener('click', closeDraftDetail);
    }

    if (draftDetailOverlay) {
        draftDetailOverlay.addEventListener('click', (e) => {
            if (e.target === draftDetailOverlay) {
                closeDraftDetail();
            }
        });
    }

    if (draftDetailEdit) {
        draftDetailEdit.addEventListener('click', () => {
            enterDraftEditMode();
        });
    }

    if (draftDetailSend) {
        draftDetailSend.addEventListener('click', () => {
            if (currentDraftIndex !== null) {
                closeDraftDetail();
                window.sendDraft(currentDraftIndex);
            }
        });
    }

    // Edit mode buttons
    const draftEditCancel = document.getElementById('draftEditCancel');
    const draftEditSave = document.getElementById('draftEditSave');

    if (draftEditCancel) {
        draftEditCancel.addEventListener('click', () => {
            exitDraftEditMode();
        });
    }

    if (draftEditSave) {
        draftEditSave.addEventListener('click', () => {
            saveDraftEdits();
        });
    }

    // Escape key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && draftDetailOverlay?.classList.contains('active')) {
            closeDraftDetail();
        }
    });
}

// Enter edit mode for the current draft
function enterDraftEditMode() {
    if (currentDraftIndex === null) return;

    const draft = AppState.drafts[currentDraftIndex];
    if (!draft) return;

    // Populate edit fields
    document.getElementById('draftEditSubject').value = draft.subject;
    document.getElementById('draftEditBody').value = draft.body || draft.preview;

    // Toggle visibility
    document.getElementById('draftSubjectRow').style.display = 'none';
    document.getElementById('draftSubjectEditRow').style.display = 'flex';
    document.getElementById('draftDetailBody').style.display = 'none';
    document.getElementById('draftEditBodyContainer').style.display = 'block';
    document.getElementById('draftViewButtons').style.display = 'none';
    document.getElementById('draftEditButtons').style.display = 'flex';

    showToast('info', 'Edit Mode', 'You can now edit the subject and body');
}

// Exit edit mode without saving
function exitDraftEditMode() {
    // Toggle visibility back
    document.getElementById('draftSubjectRow').style.display = 'flex';
    document.getElementById('draftSubjectEditRow').style.display = 'none';
    document.getElementById('draftDetailBody').style.display = 'block';
    document.getElementById('draftEditBodyContainer').style.display = 'none';
    document.getElementById('draftViewButtons').style.display = 'flex';
    document.getElementById('draftEditButtons').style.display = 'none';
}

// Save draft edits
function saveDraftEdits() {
    if (currentDraftIndex === null) return;

    const draft = AppState.drafts[currentDraftIndex];
    if (!draft) return;

    const newSubject = document.getElementById('draftEditSubject').value.trim();
    const newBody = document.getElementById('draftEditBody').value.trim();

    if (!newSubject || !newBody) {
        showToast('error', 'Required Fields', 'Subject and body cannot be empty');
        return;
    }

    // Update draft
    draft.subject = newSubject;
    draft.body = newBody;
    draft.preview = newBody.substring(0, 100) + (newBody.length > 100 ? '...' : '');

    // Update display
    draftDetailSubject.textContent = newSubject;
    const bodyHtml = newBody
        .split('\n\n')
        .map(para => `<p>${para.replace(/\n/g, '<br>')}</p>`)
        .join('');
    draftDetailBody.innerHTML = bodyHtml;

    // Exit edit mode
    exitDraftEditMode();

    // Re-render drafts grid to show updated preview
    renderDrafts();

    showToast('success', 'Draft Saved', 'Your changes have been saved');
}

function renderDrafts() {
    elements.draftsCount.textContent = `${AppState.drafts.length} draft${AppState.drafts.length !== 1 ? 's' : ''}`;

    if (AppState.drafts.length === 0) {
        elements.draftsGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                </div>
                <h3>No drafts</h3>
                <p>Run a dry run to generate email drafts</p>
            </div>
        `;
        return;
    }

    elements.draftsGrid.innerHTML = AppState.drafts.map((draft, index) => {
        const initials = draft.recipient.split(' ').map(n => n[0]).join('');

        return `
            <div class="draft-card" onclick="viewDraft(${index})">
                <div class="draft-header">
                    <div class="draft-recipient">
                        <div class="avatar">${initials}</div>
                        <div class="draft-recipient-info">
                            <span class="draft-recipient-name">${draft.recipient}</span>
                            <span class="draft-recipient-email">${draft.email}</span>
                        </div>
                    </div>
                    <span class="draft-date">${draft.date}</span>
                </div>
                <div class="draft-content">
                    <div class="draft-subject">${draft.subject}</div>
                    <div class="draft-preview">${draft.preview}</div>
                </div>
                <div class="draft-click-hint">Click to read full email</div>
                <div class="draft-footer" onclick="event.stopPropagation();">
                    <button class="btn-primary" onclick="event.stopPropagation(); sendDraft(${index})">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z"/>
                        </svg>
                        Send
                    </button>
                    <button class="btn-secondary" onclick="event.stopPropagation(); deleteDraft(${index})">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6l-2 14H7L5 6"/>
                            <path d="M10 11v6M14 11v6"/>
                        </svg>
                        Delete
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// View full draft in modal
window.viewDraft = function (index) {
    const draft = AppState.drafts[index];
    if (!draft) return;

    currentDraftIndex = index;

    const initials = draft.recipient.split(' ').map(n => n[0]).join('');

    draftDetailAvatar.textContent = initials;
    draftDetailName.textContent = draft.recipient;
    draftDetailEmail.textContent = draft.email;
    draftDetailTo.textContent = draft.email;
    draftDetailSubject.textContent = draft.subject;

    // Convert body text to HTML paragraphs
    const bodyHtml = (draft.body || draft.preview)
        .split('\n\n')
        .map(para => `<p>${para.replace(/\n/g, '<br>')}</p>`)
        .join('');

    draftDetailBody.innerHTML = bodyHtml;

    draftDetailOverlay.classList.add('active');
};

function closeDraftDetail() {
    draftDetailOverlay.classList.remove('active');
    currentDraftIndex = null;
}

window.sendDraft = async function (index) {
    const draft = AppState.drafts[index];
    if (!draft) return;

    showLoading();

    // Find contact for company info
    const contact = AppState.contacts.find(c => c.email.toLowerCase() === draft.email.toLowerCase());
    const company = contact?.company || '';

    try {
        // Try to use the backend API
        const response = await fetch(`${API_BASE}/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: draft.email, limit: 1 })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.sent && data.sent.length > 0) {
                const result = data.sent[0];
                if (result.status === 'sent') {
                    if (contact) contact.status = 'sent';
                    AppState.logs.unshift({
                        timestamp: new Date().toISOString(),
                        email: draft.email,
                        company: company,
                        status: 'SENT',
                        subject: result.subject || draft.subject,
                        error: ''
                    });
                    AppState.drafts.splice(index, 1);
                    addActivity('sent', `Email sent to ${draft.recipient}`, 'Just now');
                    hideLoading();
                    showToast('success', 'Email Sent', `Sent to ${draft.recipient} via API`);
                } else {
                    throw new Error(result.error || 'Failed to send');
                }
            }
        } else {
            throw new Error('API request failed');
        }
    } catch (error) {
        console.log('API not available, using simulation:', error.message);

        // Fallback to simulation
        await delay(800);
        if (contact) contact.status = 'sent';

        AppState.logs.unshift({
            timestamp: new Date().toISOString(),
            email: draft.email,
            company: company,
            status: 'SENT',
            subject: draft.subject,
            error: ''
        });

        AppState.drafts.splice(index, 1);
        addActivity('sent', `Email sent to ${draft.recipient}`, 'Just now');
        hideLoading();
        showToast('success', 'Email Sent', `Sent to ${draft.recipient} (simulation)`);
    }

    updateStats();
    renderDrafts();
    renderContacts();
    renderLogs();
    renderRecentActivity();
};

window.deleteDraft = function (index) {
    AppState.drafts.splice(index, 1);
    updateStats();
    renderDrafts();
    showToast('info', 'Draft Deleted', 'Draft has been removed');
};

async function sendAllDrafts() {
    showLoading();
    const count = AppState.drafts.length;

    for (let i = AppState.drafts.length - 1; i >= 0; i--) {
        await delay(500);
        await window.sendDraft(0);
    }

    hideLoading();
    showToast('success', 'All Sent', `Sent ${count} emails`);
}

// ========================================
// Logs
// ========================================

function setupLogsEvents() {
    elements.logsFilter.addEventListener('change', (e) => {
        renderLogs(e.target.value);
    });

    elements.exportLogsBtn.addEventListener('click', () => {
        exportLogsCSV();
    });
}

function renderLogs(filter = 'all') {
    let logs = AppState.logs;

    if (filter !== 'all') {
        logs = logs.filter(l => l.status.toLowerCase() === filter.toLowerCase());
    }

    if (logs.length === 0) {
        elements.logsTableBody.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                </div>
                <h3>No logs found</h3>
                <p>Activity will appear here after sending emails</p>
            </div>
        `;
        return;
    }

    elements.logsTableBody.innerHTML = logs.map(log => {
        const statusClass = log.status === 'SENT' ? 'sent' : log.status === 'ERROR' ? 'error' : 'draft';
        const statusLabel = log.status === 'SENT' ? 'Sent' : log.status === 'ERROR' ? 'Error' : 'Draft';

        return `
            <div class="table-row">
                <span class="log-timestamp">${formatTimestamp(log.timestamp)}</span>
                <span class="contact-email">${log.email}</span>
                <span class="contact-company">${log.company}</span>
                <span class="contact-status ${statusClass}">${statusLabel}</span>
                <span class="${log.error ? 'log-error' : ''}">${log.error || log.subject}</span>
            </div>
        `;
    }).join('');
}

function exportLogsCSV() {
    const headers = ['Timestamp', 'Email', 'Company', 'Status', 'Subject', 'Error'];
    const rows = AppState.logs.map(log => [
        log.timestamp,
        log.email,
        log.company,
        log.status,
        log.subject,
        log.error
    ]);

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `outreach_logs_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();

    URL.revokeObjectURL(url);
    showToast('success', 'Export Complete', 'Logs exported to CSV');
}

// ========================================
// Settings
// ========================================

function setupSettingsEvents() {
    elements.saveSettingsBtn.addEventListener('click', saveSettings);
}

function populateSettings() {
    elements.settingsName.value = AppState.config.your_name || '';
    elements.settingsEmail.value = AppState.config.your_email || '';
    elements.settingsSchool.value = AppState.config.your_school || '';
    elements.settingsMajor.value = AppState.config.your_major || '';
    elements.settingsPitch.value = AppState.config.your_pitch || '';
    elements.settingsGoal.value = AppState.config.target_goal || '';

    // Update user profile
    if (AppState.config.your_name) {
        elements.userName.textContent = AppState.config.your_name;
        const initials = AppState.config.your_name.split(' ').map(n => n[0]).join('');
        elements.userAvatar.textContent = initials;
    }
}

async function saveSettings() {
    // Preserve existing config fields and update with form values
    const updatedConfig = {
        ...AppState.config,  // Preserve existing fields like your_phone, your_title, etc.
        your_name: elements.settingsName.value,
        your_email: elements.settingsEmail.value,
        your_school: elements.settingsSchool.value,
        your_major: elements.settingsMajor.value,
        your_pitch: elements.settingsPitch.value,
        target_goal: elements.settingsGoal.value
    };

    showLoading();

    try {
        // Try to persist to backend
        const response = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedConfig)
        });

        if (response.ok) {
            AppState.config = updatedConfig;

            // Update user profile
            elements.userName.textContent = AppState.config.your_name;
            const initials = AppState.config.your_name.split(' ').map(n => n[0]).join('');
            elements.userAvatar.textContent = initials;

            hideLoading();
            showToast('success', 'Settings Saved', 'Your preferences have been saved to the server');
        } else {
            const data = await response.json();
            hideLoading();
            showToast('error', 'Save Failed', data.error || 'Could not save settings');
        }
    } catch (error) {
        console.log('API not available, saving locally only:', error.message);

        // Fallback: save to local state only
        AppState.config = updatedConfig;

        // Update user profile
        elements.userName.textContent = AppState.config.your_name;
        const initials = AppState.config.your_name.split(' ').map(n => n[0]).join('');
        elements.userAvatar.textContent = initials;

        hideLoading();
        showToast('success', 'Settings Saved', 'Saved locally (backend unavailable)');
    }
}

// ========================================
// Search
// ========================================

function setupSearchEvents() {
    elements.globalSearch.addEventListener('input', debounce((e) => {
        const query = e.target.value.trim();

        if (AppState.currentSection === 'contacts') {
            renderContacts(query);
        } else if (query) {
            // Switch to contacts and filter
            navigateTo('contacts');
            renderContacts(query);
        }
    }, 300));
}

// ========================================
// Modal
// ========================================

let modalCallback = null;

function setupModalEvents() {
    elements.modalClose.addEventListener('click', closeModal);
    elements.modalCancel.addEventListener('click', closeModal);
    elements.modalOverlay.addEventListener('click', (e) => {
        if (e.target === elements.modalOverlay) closeModal();
    });
    elements.modalConfirm.addEventListener('click', () => {
        const callback = modalCallback; // Save callback before closing
        closeModal();
        if (callback) callback(); // Execute after modal is closed
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.modalOverlay.classList.contains('active')) {
            closeModal();
        }
    });
}

function showModal(title, message, note, confirmText, callback) {
    elements.modalTitle.textContent = title;
    elements.modalMessage.innerHTML = message;
    elements.modalNote.textContent = note;
    elements.modalConfirmText.textContent = confirmText;
    modalCallback = callback;
    elements.modalOverlay.classList.add('active');
}

function closeModal() {
    elements.modalOverlay.classList.remove('active');
    modalCallback = null;
}

// ========================================
// Toast Notifications
// ========================================

function showToast(type, title, message) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<polyline points="20 6 9 17 4 12"/>',
        error: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
        warning: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
    };

    toast.innerHTML = `
        <div class="toast-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${icons[type]}</svg>
        </div>
        <div class="toast-content">
            <span class="toast-title">${title}</span>
            <span class="toast-message">${message}</span>
        </div>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(50px); }
    }
`;
document.head.appendChild(style);

// ========================================
// Loading
// ========================================

function showLoading() {
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

// ========================================
// Utility Functions
// ========================================

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = (now - date) / 1000 / 60; // minutes

    if (diff < 1) return 'Just now';
    if (diff < 60) return `${Math.floor(diff)} min ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)} hours ago`;
    return date.toLocaleDateString();
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ========================================
// Console Welcome
// ========================================

console.log('%c🚀 Outreach Dashboard', 'font-size: 20px; font-weight: bold; color: #0891b2;');
console.log('%cAI-Powered Email Campaigns', 'font-size: 12px; color: #06b6d4;');
