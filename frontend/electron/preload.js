const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electron', {
  isElectron: true,
  openFolderPicker: () => ipcRenderer.invoke('dialog:openFolder'),
  openFile: (filePath) => ipcRenderer.invoke('shell:openFile', filePath),
  checkRAM: () => ipcRenderer.invoke('system:checkRAM'),
})
