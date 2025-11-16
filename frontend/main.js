// frontend/main.js (robust, verbose, fallback)
const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');

let backendProcess = null;
const DJANGO_URL = 'http://127.0.0.1:8000';
const MAX_WAIT_MS = 120000; // 120 seconds
const MAX_ATTEMPTS = 60; // fallback after this many attempts (attempt every 2s)
const ATTEMPT_INTERVAL = 2000;

function findManagePy() {
  const candidate = path.join(__dirname, '..', 'backend', 'manage.py');
  if (fs.existsSync(candidate)) return candidate;
  console.warn('manage.py not found at', candidate);
  return null;
}

function startBackend() {
  const managePy = findManagePy();
  if (!managePy) {
    console.warn('No manage.py — assuming backend started manually.');
    return;
  }
  const venvPython = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe');
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python';
  const manageDir = path.dirname(managePy);

  backendProcess = spawn(pythonCmd, [managePy, 'runserver', '127.0.0.1:8000'], {
    cwd: manageDir,
    shell: false,
    env: process.env,
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });
  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend-err] ${data.toString().trim()}`);
  });
  backendProcess.on('close', (code) => {
    console.log(`[backend] exited with code ${code}`);
  });
}

function waitForServer(url, timeoutMs = MAX_WAIT_MS) {
  const start = Date.now();
  let attempts = 0;
  return new Promise((resolve, reject) => {
    function attempt() {
      attempts++;
      const req = http.get(url, (res) => {
        const code = res.statusCode;
        console.log(`[checker] got status ${code} on attempt ${attempts}`);
        res.destroy();
        // consider 2xx and 3xx as success
        if (code >= 200 && code < 400) return resolve(true);
        // otherwise keep waiting until timeout/fallback
        if (Date.now() - start > timeoutMs || attempts >= MAX_ATTEMPTS) {
          return reject(new Error('Timeout waiting for backend; last status ' + code));
        } else {
          setTimeout(attempt, ATTEMPT_INTERVAL);
        }
      });
      req.on('error', (err) => {
        console.log(`[checker] attempt ${attempts} - error: ${err.message}`);
        if (Date.now() - start > timeoutMs || attempts >= MAX_ATTEMPTS) {
          return reject(new Error('Timeout waiting for backend (network error)'));
        } else {
          setTimeout(attempt, ATTEMPT_INTERVAL);
        }
      });
    }
    attempt();
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadURL(DJANGO_URL);
  // win.webContents.openDevTools();
  win.on('closed', () => {
    if (backendProcess) {
      try { backendProcess.kill(); } catch (e) {}
    }
  });
}

app.whenReady().then(async () => {
  // START BACKEND: comment out startBackend() if you prefer to start Django manually
  try {
    startBackend();
  } catch (e) {
    console.warn('[INFO] startBackend failed:', e && e.message);
  }

  try {
    console.log('[INFO] Waiting up to', MAX_WAIT_MS / 1000, 's for Django...');
    await waitForServer(DJANGO_URL, MAX_WAIT_MS);
    console.log('[INFO] Backend responded — launching window.');
    createWindow();
  } catch (err) {
    console.warn('[WARN] Backend did not respond in time:', err.message);
    // As a developer convenience, open the window anyway so you can inspect frontend or devtools
    const choice = dialog.showMessageBoxSync({
      type: 'warning',
      buttons: ['Open anyway', 'Cancel'],
      defaultId: 0,
      message: 'Backend did not respond within the timeout.',
      detail: 'You can open the app window anyway (useful for frontend work), or cancel to troubleshoot the backend.',
    });
    if (choice === 0) {
      createWindow();
    } else {
      console.log('[INFO] User chose to cancel launching the window.');
    }
  }
});

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});