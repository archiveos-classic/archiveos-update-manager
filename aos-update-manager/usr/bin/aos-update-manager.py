#!/usr/bin/env python3
# Kodların buradan aşağıda devam etmeli...
import sys
import subprocess
import requests
import json
import os
import locale
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

# --- DOSYA YOLLARI ---
HOME = os.path.expanduser("~")
LOG_FILE = os.path.join(HOME, ".archiveos_update.log")
JSON_PATH = os.path.join(HOME, ".version.json")
TEMP_ZIP = os.path.join(HOME, "aos_update_temp.zip")
TEMP_DIR = os.path.join(HOME, ".aos_update_folder")

# --- GITHUB AYARLARI (GÜNCELLENDİ) ---
GITHUB_USER = "archiveos-classic"
REPO_NAME = "updates"

# Mevcut çalışma dizinindeki logo.png yolunu netleştiriyoruz
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE = os.path.join(CURRENT_DIR, "aos-updater-logo.png")

# Bu bağlantılar GITHUB_USER ve REPO_NAME üzerinden otomatik oluşur
REMOTE_JSON_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/version.json"
ZIP_URL = f"https://github.com/{GITHUB_USER}/{REPO_NAME}/archive/refs/heads/main.zip"

# Arka Plan Modu Kontrolü
SILENT_MODE = "--silent" in sys.argv

# Loglama Yapılandırması
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

def get_lang():
    try:
        lang = locale.getdefaultlocale()[0]
        return "tr" if lang and lang.startswith("tr") else "en"
    except:
        return "en"

LANG = get_lang()

STRINGS = {
    "tr": {
        "title": "ArchiveOS Güncelleyici",
        "checking": "Güncellemeler denetleniyor...",
        "offline": "Bağlantı Yok (v{})",
        "found": "Yeni Sürüm: v{}",
        "ask": "v{} sürümünü kurmak için terminal açılsın mı?",
        "latest": "Sistem Güncel (v{})",
        "btn_recheck": "Yeniden Dene",
        "terminal_msg": "ArchiveOS Kurulumu - Root şifresini girin.",
        "success_msg": "Güncelleme başarılı! Geçici dosyalar silindi.",
        "error_msg": f"Hata oluştu! Log dosyasını inceleyin:\n{LOG_FILE}",
        "running": "Kurulum yapılıyor, terminali izleyin...",
        "notify_title": "ArchiveOS Güncellemesi",
        "notify_body": "Yeni bir sürüm mevcut: v{}"
    },
    "en": {
        "title": "ArchiveOS Updater",
        "checking": "Checking for updates...",
        "offline": "Offline (v{})",
        "found": "New Version: v{}",
        "ask": "Open terminal to install v{}?",
        "latest": "System Up-to-date (v{})",
        "btn_recheck": "Try Again",
        "terminal_msg": "ArchiveOS Installation - Enter root password.",
        "success_msg": "Update successful! Temp files cleared.",
        "error_msg": f"Error occurred! Check log file:\n{LOG_FILE}",
        "running": "Installing, check terminal...",
        "notify_title": "ArchiveOS Update",
        "notify_body": "A new version is available: v{}"
    }
}

class UpdateWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str, bool)

    def run(self):
        local_version = "0.0.0"
        if not os.path.exists(JSON_PATH):
            try:
                with open(JSON_PATH, "w") as f:
                    json.dump({"version": "0.0.0"}, f)
            except: pass

        try:
            with open(JSON_PATH, "r") as f:
                local_version = json.load(f).get("version", "0.0.0")
        except: pass

        try:
            self.progress.emit(30)
            response = requests.get(REMOTE_JSON_URL, timeout=7)
            if response.status_code == 200:
                remote_version = response.json().get("version", "0.0.0")
                self.progress.emit(90)
                self.finished.emit(remote_version != local_version, remote_version, False)
            else:
                self.finished.emit(False, local_version, True)
        except:
            self.finished.emit(False, local_version, True)

class ArchiveOSUpdateManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS[LANG]["title"])
        self.setFixedSize(550, 450)

        if os.path.exists(LOGO_FILE):
            self.setWindowIcon(QIcon(LOGO_FILE))

        self.init_ui()
        self.apply_styles()

        if SILENT_MODE:
            self.hide()

        QTimer.singleShot(500, self.start_update_check)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.lbl_logo = QLabel()
        if os.path.exists(LOGO_FILE):
            pixmap = QPixmap(LOGO_FILE)
            self.lbl_logo.setPixmap(pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_title = QLabel("ArchiveOS")
        self.lbl_title.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        self.lbl_status = QLabel(STRINGS[LANG]["checking"])
        self.progress_bar = QProgressBar()
        self.btn_check = QPushButton(STRINGS[LANG]["btn_recheck"])
        self.btn_check.setFixedSize(280, 50)
        self.btn_check.setEnabled(False)
        self.btn_check.clicked.connect(self.start_update_check)
        self.layout.addStretch(); self.layout.addWidget(self.lbl_logo, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.lbl_status, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.progress_bar); self.layout.addSpacing(15)
        self.layout.addWidget(self.btn_check, alignment=Qt.AlignmentFlag.AlignCenter); self.layout.addStretch()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0c0c0c; }
            QLabel { color: #eee; font-family: 'Inter'; }
            QPushButton { background: #151515; color: white; border: 1px solid #3daee9; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background: #3daee9; color: black; }
            QProgressBar { border: 1px solid #222; border-radius: 4px; text-align: center; color: white; background: #151515; height: 15px; }
            QProgressBar::chunk { background-color: #3daee9; }
        """)

    def start_update_check(self):
        self.btn_check.setEnabled(False)
        self.lbl_status.setText(STRINGS[LANG]["checking"])
        self.progress_bar.setValue(10)
        self.worker = UpdateWorker()
        self.worker.progress.connect(lambda v: self.progress_bar.setValue(v))
        self.worker.finished.connect(self.handle_result)
        self.worker.start()

    def send_notification(self, version):
        try:
            icon = LOGO_FILE if os.path.exists(LOGO_FILE) else "system-software-update"
            subprocess.Popen([
                'notify-send',
                '-i', icon,
                STRINGS[LANG]["notify_title"],
                STRINGS[LANG]["notify_body"].format(version)
            ])
        except Exception as e:
            logging.error(f"Bildirim gönderilemedi: {e}")

    def handle_result(self, update_available, version_info, is_error):
        self.progress_bar.setValue(100)
        self.btn_check.setEnabled(True)
        if is_error:
            self.lbl_status.setText(STRINGS[LANG]["offline"].format(version_info))
            if SILENT_MODE: sys.exit(0)
        elif update_available:
            self.lbl_status.setText(STRINGS[LANG]["found"].format(version_info))
            self.send_notification(version_info)
            if SILENT_MODE:
                sys.exit(0)
            res = QMessageBox.question(self, "Update", STRINGS[LANG]["ask"].format(version_info))
            if res == QMessageBox.StandardButton.Yes:
                self.install_update(version_info)
        else:
            self.lbl_status.setText(STRINGS[LANG]["latest"].format(version_info))
            if SILENT_MODE: sys.exit(0)

    def install_update(self, new_ver):
        self.btn_check.setEnabled(False)
        self.lbl_status.setText(STRINGS[LANG]["running"])
        shell_script = (
            f"echo '--- Kurulum Basladi ---' >> '{LOG_FILE}'; "
            f"rm -rf '{TEMP_DIR}' '{TEMP_ZIP}' >> '{LOG_FILE}' 2>&1; "
            f"echo '{STRINGS[LANG]['terminal_msg']}'; "
            f"sudo -v || exit 1; "
            f"wget -O '{TEMP_ZIP}' '{ZIP_URL}' >> '{LOG_FILE}' 2>&1 && "
            f"mkdir -p '{TEMP_DIR}' && unzip -o '{TEMP_ZIP}' -d '{TEMP_DIR}' >> '{LOG_FILE}' 2>&1 && "
            f"G_DIR=$(find '{TEMP_DIR}' -maxdepth 1 -type d -name '*updates*' | head -n 1); cd \"$G_DIR\" && "
            f"if [ -f main.zip ]; then unzip -o main.zip >> '{LOG_FILE}' 2>&1; fi && "
            f"SH_PATH=$(find . -name 'install.sh' | head -n 1); "
            f"if [ -n \"$SH_PATH\" ]; then "
            f"  SH_DIR=$(dirname \"$SH_PATH\"); cd \"$SH_DIR\"; "
            f"  chmod +x install.sh && sudo ./install.sh >> '{LOG_FILE}' 2>&1 && "
            f"  echo '{{\"version\": \"{new_ver}\"}}' > '{JSON_PATH}' && "
            f"  touch /tmp/aos_success; "
            f"fi; "
            f"rm -rf '{TEMP_DIR}' '{TEMP_ZIP}'; "
            f"exit"
        )
        proc = subprocess.Popen(['konsole', '-e', 'bash', '-c', shell_script])
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(lambda: self.check_install_status(proc))
        self.check_timer.start(1000)

    def check_install_status(self, proc):
        if proc.poll() is not None:
            self.check_timer.stop()
            if os.path.exists("/tmp/aos_success"):
                os.remove("/tmp/aos_success")
                if os.path.exists(LOG_FILE):
                    try:
                        logging.shutdown()
                        os.remove(LOG_FILE)
                    except: pass
                QMessageBox.information(self, "ArchiveOS", STRINGS[LANG]["success_msg"])
                self.start_update_check()
            else:
                QMessageBox.critical(self, "ArchiveOS", STRINGS[LANG]["error_msg"])
                self.btn_check.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(not SILENT_MODE)
    app.setStyle("Fusion")
    win = ArchiveOSUpdateManager()
    if not SILENT_MODE:
        win.show()
    sys.exit(app.exec())
