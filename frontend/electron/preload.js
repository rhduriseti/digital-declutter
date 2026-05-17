const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electron', {
  isElectron: true,
  openFolderPicker: () => ipcRenderer.invoke('dialog:openFolder'),
  openFile: (filePath) => ipcRenderer.invoke('shell:openFile', filePath),
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  checkRAM: () => ipcRenderer.invoke('system:checkRAM'),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (data) => ipcRenderer.invoke('settings:set', data),
})
