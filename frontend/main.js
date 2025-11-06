// frontend/main.js
const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');

let backendProcess = null;

// The Django URL we expect to load
const DJANGO_URL = 'http://127.0.0.1:8000';
const MAX_WAIT_MS = 30000; // 30 seconds max wait

// Helper: find manage.py dynamically
function findManagePy() {
  const candidate = path.join(__dirname, '..', 'backend', 'manage.py');
  if (fs.existsSync(candidate)) return candidate;
  dialog.showErrorBox('manage.py not found', `Expected at: ${candidate}`);
  return null;
}

// Helper: start backend process
function startBackend() {
  const managePy = findManagePy();
  if (!managePy) return;

  // Prefer using your local venv Python if available
  const venvPython = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe');
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python';

  const manageDir = path.dirname(managePy);
  console.log(`[INFO] Starting Django backend from: ${manageDir}`);

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

// Helper: wait for Django to start before opening window
function waitForServer(url, timeoutMs = MAX_WAIT_MS) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function check() {
      const req = http.get(url, (res) => {
        if (res.statusCode < 500) {
          res.destroy();
          return resolve(true);
        }
      });
      req.on('error', () => {
        if (Date.now() - start > timeoutMs) {
          return reject(new Error('Timeout waiting for backend to start'));
        }
        setTimeout(check, 500);
      });
    }
    check();
  });
}

// Create Electron window
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
  // win.webContents.openDevTools(); // enable for debugging

  win.on('closed', () => {
    if (backendProcess) {
      console.log('[INFO] Terminating backend process...');
      backendProcess.kill();
    }
  });
}

app.whenReady().then(async () => {
  // Start backend
  startBackend();

  try {
    console.log('[INFO] Waiting for Django backend to respond...');
    await waitForServer(DJANGO_URL);
    console.log('[INFO] Django backend ready. Launching window.');
  } catch (err) {
    console.error('[ERROR] Django did not start in time:', err.message);
    dialog.showErrorBox('Backend Error', 'Django backend failed to start in time.');
  }

  // Open window whether backend started or not (for dev)
  createWindow();
});

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});