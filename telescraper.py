
import json
import os
import re
import asyncio
import time
import unicodedata
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ChannelPrivateError
from pathlib import Path
from colorama import init, Fore, Back, Style, just_fix_windows_console
import ctypes

# Initialize Colorama
init(autoreset=True, convert=True, strip=False)
just_fix_windows_console()

def set_window_title(title):
    # Encode the title to ANSI
    title_ansi = title.encode('ansi', 'ignore')
    ctypes.windll.kernel32.SetConsoleTitleA(title_ansi)

# Your credentials from https://my.telegram.org
api_id   = #  
api_hash = '#'

# Version Info
version = "1.0.0"
set_window_title('Telegram Scraper')

# Output Mode: 1 = Pretty Text Only, 2 = CSV Only, 3 = Both
OUTPUT_MODE = 3

# Global Ignore List (Populated At Runtime)
IGNORE_LIST = []  # Sanitized Usernames To Ignore (Leading '@' Will Be Stripped)


def sanitize_filename(name: str) -> str:
    # Sanitize A String For Safe Filenames by replacing invalid chars including backslashes
    return re.sub(r'[\\\\\\/\:\*\?"<>|]+', '_', name)


def csv_quote(field: str) -> str:
    # Escape, quote a field for CSV, replacing newlines and converting emojis to unicode
    def replace_char(c):
        cat = unicodedata.category(c)
        if cat.startswith('So'):
            return f"\\U{ord(c):08x}"
        return c
    processed = ''.join(replace_char(ch) for ch in field)
    escaped = processed.replace('"', '""').replace('\n', '\\n')
    return f'"{escaped}"'


def write_with_retry(path: Path, data: str, mode: str = 'a', encoding: str = 'utf-8'):
    # Write data to file, retrying on PermissionError (e.g., when file is open in another program).
    while True:
        try:
            with open(path, mode, encoding=encoding) as f:
                f.write(data)
            return
        except PermissionError:
            time.sleep(0.5)

async def fetch_dialogs(client):
    return [dialog async for dialog in client.iter_dialogs()]

async def fetch_entity(client, group_id):
    return await client.get_entity(group_id)

def list_local_sessions():
    return [d for d in os.listdir('.') if os.path.isdir(d) and Path(d, 'state.json').exists()]

async def create_new_chat(client):
    while True:
        print(Fore.MAGENTA + "\n=== Create New Chat Session ===\n")
        print(Fore.MAGENTA + " 1) " + Fore.WHITE + "Enter Group Identifier (Numeric Id Or @Username)")
        print(Fore.MAGENTA + " 2) " + Fore.WHITE + "List And Select From Your Dialogs\n")
        choice = input(Fore.MAGENTA + "Choose 1 Or 2: " + Style.RESET_ALL).strip()
        if choice == '1':
            ident = input(Fore.MAGENTA + "Enter Group_Identifier Or @Username: " + Style.RESET_ALL).strip()
            try: group_id = int(ident)
            except ValueError: group_id = ident
            try:
                entity = await fetch_entity(client, group_id)
                raw_title = getattr(entity, 'title', None) or getattr(entity, 'name', None)
            except Exception:
                raw_title = ident
        elif choice == '2':
            dialogs = await fetch_dialogs(client)
            print(Fore.MAGENTA + "\n=== Select A Chat By Number ===")
            for idx, dlg in enumerate(dialogs, start=1):
                print(Fore.MAGENTA + f" {idx}) " + Fore.WHITE + f"{dlg.name} ({dlg.id})")
            sel = input(Fore.MAGENTA + "\nEnter Number: " + Style.RESET_ALL).strip()
            if not sel.isdigit() or not (1 <= int(sel) <= len(dialogs)):
                print(Fore.RED + "Invalid Selection, Try Again.\n")
                continue
            dlg = dialogs[int(sel) - 1]
            group_id = dlg.id
            raw_title = dlg.name
        else:
            print(Fore.RED + "Invalid Choice. Please Enter 1 Or 2.\n")
            continue

        title = sanitize_filename(raw_title or str(group_id))
        chat_dir = f"{title}_{group_id}"
        Path(chat_dir).mkdir(exist_ok=True)
        state = {"last_id": 0, "group_id": group_id}
        Path(chat_dir, 'state.json').write_text(json.dumps(state), encoding='utf-8')
        if OUTPUT_MODE & 2:
            csv_file = Path(chat_dir, 'chat_archive.csv')
            if not csv_file.exists():
                csv_file.write_text('timestamp,id,username,name,message\n', encoding='utf-8')
        if OUTPUT_MODE & 1:
            txt_file = Path(chat_dir, 'chat_archive.txt')
            txt_file.touch(exist_ok=True)
        print(Fore.GREEN + f"\nSession Directory Created: {chat_dir}\n")
        return chat_dir, state

async def choose_chat():
    sessions = list_local_sessions()
    async with TelegramClient('temp_session', api_id, api_hash) as client:
        if sessions:
            print(Fore.MAGENTA + "\n=== Existing Chat Sessions ===\n")
            for i, name in enumerate(sessions, start=1):
                print(Fore.YELLOW + f" {i}) " + Fore.WHITE + name)
            print(Fore.YELLOW + " N) " + Fore.WHITE + "New Chat Session\n")
            sel = input(Fore.MAGENTA + "Select A Number Or 'N': " + Style.RESET_ALL).strip().lower()
            if sel == 'n': return await create_new_chat(client)
            if sel.isdigit() and 1 <= int(sel) <= len(sessions):
                chat_dir = sessions[int(sel)-1]
                state = json.loads(Path(chat_dir,'state.json').read_text(encoding='utf-8'))
                print(Fore.GREEN + f"\nResuming Session: {chat_dir}\n")
                return chat_dir, state
            print(Fore.RED + "Invalid Choice, Creating New Session.\n")
            return await create_new_chat(client)
        return await create_new_chat(client)

def setup_ignore():
    ignore = input(Fore.YELLOW + "Enter Usernames To Ignore (Comma-Separated, '@' Optional): " + Style.RESET_ALL).strip()
    global IGNORE_LIST
    IGNORE_LIST = [sanitize_filename(u.strip().lstrip('@')) for u in ignore.split(',') if u.strip()]
    print(Fore.YELLOW + "Ignore List Set: " + ", ".join(IGNORE_LIST) + "\n")

def get_display_name(entity):
    # Users have first_name/last_name, Groups/Channels have title or name
    parts = []
    if getattr(entity, 'first_name', None):
        parts.append(entity.first_name)
    if getattr(entity, 'last_name', None):
        parts.append(entity.last_name)
    if parts:
        return ' '.join(parts)
    return getattr(entity, 'title', None) or getattr(entity, 'name', None) or 'N/A'

async def read_latest(client, chat_dir, state):
    print(Fore.MAGENTA + "\n=== Reading Historical Messages ===\n")
    group_id = state['group_id']
    last_id = max(state.get('last_id', 0), 0)
    out_dir = Path(chat_dir, 'per_user_messages')
    out_dir.mkdir(exist_ok=True)
    archive_csv = Path(chat_dir, 'chat_archive.csv')
    archive_txt = Path(chat_dir, 'chat_archive.txt')

    try:
        async for msg in client.iter_messages(group_id, min_id=last_id, reverse=True):
            if not msg.sender_id or not msg.text:
                continue
            sender = await msg.get_sender()
            display_name = get_display_name(sender)
            username = getattr(sender, 'username', 'N/A') or 'N/A'
            user_id = sender.id

            if sanitize_filename(username or display_name) in IGNORE_LIST:
                continue

            timestamp = msg.date.isoformat()
            text_line = f"{timestamp} | {user_id} | @{username} | {display_name} | {msg.text}\n"
            csv_row = ','.join([
                csv_quote(timestamp),
                csv_quote(str(user_id)),
                csv_quote(username),
                csv_quote(display_name),
                csv_quote(msg.text)
            ]) + '\n'
            safe_name = sanitize_filename(f"{user_id}-{username}-{display_name}")

            # Per-user files
            if OUTPUT_MODE & 1:
                user_txt = out_dir / f"{safe_name}.txt"
                user_txt.touch(exist_ok=True)
                write_with_retry(user_txt, text_line)
            if OUTPUT_MODE & 2:
                user_csv = out_dir / f"{safe_name}.csv"
                if not user_csv.exists():
                    user_csv.write_text('timestamp,id,username,name,message\n', encoding='utf-8')
                write_with_retry(user_csv, csv_row)

            # Global archives
            if OUTPUT_MODE & 1:
                write_with_retry(archive_txt, text_line)
            if OUTPUT_MODE & 2:
                write_with_retry(archive_csv, csv_row)

            print(Fore.WHITE + f"[Latest] Saved: {timestamp} | {user_id} | @{username} | {display_name} | {msg.text}")

            if msg.id > state.get('last_id', 0):
                state['last_id'] = msg.id

        # All messages read successfully
        Path(chat_dir, 'state.json').write_text(json.dumps(state), encoding='utf-8')
        print(Fore.GREEN + f"\nHistorical Archive Updated. Last Id = {state['last_id']}\n")

    except ChannelPrivateError:
        print(Fore.RED + "You Lack Permission Or You Have Been Banned From This Channel.\n")
        while True:
            choice = input(Fore.MAGENTA + "Return To Menu (M) Or Quit (Q): " + Style.RESET_ALL).strip().lower()
            if choice == 'm':
                return 'menu'
            if choice == 'q':
                print(Fore.GREEN + "Goodbye!\n")
                exit(0)
            print(Fore.RED + "Invalid Choice. Enter M Or Q.\n")

    # After successful read, prompt user
    while True:
        choice = input(Fore.MAGENTA + "Return To Menu (M) Or Quit (Q): " + Style.RESET_ALL).strip().lower()
        if choice == 'm':
            return 'menu'
        if choice == 'q':
            print(Fore.GREEN + "Goodbye!\n")
            exit(0)
        print(Fore.RED + "Invalid Choice. Enter M Or Q.\n")


async def live_read(client, chat_dir, state):
    print(Fore.MAGENTA + "\n=== Live Reading Messages ===\n")
    out_dir = Path(chat_dir, 'per_user_messages'); out_dir.mkdir(exist_ok=True)
    archive_csv = Path(chat_dir, 'chat_archive.csv')
    archive_txt = Path(chat_dir, 'chat_archive.txt')

    @client.on(events.NewMessage(chats=state['group_id']))
    async def handler(event):
        msg = event.message
        if not msg.sender_id or not msg.text:
            return
        sender = await msg.get_sender()
        display_name = get_display_name(sender)
        username = getattr(sender, 'username', 'N/A') or 'N/A'
        user_id = sender.id

        if sanitize_filename(username or display_name) in IGNORE_LIST:
            return

        timestamp = msg.date.isoformat()
        text_line = f"{timestamp} | {user_id} | @{username} | {display_name} | {msg.text}\n"
        csv_row = ','.join([
            csv_quote(timestamp),
            csv_quote(str(user_id)),
            csv_quote(username),
            csv_quote(display_name),
            csv_quote(msg.text)
        ]) + '\n'
        safe_name = sanitize_filename(f"{user_id}-{username}-{display_name}")

        if OUTPUT_MODE & 1:
            user_txt = out_dir / f"{safe_name}.txt"
            user_txt.touch(exist_ok=True)
            write_with_retry(user_txt, text_line)
            write_with_retry(archive_txt, text_line)
        if OUTPUT_MODE & 2:
            user_csv = out_dir / f"{safe_name}.csv"
            if not user_csv.exists():
                user_csv.write_text('timestamp,id,username,name,message\n', encoding='utf-8')
            write_with_retry(user_csv, csv_row)
            write_with_retry(archive_csv, csv_row)

        print(Fore.WHITE + f"[Live] Saved: {timestamp} | {user_id} | @{username} | {display_name} | {msg.text}")
        Path(chat_dir, 'state.json').write_text(
            json.dumps({'last_id': msg.id, 'group_id': state['group_id']}),
            encoding='utf-8'
        )

    print(Fore.GREEN + "Live Read Started. Press Ctrl+C To Stop.\n")
    await client.run_until_disconnected()
def print_banner():
    print(
        Fore.MAGENTA
        + r"""
  _____    _
 |_   _|__| |___ ___ __ _ _ __ _ _ __  ___ _ _
   | |/ -_) / -_|_-</ _| '_/ _` | '_ \/ -_) '_|
   |_|\___|_\___/__/\__|_| \__,_| .__/\___|_|
                                |_|
"""
        + Style.RESET_ALL
    )

async def main():
    print_banner()
    while True:
        chat_dir,state=await choose_chat()
        setup_ignore()
        mode=input(Fore.GREEN+"Choose Mode - (1) Read Historical, (2) Live Read: "+Style.RESET_ALL).strip()
        async with TelegramClient(chat_dir, api_id, api_hash) as client:
            if mode=='1':
                res = await read_latest(client,chat_dir,state)
                if res=='menu': continue
                else: break
            else:
                await live_read(client,chat_dir,state)
                break

if __name__ == '__main__':
    import sys

    try:
        asyncio.run(main())
    except PermissionError:
        print(Fore.RED + "❌ Access Denied: Please Run As Administrator Or Adjust Permissions And Try Again.")
        input()
        sys.exit(1)
    except ConnectionError:
        print(Fore.RED + "❌ Could Not Connect To Telegram After Multiple Attempts. Check Your Network Or API Credentials.")
        input()
        sys.exit(1)
    except Exception as e:
        print(Fore.RED + f"❌ Unexpected Error: {e}")
        input()
        sys.exit(1)
