import re
import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ========= CONFIG =========
EXCEL_PATH = "numbers.xlsx"
PHONE_COLUMN = "Phone"
DEFAULT_COUNTRY_CODE = "91"

CAPTION = """hello"""

USER_DATA_DIR = "wa_profile"

WHATSAPP_LOAD_TIMEOUT_MS = 120_000
RESULT_WAIT_MS = 45_000
CHATBOX_WAIT_MS = 45_000

WAIT_AFTER_SEND_SEC = 1.2
WAIT_BETWEEN_NUMBERS_SEC = 1.0
# ==========================

def is_no_results_screen(page) -> bool:

    return page.locator("text=No results found for").count() > 0


def go_home(page) -> None:
    """
    Bring WhatsApp back to the main UI so the next iteration can click New chat.
    This fixes getting stuck on the 'New chat' / 'No results found' screen.
    """

    try:
        page.keyboard.press("Escape")
        time.sleep(0.3)
        page.keyboard.press("Escape")
        time.sleep(0.3)
    except:
        pass

    # If back arrow is visible (top-left), click it
    back_candidates = [
        "button[aria-label='Back']",
        "div[role='button'][aria-label='Back']",
        "span[data-icon='back']",
        "span[data-icon='back-light']",
    ]
    for sel in back_candidates:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.click(timeout=1500)
                time.sleep(0.4)
                break
        except:
            pass

    try:
        page.wait_for_selector("div[aria-label='Chat list'], div[role='grid'][aria-label='Chat list']",
                               timeout=10_000)
    except:

        try:
            page.goto("https://web.whatsapp.com")
            wait_for_whatsapp_ready(page, timeout_ms=60_000)
        except:
            pass

def extract_and_clean_phone(value) -> str | None:
    if pd.isna(value):
        return None
    s = str(value).strip()

    runs = re.findall(r"\d{6,}", s)
    if not runs:
        return None

    digits = re.sub(r"\D", "", max(runs, key=len))
    digits = digits.lstrip("0")
    if not digits:
        return None

    if len(digits) == 10 and DEFAULT_COUNTRY_CODE:
        digits = DEFAULT_COUNTRY_CODE + digits

    if len(digits) < 10 or len(digits) > 15:
        return None

    return digits


def _mod_key(page) -> str:
    # Windows/Linux -> Control, Mac -> Meta
    try:
        platform = page.evaluate("navigator.platform") or ""
        return "Meta" if "mac" in platform.lower() else "Control"
    except:
        return "Control"


def wait_for_whatsapp_ready(page, timeout_ms=WHATSAPP_LOAD_TIMEOUT_MS):
    page.wait_for_function(
        """
        () => {
            const selectors = [
                "div[aria-label='Chat list']",
                "div[role='grid'][aria-label='Chat list']",
                "input[placeholder*='Search']",
                "button[aria-label='New chat']",
                "div[role='button'][aria-label='New chat']",
                "[data-icon='new-chat-outline']",
                "span[data-icon='new-chat-outline']"
            ];
            return selectors.some(sel => document.querySelector(sel));
        }
        """,
        timeout=timeout_ms
    )


def click_new_chat(page) -> bool:
    candidates = [
        page.locator("button[aria-label='New chat']"),
        page.locator("div[role='button'][aria-label='New chat']"),
        page.locator("[data-icon='new-chat-outline']"),
        page.locator("span[data-icon='new-chat-outline']"),
    ]
    for c in candidates:
        try:
            if c.count() > 0:
                c.first.click(timeout=8000)
                return True
        except:
            pass
    return False


def type_in_search(page, value: str) -> bool:
    # WhatsApp search box varies, so keep it flexible
    candidates = [
        page.locator("input[placeholder*='Search']"),
        page.locator("input[type='text']"),
        page.locator("div[contenteditable='true'][role='textbox']"),
        page.locator("div[contenteditable='true']"),
    ]
    for loc in candidates:
        try:
            if loc.count() == 0:
                continue
            loc.first.click(timeout=8000)
            mod = _mod_key(page)
            page.keyboard.press(f"{mod}+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(value, delay=35)
            return True
        except:
            continue
    return False


def no_results_found(page) -> bool:
    # Example: "No results found for '91xxxx...'"
    return page.locator("span:has-text(\"No results found for '\")").count() > 0


def open_chat_from_search_results(page, phone_digits: str) -> bool:
    """
    Click the correct row in search results.
    Works for "Not in your contacts" list and normal matches.
    """
    last10 = phone_digits[-10:]

    # wait a bit for results list
    spans = page.locator("span[title]")
    try:
        spans.first.wait_for(timeout=RESULT_WAIT_MS)
    except:
        return False

    count = spans.count()
    for i in range(min(count, 120)):
        try:
            title = spans.nth(i).get_attribute("title") or ""
            title_digits = re.sub(r"\D", "", title)

            # match by last 10 digits (safe across formats)
            if last10 and last10 in title_digits:
                try:
                    spans.nth(i).click(timeout=8000)
                    return True
                except:
                    parent = spans.nth(i).locator(
                        "xpath=ancestor::div[@role='button' or @role='row' or @role='gridcell'][1]"
                    )
                    if parent.count() > 0:
                        parent.first.click(timeout=8000)
                        return True
                    # final fallback: closest div
                    spans.nth(i).locator("xpath=ancestor::div[1]").click(timeout=8000)
                    return True
        except:
            continue

    return False


def paste_image_caption_and_send(page, caption: str) -> None:
    """
    INLINE + DIALOG compatible.
    Fixes page.evaluate argument error by passing a single arg object.
    Types caption exactly (with newlines) and sends.
    """
    mod = _mod_key(page)

    # Find main composer
    composer = page.locator(
        "div[contenteditable='true'][role='textbox'][aria-label='Type a message'],"
        "div[contenteditable='true'][role='textbox'][aria-placeholder='Type a message'],"
        "div[contenteditable='true'][role='textbox'][data-tab='10']"
    ).first
    composer.wait_for(state="visible", timeout=CHATBOX_WAIT_MS)
    composer.click(timeout=8000)

    # Paste image
    page.keyboard.press(f"{mod}+V")

    # -------- Try dialog flow quickly --------
    dialog = page.locator("div[role='dialog']").first
    try:
        dialog.wait_for(state="visible", timeout=2500)

        cap_editor = dialog.locator("div[contenteditable='true'][role='textbox']").first
        cap_editor.wait_for(state="visible", timeout=10_000)
        cap_editor.click(timeout=8000)

        page.keyboard.press(f"{mod}+A")
        page.keyboard.press("Backspace")

        if caption:
            page.keyboard.type(caption, delay=10)

        send_btn = dialog.locator(
            "div[role='button'][aria-label='Send'], button[aria-label='Send'], span[data-icon='send'], [data-icon='send']"
        ).first
        send_btn.wait_for(state="visible", timeout=10_000)
        send_btn.click(timeout=8000)

        try:
            dialog.wait_for(state="hidden", timeout=20_000)
        except PWTimeout:
            pass

        time.sleep(WAIT_AFTER_SEND_SEC)
        return

    except PWTimeout:
        pass  # inline flow

    # -------- INLINE flow (your screenshot) --------
    # Wait until send button appears (means pasted media is attached)
    page.wait_for_function(
        """
        () => !!(
          document.querySelector("span[data-icon='send']") ||
          document.querySelector("button[aria-label='Send']") ||
          document.querySelector("div[role='button'][aria-label='Send']")
        )
        """,
        timeout=12_000
    )

    # Re-focus composer after paste
    composer.click(timeout=8000)
    page.keyboard.press(f"{mod}+A")
    page.keyboard.press("Backspace")

    # Lexical-safe insert caption EXACTLY (with newlines)
    ok = page.evaluate(
    """({ selector, text }) => {
        const el = document.querySelector(selector);
        if (!el) return false;

        el.focus();

        // Clear existing content safely
        try {
          const sel = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(el);
          range.collapse(false);
          sel.removeAllRanges();
          sel.addRange(range);
          sel.getRangeAt(0).deleteContents();
        } catch (e) {
          el.textContent = "";
        }

        // Insert text with REAL line breaks using <br>
        try {
          const parts = String(text ?? "").split(/\\r?\\n/);

          // Build a fragment: text + <br> + text + ...
          const frag = document.createDocumentFragment();
          for (let i = 0; i < parts.length; i++) {
            frag.appendChild(document.createTextNode(parts[i]));
            if (i < parts.length - 1) frag.appendChild(document.createElement("br"));
          }

          const sel = window.getSelection();
          if (!sel) return false;

          // Put caret inside editor
          const range = document.createRange();
          range.selectNodeContents(el);
          range.collapse(false);
          sel.removeAllRanges();
          sel.addRange(range);

          // Insert fragment
          sel.getRangeAt(0).insertNode(frag);

          // Fire input event so Lexical updates state
          el.dispatchEvent(new InputEvent("input", {
            bubbles: true,
            inputType: "insertFromPaste",
            data: text
          }));

          return true;
        } catch (e) {}

        // Fallback: try execCommand (may still collapse newlines)
        try {
          if (document.queryCommandSupported && document.queryCommandSupported("insertHTML")) {
            const html = String(text ?? "")
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/\\r?\\n/g, "<br>");
            const r = document.execCommand("insertHTML", false, html);
            if (r) return true;
          }
        } catch (e) {}

        return false;
        }""",
        arg={
            "selector": "div[contenteditable='true'][role='textbox'][aria-label='Type a message'],"
                        "div[contenteditable='true'][role='textbox'][aria-placeholder='Type a message'],"
                        "div[contenteditable='true'][role='textbox'][data-tab='10']",
            "text": caption or ""
        }
    )


    if not ok:
        raise RuntimeError("Could not insert caption into composer")

    # Click send (arrow)
    send_icon = page.locator("span[data-icon='send']").first
    if send_icon.count() > 0:
        parent = send_icon.locator(
            "xpath=ancestor::button[1] | xpath=ancestor::div[@role='button'][1]"
        ).first
        parent.click(timeout=8000)
    else:
        send_btn = page.locator(
            "button[aria-label='Send'], div[role='button'][aria-label='Send']"
        ).first
        send_btn.wait_for(state="visible", timeout=10_000)
        send_btn.click(timeout=8000)

    time.sleep(WAIT_AFTER_SEND_SEC)

def main():
    df = pd.read_excel(EXCEL_PATH)
    if PHONE_COLUMN not in df.columns:
        raise ValueError(f"Excel must contain a '{PHONE_COLUMN}' column")

    df["phone_clean"] = df[PHONE_COLUMN].apply(extract_and_clean_phone)
    df["status"] = ""
    df["note"] = ""

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--start-maximized"],
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://web.whatsapp.com")

        print("Waiting for WhatsApp Web (QR scan if needed)...")
        wait_for_whatsapp_ready(page)
        print("✅ WhatsApp ready.")

        for idx, row in df.iterrows():
            phone = row["phone_clean"]

            if not phone:
                df.at[idx, "status"] = "SKIPPED"
                df.at[idx, "note"] = "Bad/empty phone"
                continue

            try:
                wait_for_whatsapp_ready(page, timeout_ms=60_000)

                if not click_new_chat(page):
                    raise RuntimeError("New chat button not found")

                if not type_in_search(page, phone):
                    raise RuntimeError("Search input not found")

                # give WA a moment to populate results
                time.sleep(0.5)

                if no_results_found(page) or is_no_results_screen(page):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "No results found"
                    go_home(page)          
                    continue


                if not open_chat_from_search_results(page, phone):
                    df.at[idx, "status"] = "NOT_FOUND"
                    df.at[idx, "note"] = "Matching number row not clickable"
                    continue

                # ✅ Paste image (Ctrl+V), type caption, send
                paste_image_caption_and_send(page, CAPTION)

                df.at[idx, "status"] = "SENT"
                df.at[idx, "note"] = "OK"

            except PWTimeout as e:
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "note"] = f"Timeout: {str(e)[:160]}"
                go_home(page)
            except Exception as e:
                df.at[idx, "status"] = "FAILED"
                df.at[idx, "note"] = str(e)[:180]
                go_home(page)

            print(f"{idx+1}/{len(df)} -> {phone}: {df.at[idx,'status']} ({df.at[idx,'note']})")
            time.sleep(WAIT_BETWEEN_NUMBERS_SEC)

        out_path = "numbers_result.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\n✅ Done. Saved results to: {out_path}")

        context.close()


if __name__ == "__main__":
    main()

