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

function readSettings() {
  try {
    const p = path.join(os.homedir(), '.declutter', 'settings.json')
    return JSON.parse(fs.readFileSync(p, 'utf8'))
  } catch (_) {
    return {}
  }
}

function startBackend() {
  const bin = getBackendBinaryPath()

  if (app.isPackaged) {
    try { fs.chmodSync(bin, 0o755) } catch (_) {}
  }

  const logPath = getLogPath()
  fs.mkdirSync(path.dirname(logPath), { recursive: true })
  const logFd = fs.openSync(logPath, 'a')

  const settings = readSettings()
  const env = { ...process.env }
  if (settings.GOOGLE_API_KEY) env.GOOGLE_API_KEY = settings.GOOGLE_API_KEY

  backendProcess = spawn(bin, [], {
    shell: !app.isPackaged,
    stdio: ['ignore', logFd, logFd],
    env,
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
function waitForBackend(onReady, attempt = 0, maxAttempts = 80) {
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
      `The Claire API did not start within 40 seconds.\n\nCheck the log for details:\n${getLogPath()}`
    )
    return
  }
  setTimeout(() => waitForBackend(onReady, attempt + 1, maxAttempts), 500)
}

// macOS Electron apps don't inherit the shell's full PATH.
// Add common locations so ollama, brew-installed tools are findable.
function shellEnv() {
  return {
    ...process.env,
    PATH: `/usr/local/bin:/opt/homebrew/bin:${process.env.PATH || ''}`,
  }
}

// Check available disk space on the home volume. Returns free bytes.
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

// Show a simple progress window with a status line that can be updated.
function makeProgressWindow(title, heading, subtext) {
  const win = new BrowserWindow({
    width: 440,
    height: 180,
    resizable: false,
    minimizable: false,
    title,
    webPreferences: { nodeIntegration: true, contextIsolation: false },
  })
  win.loadURL(
    `data:text/html,<body style="font-family:-apple-system,sans-serif;padding:28px;background:#f5f5f5">` +
    `<h3 id="heading" style="margin:0 0 10px;font-size:15px">${heading}</h3>` +
    `<p id="status" style="color:#666;font-size:13px;margin:0">${subtext}</p>` +
    `</body>`
  )
  return win
}

function setProgressStatus(win, status) {
  if (!win || win.isDestroyed()) return
  win.webContents.executeJavaScript(
    `document.getElementById('status').textContent = ${JSON.stringify(status)}`
  ).catch(() => {})
}

async function handleCurlResult(code, progressWin, tmpZip, extractDir, appsDir, resolve) {
  if (code !== 0) {
    if (!progressWin.isDestroyed()) progressWin.close()
    const { response } = await dialog.showMessageBox({
      type: 'warning',
      title: 'Claire — Ollama Download Failed',
      message: 'Could not download Ollama',
      detail:
        'Download failed. Please check your internet connection.\n\n' +
        'Click "Visit ollama.com" to install Ollama manually, or continue with cloud AI.',
      buttons: ['Visit ollama.com', 'Use Cloud AI'],
      defaultId: 0,
    })
    if (response === 0) shell.openExternal('https://ollama.com/download')
    resolve(false)
    return
  }

  setProgressStatus(progressWin, 'Installing Ollama...')

  try {
    fs.mkdirSync(extractDir, { recursive: true })
    execSync(`unzip -o "${tmpZip}" -d "${extractDir}"`)
    fs.mkdirSync(appsDir, { recursive: true })
    execSync(`cp -R "${extractDir}/Ollama.app" "${appsDir}/"`)
    spawn('open', ['-j', '-g', `${appsDir}/Ollama.app`], { detached: true, stdio: 'ignore' })
  } catch (e) {
    if (!progressWin.isDestroyed()) progressWin.close()
    const { response } = await dialog.showMessageBox({
      type: 'warning',
      title: 'Claire — Ollama Install Failed',
      message: 'Automatic installation failed',
      detail:
        'Could not install Ollama automatically.\n\n' +
        'Click "Visit ollama.com" to install Ollama manually, or continue with cloud AI.',
      buttons: ['Visit ollama.com', 'Use Cloud AI'],
      defaultId: 0,
    })
    if (response === 0) shell.openExternal('https://ollama.com/download')
    resolve(false)
    return
  }

  setProgressStatus(progressWin, 'Waiting for Ollama to finish setup...')
  waitForOllamaCLI(() => {
    if (!progressWin.isDestroyed()) progressWin.close()
    resolve(true)
  })
}

// Download and auto-install Ollama.app into ~/Applications, then launch it
// to register the ollama CLI, then poll until the CLI is available.
function installOllama() {
  return new Promise((resolve) => {
    const progressWin = makeProgressWindow(
      'Installing Ollama...',
      'Setting up local AI (Ollama)',
      'Downloading Ollama — this runs once...'
    )

    const tmpZip = path.join(os.tmpdir(), 'Ollama-darwin.zip')
    const extractDir = path.join(os.tmpdir(), 'ollama-extract')
    const appsDir = path.join(os.homedir(), 'Applications')

    // Use curl — handles redirects, available on all macOS, shows download progress via stderr
    const curl = spawn('curl', ['-L', '-o', tmpZip, 'https://ollama.com/download/Ollama-darwin.zip'], {
      stdio: ['ignore', 'ignore', 'pipe'],
    })

    curl.stderr.on('data', (chunk) => {
      // curl progress lines look like: " 45  234M   45  105M    0     0  5210k      0  0:00:46  0:00:20  0:00:26 5331k"
      const match = chunk.toString().match(/\s+(\d+)\s+/)
      if (match) setProgressStatus(progressWin, `Downloading Ollama... ${match[1]}%`)
    })

    curl.on('close', (code) => {
      // Handle async work outside the event listener to avoid unhandled rejections
      handleCurlResult(code, progressWin, tmpZip, extractDir, appsDir, resolve)
    })
  })
}

function waitForOllamaCLI(onReady, attempt = 0, maxAttempts = 30) {
  try {
    execSync('ollama --version', { stdio: 'ignore', env: shellEnv() })
    onReady()
  } catch (_) {
    if (attempt >= maxAttempts) {
      onReady() // give up waiting, continue — CLI may just need a PATH refresh
      return
    }
    setTimeout(() => waitForOllamaCLI(onReady, attempt + 1, maxAttempts), 1000)
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
    execSync('ollama --version', { stdio: 'ignore', env: shellEnv() })
    ollamaInstalled = true
  } catch (_) {}

  if (!ollamaInstalled) {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Claire — Local AI Setup',
      message: 'Setting up local AI processing',
      detail:
        'Claire uses Gemma 3 to classify your files locally — your content never leaves your device.\n\n' +
        'Claire will automatically download and install Ollama for you.\n\n' +
        'If installation fails, Claire will fall back to cloud AI (Google AI API) for classification.',
      buttons: ['Install Ollama', 'Skip'],
      defaultId: 0,
    })
    if (response === 0) {
      const installed = await installOllama()
      if (!installed) return
    } else {
      return
    }
  }

  // Step 2: is gemma3:4b pulled?
  let modelReady = false
  try {
    const list = execSync('ollama list', { encoding: 'utf8', env: shellEnv() })
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
      buttons: ['Download Now', 'Skip'],
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
    const progressWin = makeProgressWindow(
      'Downloading Gemma 3...',
      'Downloading Gemma 3 (2.7 GB)...',
      'This runs once. Claire will use local AI for all future scans.'
    )

    const pull = spawn('ollama', ['pull', 'gemma3:4b'], { stdio: ['ignore', 'pipe', 'pipe'], env: shellEnv() })

    pull.stdout.on('data', (chunk) => {
      const line = chunk.toString().trim().split('\n').pop()
      if (line) setProgressStatus(progressWin, line)
    })

    pull.on('close', () => {
      if (!progressWin.isDestroyed()) progressWin.close()
      resolve()
    })
    pull.on('error', () => {
      if (!progressWin.isDestroyed()) progressWin.close()
      resolve()
    })
  })
}

function registerIpcHandlers() {
  const settingsPath = path.join(os.homedir(), '.declutter', 'settings.json')

  ipcMain.handle('dialog:openFolder', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
    })
    return result.canceled ? null : result.filePaths[0]
  })

  ipcMain.handle('shell:openFile', async (_event, filePath) => {
    await shell.openPath(filePath)
  })

  ipcMain.handle('shell:openExternal', async (_event, url) => {
    await shell.openExternal(url)
  })

  ipcMain.handle('settings:get', () => {
    try {
      const data = JSON.parse(fs.readFileSync(settingsPath, 'utf8'))
      return data
    } catch (_) {
      return {}
    }
  })

  ipcMain.handle('settings:set', (_event, data) => {
    try {
      fs.mkdirSync(path.dirname(settingsPath), { recursive: true })
      const existing = (() => { try { return JSON.parse(fs.readFileSync(settingsPath, 'utf8')) } catch { return {} } })()
      fs.writeFileSync(settingsPath, JSON.stringify({ ...existing, ...data }, null, 2))
    } catch (_) {}
  })

  ipcMain.handle('system:checkRAM', () => {
    const totalGB = os.totalmem() / (1024 * 1024 * 1024)
    // Use memory_pressure percentage instead of os.freemem() — macOS reclaims
    // inactive/compressed memory instantly so raw free pages are misleading.
    let freePct = 100
    try {
      const out = execSync('memory_pressure', { encoding: 'utf8' })
      const match = out.match(/System-wide memory free percentage:\s*(\d+)%/)
      if (match) freePct = parseInt(match[1], 10)
    } catch (_) {}
    const freeGB = parseFloat(((freePct / 100) * totalGB).toFixed(1))
    return { totalGB: Math.round(totalGB), freeGB, freePct }
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
}

app.whenReady().then(async () => {
  registerIpcHandlers()
  startBackend()
  await checkOllama()
  waitForBackend(createWindow)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    if (backendProcess) backendProcess.kill()
    app.quit()
  }
})

app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill()
})
