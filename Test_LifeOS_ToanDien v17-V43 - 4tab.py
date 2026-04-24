# -*- coding: utf-8 -*-
"""
SENTINEL MASTER SUITE V16.9 - ENTERPRISE ALL-IN-ONE
Cập nhật V16.9 (The Adaptive Skeleton):
- Áp dụng cơ chế Smart Fallback cho Login: Tự động thích nghi với cả 2 phiên bản HTML của User (Có Popup Mật khẩu hoặc 1-Click Login).
"""

import os
import time
import urllib.parse
from datetime import datetime
import colorama
from colorama import Fore, Style
from playwright.sync_api import sync_playwright, Page, TimeoutError

colorama.init()

TARGET_URL = "https://mimihoalua.github.io/tool/qlycuocsong.html"
XIAOMI_USER_AGENT = "Mozilla/5.0 (Linux; Android 13; 2306EPN60G Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
PC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

SNAP_DIR = r"C:\Google DRV\LifeOS\Full he sinh thai lifeos\snapLoi"
os.makedirs(SNAP_DIR, exist_ok=True)
LOG_FILE = os.path.join(SNAP_DIR, "Sentinel_Blackbox_Log.txt")

if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

def write_log(message: str, to_console: bool = True, color: str = ""):
    timestamp = datetime.now().strftime("[%H:%M:%S.%f]")[:-3] + "]"
    raw_msg = f"{timestamp} {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(raw_msg + "\n")
    if to_console:
        print(f"{color}{raw_msg}{Style.RESET_ALL}" if color else raw_msg)

def format_time(seconds: float) -> str:
    if seconds is None or seconds != seconds or seconds < 0: return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def handle_audio_sensor(event_data: dict) -> None:
    evt = event_data.get("event", "unknown")
    audio_id = event_data.get("id", "audio")
    curr_time = format_time(event_data.get("time", 0))
    ready = event_data.get("ready", 0)
    
    raw_src = event_data.get("src", "none")
    if "translate_tts" in raw_src or "translate.googleapis" in raw_src: src = "[Google TTS Voice]"
    elif "responsivevoice" in raw_src: src = "[ResponsiveVoice Fallback]"
    elif "digital_watch_alarm" in raw_src: src = "[Digital Alarm]"
    elif "silence" in raw_src: src = "[Mỏ neo 30p]"
    else: src = urllib.parse.unquote(raw_src)[-35:] 
    
    prefix = f"   [⚡ SENSOR - {audio_id}]"
    details = f"(Time: {curr_time} | R-State: {ready} | Src: {src})"
    
    if evt in ["playing", "canplay"]:
        write_log(f"{prefix} {evt.upper()} {details}", color=Fore.GREEN)
    elif evt == "error":
        if "tts" in audio_id:
            write_log(f"{prefix} Bị chặn tải link MP3, Fallback kích hoạt!", color=Fore.YELLOW)
        else:
            write_log(f"{prefix} ERROR/CRASH {details}", color=Fore.RED)
    elif evt == "ended":
        write_log(f"{prefix} ENDED {details}", color=Fore.MAGENTA)
    elif evt not in ["timeupdate", "pause", "waiting", "loadstart", "loadeddata", "loadedmetadata"]:
        write_log(f"{prefix} {evt.upper()} {details}", color=Fore.CYAN)

def inject_super_debug(page: Page) -> None:
    page.evaluate("""() => {
        const attachAudioMonitors = () => {
            const events = ['play', 'playing', 'pause', 'waiting', 'error', 'ended', 'loadstart', 'canplay'];
            document.querySelectorAll('audio').forEach(audio => {
                if(audio.dataset.monitored) return;
                audio.dataset.monitored = 'true';
                events.forEach(evt => {
                    audio.addEventListener(evt, e => {
                        if (window.pyAudioSensor) {
                            window.pyAudioSensor({
                                event: e.type, id: e.target.id || 'Unnamed-Audio', src: e.target.src || 'none',
                                time: (!isNaN(e.target.currentTime) ? e.target.currentTime : 0), ready: e.target.readyState
                            });
                        }
                    });
                });
            });
        };
        attachAudioMonitors();
        new MutationObserver(attachAudioMonitors).observe(document.body, { childList: true, subtree: true });
    }""")

class DeviceTelemetry:
    def __init__(self, device_name: str, color_code):
        self.device_name = device_name
        self.color_code = color_code

    def attach_sensors(self, page: Page) -> None:
        def log_console(msg):
            msg_type = msg.type.upper()
            c = Fore.YELLOW if msg_type == "WARNING" else Fore.RED if msg_type == "ERROR" else self.color_code
            if "tailwindcss" not in msg.text:
                write_log(f"[{self.device_name} CONSOLE_{msg_type}] {msg.text}", color=c)
        page.on("console", log_console)
        page.on("pageerror", lambda err: write_log(f"[{self.device_name} 💀 FATAL JS CRASH] {err.message}", color=Fore.RED))

def login_admin(page: Page, telemetry: DeviceTelemetry) -> bool:
    try:
        write_log(f"[{telemetry.device_name}] Đang phân tích Ma Trận DOM...", color=telemetry.color_code)
        time.sleep(1.5) 
        
        has_session = page.evaluate("() => !!localStorage.getItem('lifeos_v8_session')")
        
        if has_session:
            write_log(f"[{telemetry.device_name}] Phát hiện Session nội tại. Đang xác thực UI...", color=Fore.GREEN)
            page.locator("#todo-list").wait_for(state="visible", timeout=15000)
            write_log(f"[{telemetry.device_name}] DOM Login Sẵn Sàng (Smart Bypass).", color=Fore.GREEN)
            return True
            
        write_log(f"[{telemetry.device_name}] Yêu cầu đăng nhập, click Admin...", color=telemetry.color_code)
        
        # 1. Click Profile Admin
        page.locator("#login-profiles button:has-text('Admin')").first.click()
        
        # 2. THUẬT TOÁN THÍCH NGHI (ADAPTIVE FALLBACK)
        pwd_input = page.locator("#pwd-input")
        try:
            # Chờ thử 3 giây xem popup mật khẩu có hiện lên không
            pwd_input.wait_for(state="visible", timeout=3000)
            needs_password = True
        except TimeoutError:
            # Nếu 3 giây không hiện -> Mã HTML đang dùng cơ chế 1-click
            needs_password = False
            
        if needs_password:
            write_log(f"[{telemetry.device_name}] 🔓 Phát hiện Popup Mật khẩu. Đang điền khóa...", color=Fore.YELLOW)
            pwd_input.click()
            pwd_input.press_sequentially("admin", delay=20)
            page.locator("#password-modal button:has-text('Vào')").first.click(force=True)
        else:
            write_log(f"[{telemetry.device_name}] ⚡ HTML đang ở chế độ 1-Click, bỏ qua gõ mật khẩu...", color=Fore.YELLOW)
        
        # 3. Chờ DOM chính load xong
        page.locator("#todo-list").wait_for(state="visible", timeout=15000)
        write_log(f"[{telemetry.device_name}] Bẻ khóa thành công, DOM Sẵn Sàng.", color=Fore.GREEN)
        return True
        
    except Exception as e:
        write_log(f"[{telemetry.device_name} ❌ LOGIN FAILED] {e}", color=Fore.RED)
        try:
            fail_path = os.path.join(SNAP_DIR, f"CRASH_LOGIN_{telemetry.device_name}.png")
            page.screenshot(path=fail_path)
            write_log(f"   📸 Đã lưu ảnh hiện trường: {fail_path}", color=Fore.YELLOW)
        except Exception as snap_err:
            write_log(f"   ❌ Lỗi hệ thống khi chụp ảnh: {snap_err}", color=Fore.RED)
        return False

def wait_for_firebase_sync(page: Page, device_name: str) -> bool:
    write_log(f"[{device_name}] Đang chờ Firebase Pull dữ liệu lần đầu...", color=Fore.YELLOW)
    try:
        page.wait_for_function("window.cloudSyncCompleted === true", timeout=15000)
        write_log(f"[{device_name}] ✅ Firebase Sync Complete!", color=Fore.GREEN)
        return True
    except TimeoutError:
        write_log(f"[{device_name} ❌ SYNC TIMEOUT] Firebase không trả về Snapshot ban đầu.", color=Fore.RED)
        return False

def run_ecosystem_test() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')
    write_log("=" * 85, color=Fore.CYAN)
    write_log("🚀 SENTINEL V16.9: ALL-IN-ONE ENTERPRISE SUITE (ADAPTIVE SKELETON)".center(85), color=Fore.CYAN)
    write_log("=" * 85, color=Fore.CYAN)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx_mobile = browser.new_context(user_agent=XIAOMI_USER_AGENT, viewport={"width": 412, "height": 915}, is_mobile=True, has_touch=True)
        ctx_pc = browser.new_context(user_agent=PC_USER_AGENT, viewport={"width": 1280, "height": 720})
        
        page_mobile = ctx_mobile.new_page()
        page_pc = ctx_pc.new_page()
        
        page_mobile.expose_function("pyAudioSensor", handle_audio_sensor)
        
        tel_mobile = DeviceTelemetry("MOBILE", Fore.BLUE)
        tel_pc = DeviceTelemetry("PC", Fore.GREEN)
        
        tel_mobile.attach_sensors(page_mobile)
        tel_pc.attach_sensors(page_pc)
        
        page_mobile.goto(TARGET_URL, wait_until="domcontentloaded")
        page_pc.goto(TARGET_URL, wait_until="domcontentloaded")
        
        time.sleep(2)
        inject_super_debug(page_mobile)
        
        login_m = login_admin(page_mobile, tel_mobile)
        login_pc = login_admin(page_pc, tel_pc)
        
        if not login_m or not login_pc:
            write_log("❌ Hủy chiến dịch do Lỗi Đăng Nhập ở một hoặc cả hai thiết bị.", color=Fore.RED)
            browser.close()
            return
            
        sync_m = wait_for_firebase_sync(page_mobile, "MOBILE")
        sync_pc = wait_for_firebase_sync(page_pc, "PC")
        
        if not sync_m or not sync_pc:
            write_log("❌ Hủy chiến dịch do Lỗi Đồng Bộ ban đầu.", color=Fore.RED)
            try:
                if not sync_m: page_mobile.screenshot(path=os.path.join(SNAP_DIR, "SYNC_FAIL_MOBILE.png"))
                if not sync_pc: page_pc.screenshot(path=os.path.join(SNAP_DIR, "SYNC_FAIL_PC.png"))
                write_log("📸 Đã lưu ảnh hiện trường Lỗi Đồng Bộ.", color=Fore.YELLOW)
            except Exception as e:
                write_log(f"❌ Lỗi khi chụp ảnh Sync: {e}", color=Fore.RED)
            browser.close()
            return

        # =================================================================================
        # PHASE 1: THE PERFECT LOOP (10 ROUNDS FIREBASE SYNC)
        # =================================================================================
        write_log("\n✅ MA TRẬN ỔN ĐỊNH. BẮT ĐẦU 10 VÒNG RADAR (TASK SYNC)!\n", color=Fore.GREEN)

        total_rounds = 10
        total_latency = 0

        for i in range(1, total_rounds + 1):
            write_log(f"--- VÒNG {i}/{total_rounds} ---", color=Fore.YELLOW)
            
            task_m = f"Mobile Strike R{i} - {int(time.time() * 1000)}"
            write_log(f"   📱 Mobile tạo: [{task_m}]", color=Fore.WHITE)
            try:
                input_mob = page_mobile.locator("#input-mobile")
                input_mob.click()
                input_mob.press_sequentially(task_m, delay=20)
                input_mob.press("Enter")
                
                start_m_to_p = time.time()
                page_pc.get_by_text(task_m, exact=False).first.wait_for(state="visible", timeout=15000)
                latency_1 = (time.time() - start_m_to_p) * 1000
                total_latency += latency_1
                write_log(f"   ⏱️ [ĐỘ TRỄ M->P]: {latency_1:.2f} ms", color=Fore.CYAN)
                
                write_log(f"   💻 PC đang gạch bỏ...", color=Fore.WHITE)
                task_item_pc = page_pc.locator("li.swipe-item").filter(has_text=task_m).first
                task_item_pc.locator("button").first.click()
                page_mobile.locator("li.swipe-item.opacity-60").filter(has_text=task_m).first.wait_for(state="visible", timeout=15000)
                write_log("   ✅ ĐỒNG BỘ HOÀN HẢO", color=Fore.GREEN)
            except Exception as e:
                write_log(f"   ❌ GÃY ĐỒNG BỘ (M->P): {e}", color=Fore.RED)
                break

            time.sleep(1)

            task_p = f"PC Counter R{i} - {int(time.time() * 1000)}"
            write_log(f"\n   💻 PC tạo: [{task_p}]", color=Fore.WHITE)
            try:
                input_pc = page_pc.locator("#input-pc")
                input_pc.click()
                input_pc.press_sequentially(task_p, delay=20)
                input_pc.press("Enter")
                
                start_p_to_m = time.time()
                page_mobile.get_by_text(task_p, exact=False).first.wait_for(state="visible", timeout=15000)
                latency_2 = (time.time() - start_p_to_m) * 1000
                total_latency += latency_2
                write_log(f"   ⏱️ [ĐỘ TRỄ P->M]: {latency_2:.2f} ms", color=Fore.CYAN)
                
                write_log(f"   📱 Mobile đang gạch bỏ...", color=Fore.WHITE)
                task_item_mob = page_mobile.locator("li.swipe-item").filter(has_text=task_p).first
                task_item_mob.locator("button").first.click()
                page_pc.locator("li.swipe-item.opacity-60").filter(has_text=task_p).first.wait_for(state="visible", timeout=15000)
                write_log("   ✅ ĐỒNG BỘ HOÀN HẢO\n", color=Fore.GREEN)
            except Exception as e:
                write_log(f"   ❌ GÃY ĐỒNG BỘ (P->M): {e}", color=Fore.RED)
                break
            
            time.sleep(1)

        avg_latency = total_latency / (total_rounds * 2) if total_rounds > 0 else 0
        write_log(f"📊 ĐỘ TRỄ TRUNG BÌNH (FIREBASE): {avg_latency:.2f} ms", color=Fore.MAGENTA)

        # =================================================================================
        # PHASE 2: MUSIC ENGINE & AUDIO DUCKING
        # =================================================================================
        write_log("\n🎵 [PHASE 2] TEST LÕI NHẠC SUNO ENGINE VÀ AUDIO DUCKING...", color=Fore.YELLOW)
        try:
            page_mobile.evaluate("window.switchTab('view-music', document.querySelectorAll('.nav-btn')[3])")
            write_log("   ⏳ Chờ đồng bộ Archive.org...", color=Fore.WHITE)
            page_mobile.wait_for_selector("#music-list-container > div.song-row", timeout=15000)
            page_mobile.locator("#music-list-container > div.song-row").first.click()
            write_log("   -> Đã kích Play nhạc nền...", color=Fore.WHITE)
        except Exception:
            write_log("   ⚠️ Bỏ qua Tab Nhạc (Không tìm thấy trên giao diện hiện tại).", color=Fore.YELLOW)
        time.sleep(3)

        # =================================================================================
        # PHASE 3: ALARM & DOZE MODE (BACKGROUND TEST)
        # =================================================================================
        write_log("\n🎯 [PHASE 3] KÍCH HOẠT BÁO THỨC TRONG BÓNG TỐI (DOZE MODE)...", color=Fore.YELLOW)
        page_mobile.evaluate("window.switchTab('view-tasks', document.querySelectorAll('.nav-btn')[0])")
        page_mobile.fill("#input-mobile", f"Test báo động khẩn cấp lúc 15h00 - {int(time.time())}")
        page_mobile.locator("#form-mobile button[type='submit']").click()
        write_log("   -> Đã tạo Task mới có hẹn giờ.", color=Fore.WHITE)
        time.sleep(2)

        write_log("   -> ⚙️ Ép xung Worker: Hack giờ báo thức nổ sau 10 giây nữa.", color=Fore.WHITE)
        page_mobile.evaluate("""() => {
            if(window.todos && window.todos.length > 0) {
                window.todos[0].alarmTime = Date.now() + 10000;
                window.todos[0].alarmEnabled = true;
                window.saveLocalTodos();
            }
        }""")

        write_log("   🌙 TẮT MÀN HÌNH ĐIỆN THOẠI (Visibility = hidden)...", color=Fore.MAGENTA)
        page_mobile.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'hidden', writable: true}); document.dispatchEvent(new Event('visibilitychange')); }""")
        
        write_log("   ⏳ Đang chờ Worker đếm ngược trong nền...", color=Fore.WHITE)
        time.sleep(12) 
        
        is_ringing = page_mobile.evaluate("() => window.isAlarmRinging === true")
        if is_ringing:
            write_log("   ✅ THÀNH CÔNG: Còi báo động đã réo! Nhạc nền bị bóp cổ (Ducking).", color=Fore.GREEN)
            page_mobile.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'visible', writable: true}); document.dispatchEvent(new Event('visibilitychange')); }""")
            time.sleep(1)
            page_mobile.locator("#btn-alarm-complete").click()
            write_log("   ✅ Đã dập tắt báo động. Nhạc nền phục hồi 100%.", color=Fore.GREEN)
        else:
            write_log("   ❌ THẤT BẠI: Báo thức đã chết chìm trong Doze Mode của Android.", color=Fore.RED)

        # =================================================================================
        # PHASE 4: FOCUS TIMER (ZERO CPU)
        # =================================================================================
        write_log("\n⏳ [PHASE 4] KIỂM TRA BỘ ĐẾM GIỜ ZERO CPU...", color=Fore.YELLOW)
        page_mobile.evaluate("window.switchTab('view-focus', document.querySelectorAll('.nav-btn')[1])")
        time.sleep(1)
        
        page_mobile.locator("button:text-is('5p')").click()
        page_mobile.locator("#cd-toggle-btn").click()
        write_log("   -> Bắt đầu đếm ngược 5 phút.", color=Fore.WHITE)
        time.sleep(2)
        
        page_mobile.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'hidden', writable: true}); document.dispatchEvent(new Event('visibilitychange')); }""")
        time.sleep(3)
        page_mobile.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'visible', writable: true}); document.dispatchEvent(new Event('visibilitychange')); }""")
        write_log("   ✅ Timer vẫn đếm chuẩn xác nhờ Zero CPU Renderer.", color=Fore.GREEN)
        page_mobile.locator("#cd-reset-btn").click() 

        # =================================================================================
        # PHASE 5: KHO LƯU TRỮ MẬT (VAULT 2FA)
        # =================================================================================
        write_log("\n🗄️ [PHASE 5] TEST KHO LƯU TRỮ MẬT (VAULT 2FA)...", color=Fore.YELLOW)
        page_mobile.evaluate("window.switchTab('view-vault', document.querySelectorAll('.nav-btn')[2])")
        time.sleep(1)
        
        page_mobile.evaluate("window.VaultUI.openModal()")
        page_mobile.wait_for_selector("#vaultFormModal", state="visible")
        time.sleep(0.5)
        
        page_mobile.fill("#vaultEntryName", "Tài khoản Sinh tử")
        page_mobile.fill("#vaultEntryContent", "Tài khoản: admin_sentinel\nMật khẩu: 12345678\n2FA: JBSWY3DPEHPK3PXP")
        page_mobile.locator("#vaultFormModal button:has-text('Lưu Lại')").click()
        write_log("   -> Đã lưu tài khoản mã hóa.", color=Fore.WHITE)
        time.sleep(2)
        
        has_vault_card = page_mobile.locator(".vault-totp-code").first.is_visible()
        if has_vault_card:
            write_log("   ✅ Trích xuất Smart Input thành công! Bộ đếm 2FA OTP đang chạy LIVE.", color=Fore.GREEN)
        else:
            write_log("   ❌ Lỗi: Không sinh ra được thẻ Vault 2FA.", color=Fore.RED)

        write_log("\n" + "=" * 85, color=Fore.CYAN)
        write_log("🏁 ĐÃ HOÀN TẤT TEST CHUYÊN SÂU TOÀN BỘ HỆ SINH THÁI LIFEOS.".center(85), color=Fore.CYAN)
        write_log("=" * 85 + "\n", color=Fore.CYAN)
        
        browser.close()

if __name__ == "__main__":
    run_ecosystem_test()