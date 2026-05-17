# Claire — Family Installation Guide

Claire organises your school files automatically using local AI.
Follow these steps carefully — it takes about 10 minutes the first time.

---

## What You Need Before Starting

- A Mac running macOS 12 or later
- At least 6 GB of free disk space
- Two files from Radhika: **Claire-0.1.0-arm64.dmg** and **family_setup.sh**
- Internet connection (needed for the first launch only)

---

## Step 1 — Download the Files

Save both files Radhika shared with you into your **Downloads** folder:
- `Claire-0.1.0-arm64.dmg`
- `family_setup.sh`

---

## Step 2 — Run the Setup Script

This places the credentials Claire needs on your Mac. You only do this once.

1. Open **Terminal**
   - Press **⌘ Space** to open Spotlight
   - Type `Terminal` and press **Enter**

2. In the Terminal window, type this exactly and press **Enter**:
   ```
   bash ~/Downloads/family_setup.sh
   ```

3. You should see: `✅ Claire setup complete.`

   If you see an error, take a screenshot and send it to Radhika.

---

## Step 3 — Install Claire

1. Go to your **Downloads** folder in Finder
2. Double-click **Claire-0.1.0-arm64.dmg**
3. A window opens showing the Claire icon and an Applications folder shortcut:

   ```
   [ Claire icon ]    →    [ Applications ]
   ```

4. **Drag the Claire icon** onto the **Applications** folder icon
5. Wait for the copy to finish (progress bar at the top of the screen)
6. Eject the installer — in the Finder sidebar, click the ⏏ eject button next to **Claire Installer**

---

## Step 4 — Open Claire for the First Time

macOS will block Claire the very first time because it was not downloaded from the App Store.
Follow these steps to allow it:

1. Open **Finder** → click **Applications** in the sidebar
2. Find **Claire** and double-click it
3. A warning appears: *"Claire can't be opened because it is from an unidentified developer"*
4. Click **Cancel** (do not click Move to Trash)
5. Open **System Settings** (the gear icon in your Dock, or Apple menu → System Settings)
6. Click **Privacy & Security** in the left sidebar
7. Scroll down — you will see a message: *"Claire was blocked from use"*
8. Click **Open Anyway**
9. Enter your Mac password if asked
10. Click **Open** in the final confirmation dialog

Claire will now open normally every time — you will not see this warning again.

---

## Step 5 — Install the Local AI (Ollama)

Claire uses a local AI called Ollama to read and classify your files privately on your device.
On the very first launch, Claire will set it up for you automatically.

1. A dialog appears: **"Setting up local AI (Ollama)"**
2. Click **Install Ollama**
3. Wait while Ollama downloads (~200 MB) and installs — this takes 2–5 minutes
4. Next, Claire downloads the **Gemma 3 AI model** (~2.7 GB) — this takes 5–10 minutes on a typical connection
5. A progress window shows the download status
6. When complete, Claire opens automatically

> **Note:** Steps 3–5 only happen once. Future launches start in seconds.
> If the automatic install fails, visit **ollama.com**, download Ollama manually,
> install it, then relaunch Claire.

---

## Step 6 — Welcome Screen: Add Your Files

Claire opens to the **Welcome to Claire!** screen.

### Add local folders

1. Click **Add Folder**
2. A file picker opens — navigate to a folder you want organised
   (good choices: your Documents folder, your school folder, Downloads)
3. Click **Open**
4. Repeat to add more folders
5. To remove a folder, click the **✕** next to it

### Connect Google Drive (optional)

If your school uses Google Drive:

1. Click **Connect School Drive**
2. Your browser (Safari or Chrome) opens to a Google sign-in page
3. Sign in with your **school Google account**
4. Google asks for permission — click **Allow**
5. Close the browser tab and return to Claire
6. The button will show **School Drive Connected** ✅

Repeat with **Connect Personal Drive** if you also want your personal Google Drive scanned.

### Continue

Click **Get Started** when you have added at least one folder or connected a Drive.

---

## Step 7 — Scan Your Files

1. You are now on the **Dashboard**
2. Click **Scan Now** (blue button, top right)
3. Claire scans all your files and classifies them by subject
4. A progress screen shows what is being scanned
5. When done, you land back on the Dashboard with your file counts

**The first scan takes a few minutes.** Future scans are much faster because Claire only processes new or changed files.

---

## Step 8 — Explore Your Files

From the Dashboard you can:

- **View Organised Files** — browse your files sorted by subject (Math, Biology, English, etc.)
- **View Duplicates** — find and remove duplicate files taking up space
- **Scan Now** — re-scan any time after adding new files
- **Settings** (gear icon) — add or remove folders, connect/disconnect Google Drive

If Claire puts a file in the wrong subject, click on the file and reassign it.
Claire remembers your corrections and will not overwrite them.

---

## Troubleshooting

| Problem | What to do |
|---------|-----------|
| "Claire can't be opened" | Follow Step 4 — open via System Settings → Privacy & Security |
| Setup script shows an error | Screenshot it and send to Radhika |
| Ollama download fails | Install from **ollama.com** manually, then relaunch Claire |
| Drive connect button does nothing | Make sure you ran `family_setup.sh` in Step 2; try again |
| Drive shows "Connecting…" but never connects | Wait 30 seconds; if still stuck, close and reopen Settings |
| Files not showing up after scan | Check that the correct folder was added in Settings |
| App won't open at all | Restart your Mac and try again; if still stuck, contact Radhika |

---

## What Claire Stores on Your Mac

| What | Where |
|------|-------|
| File index (names, sizes, categories — no content) | `~/.declutter/` |
| Google Drive login token | `~/.declutter/drive_accounts/` |
| Your folder list and settings | `~/.declutter/settings.json` |
| App logs (for debugging) | `~/Library/Application Support/claire/claire-api.log` |

Claire **never uploads your file contents**.
All text classification runs locally on your Mac using Gemma 3 (Ollama).

---

## Uninstalling Claire

1. Quit Claire (right-click the Dock icon → Quit, or ⌘Q)
2. Open **Finder** → **Applications**
3. Drag **Claire** to the Trash
4. To also remove all Claire data, open Terminal and run:
   ```
   rm -rf ~/.declutter
   rm -rf ~/Library/Application\ Support/claire
   ```
