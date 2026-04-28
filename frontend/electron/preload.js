const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electron', {
  isElectron: true,
  openFolderPicker: () => ipcRenderer.invoke('dialog:openFolder'),
})
