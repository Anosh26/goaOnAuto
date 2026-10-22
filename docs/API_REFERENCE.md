# 🏛️ GoaOnAuto — Complete Architectural Specification & API Reference

> **Exhaustive Repository Catalog, Function Specifications, Class Contracts & Dataflows**  
> Covers every directory, source module, Python vision daemon, Raylib GUI app, automation script, and tool across the codebase.
>
> 🔗 **Related Documentation**:
> * 🧠 [Deep Code Logic & Algorithmic Blueprint](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/CODE_LOGIC.md)
> * 🎨 [UI Components & Design System Architecture](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/UI_COMPONENTS.md)
> * 🌟 [Interactive Vector Architecture Explorer](file:///c:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/docs/architecture/index.html)

---

## 📑 Master Table of Contents

1. [Architecture Overview & Inter-Process Communication](#1-architecture-overview--inter-process-communication)
2. [Root Service & Global Config (`src/`)](#2-root-service--global-config-src)
   - [Main Orchestrator (`src/workDirectoryWatcher.ts`)](#main-orchestrator-srcworkdirectorywatcherts)
   - [Global Environment Configuration (`src/config/index.ts`)](#global-environment-configuration-srcconfigindexts)
   - [Core System Types (`src/types/index.ts`)](#core-system-types-srctypesindexts)
3. [Ingestion & File System Watcher (`src/watcher/`)](#3-ingestion--file-system-watcher-srcwatcher)
   - [DirectoryNode (`directoryBuffer.ts`)](#directorynode-directorybufferts)
   - [DirectoryChangeBuffer (`directoryBuffer.ts`)](#directorychangebuffer-directorybufferts)
   - [SystemGovernor (`systemGovernor.ts`)](#systemgovernor-systemgovernorts)
   - [fileSyncReady (`fileSyncReady.ts`)](#filesyncready-filesyncreadyts)
   - [WatcherService (`watcherService.ts`)](#watcherservice-watcherservicets)
4. [GPU Vision & Daemon Engine (`python/`)](#4-gpu-vision--daemon-engine-python)
   - [GPU Worker Daemon (`python/daemons/gpu_worker_daemon.py`)](#gpu-worker-daemon-pythondaemonsgpu_worker_daemonpy)
   - [Aadhaar QR Decoder (`python/vision/aadhaar_qr.py`)](#aadhaar-qr-decoder-pythonvisionaadhaar_qrpy)
   - [GPU OCR Engine (`python/ocr/gpu_ocr_engine.py`)](#gpu-ocr-engine-pythonocrgpu_ocr_enginepy)
   - [Face & Passport Photo Detector (`python/vision/photo_detector.py`)](#face--passport-photo-detector-pythonvisionphoto_detectorpy)
   - [Signature & Ink Detector (`python/vision/signature_detector.py`)](#signature--ink-detector-pythonvisionsignature_detectorpy)
   - [AI Background Removal (`python/vision/ai_remove_bg.py`)](#ai-background-removal-pythonvisionai_remove_bgpy)
   - [QR Code Generator Utility (`python/vision/generate_qr.py`)](#qr-code-generator-utility-pythonvisiongenerate_qrpy)
5. [Scanner & Client IPC (`src/scanner/`)](#5-scanner--client-ipc-srcscanner)
   - [GpuDaemonClient (`gpuDaemonClient.ts`)](#gpudaemonclient-gpudaemonclientts)
   - [DocumentScanner (`documentScanner.ts`)](#documentscanner-documentscannerts)
   - [OCR Post-Processor & Spell Correction (`ocrPostProcessor.ts`)](#ocr-post-processor--spell-correction-ocrpostprocessorts)
   - [Standalone OCR Batch Scanner (`runOcrScanner.ts`)](#standalone-ocr-batch-scanner-runocrscannerts)
   - [Visual Detectors Wrapper (`visualDetectors.ts`)](#visual-detectors-wrapper-visualdetectorsts)
6. [Classification & Dossier Synthesis (`src/classifier/`)](#6-classification--dossier-synthesis-srcclassifier)
   - [DocumentClassifier (`documentClassifier.ts`)](#documentclassifier-documentclassifierts)
   - [Classification Rules Matrix (`rules.ts`)](#classification-rules-matrix-rulests)
   - [DossierExtractor (`dossierExtractor.ts`)](#dossierextractor-dossierextractorts)
   - [NameExtractor (`nameExtractor.ts`)](#nameextractor-nameextractorts)
   - [Classifier Data Types (`types.ts`)](#classifier-data-types-typests)
7. [Image Processing Pipeline (`src/image/`)](#7-image-processing-pipeline-srcimage)
   - [PhotoProcessor (`photoProcessor.ts`)](#photoprocessor-photoprocessorts)
   - [NativeProcessor (`nativeProcessor.ts`)](#nativeprocessor-nativeprocessorts)
   - [PythonOpsWrapper (`pythonOpsWrapper.ts`)](#pythonopswrapper-pythonopswrapperts)
8. [GUI Inter-Process Bridges (`src/gui/`)](#8-gui-inter-process-bridges-srcgui)
   - [Human Confirmation Bridge (`confirmationBridge.ts`)](#human-confirmation-bridge-confirmationbridgets)
   - [OCR Trainer Bridge (`ocrTrainerBridge.ts`)](#ocr-trainer-bridge-ocrtrainerbridgets)
   - [Progress Monitor Bridge (`progressBridge.ts`)](#progress-monitor-bridge-progressbridgets)
9. [Raylib Desktop GUI Applications (`python/gui/`)](#9-raylib-desktop-gui-applications-pythongui)
   - [GUI Core Components (`python/gui/core/`)](#gui-core-components-pythonguicore)
     - [High-DPI Font Atlas & Typography (`fonts.py`)](#high-dpi-font-atlas--typography-fontspy)
     - [Reusable Raylib Widgets (`widgets.py`)](#reusable-raylib-widgets-widgetspy)
     - [LaTeX Compilation Subprocess (`latex_compiler.py`)](#latex-compilation-subprocess-latex_compilerpy)
     - [Dracula Palette Tokens (`colors.py`)](#dracula-palette-tokens-colorspy)
     - [Native File Dialogs (`dialogs.py`)](#native-file-dialogs-dialogspy)
   - [Affidavit Declarations Studio (`declaration_app.py`)](#affidavit-declarations-studio-declaration_apppy)
   - [Declarations Generator Hierarchy (`python/gui/declarations/`)](#declarations-generator-hierarchy-pythonguideclarations)
   - [Interactive OCR Trainer Studio (`ocr_trainer_gui.py`)](#interactive-ocr-trainer-studio-ocr_trainer_guipy)
   - [Interactive Photo Background Matting (`bg_remover_gui.py`)](#interactive-photo-background-matting-bg_remover_guipy)
   - [Human Confirmation Dialog (`confirmation_gui.py`)](#human-confirmation-dialog-confirmation_guipy)
   - [Background Processing Queue Monitor (`progress_gui.py`)](#background-processing-queue-monitor-progress_guipy)
   - [Residence Certificate GUI Wrapper (`residence_gui.py`)](#residence-certificate-gui-wrapper-residence_guipy)
10. [Portal Web Automation Engine (`src/automation/`)](#10-portal-web-automation-engine-srcautomation)
    - [PortalSessionManager (`services/portalSessionManager.ts`)](#portalsessionmanager-servicesportalsessionmanagerts)
    - [Residence Certificate Screen 1 POM (`pages/residenceFormPage.ts`)](#residence-certificate-screen-1-pom-pagesresidenceformpagets)
    - [Application Page Base POM (`pages/applicationPage.ts`)](#application-page-base-pom-pagesapplicationpagets)
    - [Login Pages POM (`pages/loginPages.ts`)](#login-pages-pom-pagesloginpagests)
    - [Phase 1 Browser Login Runner (`scripts/phase1_browser_login.ts`)](#phase-1-browser-login-runner-scriptsphase1_browser_logints)
    - [Automated CAPTCHA Solver (`solver/captchaSolver.ts`)](#automated-captcha-solver-solvercaptchasolverts)
    - [Visual Simulation Tracker (`utils/visualTracker.ts`)](#visual-simulation-tracker-utilsvisualtrackerts)
    - [Brave Portal Launcher (`portalLauncher.ts`)](#brave-portal-launcher-portallauncherts)
    - [Residence Portal Auto-Filler (`fillResidencePortal.ts`)](#residence-portal-auto-filler-fillresidenceportalts)
    - [End-to-End Dossier & Affidavit Runner (`extractAndDeclare.ts`)](#end-to-end-dossier--affidavit-runner-extractanddeclarets)
    - [Residence Certificate Runner (`residenceCertificate.ts`)](#residence-certificate-runner-residencecertificatets)
11. [Developer Tooling & Infrastructure (`tools/`)](#11-developer-tooling--infrastructure-tools)
    - [Dataset Harvesting (`harvest_dataset.ts` & `interactive_harvester.ts`)](#dataset-harvesting-harvest_datasetts--interactive_harvesterts)
    - [Classifier Retrainer (`retrain_classifier.ts`)](#classifier-retrainer-retrain_classifierts)
    - [OCR Trainer CLI Orchestrator (`runOcrTrainer.ts`)](#ocr-trainer-cli-orchestrator-runocrtrainerts)
    - [DOM Survey Tool (`surveyScreen1.ts`)](#dom-survey-tool-surveyscreen1ts)
    - [Human Simulation Action Tracker (`portalActionTracker.ts`)](#human-simulation-action-tracker-portalactiontrackerts)
    - [Windows System Tray Service (`tools/tray/`)](#windows-system-tray-service-toolstray)
    - [Windows Explorer Context Menu Integration (`tools/context-menu/`)](#windows-explorer-context-menu-integration-toolscontext-menu)
    - [Vector Architecture Blueprint Generators (`generate_*_svg.py`)](#vector-architecture-blueprint-generators-generate__svgpy)
12. [Legal Affidavit LaTeX Templates (`templates/latex/`)](#12-legal-affidavit-latex-templates-templateslatex)
13. [Verification Test Suites & Benchmarks (`tests/`)](#13-verification-test-suites--benchmarks-tests)

---

## 1. Architecture Overview & Inter-Process Communication

GoaOnAuto eliminates manual friction in Goa government administrative filings through a **decoupled dual-process architecture**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   TypeScript Orchestrator (Node.js / Bun)                │
│  - Chokidar File Watcher & Trie Buffer (DirectoryChangeBuffer)           │
│  - System Resource Governor (3GB RAM free, <=80% CPU)                   │
│  - Multi-Document Dossier Synthesis & Heuristic Reasoning                │
│  - Playwright Browser Automation (Brave / GoaOnline ASP.NET WebForms)   │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ JSON-RPC over Named Pipes
                                     │ (\\.\pipe\goaonauto_ipc)
┌────────────────────────────────────▼─────────────────────────────────────┐
│                      Python GPU Worker Daemon (PyTorch)                  │
│  - NVIDIA GeForce RTX 4060 CUDA Acceleration (90% VRAM cap)             │
│  - DocTR Engine (DBNet Text Detection + CRNN/ParSeq Recognition)         │
│  - Dual-Format Aadhaar QR Decoder (V2/V3 BigInt + Legacy XML)           │
│  - OpenCV YuNet Face Detection & Alpha Channel Signature Extraction      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Communication Protocol
* **Protocol**: Persistent line-delimited JSON-RPC over Windows Named Pipe `\\.\pipe\goaonauto_ipc`.
* **Request Format**:
  ```json
  { "id": "uuid-v4", "action": "batch_process" | "ocr" | "aadhaar_qr" | "ping" | "exit", ...params }
  ```
* **Response Format**:
  ```json
  { "id": "uuid-v4", "success": true, "is_gpu": true, "device": "NVIDIA GeForce RTX 4060", ...data }
  ```

---

## 2. Root Service & Global Config (`src/`)

### Main Orchestrator (`src/workDirectoryWatcher.ts`)
The root daemon connecting the local directory watcher to the full automated processing pipeline.

* **`startWatching(targetDir?: string): Promise<void>`**
  * Launches `chokidar` on incoming applicant folders.
  * Debounces changes into `DirectoryChangeBuffer` (800ms quiet window).
  * Enqueues dirty client folders for batch processing.
* **`processClientFolder(folderPath: string): Promise<void>`**
  * Verifies file stability via `fileSyncReady`.
  * Calls `SystemGovernor.ensureResourceAvailability()`.
  * Dispatches images to `gpuDaemonClient.processBatch()`.
  * Classifies documents via `DocumentClassifier`.
  * Synthesizes `applicant_dossier.json`.
  * Generates `residence_form_data.json` and launches affidavit review.

---

### Global Environment Configuration (`src/config/index.ts`)
Exports the centralized singleton `config` object:

* **Paths**: `projectRoot`, `modelsDir`, `fontsDir`, `templatesDir`, `datasetDir`, `logsDir`.
* **Hardware Governors**:
  * `minFreeRamBytes`: `3 * 1024 * 1024 * 1024` (3.0 GB).
  * `maxCpuPercent`: `80` (Preserves 20% CPU for host responsiveness).
* **IPC & Daemon**:
  * `pipeName`: `'\\\\.\\pipe\\goaonauto_ipc'`

---

### Core System Types (`src/types/index.ts`)
* **`ClientBatchRecord`**: Tracks folder path, timestamps, queued documents, and processing state.
* **`WatcherOptions`**: Configurations for debounce intervals, recursive polling, and ignore patterns.

---

## 3. Ingestion & File System Watcher (`src/watcher/`)

### `DirectoryNode` (`directoryBuffer.ts`)
Trie node representing a nested folder within the watch root.

* **`constructor(name: string, fullPath: string, parent: DirectoryNode | null = null)`**: Initializes folder node.
* **`setDirty(): void`**: Sets `isDirty = true` on the node and bubbles up to root.
* **`clearDirty(): void`**: Recursively clears dirty bits, changed file maps, and child states.

### `DirectoryChangeBuffer` (`directoryBuffer.ts`)
Trie-based directory change accumulator.

* **`constructor(rootDirectoryPath: string)`**: Initializes root node.
* **`markChange(targetFilePath: string, eventType: 'add'|'change'|'unlink'): void`**: Resolves path, creates trie nodes, records mutation, and marks dirty.
* **`getChangesDFS(node?: DirectoryNode): DirectoryNode[]`**: Traverses trie using Depth-First Search to gather ready batches.
* **`resetBuffer(): void`**: Clears all trie mutations.

### `SystemGovernor` (`systemGovernor.ts`)
Hardware safety manager protecting system responsiveness.

* **`static getInstance(): SystemGovernor`**: Returns active singleton.
* **`getStatus(): SystemResourceStatus`**: Returns real-time RAM/CPU telemetry and threshold booleans.
* **`ensureResourceAvailability(maxWaitMs = 15000): Promise<boolean>`**: Polls every 1s until free RAM $\ge 3\text{GB}$ and CPU usage $\le 80\%$.

### `fileSyncReady` (`fileSyncReady.ts`)
* **`isFileWriteComplete(filePath: string, checkIntervalMs = 300): Promise<boolean>`**: Asserts file size stability across intervals.

### `WatcherService` (`watcherService.ts`)
* **`initWatcher(watchPath: string, onChange: Function): FSWatcher`**: Wraps Chokidar with system-specific ignore filters (`node_modules`, `.git`, `.venv`).

---

## 4. GPU Vision & Daemon Engine (`python/`)

### GPU Worker Daemon (`python/daemons/gpu_worker_daemon.py`)
Persistent background server keeping PyTorch CUDA weights in VRAM.

* **`GpuWorkerService.get_system_metrics() -> dict`**: Reports CPU, RAM, and RTX 4060 VRAM allocations.
* **`GpuWorkerService.process_single_ocr(image_path: str) -> dict`**: Executes text detection and recognition.
* **`GpuWorkerService.process_single_full(image_path: str) -> dict`**: Executes OCR; if text $< 35$ characters, triggers YuNet face detection and signature alpha extraction.
* **`GpuWorkerService.process_batch(image_paths: list) -> list`**: Sequentially processes images without VRAM reloads.
* **`run_daemon()`**: Listens on Windows Named Pipe (`\\.\pipe\goaonauto_ipc`) for JSON-RPC commands.

### Aadhaar QR Decoder (`python/vision/aadhaar_qr.py`)
* **`detect_and_decode_qr(image_path: str) -> dict`**: Multi-engine scanner (`pyzbar` CLAHE $\rightarrow$ `zxingcpp` $\rightarrow$ OpenCV).
* **`_extract_legacy_xml(xml_string: str) -> dict | None`**: Regex parser for `<PrintLetterBarcodeData>` XML attributes.
* **`_extract_secure_qr(raw_bytes: bytes) -> dict | None`**: BigInt Base10 converter, gzip magic byte finder (`1f 8b 08`), sliding window zlib decompressor, and `\xff` delimiter field unpacker.

### GPU OCR Engine (`python/ocr/gpu_ocr_engine.py`)
* **`detect_device_mode() -> tuple[bool, str]`**: Detects NVIDIA CUDA availability and device name.
* **`run_ocr(image_path: str) -> dict`**: Runs DocTR deep learning reader on candidate crops with confidence scoring.

### Face & Passport Photo Detector (`python/vision/photo_detector.py`)
* **`detect_passport_photo(image_path: str) -> dict`**: Runs OpenCV YuNet face detection, validates face proportions, aspect ratio ($3.5\times 4.5\text{ cm}$), and returns crop coordinates.

### Signature & Ink Detector (`python/vision/signature_detector.py`)
* **`detect_signature(image_path: str) -> dict`**: Evaluates stroke density, ink color segmentation (blue/black ballpoint ink), and contour aspect ratios.

### AI Background Removal (`python/vision/ai_remove_bg.py`)
* **`remove_background(image_path: str, output_path: str) -> bool`**: Executes U2-Net / BiRefNet matting to isolate portrait subjects against a solid white background ($<50\text{ KB}$ portal compliance).

### QR Code Generator Utility (`python/vision/generate_qr.py`)
* **`generate_aadhaar_test_qr(output_path: str, data: dict) -> str`**: Generates synthetic XML Aadhaar QR codes for automated test suites.

---

## 5. Scanner & Client IPC (`src/scanner/`)

### `GpuDaemonClient` (`gpuDaemonClient.ts`)
* **`ensureDaemonRunning(): Promise<void>`**: Asserts Windows Named Pipe connectivity (`\\.\pipe\goaonauto_ipc`) or launches daemon.
* **`processBatch(imagePaths: string[]): Promise<GpuOcrResult[]>`**: Dispatches batch OCR inference request.
* **`decodeAadhaarQr(imagePath: string): Promise<AadhaarQrResult>`**: Dispatches QR extraction request.
* **`checkHealth(): Promise<boolean>`**: Sends `ping` and awaits `pong`.

### `DocumentScanner` (`documentScanner.ts`)
* **`scanDocument(filePath: string): Promise<ScannedDocument>`**: Coordinates OCR, image optimization, QR decoding, and rule categorization for a single file.

### OCR Post-Processor & Spell Correction (`ocrPostProcessor.ts`)
* **`loadSpellCorrections(): SpellCorrectionsData`**: Caches learned corrections from `dataset/ocr_spell_corrections.json`.
* **`applyOcrPostProcessing(rawText: string): string`**: Applies regex repairs (`O1/` $\rightarrow$ `01/`) and word boundary replacements.
* **`recordSpellCorrection(original: string, corrected: string): boolean`**: Saves operator corrections to dictionary.

### Standalone OCR Batch Scanner (`runOcrScanner.ts`)
* CLI entrypoint (`bun run ocr:scan [dir]`) that scans a directory, applies OCR post-processing, renames files semantically, and synthesizes `applicant_dossier.json`.

### Visual Detectors Wrapper (`visualDetectors.ts`)
* Exposes TypeScript bindings for calling Python photo and signature detection routines.

---

## 6. Classification & Dossier Synthesis (`src/classifier/`)

### `DocumentClassifier` (`documentClassifier.ts`)
* **`classifyDocument(rawText: string, filePath: string, isPhoto: boolean, isSignature: boolean): ClassificationResult`**: Matches text against 15+ Goan certificate classes using weighted token frequencies, negative exclusions, and filename cues.

### Classification Rules Matrix (`rules.ts`)
Defines token patterns, weights, and exclusions for:
* `aadhaar`, `birth_cert`, `residence_cert`, `bonafide_cert`, `marksheet`, `school_leaving`, `talathi_report`, `ration_card`, `voter_id`, `pan_card`, `passport_photo`, `signature`.

### `DossierExtractor` (`dossierExtractor.ts`)
* **`calculateAgeFromDob(dobStr: string): number | undefined`**: Accurately computes completed years of age.
* **`deduceYearsInGoa(text: string, docType: string, filePath: string): DossierField<number> | undefined`**: Deduces residency duration.
* **`deduceDOB(text: string, filePath: string, docType?: string)`**: Multilingual DOB parser.
* **`deduceAadhaarNumber(documents: ExtractedDocument[], qrResult?)`**: Extracts Verhoeff-compliant 12-digit UID.
* **`deducePreviousResidenceCert(documents: ExtractedDocument[])`**: Extracts previous cert numbers and dates.
* **`synthesizeDossier(documents: ExtractedDocument[], qrResult?): ApplicantDossier`**: Master fusion algorithm.

### `NameExtractor` (`nameExtractor.ts`)
* **`extractApplicantName(rawText: string, docType: string): string | undefined`**: Strips salutations (`Shri`, `Smt`, `Kumari`, `Mast`) and extracts clean applicant names.

### Classifier Data Types (`types.ts`)
* Defines `ApplicantDossier`, `DossierField<T>`, and `ClassificationResult`.

---

## 7. Image Processing Pipeline (`src/image/`)

### `PhotoProcessor` (`photoProcessor.ts`)
* **`optimizePassportPhoto(inputPath: string, outputPath: string): Promise<boolean>`**: Resizes, compresses to $<50\text{ KB}$, crops portrait ratios, and ensures white backgrounds.

### `NativeProcessor` (`nativeProcessor.ts`)
* Utility converting various raw formats (`.webp`, `.tiff`, `.heic`) to portal-compatible `.jpg`/`.png`.

### `PythonOpsWrapper` (`pythonOpsWrapper.ts`)
* Subprocess runner invoking `python/vision/ai_remove_bg.py`.

---

## 8. GUI Inter-Process Bridges (`src/gui/`)

### Human Confirmation Bridge (`confirmationBridge.ts`)
* **`promptHumanConfirmation(doc: ScannedDocument): Promise<HumanReviewResult>`**: Spawns `confirmation_gui.py` and awaits human verification.

### OCR Trainer Bridge (`ocrTrainerBridge.ts`)
* **`OcrTrainerSession`**: Persistent child process session streaming document updates and feedback over stdin/stdout IPC without window recreation flickering.

### Progress Monitor Bridge (`progressBridge.ts`)
* **`ProgressMonitorBridge`**: Spawns and updates `progress_gui.py` displaying processing queue cards.

---

## 9. Raylib Desktop GUI Applications (`python/gui/`)

### GUI Core Components (`python/gui/core/`)
* **`fonts.py`**:
  * `load_custom_font(filename, base_size=48)`: Loads JetBrains Mono with bilinear filtering.
  * `draw_text_clean()`: Sub-pixel crisp text renderer.
  * `measure_text_clean()`: Exact horizontal pixel width measurement.
* **`widgets.py`**:
  * `FormField`: Encapsulates text inputs, cursor position, and clipboard paste.
  * `draw_button()`: Scissor-clipped button with hover shading and click detection.
  * `draw_input_row()`: Input row with label and focus highlights.
* **`latex_compiler.py`**:
  * `compile_latex_to_pdf(tex_path, output_dir)`: Runs MiKTeX/XeLaTeX subprocess in nonstopmode.
* **`colors.py`**: Dracula theme color palette constants.
* **`dialogs.py`**:
  * `open_file_dialog(title, filetypes)`: Native Windows file picker (`tkinter.filedialog`).

### Affidavit Declarations Studio (`declaration_app.py`)
* High-DPI immediate-mode GUI with Dracula theme.
* **Dynamic Signature Scaler**: Real-time $50\%$ to $240\%$ scaling controls directly synchronized with LaTeX `\includegraphics`.
* **Live Synchronization**: Edits in GUI immediately sync to `.tex` using safe regex lambda replacements.

### Declarations Generator Hierarchy (`python/gui/declarations/`)
* **`base.py` (`BaseDeclaration`)**: Abstract base defining field mappings, template loaders, and PDF generation.
* **`residence/residence_declaration.py`**: Self and child residence declaration generator.
* **`obc/obc_declaration.py`**: OBC caste certificate declaration generator.
* **`divergence/divergence_declaration.py`**: Name divergence affidavit generator.

### Interactive OCR Trainer Studio (`ocr_trainer_gui.py`)
3-pane docked window-in-window UI:
* **Sub-Window 1 (Document Inspector)**: Zoom/pan controls, recessed viewport.
* **Sub-Window 2 (Live OCR Stream)**: Monospace line gutter, click-to-populate spell teaching.
* **Sub-Window 3 (Ground-Truth & Retraining)**: 1-5 star rating card, 7 demographic fields, save actions.

### Interactive Photo Background Matting (`bg_remover_gui.py`)
* Interactive canvas for manual crop adjustments and AI white background matting.

### Human Confirmation Dialog (`confirmation_gui.py`)
* Immediate-mode dialog presenting document classification for single-click confirmation.

### Background Processing Queue Monitor (`progress_gui.py`)
* Lightweight desktop HUD displaying real-time batch queues and hardware telemetry.

### Residence Certificate GUI Wrapper (`residence_gui.py`)
* Direct entrypoint launching `declaration_app.py` preconfigured for Residence Declarations.

---

## 10. Portal Web Automation Engine (`src/automation/`)

### `PortalSessionManager` (`services/portalSessionManager.ts`)
* **`resolveBravePath(): string`**: Finds `brave.exe` in Program Files or LocalAppData.
* **`resolveProfileDir(): string`**: Prepares `.brave_automation_profile`.
* **`launchBravePortalContext(): Promise<{ context, page }>`**: Launches Brave with sandbox flags.
* **`isUserLoggedIn(page: Page): Promise<boolean>`**: Checks for authenticated cookies and logout buttons.
* **`updatePortalStatusOverlay(page, message, type)`**: Injects Dracula HUD badge in portal DOM.
* **`waitForManualLogin(page, timeout)`**: Monitors all tabs for login and CAPTCHA solving.
* **`navigateToResidenceService(page)`**: Triggers ASP.NET `__doPostBack` and enters Screen 1.
* **`startPortalPhase1(config)`**: Master Phase 1 orchestrator.

### Residence Certificate Screen 1 POM (`pages/residenceFormPage.ts`)
Comprehensive 59-control DOM Page Object Model:
* **`fillPersonalDetails(data)`**: Full Name, DOB, Age, Gender, Marital Status, Relation.
* **`fillResidentialAddressModal(data)`**: Triggers modal (`#btnaddnew`), populates House No, District, AJAX Taluka, AJAX Village, and confirms save.
* **`fillIdProofAndDeclaration(data)`**: Enters Aadhaar UID and checks Self-Declaration.
* **`fillScreen1(data)`**: Master runner populating all Screen 1 fields.

### Application Page Base POM (`pages/applicationPage.ts`)
* Base class offering helpers for AJAX dropdown options, ASP.NET update panels, and alert dismissals.

### Login Pages POM (`pages/loginPages.ts`)
* Helpers for entering credentials and handling login forms on GoaOnline.

### Phase 1 Browser Login Runner (`scripts/phase1_browser_login.ts`)
* Standalone script to test login handshake and REV05 navigation.

### Automated CAPTCHA Solver (`solver/captchaSolver.ts`)
* **`solveCaptcha(captchaElement): Promise<string>`**: Preprocesses CAPTCHA images (thresholding, contrast stretching) and applies character whitelisting via OCR.

### Visual Simulation Tracker (`utils/visualTracker.ts`)
* **`attachVisualTracker(page: Page)`**: Injects a visual cursor and click ripple overlay to assist operator inspection.

### Brave Portal Launcher (`portalLauncher.ts`)
* Manages headless and headed Brave browser launches with persistent contexts.

### Residence Portal Auto-Filler (`fillResidencePortal.ts`)
* Master auto-filler reading `residence_form_data.json` or `applicant_dossier.json` and driving the browser.

### End-to-End Dossier & Affidavit Runner (`extractAndDeclare.ts`)
* End-to-end CLI orchestrating dossier extraction, GUI affidavit review, and PDF compilation.

### Residence Certificate Runner (`residenceCertificate.ts`)
* Bun CLI script wrapping the Residence Certificate workflow.

---

## 11. Developer Tooling & Infrastructure (`tools/`)

### Dataset Harvesting (`harvest_dataset.ts` & `interactive_harvester.ts`)
* Scans applicant directories, classifies documents, and organizes training samples into `dataset/raw/<category>/`.

### Classifier Retrainer (`retrain_classifier.ts`)
* Analyzes historical corrections from `dataset/corrections.jsonl` and recalculates TF-IDF keyword weights in `src/classifier/rules.ts`.

### OCR Trainer CLI Orchestrator (`runOcrTrainer.ts`)
* Launches interactive operator review sessions for evaluating extraction accuracy.

### DOM Survey Tool (`surveyScreen1.ts`)
* Navigates live GoaOnline forms and dumps 59-control element inventories into `recordings/`.

### Human Simulation Action Tracker (`portalActionTracker.ts`)
* Records human DOM interactions (clicks, keyboard inputs, select options, PostBacks) emitting executable simulation blueprints.

### Windows System Tray Service (`tools/tray/`)
* **`tray_service.py`**: System tray icon (`pystray`) providing one-click access to start the watcher, open the affidavit GUI, or kill the GPU daemon.

### Windows Explorer Context Menu Integration (`tools/context-menu/`)
* **`register_unified_context_menu.ps1`**: Registers 6 right-click context menu actions on Windows folders:
  1. `OCR Scan & Renaming`
  2. `Residence Declaration GUI`
  3. `OBC Declaration GUI`
  4. `Divergence Affidavit GUI`
  5. `Optimize Passport Photo`
  6. `Portal Auto-Fill`

### Vector Architecture Blueprint Generators (`generate_*_svg.py`)
* Python scripts generating the vector architecture blueprints in `docs/architecture/`.

---

## 12. Legal Affidavit LaTeX Templates (`templates/latex/`)

* **`residence_self.tex`**: Template for adult individual residence affidavits. Enforces single A4 page fit via `\onehalfspacing`.
* **`residence_child.tex`**: Template for minor/child residence declarations with parental relation clauses.
* **`obc_self.tex` & `obc_child.tex`**: Templates for OBC community caste declaration certificates.
* **`divergence.tex`**: Affidavit template for name divergence across records.

---

## 13. Verification Test Suites & Benchmarks (`tests/`)

* **`portalPhase1.ts`**: Verification runner for Brave launch, citizen authentication, and REV05 navigation.
* **`portalPhase2Test.ts`**: Verification runner for Screen 1 auto-fill on live GoaOnline sessions.
* **`gpuBatchBenchmark.ts`**: Measures RTX 4060 inference speed (target: $<1.2\text{s}$ per multi-page document).
* **`datasetEvaluator.ts`**: Runs precision/recall metrics over verified document samples.
* **Unit Tests**:
  * `directoryChangeBuffer.test.ts`: Verifies trie change accumulation and DFS traversal.
  * `systemGovernor.test.ts`: Validates RAM and CPU threshold enforcement.
  * `photoDetector.test.ts` & `signatureDetector.test.ts`: Verifies face and ink detection algorithms.
