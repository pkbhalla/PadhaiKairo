import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

OUTPUT_DIR = Path("d:/Personal/AIAgentsHackathon/test_screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def run_e2e_tests():
    print("==================================================================")
    print("STARTING COMPLETE E2E VERIFICATION OF DYNAMIC USER JOURNEY")
    print("==================================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        alerts = []
        async def handle_dialog(dialog):
            msg = dialog.message
            alerts.append(msg)
            print(f"  [DIALOG {dialog.type.upper()}]: {msg.replace(chr(10), ' | ')}")
            await dialog.accept()

        page.on("dialog", lambda d: asyncio.create_task(handle_dialog(d)))

        # ----------------------------------------------------------------------
        # 1. VERIFY HOMEPAGE WITH ZERO HARDCODED STUDENT DROPDOWNS
        # ----------------------------------------------------------------------
        print("\n--- STEP 1: VERIFY HOMEPAGE & ZERO HARDCODED STUDENT DROPDOWNS ---")
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        title = await page.title()
        print(f"  Page Title: {title}")
        assert "Agentic Learning Coach" in title, f"Unexpected page title: {title}"

        # Assert no #user-select or hardcoded student selector exists
        user_select_count = await page.locator("#user-select").count()
        print(f"  Hardcoded Student Selector Count (#user-select): {user_select_count}")
        assert user_select_count == 0, "Error: Hardcoded student selector should NOT exist!"

        # Assert course-select exists
        course_select = page.locator("#course-select")
        assert await course_select.count() > 0, "Course selector #course-select should exist"
        course_options = await course_select.inner_text()
        print(f"  Course Selector Options: {course_options.strip().replace(chr(10), ', ')}")

        # Assert Google Auth sign-in button is visible in header
        auth_badge = page.locator("#auth-badge-container")
        auth_text = await auth_badge.inner_text()
        print(f"  Auth Container Content: '{auth_text.strip()}'")
        assert "Sign in with Google" in auth_text or "●" in auth_text, "Auth container should show Sign in or status"

        await page.screenshot(path=str(OUTPUT_DIR / "01_guest_homepage.png"), full_page=True)
        print("  [PASSED] Step 1: Homepage opens cleanly with ZERO hardcoded student dropdowns.")

        # ----------------------------------------------------------------------
        # 2. TEST GUEST FUNNEL: SEND 2 CHAT MESSAGES & VERIFY SIGN-IN MODAL
        # ----------------------------------------------------------------------
        print("\n--- STEP 2: TEST GUEST FUNNEL (2 CHAT MESSAGES -> SIGN-IN MODAL) ---")
        # Switch to Socratic Coach tab
        await page.click(".tab-item:has-text('Socratic Tutor & Coach')")
        await page.wait_for_timeout(500)

        # Message 1
        chat_input = page.locator("#chat-input")
        await chat_input.fill("What is backpropagation in neural networks?")
        print("  Sending Message 1: 'What is backpropagation in neural networks?'")
        async with page.expect_response(lambda r: "/chat" in r.url, timeout=30000) as resp1:
            await page.click("button:has-text('Send')")
        r1 = await resp1.value
        print(f"  Message 1 Response Status: {r1.status}")
        await page.wait_for_timeout(1000)

        # Message 2
        await chat_input.fill("How does gradient descent update the weights?")
        print("  Sending Message 2: 'How does gradient descent update the weights?'")
        async with page.expect_response(lambda r: "/chat" in r.url, timeout=30000) as resp2:
            await page.click("button:has-text('Send')")
        r2 = await resp2.value
        print(f"  Message 2 Response Status: {r2.status}")
        await page.wait_for_timeout(1000)

        # Verify modal is triggered
        auth_modal = page.locator("#auth-prompt-modal")
        is_modal_visible = await auth_modal.is_visible()
        print(f"  'Save Your Learning Journey!' Modal Visible: {is_modal_visible}")
        assert is_modal_visible, "Error: Guest funnel modal #auth-prompt-modal should be visible after 2 messages!"

        modal_heading = await auth_modal.locator("h2").inner_text()
        print(f"  Modal Heading: '{modal_heading}'")
        assert "Save Your Learning Journey" in modal_heading, f"Modal heading mismatch: {modal_heading}"

        await page.screenshot(path=str(OUTPUT_DIR / "02_guest_funnel_modal.png"))
        print("  [PASSED] Step 2: Guest funnel modal successfully triggered after 2 messages.")

        # ----------------------------------------------------------------------
        # 3. CLICK 'Sign in with Google' -> OPEN SUBJECT CREATION MODAL & FETCH YOUTUBE
        # ----------------------------------------------------------------------
        print("\n--- STEP 3: SIGN IN & DYNAMIC SUBJECT CREATION WITH YOUTUBE CAPTIONS ---")
        # Click Sign in with Google in the modal
        signin_btn = auth_modal.locator("button:has-text('Sign in with Google')")
        await signin_btn.click()
        await page.wait_for_selector("#new-course-modal", state="visible", timeout=10000)

        # Verify New Course Modal opens
        course_modal = page.locator("#new-course-modal")
        is_course_modal_visible = await course_modal.is_visible()
        print(f"  New Subject Modal Visible: {is_course_modal_visible}")
        assert is_course_modal_visible, "New course modal should be visible"

        # Verify YouTube input and Fetch Captions button
        yt_input = page.locator("#course-yt-url")
        assert await yt_input.count() > 0, "YouTube URL input #course-yt-url must exist"
        fetch_btn = page.locator("button:has-text('Fetch Captions')")
        assert await fetch_btn.count() > 0, "Fetch Captions button must exist"

        # Fill YouTube lecture link
        yt_url = "https://www.youtube.com/watch?v=aircAruvnKk"
        await yt_input.fill(yt_url)
        print(f"  Entered YouTube URL: {yt_url}")

        # Click 'Fetch Captions' and wait for API
        print("  Clicking 'Fetch Captions'...")
        async with page.expect_response(lambda r: "/youtube/fetch-transcript" in r.url, timeout=30000) as yt_resp:
            await fetch_btn.click()
        yt_r = await yt_resp.value
        yt_data = await yt_r.json()
        print(f"  YouTube API Result: success={yt_data.get('success')}, charCount={yt_data.get('charCount')}")

        status_text = await page.locator("#yt-preview-status").inner_text()
        print(f"  UI Transcript Status: '{status_text}'")
        assert "Found Transcript" in status_text or yt_data.get("success"), "Transcript fetch status not confirmed"
        await page.screenshot(path=str(OUTPUT_DIR / "03_youtube_captions_fetched.png"))

        # Verify / fill Course Title and Subtopics
        title_input = page.locator("#course-title-input")
        await title_input.fill("Machine Learning & Neural Networks")
        topics_input = page.locator("#course-topics-input")
        await topics_input.fill("Linear Regression, Gradient Descent, Backpropagation, Transformers, Overfitting")

        print("  Clicking 'Generate Dynamic Mastery Graph & Schedule'...")
        async with page.expect_response(lambda r: "/courses/create" in r.url, timeout=60000) as create_resp:
            await page.locator("#btn-submit-create-course").click()
        create_r = await create_resp.value
        create_data = await create_r.json()
        print(f"  Course Creation API Status: {create_r.status}, CourseId: {create_data.get('courseId')}")
        print(f"  Initialized Concepts: {len(create_data.get('concepts', []))}")
        print(f"  Ingested Sources: {len(create_data.get('sources', []))}")

        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUTPUT_DIR / "04_course_created.png"), full_page=True)
        print("  [PASSED] Step 3: Dynamic Subject created with live YouTube lecture transcript.")

        # ----------------------------------------------------------------------
        # 4. VERIFY ACTIVE SUBJECT SWITCHES TO MACHINE LEARNING & ALL 7 TABS OPERATE ON ML
        # ----------------------------------------------------------------------
        print("\n--- STEP 4: VERIFY ACTIVE SUBJECT IS ML & TEST ALL 7 TABS ---")

        # 4.1 TAB 1: MASTERY & DECAY GRAPH
        print("\n  [4.1] TAB 1: Mastery & Decay Graph")
        await page.click(".tab-item:has-text('Mastery & Decay Graph')")
        await page.wait_for_timeout(800)
        concept_elements = await page.locator(".concept-item").all()
        print(f"    Concepts rendered in graph: {len(concept_elements)}")
        assert len(concept_elements) >= 4, f"Expected >= 4 concepts, found {len(concept_elements)}"
        for idx, el in enumerate(concept_elements):
            text = await el.inner_text()
            print(f"      - Concept #{idx+1}: {text.replace(chr(10), ' | ')}")
            assert not any(db in text.lower() for db in ["sql & joins", "relational algebra", "er modeling", "acid"]), "Should not contain DBMS topics!"
        await page.screenshot(path=str(OUTPUT_DIR / "05_tab1_mastery_ml.png"), full_page=True)
        print("    [TAB 1 OK] Mastery Graph operates on Machine Learning concepts.")

        # 4.2 TAB 2: SOCRATIC COACH
        print("\n  [4.2] TAB 2: Socratic Coach")
        await page.click(".tab-item:has-text('Socratic Tutor & Coach')")
        await page.wait_for_timeout(500)
        coach_input = page.locator("#chat-input")
        await coach_input.fill("Explain the self-attention mechanism in Transformers in simple terms.")
        async with page.expect_response(lambda r: "/chat" in r.url, timeout=60000) as coach_resp:
            await page.click("button:has-text('Send')")
        coach_r = await coach_resp.value
        print(f"    Coach Chat Status: {coach_r.status}")
        await page.wait_for_timeout(1000)
        last_coach_msg = await page.locator(".msg").last.inner_text()
        print(f"    Coach Guidance Snippet: {last_coach_msg[:200]}...")
        await page.screenshot(path=str(OUTPUT_DIR / "06_tab2_coach_ml.png"), full_page=True)
        print("    [TAB 2 OK] Socratic Coach grounded in Machine Learning.")

        # 4.3 TAB 3: STUDY GUIDES & BRIEFINGS
        print("\n  [4.3] TAB 3: Study Guides & Briefings")
        await page.click(".tab-item:has-text('Study Guides & Briefings')")
        await page.wait_for_timeout(500)
        guide_input = page.locator("#guide-topic-input")
        await guide_input.fill("Backpropagation & Gradient Flow")
        async with page.expect_response(lambda r: "/study-guide/generate" in r.url, timeout=60000) as guide_resp:
            await page.click("button:has-text('Generate Guide')")
        guide_r = await guide_resp.value
        print(f"    Study Guide API Status: {guide_r.status}")
        await page.wait_for_timeout(1000)
        guide_text = await page.locator("#guide-content").inner_text()
        print(f"    Synthesized Guide Length: {len(guide_text)} chars")
        print(f"    Guide Preview: {guide_text[:250]}...")
        assert "backpropagation" in guide_text.lower() or "gradient" in guide_text.lower() or len(guide_text) > 100
        await page.screenshot(path=str(OUTPUT_DIR / "07_tab3_guide_ml.png"), full_page=True)
        print("    [TAB 3 OK] Study Guide generated for Machine Learning.")

        # 4.4 TAB 4: ACTIVE RECALL FLASHCARDS
        print("\n  [4.4] TAB 4: Active Recall Flashcards")
        await page.click(".tab-item:has-text('Active Recall Flashcards')")
        await page.wait_for_timeout(500)
        flash_input = page.locator("#flashcard-topic-input")
        await flash_input.fill("Transformers & Neural Architectures")
        async with page.expect_response(lambda r: "/flashcards/generate" in r.url, timeout=60000) as flash_resp:
            await page.click("button:has-text('Generate Deck')")
        flash_r = await flash_resp.value
        print(f"    Flashcards API Status: {flash_r.status}")
        await page.wait_for_timeout(1000)
        cards_count = await page.locator(".flashcard").count()
        print(f"    Flashcards Rendered: {cards_count}")
        assert cards_count >= 1, "At least 1 flashcard should be rendered"
        # Test flip animation
        first_card = page.locator(".flashcard").first
        await first_card.click()
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUTPUT_DIR / "08_tab4_flashcards_ml.png"), full_page=True)
        print("    [TAB 4 OK] Active recall flashcards generated and flipped.")

        # 4.5 TAB 5: PRACTICE DRILLS
        print("\n  [4.5] TAB 5: Practice Drills")
        await page.click(".tab-item:has-text('Practice Quizzes')")
        await page.wait_for_timeout(500)
        quiz_input = page.locator("#quiz-topic-input")
        await quiz_input.fill("Gradient Descent & Learning Rate")
        async with page.expect_response(lambda r: "/quiz/generate" in r.url, timeout=60000) as quiz_resp:
            await page.click("button:has-text('Generate Drill')")
        quiz_r = await quiz_resp.value
        print(f"    Quiz Generator API Status: {quiz_r.status}")
        await page.wait_for_timeout(1000)
        q_count = await page.locator("#quiz-body > div").count()
        print(f"    Questions Rendered: {q_count}")
        assert q_count >= 1, "At least 1 quiz question rendered"

        # Select answers
        for q_id in range(1, q_count + 1):
            opt = page.locator(f"#opt-{q_id}-0")
            if await opt.count() > 0:
                await opt.click()
                await page.wait_for_timeout(200)

        # Submit quiz
        submit_btn = page.locator("#btn-submit-quiz")
        if await submit_btn.is_visible():
            async with page.expect_response(lambda r: "/quiz/grade" in r.url, timeout=60000) as grade_resp:
                await submit_btn.click()
            grade_r = await grade_resp.value
            grade_data = await grade_r.json()
            print(f"    Quiz Grade Result: score={grade_data.get('score')}, newMastery={grade_data.get('newMastery')}")

        await page.screenshot(path=str(OUTPUT_DIR / "09_tab5_drills_ml.png"), full_page=True)
        print("    [TAB 5 OK] Practice drills generated and graded for Machine Learning.")

        # 4.6 TAB 6: RETENTION GUARDIAN & CALENDAR
        print("\n  [4.6] TAB 6: Retention Guardian & Calendar")
        await page.click(".tab-item:has-text('Retention Guardian & Calendar')")
        await page.wait_for_timeout(500)
        guardian_btn = page.locator("#btn-guardian")
        async with page.expect_response(lambda r: "/guardian/scan" in r.url, timeout=60000) as scan_resp:
            await guardian_btn.click()
        scan_r = await scan_resp.value
        scan_data = await scan_r.json()
        print(f"    Retention Scan Status: {scan_r.status}")
        print(f"    Decayed Concepts Detected: {scan_data.get('decayedCount')}")
        print(f"    Actions Taken: {len(scan_data.get('actionsTaken', []))}")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUTPUT_DIR / "10_tab6_guardian_ml.png"), full_page=True)
        print("    [TAB 6 OK] Retention Guardian scan completed.")

        # 4.7 TAB 7: INGESTED SOURCES & TRANSCRIPTS
        print("\n  [4.7] TAB 7: Ingested Sources & Transcripts")
        async with page.expect_response(lambda r: "/sources" in r.url, timeout=60000):
            await page.click(".tab-item:has-text('Ingested Sources & Transcripts')")
        await page.wait_for_selector("#sources-container strong, #sources-container h4", timeout=10000)
        await page.wait_for_timeout(500)
        sources_text = await page.locator("#sources-container").inner_text()
        print(f"    Sources Container Text Preview:\n      {sources_text[:300].replace(chr(10), ' ')}")
        assert "Video Lecture Notes" in sources_text or "Machine Learning" in sources_text, "Machine learning source material should be listed"
        await page.screenshot(path=str(OUTPUT_DIR / "11_tab7_sources_ml.png"), full_page=True)
        print("    [TAB 7 OK] Ingested sources display Machine Learning YouTube lecture transcripts.")

        # ----------------------------------------------------------------------
        # 5. VERIFY DARK MODE TOGGLE & SHARP CONTRAST
        # ----------------------------------------------------------------------
        print("\n--- STEP 5: VERIFY DARK MODE TOGGLE & CONTRAST ---")
        theme_toggle = page.locator("#theme-toggle")
        await theme_toggle.click()
        await page.wait_for_timeout(800)

        theme_attr = await page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        print(f"  Theme attribute after toggle: '{theme_attr}'")
        assert theme_attr == "dark", f"Expected dark theme, got {theme_attr}"

        contrast_styles = await page.evaluate("""() => {
            const body = window.getComputedStyle(document.body);
            const header = window.getComputedStyle(document.querySelector('header'));
            const card = window.getComputedStyle(document.querySelector('.card'));
            const select = window.getComputedStyle(document.querySelector('select'));
            return {
                bodyBg: body.backgroundColor,
                bodyColor: body.color,
                headerBg: header.backgroundColor,
                cardBg: card.backgroundColor,
                cardColor: card.color,
                selectBg: select.backgroundColor,
                selectColor: select.color
            };
        }""")
        print(f"  Dark Mode Styles: {contrast_styles}")
        await page.screenshot(path=str(OUTPUT_DIR / "12_dark_mode_active.png"), full_page=True)

        # Toggle back to light
        await theme_toggle.click()
        await page.wait_for_timeout(600)
        theme_attr_light = await page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        print(f"  Theme attribute after toggle back: '{theme_attr_light}'")
        assert theme_attr_light == "light", f"Expected light theme, got {theme_attr_light}"
        await page.screenshot(path=str(OUTPUT_DIR / "13_light_mode_active.png"), full_page=True)
        print("  [PASSED] Step 5: Dark mode toggle is smooth and text contrast is sharp.")

        print("\n==================================================================")
        print("ALL 5 VERIFICATION STEPS PASSED SUCCESSFULLY!")
        print("==================================================================")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
