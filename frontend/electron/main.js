const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron')
const path = require('path')
const fs = require('fs')
const os = require('os')
const { spawn, execSync } = require('child_process')
const http = require('http')

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL
let mainWindow
let backendProcess

// In production, the PyInstaller binary is bundled inside the .app under Resources/.
// In dev, fall back to the pip-installed CLI entry point.
function getBackendBinaryPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'declutter-api-bin')
  }
  return 'declutter-api'
}

function getLogPath() {
  return path.join(app.getPath('userData'), 'claire-api.log')
}

function startBackend() {
  const bin = getBackendBinaryPath()

  if (app.isPackaged) {
    try { fs.chmodSync(bin, 0o755) } catch (_) {}
  }

  const logPath = getLogPath()
  fs.mkdirSync(path.dirname(logPath), { recursive: true })
  const logFd = fs.openSync(logPath, 'a')

  backendProcess = spawn(bin, [], {
    shell: !app.isPackaged,
    stdio: ['ignore', logFd, logFd],
    detached: false,
  })

  backendProcess.on('error', (err) => {
    dialog.showErrorBox(
      'Claire — Backend Error',
      `Could not start the Claire API.\n\nDetails: ${err.message}\n\nLog: ${getLogPath()}`
    )
  })
}

// Poll localhost:8000 until the backend is ready, then call onReady().
// Gives up after maxAttempts and shows an error dialog.
function waitForBackend(onReady, attempt = 0, maxAttempts = 30) {
  http.get('http://localhost:8000/', (res) => {
    if (res.statusCode === 200) {
      onReady()
    } else {
      retryOrFail(onReady, attempt, maxAttempts)
    }
  }).on('error', () => {
    retryOrFail(onReady, attempt, maxAttempts)
  })
}

function retryOrFail(onReady, attempt, maxAttempts) {
  if (attempt >= maxAttempts) {
    dialog.showErrorBox(
      'Claire — Startup Timeout',
      `The Claire API did not start within 15 seconds.\n\nCheck the log for details:\n${getLogPath()}`
    )
    return
  }
  setTimeout(() => waitForBackend(onReady, attempt + 1, maxAttempts), 500)
}

// Check available disk space on the home volume.
// Returns free bytes.
function getFreeDiskBytes() {
  try {
    const out = execSync('df -k ~', { encoding: 'utf8' })
    const line = out.trim().split('\n')[1]
    const freeKB = parseInt(line.trim().split(/\s+/)[3], 10)
    return freeKB * 1024
  } catch (_) {
    return Infinity
  }
}

// Check if Ollama is installed and gemma3:4b is pulled.
// Writes ~/.declutter/ollama_ready when both are confirmed so future launches skip this.
async function checkOllama() {
  const flagPath = path.join(app.getPath('home'), '.declutter', 'ollama_ready')
  if (fs.existsSync(flagPath)) return

  // Disk space check — need at least 3GB for Ollama + gemma3:4b
  const MIN_DISK_BYTES = 3 * 1024 * 1024 * 1024
  const freeDisk = getFreeDiskBytes()
  if (freeDisk < MIN_DISK_BYTES) {
    const freeGB = (freeDisk / (1024 * 1024 * 1024)).toFixed(1)
    await dialog.showMessageBox({
      type: 'warning',
      title: 'Claire — Low Disk Space',
      message: 'Not enough disk space',
      detail:
        `Claire needs ~3 GB to download the Gemma 3 AI model.\n\n` +
        `Your disk has ${freeGB} GB free. Please free up some space and relaunch Claire.`,
      buttons: ['OK'],
    })
    return
  }

  // Step 1: is Ollama installed?
  let ollamaInstalled = false
  try {
    execSync('ollama --version', { stdio: 'ignore' })
    ollamaInstalled = true
  } catch (_) {}

  if (!ollamaInstalled) {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Claire — Local AI Setup',
      message: 'Install Ollama for local AI processing',
      detail:
        'Claire uses Gemma 3 to classify your files locally — your content never leaves your device.\n\n' +
        'Ollama is not installed. You can install it now, or continue using cloud mode (Google AI API).',
      buttons: ['Download Ollama', 'Use Cloud Mode'],
      defaultId: 0,
    })
    if (response === 0) {
      shell.openExternal('https://ollama.com/download')
    }
    return
  }

  // Step 2: is gemma3:4b pulled?
  let modelReady = false
  try {
    const list = execSync('ollama list', { encoding: 'utf8' })
    modelReady = list.includes('gemma3:4b') || list.includes('gemma3')
  } catch (_) {}

  if (!modelReady) {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Claire — Downloading Gemma 3',
      message: 'Download Gemma 3 model (~2.7 GB)',
      detail:
        'Claire needs to download the Gemma 3 model once for local AI processing.\n\n' +
        'This takes a few minutes on a typical connection. You can skip this and use cloud mode instead.',
      buttons: ['Download Now', 'Use Cloud Mode'],
      defaultId: 0,
    })
    if (response === 1) return

    await pullGemma()
  }

  // Mark complete so this check is skipped on future launches
  fs.mkdirSync(path.dirname(flagPath), { recursive: true })
  fs.writeFileSync(flagPath, new Date().toISOString())
}

function pullGemma() {
  return new Promise((resolve) => {
    let progressWin = new BrowserWindow({
      width: 420,
      height: 160,
      resizable: false,
      minimizable: false,
      title: 'Downloading Gemma 3...',
      webPreferences: { nodeIntegration: true, contextIsolation: false },
    })
    progressWin.loadURL(
      'data:text/html,<body style="font-family:sans-serif;padding:24px;background:#f5f5f5">' +
      '<h3 style="margin:0 0 12px">Downloading Gemma 3 (2.7 GB)...</h3>' +
      '<p style="color:#666;font-size:13px">This runs once. Claire will use local AI for all future scans.</p>' +
      '</body>'
    )

    const pull = spawn('ollama', ['pull', 'gemma3:4b'], { stdio: ['ignore', 'pipe', 'pipe'] })
    pull.on('close', () => {
      progressWin.close()
      resolve()
    })
    pull.on('error', () => {
      progressWin.close()
      resolve()
    })
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    titleBarStyle: 'hiddenInset',
    title: 'Claire',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (DEV_SERVER_URL) {
    mainWindow.loadURL(DEV_SERVER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  ipcMain.handle('dialog:openFolder', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
    })
    return result.canceled ? null : result.filePaths[0]
  })

  ipcMain.handle('shell:openFile', async (_event, filePath) => {
    await shell.openPath(filePath)
  })

  ipcMain.handle('system:checkRAM', () => {
    const totalGB = os.totalmem() / (1024 * 1024 * 1024)
    const freeGB = os.freemem() / (1024 * 1024 * 1024)
    return { totalGB: Math.round(totalGB), freeGB: parseFloat(freeGB.toFixed(1)) }
  })
}

app.whenReady().then(async () => {
  startBackend()
  await checkOllama()
  waitForBackend(createWindow)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill()
})
