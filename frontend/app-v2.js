/**
 * Resonate v2 - AI Outreach Platform
 * 
 * Frontend JavaScript for the redesigned, intuitive UI
 * Featuring Apollo.io contact discovery and campaign management
 */

// ========================================
// Configuration & State
// ========================================

const getApiBaseUrl = () => {
    if (window.location.hostname.includes('onrender.com')) {
        return window.location.origin + '/api';
    }
    const customApiUrl = localStorage.getItem('apiBaseUrl');
    if (customApiUrl) {
        return customApiUrl;
    }
    return 'http://localhost:5000/api';
};

const API_BASE = getApiBaseUrl();

// Application State
const AppState = {
    user: null,
    token: localStorage.getItem('authToken'),
    contacts: [],
    searchResults: [],
    selectedContacts: new Set(),
    currentSection: 'discover',
    apolloConfigured: false,
};

// ========================================
// Utility Functions
// ========================================

function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const iconMap = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent-success)"><polyline points="20 6 9 17 4 12"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent-error)"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent-info)"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    };

    toast.innerHTML = `
        <div class="toast-icon">${iconMap[type]}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            ${message ? `<div class="toast-message">${message}</div>` : ''}
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getInitials(firstName, lastName) {
    return ((firstName?.[0] || '') + (lastName?.[0] || '')).toUpperCase() || '?';
}

async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (AppState.token) {
        headers['Authorization'] = `Bearer ${AppState.token}`;
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ========================================
// Authentication
// ========================================

async function checkAuth() {
    if (!AppState.token) {
        window.location.href = 'login.html';
        return false;
    }

    try {
        const userData = await apiRequest('/auth/me');
        AppState.user = userData;
        updateUserUI();
        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('authToken');
        window.location.href = 'login.html';
        return false;
    }
}

function updateUserUI() {
    if (AppState.user) {
        const name = AppState.user.name || AppState.user.email;
        document.getElementById('userName').textContent = name;
        document.getElementById('userAvatar').textContent = getInitials(
            name.split(' ')[0],
            name.split(' ')[1]
        );
    }
}

function logout() {
    localStorage.removeItem('authToken');
    AppState.token = null;
    AppState.user = null;
    window.location.href = 'login.html';
}

// ========================================
// Navigation
// ========================================

function navigateTo(section) {
    // Update sidebar
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === section) {
            item.classList.add('active');
        }
    });

    // Update sections
    document.querySelectorAll('.section-page').forEach(page => {
        page.classList.remove('active');
    });

    const sectionElement = document.getElementById(`${section}Section`);
    if (sectionElement) {
        sectionElement.classList.add('active');
    }

    // Update header
    const titles = {
        discover: { title: 'Find Contacts', subtitle: "Search 270M+ professionals with Apollo.io" },
        contacts: { title: 'My Contacts', subtitle: 'Manage your contact list' },
        campaigns: { title: 'Campaigns', subtitle: 'Create and launch email campaigns' },
        activity: { title: 'Activity', subtitle: 'View email logs and campaign history' },
        settings: { title: 'Settings', subtitle: 'Configure your account and integrations' },
    };

    const info = titles[section] || { title: section, subtitle: '' };
    document.getElementById('pageTitle').textContent = info.title;
    document.getElementById('pageSubtitle').textContent = info.subtitle;

    AppState.currentSection = section;

    // Load section-specific data
    if (section === 'contacts') {
        loadContacts();
    } else if (section === 'activity') {
        loadActivity();
    }
}

// ========================================
// Apollo Search
// ========================================

async function checkApolloStatus() {
    try {
        const status = await apiRequest('/v2/apollo/status');
        AppState.apolloConfigured = status.configured;

        const statusEl = document.getElementById('apolloStatus');
        if (status.configured) {
            statusEl.innerHTML = '<span style="color:var(--accent-success)">● Connected</span>';
        } else {
            statusEl.innerHTML = '<span style="color:var(--accent-warning)">● Not Configured</span>';
            showToast('Apollo Not Configured', 'Add APOLLO_API_KEY to enable contact search', 'info');
        }
    } catch (error) {
        console.error('Apollo status check failed:', error);
        document.getElementById('apolloStatus').innerHTML = '<span style="color:var(--accent-error)">● Error</span>';
    }
}

async function searchContacts(e) {
    e?.preventDefault();

    const company = document.getElementById('searchCompany').value.trim();
    const title = document.getElementById('searchTitle').value.trim();
    const location = document.getElementById('searchLocation').value.trim();
    const seniority = document.getElementById('searchSeniority').value;
    const limit = parseInt(document.getElementById('searchLimit').value);
    const companySize = document.getElementById('searchCompanySize').value;

    if (!company && !title && !location) {
        showToast('Search Required', 'Please enter at least a company, title, or location', 'error');
        return;
    }

    // Show loading state
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('loadingState').style.display = 'block';

    try {
        const payload = { limit };

        if (company) payload.company = company;
        if (title) payload.jobTitles = title.split(',').map(t => t.trim());
        if (location) payload.locations = [location];
        if (seniority) payload.seniority = [seniority];
        if (companySize) payload.companySizes = [companySize];

        const results = await apiRequest('/v2/apollo/search', {
            method: 'POST',
            body: JSON.stringify(payload),
        });

        AppState.searchResults = results.contacts || [];
        AppState.selectedContacts.clear();
        updateSelectionBar();

        renderSearchResults(AppState.searchResults, results.total);

        if (AppState.searchResults.length > 0) {
            showToast('Search Complete', `Found ${results.total} contacts`, 'success');
        } else {
            showToast('No Results', 'Try adjusting your search criteria', 'info');
        }

    } catch (error) {
        showToast('Search Failed', error.message, 'error');
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('emptyState').style.display = 'flex';
    }
}

function renderSearchResults(contacts, total) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';

    document.getElementById('resultsCount').textContent = `${total} contacts found`;

    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';

    if (contacts.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="8" y1="12" x2="16" y2="12"/>
                    </svg>
                </div>
                <h3>No Contacts Found</h3>
                <p>Try broadening your search criteria or searching a different company.</p>
            </div>
        `;
        return;
    }

    contacts.forEach((contact, index) => {
        const card = document.createElement('div');
        card.className = 'contact-card';
        card.dataset.index = index;

        if (AppState.selectedContacts.has(index)) {
            card.classList.add('selected');
        }

        const hasEmail = contact.email && contact.email.includes('@');
        const hasLinkedIn = contact.linkedin_url;

        card.innerHTML = `
            <div class="select-checkbox"></div>
            <div class="contact-avatar">${getInitials(contact.first_name, contact.last_name)}</div>
            <div class="contact-info">
                <div class="contact-name">${contact.first_name} ${contact.last_name}</div>
                <div class="contact-title">${contact.job_title || 'Unknown Title'}</div>
                <div class="contact-company">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;">
                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                    </svg>
                    ${contact.company || 'Unknown Company'}
                </div>
                <div class="contact-meta">
                    ${hasEmail ? '<span class="contact-tag has-email">✓ Email</span>' : '<span class="contact-tag">No Email</span>'}
                    ${hasLinkedIn ? '<span class="contact-tag has-linkedin">LinkedIn</span>' : ''}
                    ${contact.city ? `<span class="contact-tag">${contact.city}</span>` : ''}
                </div>
            </div>
        `;

        card.addEventListener('click', () => toggleContactSelection(index));

        grid.appendChild(card);
    });
}

function toggleContactSelection(index) {
    if (AppState.selectedContacts.has(index)) {
        AppState.selectedContacts.delete(index);
    } else {
        AppState.selectedContacts.add(index);
    }

    // Update card UI
    const card = document.querySelector(`.contact-card[data-index="${index}"]`);
    if (card) {
        card.classList.toggle('selected', AppState.selectedContacts.has(index));
    }

    updateSelectionBar();
}

function updateSelectionBar() {
    const bar = document.getElementById('selectionBar');
    const count = AppState.selectedContacts.size;

    document.getElementById('selectedCount').textContent = count;

    if (count > 0) {
        bar.classList.add('visible');
    } else {
        bar.classList.remove('visible');
    }
}

function clearSelection() {
    AppState.selectedContacts.clear();

    document.querySelectorAll('.contact-card.selected').forEach(card => {
        card.classList.remove('selected');
    });

    updateSelectionBar();
}

async function importSelectedContacts() {
    if (AppState.selectedContacts.size === 0) {
        showToast('No Selection', 'Please select contacts to import', 'error');
        return;
    }

    const selectedData = Array.from(AppState.selectedContacts).map(i => AppState.searchResults[i]);

    let imported = 0;
    let errors = 0;

    for (const contact of selectedData) {
        try {
            await apiRequest('/v2/contacts', {
                method: 'POST',
                body: JSON.stringify({
                    firstName: contact.first_name,
                    lastName: contact.last_name,
                    email: contact.email,
                    company: contact.company,
                    jobTitle: contact.job_title,
                    city: contact.city,
                    state: contact.state,
                    linkedinUrl: contact.linkedin_url,
                    notes: `Imported from Apollo.io | ${contact.industry || ''}`,
                }),
            });
            imported++;
        } catch (error) {
            errors++;
            console.error('Import error:', error);
        }
    }

    if (imported > 0) {
        showToast('Import Complete', `${imported} contacts imported successfully`, 'success');
    }

    if (errors > 0) {
        showToast('Some Failed', `${errors} contacts failed to import (may be duplicates)`, 'error');
    }

    clearSelection();
}

function clearSearchForm() {
    document.getElementById('searchCompany').value = '';
    document.getElementById('searchTitle').value = '';
    document.getElementById('searchLocation').value = '';
    document.getElementById('searchSeniority').value = '';
    document.getElementById('searchLimit').value = '25';
    document.getElementById('searchCompanySize').value = '';
}

// ========================================
// Contacts Management
// ========================================

async function loadContacts() {
    try {
        const data = await apiRequest('/v2/contacts');
        AppState.contacts = data.contacts || [];
        renderContactsTable();
        updateCampaignStats();
    } catch (error) {
        console.error('Failed to load contacts:', error);
        showToast('Error', 'Failed to load contacts', 'error');
    }
}

function renderContactsTable() {
    const tbody = document.getElementById('contactsTableBody');
    tbody.innerHTML = '';

    if (AppState.contacts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:var(--space-xl);color:var(--text-muted);">
                    No contacts yet. Use the Find Contacts feature to discover prospects.
                </td>
            </tr>
        `;
        return;
    }

    AppState.contacts.forEach(contact => {
        const tr = document.createElement('tr');

        const statusClass = {
            pending: 'pending',
            sent: 'sent',
            'no-email': 'no-email',
        }[contact.status] || 'pending';

        tr.innerHTML = `
            <td><input type="checkbox" class="contact-checkbox" data-id="${contact.id}"></td>
            <td>
                <div style="display:flex;align-items:center;gap:var(--space-sm);">
                    <div class="avatar" style="width:32px;height:32px;font-size:12px;">${getInitials(contact.firstName, contact.lastName)}</div>
                    <span>${contact.firstName} ${contact.lastName}</span>
                </div>
            </td>
            <td>${contact.email || '<span style="color:var(--text-muted)">—</span>'}</td>
            <td>${contact.company || '—'}</td>
            <td>${contact.jobTitle || '—'}</td>
            <td><span class="status-badge ${statusClass}">${contact.status}</span></td>
            <td>
                <button class="btn btn-secondary" style="padding:4px 8px;font-size:12px;" onclick="deleteContact(${contact.id})">
                    Delete
                </button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

async function deleteContact(id) {
    if (!confirm('Are you sure you want to delete this contact?')) return;

    try {
        await apiRequest(`/v2/contacts/${id}`, { method: 'DELETE' });
        showToast('Deleted', 'Contact removed', 'success');
        loadContacts();
    } catch (error) {
        showToast('Error', 'Failed to delete contact', 'error');
    }
}

// ========================================
// Campaigns
// ========================================

function updateCampaignStats() {
    const total = AppState.contacts.length;
    const withEmail = AppState.contacts.filter(c => c.email && c.email.includes('@')).length;
    const contacted = AppState.contacts.filter(c => c.status === 'sent').length;
    const pending = AppState.contacts.filter(c => c.status === 'pending' && c.email).length;

    document.getElementById('campaignTotalContacts').textContent = total;
    document.getElementById('campaignWithEmail').textContent = withEmail;
    document.getElementById('campaignContacted').textContent = contacted;

    // Update dropdown
    const dropdown = document.getElementById('campaignContacts');
    dropdown.innerHTML = `
        <option value="all">All Pending Contacts (${pending})</option>
        <option value="selected">Selected Contacts (0)</option>
    `;
}

async function previewCampaign() {
    const name = document.getElementById('campaignName').value;
    const style = document.getElementById('emailStyle').value;
    const goal = document.getElementById('campaignGoal').value;

    if (!name) {
        showToast('Required', 'Please enter a campaign name', 'error');
        return;
    }

    showToast('Coming Soon', 'Email preview feature coming soon!', 'info');
}

async function launchCampaign() {
    const name = document.getElementById('campaignName').value;
    const contactsOption = document.getElementById('campaignContacts').value;

    if (!name) {
        showToast('Required', 'Please enter a campaign name', 'error');
        return;
    }

    const pending = AppState.contacts.filter(c => c.status === 'pending' && c.email);

    if (pending.length === 0) {
        showToast('No Contacts', 'No pending contacts to email', 'error');
        return;
    }

    if (!confirm(`Launch campaign to ${pending.length} contacts?`)) return;

    showToast('Coming Soon', 'Campaign launch feature coming soon!', 'info');
}

// ========================================
// Activity / Logs
// ========================================

async function loadActivity() {
    try {
        const data = await apiRequest('/logs');
        renderActivityList(data.logs || []);
    } catch (error) {
        console.error('Failed to load activity:', error);
    }
}

function renderActivityList(logs) {
    const list = document.getElementById('activityList');

    if (logs.length === 0) {
        list.innerHTML = `
            <div style="text-align:center;padding:var(--space-xl);color:var(--text-muted);">
                No activity yet. Launch a campaign to see logs here.
            </div>
        `;
        return;
    }

    list.innerHTML = logs.slice(0, 50).map(log => `
        <div class="activity-item">
            <div class="activity-icon" style="background:${log.status === 'sent' ? 'var(--accent-success-light)' : 'var(--accent-error-light)'};">
                <svg viewBox="0 0 24 24" fill="none" stroke="${log.status === 'sent' ? 'var(--accent-success)' : 'var(--accent-error)'}" stroke-width="2">
                    ${log.status === 'sent'
            ? '<polyline points="20 6 9 17 4 12"/>'
            : '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'}
                </svg>
            </div>
            <div style="flex:1;">
                <div style="font-weight:500;">${log.email}</div>
                <div style="font-size:var(--font-size-xs);color:var(--text-tertiary);">
                    ${log.company} • ${log.timestamp}
                </div>
            </div>
            <span class="status-badge ${log.status}">${log.status}</span>
        </div>
    `).join('');
}

// ========================================
// Initialization
// ========================================

async function init() {
    // Check authentication first
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) return;

    // Set up navigation
    document.querySelectorAll('.nav-item[data-section]').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(item.dataset.section);
        });
    });

    // Set up logout
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
        e.preventDefault();
        logout();
    });

    // Set up Apollo search
    document.getElementById('apolloSearchForm').addEventListener('submit', searchContacts);
    document.getElementById('clearSearchBtn').addEventListener('click', clearSearchForm);

    // Set up selection bar actions
    document.getElementById('clearSelectionBtn').addEventListener('click', clearSelection);
    document.getElementById('importSelectedBtn').addEventListener('click', importSelectedContacts);

    // Set up campaign actions
    document.getElementById('previewCampaignBtn').addEventListener('click', previewCampaign);
    document.getElementById('launchCampaignBtn').addEventListener('click', launchCampaign);

    // Check Apollo status
    await checkApolloStatus();

    // Load initial data
    await loadContacts();

    console.log('🚀 Resonate v2 initialized');
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
