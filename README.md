# 👩‍🌾 Telegram Chat Scraper (Telescraper)

A simple and customizable **Telegram chat/group message scraper** written in Python, using [Telethon](https://github.com/LonamiWebs/Telethon). It supports **historical message archiving**, **live message capturing**, and flexible **output formats** (CSV and plain text).

---

## ✨ Features

- 📥 **Scrape messages from any Telegram group/channel**
- ⏳ **Read historical messages** or 🟢 **monitor live messages**
- 📁 Saves per-user message history into:
  - `TXT` files (pretty printed)
  - `CSV` files (structured for analysis)
- 🚫 Ignore specific users by username
- 💾 Automatically resumes previous sessions
- 💡 Intuitive CLI-based user interface
- 🕵️ Ideal for OSINT use

---

## 📸 Screenshots

![screenshot](https://i.imgur.com/YLj7Cvz.png)

---

## ⚙️ Setup & Installation

### Add Your Telegram API Credentials

To connect to Telegram, you need to create an app and obtain:

- **API ID**
- **API Hash**

Get them from [https://my.telegram.org](https://my.telegram.org):

1. Log in with your Telegram account.
2. Click on **API Development Tools**.
3. Create a new application.
4. Copy your `api_id` and `api_hash`.
5. Put them into the python script

## 📋 Script Options

Inside the script, modify:

    OUTPUT_MODE = 3

Mode Description:
- `1`	— Pretty Text Only
- `2`	— CSV Only
- `3`	— Both CSV and Text (Default)

You can also set a more permanent ignore list by changing:

    IGNORE_LIST = []

## 💻 In App Options

The first time you open the app it will ask you for your Telegram phone number and code, then it will allow you to:

- **Select or create a chat/group session**
- **Enter group by ID or username**, or **select from your dialog list**
- **Choose mode**:
  - `1` — Read historical messages
  - `2` — Start live capture
- **Specify usernames to ignore** (comma-separated, optional)

When selecting a chat/group session it will ask you again for your Telegram phone number and code, this will be saved for that session and it won't ask you again when returning to it.

# 📤 Output Structure

The output structure consists of a main directory named Chat_Session_Name_GroupID, which contains the following files and subdirectories:

- chat_archive.csv: A global CSV archive file that stores chat data in a structured format.
- chat_archive.txt: A global text archive file that stores chat data in a readable text format.
- state.json: A JSON file that tracks the progress state of the chat session.
- per_user_messages/: A subdirectory that contains individual user message files. Each user has two files:
  - A text file named 123456789-john-doe.txt that stores the user's messages in a readable text format.
  - A CSV file named 123456789-john-doe.csv that stores the user's messages in a structured CSV format.

# 💡 Notes

- Make sure your Telegram account is active and not restricted.
- You can use this tool only on groups/channels you're a member of.
- If you are banned/kicked from a group the app will inform you and end the log.

