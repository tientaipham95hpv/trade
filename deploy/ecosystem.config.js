// Cấu hình PM2 để quản lý tiến trình bot nếu sử dụng NodeJS/PM2
module.exports = {
  apps: [
    {
      name: "binance-bot",
      script: "run_bot.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
