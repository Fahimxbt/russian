from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os

# ========== CONFIG FROM ENV ==========
STRING_SESSION = os.environ.get('STRING_SESSION')
API_ID = int(os.environ.get('API_ID', 25897592))
API_HASH = os.environ.get('API_HASH')

if not STRING_SESSION or not API_HASH:
    raise ValueError("Missing STRING_SESSION or API_HASH environment variables!")
# =====================================

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

bot_entity = None
sticker_msg_id = None
heyyy_msg_id = None
f_msg_id = None
match_active = False
promo_sent = False
sending_lock = False
promo_cancelled = False


async def find_sticker():
    global sticker_msg_id, heyyy_msg_id, f_msg_id
    try:
        msgs = await client.get_messages('me', limit=50)
        for m in msgs:
            if m.sticker:
                sticker_msg_id = m.id
                print("[+] Sticker found!")
            if m.text and m.text.lower() == 'heyyy':
                heyyy_msg_id = m.id
                print("[+] 'heyyy' message found!")
            if m.text and m.text.upper() == 'F':
                f_msg_id = m.id
                print("[+] 'F' message found!")

        if sticker_msg_id and heyyy_msg_id and f_msg_id:
            return True

    except Exception as e:
        print(f"[!] Find error: {e}")

    print("[!] Send 'heyyy', 'F', and sticker to Saved Messages first!")
    return False


async def click_find_partner():
    global match_active, promo_sent, promo_cancelled
    try:
        msgs = await client.get_messages(bot_entity, limit=5)
        for m in msgs:
            if m.reply_markup:
                for row in m.reply_markup.rows:
                    for btn in row.buttons:
                        if 'Find a Partner' in btn.text or 'Find' in btn.text:
                            try:
                                await m.click(text=btn.text)
                                print("[→] Find a Partner clicked")
                                match_active = False
                                promo_sent = False
                                promo_cancelled = False
                                return True
                            except:
                                continue
    except Exception as e:
        print(f"[!] get_messages error: {e}")

    try:
        await client.send_message(bot_entity, '/search')
        print("[→] /search sent (fallback)")
    except Exception as e:
        print(f"[!] Fallback error: {e}")

    match_active = False
    promo_sent = False
    promo_cancelled = False
    return True


async def send_stop_and_next():
    global match_active, promo_sent, promo_cancelled
    try:
        await client.send_message(bot_entity, '/stop')
        print("[→] /stop sent")
        await asyncio.sleep(3)
        await click_find_partner()
    except Exception as e:
        print(f"[!] Stop/Next error: {e}")
        match_active = False
        promo_sent = False
        promo_cancelled = False


async def send_promo():
    global promo_sent, sending_lock, promo_cancelled

    if sending_lock or promo_sent:
        print("[*] Already sending or already sent, skipping...")
        return

    sending_lock = True
    promo_cancelled = False
    print("[*] Starting forward sequence...")

    try:
        if promo_cancelled:
            print("[!] Promo cancelled before heyyy")
            return

        if heyyy_msg_id:
            await client.forward_messages(bot_entity, heyyy_msg_id, 'me')
            print("[+] Forwarded: heyyy")
        else:
            await client.send_message(bot_entity, "heyyy")
            print("[+] Sent: heyyy")

        await asyncio.sleep(3)

        if promo_cancelled:
            print("[!] Promo cancelled before F")
            return

        if f_msg_id:
            await client.forward_messages(bot_entity, f_msg_id, 'me')
            print("[+] Forwarded: F")
        else:
            await client.send_message(bot_entity, "F")
            print("[+] Sent: F")

        await asyncio.sleep(3)

        if promo_cancelled:
            print("[!] Promo cancelled before sticker")
            return

        if sticker_msg_id:
            await client.forward_messages(bot_entity, sticker_msg_id, 'me')
            print("[+] Sticker forwarded!")
        else:
            await client.send_message(bot_entity, "💜 @chatxbt_bot\nhttps://t.me/chatxbt_bot")
            print("[+] Text promo sent!")

        promo_sent = True
        await asyncio.sleep(3)

    except Exception as e:
        print(f"[!] Send error: {e}")

    finally:
        sending_lock = False


@client.on(events.NewMessage(chats='@Anonymouslyrobot'))
async def handler(event):
    global match_active, promo_sent, sending_lock, promo_cancelled
    text = event.text or ''

    if ('Your partner ended the chat' in text or 
        'You left the chat' in text or
        "I'm an anonymous chat bot" in text):

        if sending_lock and not promo_sent:
            print("[!] Chat ended during promo! Cancelling...")
            promo_cancelled = True

        print("[✓] Chat ended, finding new partner...")
        match_active = False
        promo_sent = False
        await asyncio.sleep(3)
        await click_find_partner()
        return

    if sending_lock:
        print("[*] Currently sending, ignoring new message...")
        return

    if 'Start chatting' in text:
        print("[+] Match started!")
        match_active = True
        promo_sent = False
        promo_cancelled = False
        await asyncio.sleep(1)
        await send_promo()

        if not promo_cancelled:
            await send_stop_and_next()
        else:
            print("[!] Promo was cancelled, skipping /stop")
            sending_lock = False
        return

    if 'Finding a partner soon' in text:
        print("[...] Searching...")
        match_active = False
        promo_sent = False
        return

    if match_active and not event.out and not promo_sent and not sending_lock:
        print("[+] Partner messaged first!")
        await send_promo()
        if not promo_cancelled:
            await send_stop_and_next()


async def main():
    global bot_entity
    await client.start()
    print("[*] xbt1-bot (Anonymouslyrobot) started!")

    bot_entity = await client.get_entity('@Anonymouslyrobot')
    await find_sticker()
    await click_find_partner()

    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
