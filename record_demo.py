import asyncio
import os
import shutil
import time

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/config/.cache/ms-playwright"
from playwright.async_api import async_playwright

async def record():
    rec_dir = "/config/Desktop/BuildWithGemini/financial-recovery-agent/demo_recordings"
    os.makedirs(rec_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        
        context = await browser.new_context(
            record_video_dir=rec_dir,
            record_video_size={"width": 1280, "height": 800},
            viewport={"width": 1280, "height": 800}
        )
        
        page = await context.new_page()
        print("Navigating to http://localhost:8080...")
        await page.goto("http://localhost:8080", wait_until="networkidle")
        await asyncio.sleep(2.5) # View initial welcome

        # --- Turn 1: Emergency Scam Triage ---
        print("Starting Turn 1: Emergency Triage...")
        prompt1 = "I was targeted by an imposter wire scam yesterday for $4,500. What emergency triage steps should I take?"
        input_el = page.locator("#input")
        await input_el.click()
        await input_el.type(prompt1, delay=35)
        await asyncio.sleep(0.8)
        await page.locator("button:has-text('Send')").click()

        # Wait for agent response
        print("Waiting for response 1...")
        await page.wait_for_function(
            "() => { const turns = document.querySelectorAll('.dialogue-turn.agent'); return turns.length >= 2 && turns[turns.length-1].textContent.length > 50; }",
            timeout=90000
        )
        await asyncio.sleep(4.0)

        # Smooth scroll
        await page.evaluate("() => { const log = document.getElementById('log'); log.scrollTop = log.scrollHeight; }")
        await asyncio.sleep(2.0)

        # --- Turn 2: Rich Tool Calls + Database Lookup + Calculation ---
        print("Starting Turn 2: Database lookup + Statutory deadline calculation...")
        prompt2 = "Please search our verified relief database for imposter wire scam resources and calculate my Regulation E 60-day dispute deadlines for an incident on 2026-11-10."
        await input_el.click()
        await input_el.type(prompt2, delay=30)
        await asyncio.sleep(0.8)
        await page.locator("button:has-text('Send')").click()

        # Wait for agent response
        print("Waiting for response 2...")
        await page.wait_for_function(
            "() => { const turns = document.querySelectorAll('.dialogue-turn.agent'); return turns.length >= 3 && turns[turns.length-1].textContent.length > 50; }",
            timeout=90000
        )
        await asyncio.sleep(6.0)

        # Scroll to show the complete response
        await page.evaluate("() => { const log = document.getElementById('log'); log.scrollTop = log.scrollHeight; }")
        await asyncio.sleep(4.0)

        # Close page and context to finalize video
        await page.close()
        video_path = await page.video.path()
        await context.close()
        await browser.close()
        print(f"Recorded video saved to: {video_path}")
        return video_path

if __name__ == "__main__":
    v_path = asyncio.run(record())
    # Transcode to mp4
    mp4_out = "/config/Desktop/BuildWithGemini/demo_video.mp4"
    os.system(f"ffmpeg -y -i {v_path} -c:v libx264 -pix_fmt yuv420p -preset fast -crf 22 {mp4_out}")
    print(f"Final MP4 ready at: {mp4_out}")
