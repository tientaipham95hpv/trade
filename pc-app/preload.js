const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getConfig: () => ipcRenderer.invoke('get-app-config'),
  saveConfig: (cfg) => ipcRenderer.invoke('save-app-config', cfg),
  updateTray: (stats) => ipcRenderer.send('update-tray-stats', stats),
  notify: (payload) => ipcRenderer.send('show-notification', payload),
  onTriggerAction: (callback) => {
    ipcRenderer.on('trigger-action', (event, action) => callback(action));
  }
});
