# -*- coding: utf-8 -*-
"""
SENTINEL MASTER SUITE (V3.1) - MỤC TIÊU: MIMIHOALUA / XIEMSANSANG
Tối ưu: Tương thích kiến trúc Single Native Audio + V2 Passive Anchor.
Bảo vệ: Bọc thép ép kiểu NaN, Smart Polling chờ OS nạp Metadata.
"""

import os
import time
import urllib.parse
import colorama
from colorama import Fore, Style
from playwright.sync_api import sync_playwright, Page, Response, BrowserContext, TimeoutError as PlaywrightTimeoutError

colorama.init()

TARGET_URL = "https://mimihoalua.github.io/tool/nghenhac.html"
XIAOMI_USER_AGENT = "Mozilla/5.0 (Linux; Android 13; 2306EPN60G Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"

def format_time(seconds: float) -> str:
    """Format thời gian giây sang chuỗi MM:SS. Bọc thép chống lỗi NaN lọt từ JS."""
    if seconds is None or seconds != seconds or seconds < 0: 
        return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def handle_response(response: Response) -> None:
    """Bắt và log các luồng mạng MP3."""
    if ".mp3" in response.url.lower():
        status = response.status
        file_name = urllib.parse.unquote(response.url.split('/')[-1])
        if status == 200:
            print(Fore.GREEN + f"   [MẠNG] Kéo nguyên file (200): {file_name[-40:]}" + Style.RESET_ALL)
        elif status in [301, 302]:
            print(Fore.YELLOW + f"   [MẠNG] Redirect (302): {file_name[-40:]}" + Style.RESET_ALL)

def handle_audio_sensor(event_data: dict) -> None:
    """In log Siêu Debug để theo dõi vòng đời thẻ Audio."""
    evt = event_data.get("event", "unknown")
    audio_id = event_data.get("id", "audio")
    src = urllib.parse.unquote(event_data.get("src", "none"))[-40:] 
    curr_time = format_time(event_data.get("time", 0))
    ready = event_data.get("ready", 0)
    network = event_data.get("network", 0)
    
    prefix = f"   [⚡ SENSOR - {audio_id}]"
    details = f"(Time: {curr_time} | R-State: {ready} | N-State: {network} | Src: {src})"
    
    if evt in ["playing", "canplay"]:
        print(Fore.GREEN + f"{prefix} {evt.upper()} {details}" + Style.RESET_ALL)
    elif evt in ["waiting", "stalled", "loadstart"]:
        print(Fore.YELLOW + f"{prefix} {evt.upper()} {details}" + Style.RESET_ALL)
    elif evt == "error":
        print(Fore.RED + f"{prefix} ERROR/CRASH {details}" + Style.RESET_ALL)
    elif evt == "ended":
        print(Fore.MAGENTA + f"{prefix} ENDED {details}" + Style.RESET_ALL)
    else: 
        print(Fore.CYAN + f"{prefix} {evt.upper()} {details}" + Style.RESET_ALL)

def inject_super_debug(page: Page) -> None:
    """Cấy máy đo nhịp tim vào mọi thẻ Audio trên DOM."""
    page.evaluate("""() => {
        const attachAudioMonitors = () => {
            const events = ['play', 'playing', 'pause', 'waiting', 'stalled', 'error', 'ended', 'loadstart', 'canplay'];
            document.querySelectorAll('audio').forEach(audio => {
                if(audio.dataset.monitored) return;
                audio.dataset.monitored = 'true';
                events.forEach(evt => {
                    audio.addEventListener(evt, e => {
                        if (window.pyAudioSensor) {
                            window.pyAudioSensor({
                                event: e.type,
                                id: e.target.id || 'Unnamed-Audio',
                                src: e.target.src || 'none',
                                time: (!isNaN(e.target.currentTime) ? e.target.currentTime : 0),
                                ready: e.target.readyState,
                                network: e.target.networkState
                            });
                        }
                    });
                });
            });
        };
        attachAudioMonitors();
        const observer = new MutationObserver(attachAudioMonitors);
        observer.observe(document.body, { childList: true, subtree: true });
    }""")

def bypass_autoplay_and_init(page: Page) -> None:
    print("⏳ Đang kết nối Trạm phát nhạc & Cấy máy đo Sensor...")
    page.goto(TARGET_URL)
    
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

    inject_super_debug(page)

    try:
        # Nhấp vào nút "Khởi Động & Phát Nhạc" trên UI
        btn_locator = page.locator("button:has-text('Khởi Động')").first
        btn_locator.wait_for(state="visible", timeout=3000)
        btn_locator.click()
        print(Fore.GREEN + "✅ Đã kích hoạt Play bằng nút UI." + Style.RESET_ALL)
    except PlaywrightTimeoutError:
        print(Fore.YELLOW + "⚠️ Không thấy nút UI, kích hoạt Fallback click..." + Style.RESET_ALL)
        page.mouse.click(200, 400)
    time.sleep(2)

# =====================================================================
# PHASE 1: HARDWARE FLOW (TUA CHUẨN QUA BÀI)
# =====================================================================
def run_phase_1_hardware_flow(context: BrowserContext) -> None:
    print(Fore.CYAN + "\n" + "=" * 80)
    print("🚀 PHASE 1: XIAOMI 13T SIMULATOR - HARDWARE FLOW".center(80))
    print("=" * 80 + Style.RESET_ALL)
    
    page = context.new_page()
    page.expose_function("pyAudioSensor", handle_audio_sensor)
    page.on("response", handle_response)
    bypass_autoplay_and_init(page)

    track_count = 1
    while track_count <= 2: 
        print(Fore.CYAN + f"\n--- BÀI TEST SỐ {track_count} ---" + Style.RESET_ALL)
        time.sleep(4)
        
        audio_state = page.evaluate("""() => {
            const a = document.getElementById('mstq-player');
            if(!a || a.paused) return null;
            return { playing: true, dur: (!isNaN(a.duration) ? a.duration : 0), src: a.src, ready: a.readyState };
        }""")
        
        if not audio_state:
            print(Fore.RED + "❌ Lỗi: Không tìm thấy Audio chính đang hát." + Style.RESET_ALL)
            break
            
        if audio_state['dur'] > 30:
            print(f"   🎵 Tua đến 20s cuối để mô phỏng chuyển bài tự nhiên...")
            page.evaluate("""() => {
                const a = document.getElementById('mstq-player');
                if(a && !isNaN(a.duration) && a.duration > 30) a.currentTime = a.duration - 20;
            }""")
            time.sleep(1)

        print(Fore.MAGENTA + "   🌙 TẮT MÀN HÌNH (Visibility = hidden)... Đợi HĐH MIUI ra tay..." + Style.RESET_ALL)
        page.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'hidden', writable: true}); document.dispatchEvent(new Event('visibilitychange')); }""")
        
        time.sleep(25) 
        
        new_state = page.evaluate("""() => {
            const a = document.getElementById('mstq-player');
            return a ? { ready: a.readyState, src: a.src } : null;
        }""")
        
        if not new_state:
            print(Fore.RED + "   ❌ Mất thẻ Audio." + Style.RESET_ALL)
            break

        if new_state['src'] != audio_state['src']:
            if new_state['ready'] < 3:
                print(Fore.RED + f"   🚨 CẢNH BÁO BÓNG MA: ReadyState = {new_state['ready']}. BỊ MIUI CẮT LOA!" + Style.RESET_ALL)
                break
            else:
                print(Fore.GREEN + f"   ✨ PHẦN CỨNG TỐT (ReadyState {new_state['ready']}). Bất tử thành công." + Style.RESET_ALL)
                track_count += 1
        else:
            print(Fore.RED + "   ❌ LỖI KẸT BÀI: Nhạc dừng cứng ở bài cũ." + Style.RESET_ALL)
            break
    page.close()

# =====================================================================
# PHASE 2: SMART SEEK MARATHON (TEST ĐỘ BỀN)
# =====================================================================
def run_phase_3_marathon(context: BrowserContext) -> None:
    START_INDEX = 0 
    TOTAL_TRACKS = 50 
    
    print(Fore.CYAN + "\n" + "=" * 80)
    print(f"🚀 PHASE 2: SMART SEEK MARATHON (BẮT ĐẦU TỪ BÀI {START_INDEX + 1})".center(80))
    print("=" * 80 + Style.RESET_ALL)
    
    page = context.new_page()
    page.expose_function("pyAudioSensor", handle_audio_sensor)
    page.on("response", handle_response)
    bypass_autoplay_and_init(page)

    print(Fore.YELLOW + f"▶️ Kích hoạt UI Bài số {START_INDEX + 1}..." + Style.RESET_ALL)
    try:
        page.locator(".song-row").nth(START_INDEX).click(timeout=3000)
        time.sleep(3)
    except PlaywrightTimeoutError:
        try:
            page.locator(".song-row").nth(0).click()
        except:
            pass

    print(Fore.MAGENTA + "   🌙 TẮT MÀN HÌNH - ÉP MÔI TRƯỜNG ZERO CPU NGAY TỪ ĐẦU..." + Style.RESET_ALL)
    page.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'hidden', writable: true}); document.dispatchEvent(new Event('visibilitychange')); }""")
    
    track_counter = 1
    while track_counter <= TOTAL_TRACKS: 
        dur_sec = 0
        poll_count = 0
        telemetry = None
        
        # Mắt thần chờ OS load xong Metadata (chống lỗi NaN)
        while dur_sec <= 0 and poll_count < 15:
            telemetry = page.evaluate("""() => {
                const activeRow = document.querySelector('.song-row.active');
                const a = document.getElementById('mstq-player');
                let songTitle = activeRow ? (activeRow.querySelector('.font-bold')?.innerText || activeRow.querySelector('.font-semibold')?.innerText || 'Unknown') : 'Unknown';
                return {
                    ui_title: songTitle,
                    audio_src: a ? a.src : '',
                    audio_duration: (a && !isNaN(a.duration) && isFinite(a.duration)) ? a.duration : 0
                };
            }""")
            dur_sec = telemetry.get('audio_duration', 0)
            if dur_sec > 0: break
            time.sleep(1)
            poll_count += 1
            
        if not telemetry or not telemetry['audio_src']:
            print(Fore.RED + "❌ Thẻ Audio đã biến mất khỏi DOM." + Style.RESET_ALL)
            break
            
        print(Fore.CYAN + f"\n--- BÀI HÁT: [{telemetry['ui_title']}] (Thời lượng: {format_time(dur_sec)}) ---" + Style.RESET_ALL)

        reached_end_zone = False
        stall_counter = 0

        while not reached_end_zone:
            time.sleep(4)
            status = page.evaluate("""() => {
                const a = document.getElementById('mstq-player');
                let bufferedEnd = 0;
                if (a && a.buffered.length > 0) bufferedEnd = a.buffered.end(a.buffered.length - 1);
                return { 
                    current: (a && !isNaN(a.currentTime)) ? a.currentTime : 0, 
                    buffered: (!isNaN(bufferedEnd)) ? bufferedEnd : 0, 
                    network: a ? a.networkState : 0 
                };
            }""")
            
            buf_sec, curr_sec = status['buffered'], status['current']
            
            if status['network'] == 3:
                 print(Fore.RED + "🚨 BÁO ĐỘNG: MẤT TIẾNG (NO_SOURCE)!" + Style.RESET_ALL)
                 break

            target_end_sec = dur_sec - 20
            if target_end_sec <= 0 or curr_sec >= target_end_sec:
                reached_end_zone = True
                break

            safe_jump = buf_sec - 3
            if safe_jump >= target_end_sec:
                print(Fore.YELLOW + f"   ⏩ Buffer đủ. Tua thẳng đến 20s cuối..." + Style.RESET_ALL)
                page.evaluate(f"const a = document.getElementById('mstq-player'); if(a && !isNaN(a.duration)) a.currentTime = {target_end_sec};")
                reached_end_zone = True
            elif safe_jump > curr_sec + 5:
                page.evaluate(f"const a = document.getElementById('mstq-player'); if(a) a.currentTime = {safe_jump};")
                stall_counter = 0
            else:
                stall_counter += 1
                if stall_counter > 5:
                    page.evaluate(f"const a = document.getElementById('mstq-player'); if(a) a.currentTime = {curr_sec + 10};")
                    stall_counter = 0

        # Vùng đợi chuyển bài tự nhiên
        if dur_sec > 30: time.sleep(25)
        else: time.sleep(dur_sec + 5)
        
        new_src = page.evaluate("() => { const a = document.getElementById('mstq-player'); return a ? a.src : ''; }")
        
        if new_src != telemetry['audio_src']:
            print(Fore.GREEN + f"✅ Qua bài mới thành công trong nền! (Prefetch & Anchor hoạt động hoàn hảo)" + Style.RESET_ALL)
            track_counter += 1
        else:
            print(Fore.RED + "❌ LỖI ĐỨT GÃY: Không sang bài. Luồng đã bị chặn." + Style.RESET_ALL)
            break
            
    page.close()

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=XIAOMI_USER_AGENT,
            viewport={"width": 412, "height": 915},
            is_mobile=True,
            has_touch=True
        )
        try:
            run_phase_1_hardware_flow(context)
            time.sleep(2)
            run_phase_3_marathon(context)
        except Exception as e:
            print(Fore.RED + f"\nLỖI THỰC THI CHÍNH: {e}" + Style.RESET_ALL)
        finally:
            print(Fore.CYAN + "\n========================================================")
            print("🏁 ĐÃ HOÀN TẤT TOÀN BỘ CHUỖI KIỂM THỬ (MASTER SUITE V3.1).")
            print("========================================================" + Style.RESET_ALL)
            browser.close()

if __name__ == "__main__":
    main()