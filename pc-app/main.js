const { app, BrowserWindow, Tray, Menu, ipcMain, globalShortcut, Notification, shell, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow = null;
let tray = null;
let isQuitting = false;

// Đọc cấu hình lưu trữ cục bộ
const userDataPath = app.getPath('userData');
const configFile = path.join(userDataPath, 'desktop_config.json');

function loadConfig() {
  const defaults = {
    serverUrl: 'https://trader.noza.site',
    authToken: '',
    soundEnabled: true,
    minimizeToTray: true,
    hotkeyEmergency: 'CommandOrControl+Shift+K',
    refreshIntervalSec: 3
  };
  try {
    if (fs.existsSync(configFile)) {
      return { ...defaults, ...JSON.parse(fs.readFileSync(configFile, 'utf8')) };
    }
  } catch (e) {
    console.error('Error loading config:', e);
  }
  return defaults;
}

function saveConfig(cfg) {
  try {
    fs.writeFileSync(configFile, JSON.stringify(cfg, null, 2), 'utf8');
    return true;
  } catch (e) {
    console.error('Error saving config:', e);
    return false;
  }
}

let appConfig = loadConfig();

function createWindow() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png');
  const appIcon = nativeImage.createFromPath(iconPath);

  mainWindow = new BrowserWindow({
    width: 1420,
    height: 900,
    minWidth: 1050,
    minHeight: 720,
    title: 'Binance Futures Institutional Quant Pro Terminal',
    backgroundColor: '#080a0f',
    icon: appIcon,
    frame: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      backgroundThrottling: false
    }
  });

  // Load UI
  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Xử lý đóng cửa sổ: Thu nhỏ xuống khay Taskbar thay vì tắt app
  mainWindow.on('close', (event) => {
    if (!isQuitting && appConfig.minimizeToTray) {
      event.preventDefault();
      mainWindow.hide();
      if (tray && Notification.isSupported()) {
        new Notification({
          title: 'Binance Quant Pro',
          body: 'Ứng dụng đang chạy ngầm trong khay hệ thống Taskbar.',
          icon: appIcon
        }).show();
      }
    }
  });

  // Mở link ngoài bằng trình duyệt mặc định
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// Khởi tạo System Tray (Khay Hệ Thống)
function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png');
  const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 18, height: 18 });

  tray = new Tray(trayIcon);
  tray.setToolTip('Binance Futures Quant Pro Terminal\nTrạng thái: Đang kết nối VPS...');

  updateTrayMenu({ status: 'Online', pnl: '+$0.00', positions: 0 });

  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function updateTrayMenu(info = {}) {
  if (!tray) return;

  const pnlText = info.pnl || '+$0.00';
  const posCount = info.positions !== undefined ? info.positions : 0;
  const statusText = info.status || 'Active';

  const contextMenu = Menu.buildFromTemplate([
    {
      label: `📈 PnL Hôm Nay: ${pnlText}`,
      enabled: false
    },
    {
      label: `⚡ Vị thế đang mở: ${posCount} lệnh`,
      enabled: false
    },
    {
      label: `🌐 Trạng thái VPS: ${statusText}`,
      enabled: false
    },
    { type: 'separator' },
    {
      label: '🖥️ Mở Giao Diện Cockpit',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: '⏸️ Tạm Dừng Bot',
      click: () => {
        if (mainWindow) mainWindow.webContents.send('trigger-action', 'pause');
      }
    },
    {
      label: '▶️ Bật Lại Bot',
      click: () => {
        if (mainWindow) mainWindow.webContents.send('trigger-action', 'resume');
      }
    },
    { type: 'separator' },
    {
      label: '🚨 ĐÓNG SẠCH LỆNH KHẨN CẤP (Kill-Switch)',
      click: () => {
        if (mainWindow) mainWindow.webContents.send('trigger-action', 'emergency-close-all');
      }
    },
    { type: 'separator' },
    {
      label: '❌ Thoát Ứng Dụng',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  tray.setToolTip(`Binance Quant Pro | PnL: ${pnlText} | Positions: ${posCount}`);
}

// Đăng ký Phím Tắt Khẩn Cấp Toàn Cục
function registerGlobalHotkeys() {
  globalShortcut.unregisterAll();
  const hotkey = appConfig.hotkeyEmergency || 'CommandOrControl+Shift+K';

  try {
    const ret = globalShortcut.register(hotkey, () => {
      console.log('Emergency Hotkey Triggered:', hotkey);
      if (mainWindow) {
        mainWindow.webContents.send('trigger-action', 'emergency-close-all');
      }
      if (Notification.isSupported()) {
        new Notification({
          title: '🚨 EMERGENCY KILL-SWITCH ACTIVATED',
          body: 'Đang gửi tín hiệu đóng toàn bộ vị thế Binance khẩn cấp!',
          urgency: 'critical'
        }).show();
      }
    });

    if (!ret) {
      console.warn('Hotkey registration failed for:', hotkey);
    }
  } catch (e) {
    console.error('Error registering hotkey:', e);
  }
}

// App Lifecycle
app.whenReady().then(() => {
  createWindow();
  createTray();
  registerGlobalHotkeys();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

// IPC Communication Handlers
ipcMain.handle('get-app-config', () => {
  return appConfig;
});

ipcMain.handle('save-app-config', (event, newCfg) => {
  appConfig = { ...appConfig, ...newCfg };
  saveConfig(appConfig);
  registerGlobalHotkeys();
  return true;
});

ipcMain.on('update-tray-stats', (event, stats) => {
  updateTrayMenu(stats);
});

ipcMain.on('show-notification', (event, { title, body, silent }) => {
  if (Notification.isSupported()) {
    const notif = new Notification({
      title: title || 'Binance Quant Pro',
      body: body || '',
      silent: silent || false,
      icon: path.join(__dirname, 'assets', 'icon.png')
    });
    notif.show();
    notif.on('click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  }
});
