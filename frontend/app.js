/**
 * Text-to-Video Studio -- Client Application
 * Handles auth, generation, polling, gallery, and UI interactions.
 */

const API = '';  // Same-origin

/** Helper: append auth token as query param for media URLs */
function mediaUrl(path, token) {
  const sep = path.includes('?') ? '&' : '?';
  return `${API}${path}${sep}token=${encodeURIComponent(token)}`;
}

class VideoStudioApp {
  constructor() {
    this.token = localStorage.getItem('token');
    this.user = JSON.parse(localStorage.getItem('user') || 'null');
    this.activeTaskId = null;
    this.pollInterval = null;

    this.initElements();
    this.initEvents();
    this.checkAuth();
  }

  // ─── Element References ───
  initElements() {
    // Auth
    this.authOverlay = document.getElementById('auth-overlay');
    this.loginForm = document.getElementById('login-form');
    this.registerForm = document.getElementById('register-form');
    this.authError = document.getElementById('auth-error');
    // App
    this.appEl = document.getElementById('app');
    this.gpuStatus = document.getElementById('gpu-status');
    this.headerUsername = document.getElementById('header-username');
    this.userAvatar = document.getElementById('user-avatar');
    // Prompt
    this.promptInput = document.getElementById('prompt-input');
    this.charCount = document.getElementById('char-count');
    this.generateBtn = document.getElementById('generate-btn');
    this.settingsToggle = document.getElementById('settings-toggle');
    this.settingsPanel = document.getElementById('settings-panel');
    // Settings
    this.resolutionSelect = document.getElementById('setting-resolution');
    this.durationRange = document.getElementById('setting-duration');
    this.stepsRange = document.getElementById('setting-steps');
    this.guidanceRange = document.getElementById('setting-guidance');
    this.durationValue = document.getElementById('duration-value');
    this.stepsValue = document.getElementById('steps-value');
    this.guidanceValue = document.getElementById('guidance-value');
    // Progress
    this.progressSection = document.getElementById('progress-section');
    this.progressBar = document.getElementById('progress-bar');
    this.progressPercent = document.getElementById('progress-percent');
    this.progressMessage = document.getElementById('progress-message');
    this.progressPrompt = document.getElementById('progress-prompt');
    // Player
    this.playerSection = document.getElementById('player-section');
    this.videoPlayer = document.getElementById('video-player');
    // Gallery
    this.galleryGrid = document.getElementById('gallery-grid');
    this.galleryEmpty = document.getElementById('gallery-empty');
    // Toast
    this.toastContainer = document.getElementById('toast-container');
  }

  // ─── Event Bindings ───
  initEvents() {
    // Auth
    this.loginForm.addEventListener('submit', e => { e.preventDefault(); this.handleLogin(); });
    this.registerForm.addEventListener('submit', e => { e.preventDefault(); this.handleRegister(); });
    document.getElementById('show-register').addEventListener('click', e => { e.preventDefault(); this.showForm('register'); });
    document.getElementById('show-login').addEventListener('click', e => { e.preventDefault(); this.showForm('login'); });
    document.getElementById('logout-btn').addEventListener('click', () => this.logout());

    // Prompt
    this.promptInput.addEventListener('input', () => { this.charCount.textContent = this.promptInput.value.length; });
    this.generateBtn.addEventListener('click', () => this.handleGenerate());

    // Settings
    this.settingsToggle.addEventListener('click', () => {
      this.settingsToggle.classList.toggle('open');
      this.settingsPanel.classList.toggle('open');
    });
    this.durationRange.addEventListener('input', () => { this.durationValue.textContent = this.durationRange.value + 's'; });
    this.stepsRange.addEventListener('input', () => { this.stepsValue.textContent = this.stepsRange.value; });
    this.guidanceRange.addEventListener('input', () => { this.guidanceValue.textContent = this.guidanceRange.value; });

    // Player
    document.getElementById('download-btn').addEventListener('click', () => this.downloadVideo());
    document.getElementById('new-video-btn').addEventListener('click', () => this.resetToPrompt());

    // Load saved settings
    this.loadSettings();
  }

  // ─── API Helper ───
  async api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const res = await fetch(`${API}${path}`, { ...options, headers });

    if (res.status === 401) {
      this.logout();
      throw new Error('Session expired');
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  // ═══════════════════════════════════════
  // AUTH
  // ═══════════════════════════════════════

  checkAuth() {
    if (this.token && this.user) {
      this.showApp();
    } else {
      this.showAuth();
    }
  }

  showAuth() {
    this.authOverlay.classList.remove('hidden');
    this.appEl.classList.add('hidden');
  }

  showApp() {
    this.authOverlay.classList.add('hidden');
    this.appEl.classList.remove('hidden');
    this.headerUsername.textContent = this.user.username;
    this.userAvatar.textContent = this.user.username.charAt(0).toUpperCase();
    this.checkHealth();
    this.loadGallery();
  }

  showForm(type) {
    this.authError.classList.remove('visible');
    if (type === 'register') {
      this.loginForm.classList.remove('active');
      this.registerForm.classList.add('active');
    } else {
      this.registerForm.classList.remove('active');
      this.loginForm.classList.add('active');
    }
  }

  showAuthError(msg) {
    this.authError.textContent = msg;
    this.authError.classList.add('visible');
    setTimeout(() => this.authError.classList.remove('visible'), 5000);
  }

  async handleLogin() {
    const btn = document.getElementById('login-btn');
    btn.classList.add('loading');
    try {
      const data = await this.api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          username: document.getElementById('login-username').value,
          password: document.getElementById('login-password').value,
        }),
      });
      this.setAuth(data);
    } catch (err) {
      this.showAuthError(err.message);
    } finally {
      btn.classList.remove('loading');
    }
  }

  async handleRegister() {
    const btn = document.getElementById('register-btn');
    btn.classList.add('loading');
    try {
      const data = await this.api('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          username: document.getElementById('reg-username').value,
          email: document.getElementById('reg-email').value,
          password: document.getElementById('reg-password').value,
        }),
      });
      this.setAuth(data);
    } catch (err) {
      this.showAuthError(err.message);
    } finally {
      btn.classList.remove('loading');
    }
  }

  setAuth(data) {
    this.token = data.access_token;
    this.user = data.user;
    localStorage.setItem('token', this.token);
    localStorage.setItem('user', JSON.stringify(this.user));
    this.showApp();
    this.toast('Welcome, ' + this.user.username + '!', 'success');
  }

  logout() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.stopPolling();
    this.showAuth();
  }

  // ═══════════════════════════════════════
  // HEALTH CHECK
  // ═══════════════════════════════════════

  async checkHealth() {
    try {
      const data = await this.api('/api/health');
      const el = this.gpuStatus;
      if (data.gpu_available) {
        el.classList.add('online');
        el.classList.remove('offline');
        el.querySelector('.status-text').textContent = data.gpu_name || 'GPU Ready';
      } else {
        el.classList.add('offline');
        el.classList.remove('online');
        el.querySelector('.status-text').textContent = 'CPU Mode';
      }
    } catch {
      this.gpuStatus.querySelector('.status-text').textContent = 'Offline';
    }
  }

  // ═══════════════════════════════════════
  // GENERATION
  // ═══════════════════════════════════════

  async handleGenerate() {
    const prompt = this.promptInput.value.trim();
    if (!prompt || prompt.length < 5) {
      this.toast('Please enter at least 5 characters', 'error');
      return;
    }

    this.generateBtn.disabled = true;
    this.saveSettings();

    try {
      const data = await this.api('/api/generate', {
        method: 'POST',
        body: JSON.stringify({
          prompt,
          scene_duration: parseFloat(this.durationRange.value),
          num_inference_steps: parseInt(this.stepsRange.value),
          guidance_scale: parseFloat(this.guidanceRange.value),
          resolution: parseInt(this.resolutionSelect.value),
        }),
      });

      this.activeTaskId = data.task_id;
      this.showProgress(prompt);
      this.startPolling();
      this.toast('Generation started!', 'success');

    } catch (err) {
      this.toast(err.message, 'error');
      this.generateBtn.disabled = false;
    }
  }

  showProgress(prompt) {
    this.progressSection.classList.remove('hidden');
    this.playerSection.classList.add('hidden');
    this.progressPrompt.textContent = prompt;
    this.updateProgressUI(0, 'Preparing pipeline...');
  }

  updateProgressUI(progress, message) {
    this.progressPercent.textContent = Math.round(progress) + '%';
    this.progressBar.querySelector('.progress-fill').style.width = progress + '%';
    this.progressMessage.textContent = message || '';
    const glow = this.progressBar.querySelector('.progress-glow');
    if (progress > 0) {
      glow.style.display = 'block';
      glow.style.left = `calc(${progress}% - 15px)`;
    }
  }

  startPolling() {
    this.stopPolling();
    this.pollInterval = setInterval(() => this.pollTask(), 2000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  async pollTask() {
    if (!this.activeTaskId) return;
    try {
      const task = await this.api(`/api/tasks/${this.activeTaskId}`);

      if (task.status === 'processing' || task.status === 'pending') {
        this.updateProgressUI(task.progress, task.progress_message);
      } else if (task.status === 'completed') {
        this.stopPolling();
        this.updateProgressUI(100, 'Video ready!');
        setTimeout(() => this.showVideo(task), 600);
        this.toast('Video generated successfully!', 'success');
        this.loadGallery();
      } else if (task.status === 'failed') {
        this.stopPolling();
        this.progressSection.classList.add('hidden');
        this.toast('Generation failed: ' + (task.error || 'Unknown error'), 'error');
        this.generateBtn.disabled = false;
      }
    } catch (err) {
      console.error('Poll error:', err);
    }
  }

  showVideo(task) {
    this.progressSection.classList.add('hidden');
    this.playerSection.classList.remove('hidden');

    const videoUrl = mediaUrl(task.video_url, this.token);
    this.videoPlayer.src = videoUrl;
    this.videoPlayer.load();
    this.generateBtn.disabled = false;
  }

  downloadVideo() {
    if (!this.activeTaskId) return;
    const url = mediaUrl(`/api/tasks/${this.activeTaskId}/video`, this.token);
    const filename = `video_${this.activeTaskId.slice(0, 8)}.mp4`;

    fetch(url)
      .then(r => r.blob())
      .then(blob => {
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(blobUrl);
      })
      .catch(() => this.toast('Download failed', 'error'));
  }

  resetToPrompt() {
    this.playerSection.classList.add('hidden');
    this.progressSection.classList.add('hidden');
    this.activeTaskId = null;
    this.promptInput.value = '';
    this.charCount.textContent = '0';
    this.promptInput.focus();
  }

  // ═══════════════════════════════════════
  // GALLERY
  // ═══════════════════════════════════════

  async loadGallery() {
    try {
      const tasks = await this.api('/api/tasks');
      this.renderGallery(tasks);
    } catch {
      // Silent fail for gallery
    }
  }

  renderGallery(tasks) {
    if (!tasks.length) {
      this.galleryGrid.innerHTML = '';
      this.galleryEmpty.classList.remove('hidden');
      return;
    }

    this.galleryEmpty.classList.add('hidden');
    this.galleryGrid.innerHTML = tasks.map(t => {
      const thumbHtml = t.thumbnail_url
        ? `<img class="gallery-thumb" src="${mediaUrl(t.thumbnail_url, this.token)}" alt="Thumbnail" loading="lazy">`
        : `<div class="gallery-thumb-placeholder">V</div>`;

      const date = new Date(t.created_at).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });

      return `
        <div class="gallery-item" data-id="${t.id}" data-status="${t.status}">
          ${thumbHtml}
          <div class="gallery-info">
            <p class="gallery-prompt">${this.escapeHtml(t.prompt)}</p>
            <div class="gallery-meta">
              <span class="gallery-status ${t.status}">${t.status}</span>
              <span>${date}</span>
              <button class="gallery-delete-btn" data-id="${t.id}" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Click handlers
    this.galleryGrid.querySelectorAll('.gallery-item').forEach(item => {
      item.addEventListener('click', e => {
        if (e.target.closest('.gallery-delete-btn')) return;
        const id = item.dataset.id;
        const status = item.dataset.status;
        if (status === 'completed') {
          this.activeTaskId = id;
          this.api(`/api/tasks/${id}`).then(t => this.showVideo(t));
        } else if (status === 'processing' || status === 'pending') {
          this.activeTaskId = id;
          this.showProgress('');
          this.startPolling();
        }
      });
    });

    this.galleryGrid.querySelectorAll('.gallery-delete-btn').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (confirm('Delete this video?')) {
          try {
            await this.api(`/api/tasks/${id}`, { method: 'DELETE' });
            this.toast('Deleted', 'info');
            this.loadGallery();
          } catch (err) {
            this.toast(err.message, 'error');
          }
        }
      });
    });
  }

  // ═══════════════════════════════════════
  // SETTINGS PERSISTENCE
  // ═══════════════════════════════════════

  saveSettings() {
    localStorage.setItem('settings', JSON.stringify({
      resolution: this.resolutionSelect.value,
      duration: this.durationRange.value,
      steps: this.stepsRange.value,
      guidance: this.guidanceRange.value,
    }));
  }

  loadSettings() {
    try {
      const s = JSON.parse(localStorage.getItem('settings'));
      if (s) {
        this.resolutionSelect.value = s.resolution || '768';
        this.durationRange.value = s.duration || '3';
        this.stepsRange.value = s.steps || '30';
        this.guidanceRange.value = s.guidance || '7.5';
        this.durationValue.textContent = this.durationRange.value + 's';
        this.stepsValue.textContent = this.stepsRange.value;
        this.guidanceValue.textContent = this.guidanceRange.value;
      }
    } catch { /* ignore */ }
  }

  // ═══════════════════════════════════════
  // TOAST
  // ═══════════════════════════════════════

  toast(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    this.toastContainer.appendChild(el);
    setTimeout(() => { el.classList.add('fadeout'); setTimeout(() => el.remove(), 300); }, 4000);
  }

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// ─── Initialize ───
document.addEventListener('DOMContentLoaded', () => {
  window.app = new VideoStudioApp();
});
