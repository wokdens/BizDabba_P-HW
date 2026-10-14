# ⚡ BizDabba Cloud Demo (Option 1: Browser-Streamed GUI)
**Powered by Wokdens.com**

This directory contains the complete, containerized browser-streaming setup for **BizDabba for Paint & Hardware**.

---

## 🎯 Key Highlights
* **Zero Reverse-Engineering Risk:** The `.exe`, Python code, and SQLite database run strictly on the server. The client only sees an interactive video/canvas stream in their browser.
* **Zero Client Friction:** No downloads, no installations, no Windows SmartScreen warnings. Clients simply click a link and start using the software.
* **0% Code Rewrite:** Uses the exact, verified Python + Tkinter desktop codebase as-is.

---

## 🚀 How to Test Locally on Your Laptop

### Step 1: Open Docker Desktop
1. Open the Start menu on your laptop and search for **Docker Desktop**.
2. Click it to launch. Wait 15–30 seconds until the bottom-left whale icon turns green (Engine Running).

### Step 2: Build and Run
Open PowerShell in the project directory and run:
```powershell
docker compose -f cloud_demo/docker-compose.yml up --build -d
```

### Step 3: Open in Browser
Open your browser and navigate to:
```
http://localhost:8080
```
BizDabba will automatically launch full-screen inside your browser tab!

To stop the container when done:
```powershell
docker compose -f cloud_demo/docker-compose.yml down
```

---

## 🌐 How to Share an Instant Public Link (Test on Phone)

You can share a live public link directly from your laptop without deploying to a cloud server:

1. Download the free [Cloudflare Tunnel CLI (`cloudflared`)](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe).
2. Run this command in PowerShell while your Docker container is running:
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:8080
   ```
3. Cloudflare will give you a temporary public URL like:
   `https://random-words.trycloudflare.com`
4. Open that URL on your phone or send it to a test user. It will open BizDabba in their browser!

---

## ☁️ Permanent Cloud Deployment ($0 to $5/month)

### Option A: Render.com (1-Click Web Service)
1. Push this branch to GitHub.
2. Sign in to [Render.com](https://render.com).
3. Click **New +** -> **Web Service** -> Connect your GitHub repo (`BizDabba_P-HW` or `BusinessApp`).
4. Select **Docker** environment. Render will automatically detect `cloud_demo/Dockerfile`.
5. Click **Deploy**. Render gives you a free HTTPS link (e.g. `https://bizdabba-demo.onrender.com`).

### Option B: Any Linux VPS (DigitalOcean, Hetzner, AWS Lightsail - $4–$6/mo)
Run these 3 commands on your VPS:
```bash
git clone https://github.com/wokdens/BizDabba_P-HW.git
cd BizDabba_P-HW
docker compose -f cloud_demo/docker-compose.yml up -d
```
Your demo will immediately be live at `http://your-server-ip:8080`!
