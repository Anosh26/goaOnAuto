# GoaOnAuto - System Architecture & Automation Context

**Stack**: Bun, TypeScript, Playwright (Chromium/Brave), Python 3.12+ (PyTorch CUDA 12.4, EasyOCR, OpenCV, pyzbar), Raylib GUI (PyRay Static 6.0), XeLaTeX.  
**Architecture**: TypeScript orchestration & Playwright browser automation communicating with Python GPU Worker (`gpu_worker_daemon.py`) via persistent JSON-RPC over TCP `127.0.0.1:50051`.

---

## 🏛️ Interactive Architecture & Vector Blueprint

The system includes an interactive, infinite-zoom vector architectural suite located in `docs/architecture/`:
- **Interactive Explorer (15% to 5,000% Zoom + Pan)**: [`docs/architecture/index.html`](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/architecture/index.html)
- **Macro Visual Pipeline Flow**: [`docs/architecture/goaonauto_visual_architecture.svg`](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/architecture/goaonauto_visual_architecture.svg)
- **Exploded Cutaway (GPU Vision Core)**: [`docs/architecture/inside_gpu_vision.svg`](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/architecture/inside_gpu_vision.svg)
- **Exploded Cutaway (WebForms Portal Bot)**: [`docs/architecture/inside_portal_bot.svg`](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/architecture/inside_portal_bot.svg)
- **Deep Technical Engineering Spec**: [`docs/architecture/goaonauto_architecture.svg`](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/architecture/goaonauto_architecture.svg)

---

## Key Modules & Pipeline

1. **OCR & Vision Engine**:
   - `src/scanner/gpuDaemonClient.ts`: Persistent JSON-RPC client communicating with Python GPU daemon.
   - `python/ocr/gpu_ocr_engine.py`: EasyOCR (CRAFT + ResNet-BiLSTM CUDA RTX 4060) + Tesseract fallback.
   - `python/vision/aadhaar_qr.py`: Secure V2/V3 compressed & legacy XML Aadhaar QR decoder (BigInt bit-unpacking via zlib + Verhoeff Modulo-10 checksum validation).
   - `python/vision/photo_detector.py` & `signature_detector.py`: OpenCV face detection & transparent signature alpha isolation.
   - `python/vision/ai_remove_bg.py`: U2-Net / BiRefNet solid white background matting (<50KB portal compliant).

2. **Classification & Dossier Synthesis**:
   - `src/scanner/ocrPostProcessor.ts`: Optical confusion matrix correction (`O`↔`0`, `l`↔`1`, `S`↔`5`, `B`↔`8`) & Goa administrative dictionary normalizer.
   - `src/classifier/documentClassifier.ts` & `rules.ts`: 15+ Goan certificate classes (Aadhaar, Birth, Talathi, School Leaving, Utility Bills, etc.).
   - `src/classifier/dossierExtractor.ts`: Synthesizes unified `applicant_dossier.json` with chronological age math, Verhoeff validation, and continuous 15-year residency deduction.
   - `src/workDirectoryWatcher.ts`: Chokidar file watcher with 800ms debounce buffer & DFS queue.

3. **Raylib Desktop GUI & Declarations Studio**:
   - `python/gui/declaration_app.py`: High-DPI immediate-mode GUI with Dracula theme, Dual-Column & Narrow multitasking modes.
   - `python/gui/core/widgets.py`: Advanced text input with cursor positioning, `Ctrl+Arrow` word-jumping, and live clipboard paste.
   - **Dynamic Signature Scaler**: Real-time `50%` to `240%` scaling controls (`[-] 100% [+] [↺]`) inside preview texture card, synchronized directly with XeLaTeX generation (`\includegraphics[width={w_cm}cm, height={h_cm}cm, keepaspectratio]`).
   - **Enhanced Typography**: Base font sizes increased by +2 pt across headers, inputs, labels, status badges, and action buttons for clean High-DPI legibility.
   - `python/gui/declarations/`: Polymorphic generators (`residence_declaration.py`, `obc_declaration.py`, `divergence_declaration.py`) inheriting from `base.py`.
   - Compiles print-ready single-page PDF legal declarations (`residence_declaration.pdf`).

4. **Continuous Learning & OCR Trainer Loop**:
   - `tools/runOcrTrainer.ts` & `python/gui/ocr_trainer_gui.py`: Interactive review tool where operators rate extraction accuracy (1-5 stars) and correct recognized text tokens.
   - `dataset/ocr_spell_corrections.json` & `dataset/ocr_corrections.jsonl`: Ground-truth feedback dictionaries auto-tuned into post-processing.
   - `tools/retrain_classifier.ts`: Dynamic TF-IDF rule and keyword weight optimizer.

5. **Portal Automation (GoaOnline REV05)**:
   - `src/automation/services/portalSessionManager.ts`: Launches Brave browser with persistent profile (`.brave_automation_profile`), monitors manual citizen login, and handles navigation to REV05.
   - **Chromium Sandbox Enforcement**: `chromiumSandbox: true` & `ignoreDefaultArgs: ['--no-sandbox']` cleanly eliminates the `--no-sandbox` security warning infobar in Brave.
   - `src/automation/pages/residenceFormPage.ts`: Comprehensive 59-control DOM Page Object Model for Screen 1.
   - `tools/surveyScreen1.ts`: Live interactive DOM inspector emitting 59-control element inventories.
   - `tools/portalActionTracker.ts`: Live human action simulation recorder with visual HUD overlay emitting 291-step simulation blueprints.

---

## Phase 1 Breakthrough: "Proceed to Apply" Navigation

- **Problem**: `locator.click()` in Playwright issued synthetic CDP mouse events on an ASP.NET WebForms anchor tag (`<a id="cphBody_gvService_lnkProceedApply_0" href="javascript:__doPostBack(...)">`), which Chromium does not evaluate as trusted navigation gestures for `javascript:` pseudoprotocol URLs. The page silently remained on the overview page.
- **Fix in `portalSessionManager.ts`**:
  1. Targeted exact anchor IDs (`#cphBody_gvService_lnkProceedApply_0`, `a[href*="lnkProceedApply"]`).
  2. Dispatched native in-page execution via `activePage.evaluate()` triggering `.click()` and `window.__doPostBack('ctl00$cphBody$gvService$ctl02$lnkProceedApply', '')`.
  3. Added `activePage.on('dialog')` handler to auto-accept browser confirm/alert dialogs.
  4. Implemented polling for URL transition away from `deptServices` to `services.goaonline.gov.in/GS/...` and strict failure assertion.

---

## Phase 2 Complete: Residence Screen 1 Automation

All Screen 1 controls, AJAX dependencies, and modal workflows are implemented in [residenceFormPage.ts](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/src/automation/pages/residenceFormPage.ts):

1. **Application Mode**: Self (`#id6a`) vs. Relative/Child (`#id6b`) with relationship (`#idaf`) and relative name (`#idb0`).
2. **Purpose & Period**: Purpose selection (`#id2b`), period duration (`#id2d`, `#year`, `#id2e`).
3. **Personal Info**: Title (`#id2f`), Full Name (`#id30`), DOB direct entry/calendar (`#DOB`), Age (`#idb2`), Place of birth (`#id2a`), Gender (`#id32`), Marital status (`#id33`), Relation details (`#id34`, `#id35`), Mobile (`#id36`), Email (`#id37`), Occupation (`#id38`), Previous Certificate conditional fields (`#id3f`, `#idc3`, `#issuedate`, `#idc4`, `#idc8`).
4. **Residential Address Modal Workflow**:
   - Triggers modal via `#btnaddnew` and waits for visibility of `#id42`.
   - Populates House No (`#id42`), Premises Type (`#id43`), Current Stay (`#id44`), Locality (`#id46`).
   - Populates District (`#id47`), waits for dynamic AJAX Taluka options (`#id48`), selects Taluka, waits for AJAX Village options (`#id49`), selects Village.
   - Pincode (`#id4a`), Period (`#id4b`), Stay From Date (`#fromdate`), Compulsory `drpApplyTo_` (`#id45`).
   - Dispatches address save via `#id4f` (`btnDtlUpdate_:confirmButton`) and confirms modal via `#id4d` (`btnDtlUpdate_:myModal:yesButton`).
   - Gracefully closes modal backdrop dialog.
5. **ID Proof & Declaration**: Aadhaar Card (`#id3d`) with 12-digit Verhoeff-validated number (`#id3e`), Self-Declaration checkbox (`#id41`).
6. **Safe Review Mode**: The bot populates all Screen 1 fields and leaves the browser open for operator review before submission.

---

## Tooling & Command Palette

- **`bun run ocr:scan [dir]`**: Standalone batch OCR & AI document classification with intelligent file renaming and dossier extraction.
- **`bun run portal:fill [dir]`**: End-to-end auto-filler loading `residence_form_data.json` or `applicant_dossier.json` and populating Screen 1 in Brave.
- **`bun run test:portal:phase2`**: Dry-run verification script testing Screen 1 auto-fill on live GoaOnline REV05 session.
- **`bun run ocr:train`**: Interactive OCR rating and ground-truth correction suite.
- **`bun run data:retrain`**: Classifier TF-IDF keyword weight optimizer.
- **`bun run portal:survey`**: Interactive DOM survey tool capturing interactive elements and simulating actions into `recordings/`.
- **`bun run portal:track`**: Live human simulation action recorder with visual overlay tracking clicks, inputs, dropdowns, and ASP.NET PostBacks.
- **`bun run menu:register`**: Registers unified Windows Explorer context menu with 6 tools (OCR Scanner, Declarations, Photo Optimizer, and Portal Auto-Fill).

---

## Phase 3 Scope (Upcoming)

1. **Screen 2 DOM Survey**: Map document upload slots (Applicant Photo <50KB, Residence Declaration PDF, Identity Proof, Age Proof, Residence Proofs).
2. **Automated Attachment Upload**: Wire `residenceFormPage.ts` Screen 2 methods with processed assets from the client dossier folder via direct file injection.
3. **Fee & Submission Verification**: Complete payment / acknowledgement generation stage with operator override.
