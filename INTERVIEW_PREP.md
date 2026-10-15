# 🎯 GoaOnAuto — Complete Interview Preparation Guide

> **Your one-stop study sheet for tomorrow's interview.**
> Covers: Basic fundamentals → Technical deep-dives → Decision & trade-off questions → System design questions → Debugging war stories → Behavioral/STAR answers → Future scope & scalability.

---

## 📑 Table of Contents

1. [The 30-Second Elevator Pitch](#1-the-30-second-elevator-pitch)
2. [Basic Fundamental Questions](#2-basic-fundamental-questions)
3. [Architecture & System Design Questions](#3-architecture--system-design-questions)
4. [Technical Deep-Dive Questions](#4-technical-deep-dive-questions)
5. [Decision & Trade-Off Questions](#5-decision--trade-off-questions)
6. [Debugging & Problem-Solving War Stories](#6-debugging--problem-solving-war-stories)
7. [Computer Vision & AI/ML Questions](#7-computer-vision--aiml-questions)
8. [Web Automation & Browser Engineering Questions](#8-web-automation--browser-engineering-questions)
9. [GUI & UI/UX Design Questions](#9-gui--uiux-design-questions)
10. [Data Engineering & Pipeline Questions](#10-data-engineering--pipeline-questions)
11. [Security, Privacy & Compliance Questions](#11-security-privacy--compliance-questions)
12. [Testing & Quality Assurance Questions](#12-testing--quality-assurance-questions)
13. [Behavioral & STAR Method Questions](#13-behavioral--star-method-questions)
14. [Scalability & Future Scope Questions](#14-scalability--future-scope-questions)
15. [Rapid-Fire Quick Recall Sheet](#15-rapid-fire-quick-recall-sheet)

---

## 1. The 30-Second Elevator Pitch

> **Memorize this. Rehearse it out loud 3 times before the interview.**

**"GoaOnAuto is an end-to-end intelligent automation system I built to eliminate manual friction in processing Goa government citizen service applications — specifically Residence Certificates on the GoaOnline portal.**

**It watches a folder for incoming applicant documents, uses a persistent GPU daemon running on an RTX 4060 to classify documents and extract information from Aadhaar QR codes, presents an interactive Raylib desktop GUI for human review and legal affidavit customization, compiles pixel-perfect LaTeX PDFs, and then auto-populates the GoaOnline web portal using Playwright browser automation.**

**The tech stack is TypeScript with Bun for orchestration, Python with PyTorch CUDA for the GPU vision engine, Raylib for the desktop GUI, and Playwright for browser automation — all communicating over JSON-RPC on Windows Named Pipes."**

---

## 2. Basic Fundamental Questions

### Q: What is GoaOnAuto?
**A:** GoaOnAuto is an end-to-end intelligent automation system that processes Goa government administrative applications. It monitors incoming applicant document folders, classifies documents using GPU-accelerated AI, extracts demographic data from Aadhaar QR codes and OCR, lets a human operator review and customize legal affidavits through a desktop GUI, compiles print-ready LaTeX PDFs, and auto-fills the GoaOnline government portal using Playwright.

---

### Q: What problem does it solve?
**A:** Filing a Residence Certificate on GoaOnline requires:
1. Manually reading ~8-12 different documents per applicant (Aadhaar, birth certificates, school records, etc.)
2. Manually typing 25+ form fields across complex web forms with cascading AJAX dropdowns and modals
3. Manually creating legal affidavits as PDFs
4. Manually uploading documents with strict size/format constraints

This is tedious, error-prone, and takes 20-30 minutes per application manually. GoaOnAuto reduces this to 5-10 minutes (including human review) with near-zero data entry errors, because demographic data is extracted directly from cryptographic Aadhaar QR codes rather than manual typing.

---

### Q: Who is the target user?
**A:** Government service agents, document processing clerks, and citizen service facilitators who handle high volumes of Goa Residence Certificate applications. The system is designed as a "human-in-the-loop" tool — it automates the tedious parts while keeping a human operator in control for final review.

---

### Q: What is the tech stack?
**A:**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | TypeScript + Bun | File watching, classification, dossier synthesis, CLI tools |
| **GPU Vision Engine** | Python 3.13 + PyTorch CUDA 12.4 | EasyOCR, Aadhaar QR decoding, face/signature detection |
| **Desktop GUI** | Python + Raylib (PyRay 6.0) | Immediate-mode interactive forms, OCR trainer, photo optimizer |
| **Legal Document Gen** | LaTeX (MiKTeX pdflatex/XeLaTeX) | Pixel-perfect single-page A4 legal affidavits |
| **Browser Automation** | Playwright + Brave (Chromium) | GoaOnline portal form filling, CAPTCHA solving |
| **IPC** | JSON-RPC over Named Pipes (`\\.\pipe\goaonauto_ipc`) | Low-latency, kernel-buffered TypeScript <-> Python GPU IPC |

---

### Q: Walk me through the end-to-end flow
**A:** The system has 5 pipeline stages:

1. **Ingestion (Directory Watcher)**: Monitors a folder (e.g., Google Drive sync). When documents are dropped, a Trie-based change buffer accumulates file events with 800ms debouncing. A System Governor checks hardware (>=3GB free RAM, <=80% CPU) before processing.

2. **AI Document Classification & QR Extraction**: Documents are sent to a persistent Python GPU daemon over a low-latency Windows Named Pipe. EasyOCR (CRAFT + ResNet-BiLSTM on RTX 4060) extracts text. An Aadhaar QR decoder extracts golden-source demographic data. A weighted multi-rule classifier categorizes documents into 15+ types (Aadhaar, birth cert, residence cert, marksheet, etc.).

3. **Dossier Synthesis & Human Review**: All extracted data is fused into a unified `applicant_dossier.json`. Aadhaar QR data (Tier 1, confidence 1.0) overrides OCR data (Tier 2). The dossier deduces age, years in Goa, and previous certificate details. A Raylib GUI lets the operator verify and correct data.

4. **Affidavit Generation**: An interactive Raylib Declarations Studio lets the operator customize the legal declaration, pick photo/signature files, and compile LaTeX templates into single-page A4 PDFs in <2 seconds.

5. **Web Portal Automation**: Playwright opens Brave browser, waits for the operator to authenticate on GoaOnline, navigates to the Residence Certificate form (REV05 Screen 1), and auto-fills all 59 form controls. The browser stays open in "Safe Review Mode" for human verification before submission.

---

### Q: What types of documents can the system process?
**A:** 15+ Goan certificate classes:
- Aadhaar Card (with QR code extraction)
- Birth Certificate
- Residence Certificate (existing/previous)
- Bonafide School Certificate
- School Leaving Certificate
- Academic Marksheets
- Talathi Report
- Ration Card
- Voter ID
- PAN Card
- Passport Photo
- Signature
- Utility Bills (Electricity, Water)
- Income Certificates

---

### Q: What legal documents does it generate?
**A:** Three types of affidavit declarations:
1. **Residence Declaration** — Self mode (individual adult) and Child mode (minor with parental relation)
2. **OBC (Other Backward Class) Declaration** — Caste certificate affidavit
3. **Divergence Declaration** — Affidavit for name discrepancies across documents

All use LaTeX templates compiled into print-ready single-page A4 PDFs.

---

## 3. Architecture & System Design Questions

### Q: Why did you choose a dual-process architecture (TypeScript + Python) instead of a single language?
**A:** This was a deliberate trade-off:

- **TypeScript/Bun** excels at file system operations, JSON manipulation, async/await orchestration, and Playwright browser automation. It has first-class support for Playwright and Chokidar.
- **Python** is the de facto standard for GPU/ML workloads. PyTorch, EasyOCR, OpenCV, and pyzbar all have mature Python APIs but poor or nonexistent Node.js equivalents.

Building everything in Python would sacrifice Playwright's superior browser automation API and TypeScript's type safety. Building everything in TypeScript would mean wrapping every ML library through fragile C++ bindings.

The JSON-RPC over Named Pipes bridge is lightweight and adds sub-millisecond (<1ms) latency per call — completely bypassing the TCP/IP network stack.

---

### Q: Why JSON-RPC over Named Pipes and not REST, gRPC, or TCP sockets?
**A:**
- **REST/HTTP**: Overkill for local IPC. HTTP headers add unnecessary overhead. No need for routing, middleware, or content negotiation.
- **gRPC**: Would require Protocol Buffer compilation and schema management. Good for microservices, excessive for a 2-process system on localhost.
- **TCP Sockets**: Incurs network stack overhead (loopback routing, TCP windowing, port binding conflicts).
- **Named Pipes + JSON-RPC**: Bypasses the network stack entirely via OS kernel-buffered memory for sub-millisecond latency. Line-delimited JSON is human-readable for debugging, avoids port collision issues, and provides safe process isolation.

The protocol is just `{"id": "uuid", "action": "batch_process", ...params}\n` -> `{"id": "uuid", "success": true, ...results}\n`.

---

### Q: How does the System Governor work? Why is it necessary?
**A:** The System Governor is a hardware safety manager that prevents the automation system from freezing the operator's machine during heavy GPU inference.

**How it works:**
- Reads free RAM via `os.freemem()` and validates >= 3.0 GB
- Computes CPU utilization across all logical cores:
  - `totalTick = sum(user + nice + sys + idle + irq)` per core
  - `idlePercent = (sum(idle) / totalTick) * 100`
  - `CPU_usage = 100 - idlePercent`
- If CPU > 80% or RAM < 3GB, it enters an async polling loop (1s intervals, max 15s timeout) until resources free up

**Why it's necessary:** The RTX 4060 CUDA operations allocate large GPU tensors. Combined with Brave browser, Raylib GUI, and Google Drive sync running simultaneously, it's easy to exhaust 16GB of system RAM. The governor prevents OOM kills and system freezes.

---

### Q: Explain the Trie-based Directory Change Buffer
**A:** When users drop a folder of 20+ documents (or sync via Google Drive), the OS file watcher fires hundreds of low-level `fs.watch` events out of order. Processing each event individually causes race conditions and partial file reads.

**Solution — Prefix Trie:**
1. The root watch directory is the trie root node
2. Each subdirectory level maps to a `DirectoryNode` (name, fullPath, isDirty, children Map, changedFiles Map)
3. When `markChange(filePath, eventType)` is called:
   - Path is split into segments: `["Client_John", "docs", "Aadhaar.pdf"]`
   - Intermediate nodes are created on-the-fly
   - The file mutation is recorded with a timestamp
   - **Dirty-bit propagation**: `setDirty()` traverses upward through parent pointers, marking the entire ancestor chain as dirty — O(depth) time
4. **DFS Batch Harvesting**: `getChangesDFS()` traverses only dirty branches (clean subtrees are pruned in O(1)), returning leaf directories with recorded mutations

**Complexity:** Marking is O(path_depth), harvesting is O(dirty_nodes) instead of O(all_nodes).

---

### Q: Draw the system architecture on a whiteboard
**A:** *(Practice drawing this)*

```
[Google Drive / Local Folder]
        │ fs.watch + 800ms debounce
        ▼
[Trie Change Buffer] → [System Governor: >=3GB RAM, <=80% CPU]
        │
        ▼
[GPU Worker Daemon (Python, RTX 4060)]
   ├── EasyOCR (CRAFT + ResNet-BiLSTM)
   ├── Aadhaar QR Decoder (BigInt → Gzip → Fields)
   ├── Face Detection (YuNet ONNX)
   └── Signature Extraction (HSV ink isolation)
        │ JSON-RPC over Named Pipe (\\.\pipe\goaonauto_ipc)
        ▼
[Document Classifier (15+ categories, weighted TF-IDF)]
        │
        ▼
[Dossier Synthesis] → applicant_dossier.json
        │
   ┌────┴────┐
   ▼         ▼
[Raylib GUI]  [LaTeX Compiler]
   │              │
   ▼              ▼
[residence_form_data.json + residence_declaration.pdf]
        │
        ▼
[Playwright → Brave → GoaOnline Portal (25+ form fields)]
```

---

### Q: How do TypeScript and Python processes communicate?
**A:** Through a persistent line-delimited JSON-RPC protocol over a Windows Named Pipe (`\\.\pipe\goaonauto_ipc`).

**Flow:**
1. TypeScript's `GpuDaemonClient` calls `ensureDaemonRunning()` — checks if the named pipe server is active, otherwise spawns the Python daemon as a child process
2. Connects to the named pipe (persistent stream avoiding reconnection overhead)
3. Sends JSON requests: `{"id": "uuid", "action": "batch_process", "paths": [...]}\n`
4. Python daemon processes the request using GPU, returns: `{"id": "uuid", "success": true, "results": [...]}\n`
5. TypeScript parses the response and continues the pipeline

The persistent connection avoids reconnection overhead. The daemon keeps PyTorch models resident in GPU VRAM (~2-4 seconds to load cold, but instant on warm calls).

The persistent connection avoids reconnection overhead. The daemon keeps PyTorch models resident in GPU VRAM (~2-4 seconds to load cold, but instant on warm calls).

---

## 4. Technical Deep-Dive Questions

### Q: How does Aadhaar QR decoding work?
**A:** India's UIDAI uses two QR code formats:

**Format 1 — Legacy XML:**
- Plain text or Base64-wrapped XML: `<PrintLetterBarcodeData uid="..." name="..." dob="..." gender="..." ...>`
- Parsed with regex attribute extraction

**Format 2 — Secure e-Aadhaar V2/V3 (the hard one):**
1. QR data is a giant Base10 BigInteger string (1,200+ digits)
2. Convert to raw bytes: `big_int.to_bytes((big_int.bit_length() + 7) // 8, byteorder='big')`
3. First ~256 bytes are an RSA digital signature — skip these
4. Search for GZIP magic bytes `\x1f\x8b\x08` to find the compressed payload
5. Decompress using `zlib.decompress()` with three fallback window configurations:
   - `MAX_WBITS | 16` (standard gzip)
   - `MAX_WBITS | 32` (auto-detect)
   - `-MAX_WBITS` (raw deflate)
6. Decompressed stream is `\xff`-delimited:
   - Field 2: Full Name
   - Field 3: DOB (DD-MM-YYYY)
   - Field 4: Gender (M/F/T)
   - Field 5: Care Of (S/O, D/O, W/O)
   - Fields 6-14: District, House No, Locality, Pincode, State, Taluka, Village

**Why this matters:** QR data is cryptographically signed by UIDAI — it's a "golden source" with 100% accuracy, unlike OCR which has typos.

---

### Q: What is the Verhoeff checksum and why do you use it?
**A:** The Verhoeff algorithm is a checksum based on the dihedral group D₅ (the symmetry group of a regular pentagon). It's used by India's UIDAI for Aadhaar number validation.

**Aadhaar number rules:**
- Exactly 12 digits
- Never starts with 0 or 1
- Last digit is the Verhoeff check digit

**How it works:** Uses three mathematical tables (multiplication, permutation, inverse) based on D₅ group operations. The algorithm processes each digit through these tables and validates that the final checksum equals 0.

**Why I use it:** When OCR extracts a 12-digit number from a document, I can validate it's actually an Aadhaar number (not just a random 12-digit sequence) by running the Verhoeff check. Validated numbers get confidence 1.0; failed ones are rejected.

---

### Q: How does the document classification work?
**A:** A weighted multi-rule TF-IDF-style classifier.

For each document class C (e.g., `residence_cert`, `birth_cert`):

```
Score(C) = Σ(wₖ × count(k)) + Bonus_filename - Σ(pₑ × count(e))
```

Where:
- `wₖ` = weight of keyword k (e.g., "RESIDENCE" = 3.0 for `residence_cert`)
- `count(k)` = occurrences of keyword in OCR text
- `Bonus_filename` = extra score if filename contains category hints
- `pₑ` = penalty for exclusion words (e.g., "BIRTH" penalizes `residence_cert`)

**Additional rules:**
- `requiredTokens`: If defined, at least one must be present or score drops to 0 (e.g., Aadhaar must contain "UNIQUE IDENTIFICATION AUTHORITY OF INDIA")
- The category with the highest normalized score above a minimum threshold wins

**Continuous learning:** The OCR Trainer GUI lets operators correct misclassifications, which feeds into `corrections.jsonl`. The `retrain_classifier.ts` tool recalculates keyword weights based on accumulated corrections.

---

### Q: How does OCR post-processing work?
**A:** OCR engines (EasyOCR, Tesseract) frequently confuse optically similar characters:

| OCR Output | Correct | Context |
|------------|---------|---------|
| `O` | `0` | In dates: `O1/O5/2004` → `01/05/2004` |
| `l` or `I` | `1` | In numbers: `l234` → `1234` |
| `S` | `5` | In pincodes: `40S003` → `405003` |
| `B` | `8` | In UIDs: `B012` → `8012` |

**Processing chain:**
1. **Regex passes**: Target date patterns, pincodes, certificate numbers
2. **Word boundary substitutions**: Apply learned corrections using `\b${word}\b`
3. **Continuous learning**: When an operator corrects text in the OCR Trainer GUI, the correction is saved to `dataset/ocr_spell_corrections.json` and the cache is invalidated

---

### Q: What is the "Golden Source" data precedence tiering?
**A:**
- **Tier 1 — Aadhaar QR (Confidence 1.0):** Cryptographically signed by UIDAI. Name, DOB, gender, and address from QR *always* override OCR data.
- **Tier 2 — OCR Fallbacks:** Used only for fields absent from QR: years of residence in Goa, previous certificate numbers, parent relations from birth certificates, school names from bonafide certificates.

The unified dossier synthesizer merges both tiers, with Tier 1 taking priority on any conflicts.

---

### Q: How does face detection work for passport photos?
**A:**
1. When OCR returns <35 characters from an image, it's tested for passport photo or signature features
2. **Face detection**: OpenCV YuNet ONNX model detects face bounding boxes
3. **Portrait validation**:
   - Aspect ratio check: height > width (portrait ratio ~3.5cm × 4.5cm ≈ 0.77)
   - Face coverage: 40%-75% of image area
4. If validated, the image is classified as `passport_photo`

---

### Q: How does signature detection work?
**A:**
1. Convert image to HSV color space
2. Isolate blue ink (H: 100-130, S: 50-255, V: 50-255) and black ink
3. Run Otsu thresholding and contour analysis
4. Validate stroke aspect ratio and bounding box stroke density
5. Convert dark ink strokes to 4-channel RGBA (transparent background, alpha = 0)
6. This produces clean signatures for placement on LaTeX affidavit templates

---

## 5. Decision & Trade-Off Questions

### Q: Why Raylib instead of Electron, Qt, or a web-based GUI?
**A:**

| Factor | Raylib | Electron | Qt |
|--------|--------|----------|-----|
| **Memory** | <30 MB | >400 MB | ~200 MB |
| **Startup** | <200ms | 3-5 seconds | 1-2 seconds |
| **GPU Integration** | Direct OpenGL textures | Chromium renderer | Widget system |
| **Dynamic Resize** | Instant (no layout reflow) | Layout reflow delays | Signal/slot delays |
| **Dependencies** | Single .pyd/.so | Node.js + Chromium | Qt binaries |

**Key reasons:**
1. **Memory**: The system already runs Brave browser + GPU daemon + Google Drive sync. Adding Electron would add 400MB+ RAM for each GUI window.
2. **Immediate Mode**: Every frame at 60 FPS, the UI is recalculated from scratch. This means window resize works instantly without layout reflow glitches.
3. **GPU affinity**: Raylib shares OpenGL context, making it easy to render GPU-processed textures directly.
4. **Speed**: <200ms cold start vs 3-5 seconds for Electron. Important when the watcher spawns confirmation dialogs for each batch.

---

### Q: Why Bun instead of Node.js?
**A:**
1. **Speed**: Bun's TypeScript execution is 3-5× faster than Node.js with tsx/ts-node compilation
2. **Native TypeScript**: No separate compilation step needed
3. **Built-in tooling**: Package manager, test runner, file I/O APIs built-in
4. **Compatibility**: Falls back to `npx tsx` for Playwright scripts where Bun's compatibility is imperfect

---

### Q: Why Brave browser instead of headless Chromium?
**A:**
1. **Persistent profile**: GoaOnline requires citizen authentication. A persistent browser profile (`.brave_automation_profile`) preserves cookies/sessions across runs, so the operator doesn't re-login every time.
2. **Headed mode**: The bot runs in "Safe Review Mode" — the operator sees the browser, watches forms being filled, and can intervene. Headless would hide this.
3. **Sandbox enforcement**: By using `chromiumSandbox: true` and `ignoreDefaultArgs: ['--no-sandbox']`, Brave launches cleanly without the yellow security warning infobar.

---

### Q: Why LaTeX for PDF generation instead of HTML-to-PDF or a PDF library?
**A:**
1. **Legal precision**: Legal affidavits require exact formatting — specific fonts, margins, spacing. LaTeX gives sub-millimeter typographic control.
2. **Single-page guarantee**: `\onehalfspacing` combined with calculated margins ensures the declaration fits exactly on one A4 page.
3. **Templating**: LaTeX templates use simple placeholder tokens (`{{FULL_NAME}}`, `{{DOB}}`) that are replaced via regex — clean and maintainable.
4. **Print quality**: LaTeX produces 300 DPI print-ready PDFs with perfect kerning and ligatures.

---

### Q: Why a persistent GPU daemon instead of spawning Python per-request?
**A:**
- **Cold start penalty**: Loading PyTorch + EasyOCR + CUDA models takes 2-4 seconds. If spawned per-document, processing 20 documents = 40-80 seconds of wasted model loading.
- **Persistent daemon**: Models stay resident in GPU VRAM. First load is 2-4s, subsequent calls are instant (only inference time: ~200-800ms).
- **VRAM management**: The daemon caps CUDA allocations to 90% of physical VRAM (`torch.cuda.set_per_process_memory_fraction(0.90, 0)`), leaving headroom for Windows DWM and browser rendering.
- **Batch efficiency**: Multiple documents are processed sequentially through warm GPU tensors without model reloads.

---

### Q: Why didn't you use a cloud OCR service (Google Vision, AWS Textract)?
**A:**
1. **Privacy**: Aadhaar cards contain sensitive biometric identifiers. Sending them to cloud services raises data protection concerns.
2. **Cost**: At scale, cloud OCR costs add up. The RTX 4060 is a one-time hardware cost.
3. **Latency**: Local GPU inference is 200-800ms. Cloud round-trips add 500-2000ms network latency.
4. **Offline capability**: The system works without internet (except for the portal submission step).
5. **Customization**: The custom post-processing pipeline (optical disambiguation, spell correction, Goa-specific dictionaries) would be harder to implement on top of a cloud API.

---

### Q: Why a Trie instead of a simple queue or hashmap for the file watcher?
**A:**
- **Queue**: Doesn't model the hierarchical folder structure. Can't efficiently determine "all files in Client_John are ready."
- **HashMap**: Flat lookup, no parent-child relationship tracking. Can't do dirty-bit propagation or subtree pruning.
- **Trie**: Models the directory hierarchy naturally. Dirty-bit propagation enables O(depth) marking and O(dirty_nodes) harvesting. Clean subtrees are pruned in O(1) during DFS traversal.

---

## 6. Debugging & Problem-Solving War Stories

### Q: Tell me about the hardest bug you encountered
**A:** The **ASP.NET PostBack navigation bug**.

**The problem:** GoaOnline's "Proceed to Apply" button is an anchor tag with `href="javascript:__doPostBack(...)"`. When Playwright's `locator.click()` sent a synthetic Chrome DevTools Protocol (CDP) mouse event, Chromium treated it as an **untrusted navigation gesture** because it targets a `javascript:` pseudoprotocol URL. The page silently stayed on the overview page — no error, no crash, just... nothing happened.

**How I debugged it:**
1. Tried standard `locator.click()` — didn't work
2. Tried `.click({force: true})` — still didn't work
3. Tried `dispatchEvent('click')` — still didn't work
4. Read the Chromium source code and realized CDP synthetic events are intentionally blocked on `javascript:` URLs for security
5. Realized I needed to execute the click in the page's **native JavaScript context**

**The fix:**
```javascript
await page.evaluate(() => {
  const el = document.querySelector('#cphBody_gvService_lnkProceedApply_0');
  if (el) {
    el.click();
  } else if (window.__doPostBack) {
    window.__doPostBack('ctl00$cphBody$gvService$ctl02$lnkProceedApply', '');
  }
});
```

Plus: Added `page.on('dialog')` handler for auto-accepting alerts, and polling for URL transition away from `/deptServices`.

---

### Q: Tell me about a challenging performance issue
**A:** **GPU model cold start vs. hot inference.**

Initially, each document triggered a fresh Python subprocess that loaded PyTorch + CUDA models from scratch (2-4 seconds each). For a batch of 20 documents, the total model loading overhead was 40-80 seconds — far longer than the actual inference time.

**Solution:** I redesigned the system as a persistent daemon that:
1. Starts once and keeps weights resident in GPU VRAM
2. Accepts batches over TCP, processes sequentially without model unloads
3. Caps VRAM at 90% to prevent OOM
4. Uses `ensureDaemonRunning()` with health check (`ping`/`pong`) before dispatching

This reduced 20-document batch time from ~90 seconds to ~15 seconds.

---

### Q: How did you handle the cascading AJAX dropdown problem?
**A:** GoaOnline's address modal uses ASP.NET UpdatePanels. Selecting a District triggers a server round-trip that rebuilds the Taluka `<select>`. Selecting Taluka rebuilds Village `<select>`.

**The naive approach fails:** If you select District and immediately try to select Taluka, the Taluka dropdown hasn't been repopulated yet — it's still disabled with a single "Loading..." option.

**My solution:**
```typescript
// 1. Select District
await page.selectOption('#id47', { label: data.district });
// 2. Wait for Taluka to repopulate AND become enabled
await page.waitForFunction(() => {
  const taluka = document.querySelector('#id48');
  return taluka && taluka.options.length > 1 && !taluka.disabled;
}, null, { timeout: 10000 });
// 3. Now select Taluka
await page.selectOption('#id48', { label: data.taluka });
// 4. Wait for Village repopulation...
```

The key insight is `waitForFunction()` with a DOM predicate — not `waitForSelector()` (which only waits for element existence, not content population).

---

### Q: How did you handle file sync race conditions?
**A:** When files are being uploaded via Google Drive sync or actively written by a scanner, the file watcher fires events before the file is fully written. Reading a half-written PDF produces corrupted data.

**Solution — I/O Quiescence Detection:**
```typescript
async function isFileWriteComplete(filePath, checkIntervalMs = 300) {
  const size1 = (await fs.stat(filePath)).size;
  await sleep(checkIntervalMs);
  const size2 = (await fs.stat(filePath)).size;
  return size2 === size1 && size2 > 0;
}
```

Two consecutive reads must match and be non-zero. The file is held in the buffer until stable.

---

## 7. Computer Vision & AI/ML Questions

### Q: What OCR engine do you use and why?
**A:** **EasyOCR** (CRAFT text detection + ResNet-BiLSTM recognition), running on CUDA (RTX 4060).

**Why EasyOCR over Tesseract:**
- CRAFT detector is superior for multi-script, multi-orientation text on scanned documents
- BiLSTM recognizer handles connected cursive and degraded text better
- GPU acceleration makes it 5-10× faster than Tesseract on CPU
- Better accuracy on Indian documents (Hindi, Marathi, Konkani mixed scripts)

**Tesseract fallback:** Used as a secondary option when EasyOCR confidence is low.

---

### Q: How do you handle the 90% VRAM cap?
**A:** 
```python
torch.cuda.set_per_process_memory_fraction(0.90, 0)
```
This tells PyTorch to use at most 90% of the RTX 4060's physical VRAM. The remaining 10% is reserved for:
- Windows Desktop Window Manager (DWM) compositor
- Brave browser GPU rendering
- Raylib OpenGL context

Without this cap, large batches can cause CUDA OOM errors that crash the daemon and require a full restart.

---

### Q: How does the continuous learning loop work?
**A:**
1. **OCR Trainer GUI**: Operator reviews documents in a 3-pane window (Document Inspector + OCR Stream + Ground Truth)
2. **Rating**: 1-5 star extraction quality assessment
3. **Corrections**: Operator corrects misrecognized text and misclassifications
4. **Persistence**: Corrections are saved to `corrections.jsonl` and `ocr_spell_corrections.json`
5. **Retraining**: `retrain_classifier.ts` reads corrections and recalculates TF-IDF keyword weights
6. **Integration**: Updated weights are applied to the classifier, and spell corrections are loaded into the OCR post-processor

This creates a feedback loop where the system improves with every operator interaction.

---

### Q: How does background removal work for passport photos?
**A:** Uses U2-Net or BiRefNet neural network models for semantic segmentation:
1. Model produces a foreground mask (salient object detection)
2. Mask is applied as an alpha channel to isolate the person
3. Transparent background is replaced with solid white
4. Image is compressed to <50KB (GoaOnline portal compliance)
5. Aspect ratio is locked to 3.5cm × 4.5cm passport standard

---

## 8. Web Automation & Browser Engineering Questions

### Q: How does the portal automation handle authentication?
**A:** It doesn't automate login. Instead:
1. Brave launches with a persistent profile (`.brave_automation_profile`)
2. The bot navigates to GoaOnline and waits for the operator to manually log in
3. `isUserLoggedIn()` polls with a 5-step algorithm:
   - URL exclusion (login/register pages → false)
   - Password field presence → false
   - Header login button presence → false
   - Logout anchor/user profile container → true
   - `.ASPXAUTH` cookie validation (length > 20 bytes) → true
4. Once authenticated, the bot takes over for form filling

**Why manual login?** GoaOnline uses CAPTCHAs and OTP-based citizen authentication. While we have a CAPTCHA solver, the OTP step requires the citizen's phone — only a human can complete it.

---

### Q: What is a Page Object Model (POM) and how do you use it?
**A:** POM is a design pattern where each web page is represented as a class with:
- **Selectors** as properties: `#id30` for Full Name, `#DOB` for Date of Birth
- **Actions** as methods: `fillPersonalDetails()`, `fillResidentialAddressModal()`

My `ResidenceFormPage` POM maps 59 interactive controls across GoaOnline's Screen 1:
- Application mode (Self/Relative)
- Purpose & period selection
- Personal info (name, DOB, age, gender, marital status)
- Residential address modal (with AJAX cascading dropdowns)
- ID proof (Aadhaar number with Verhoeff validation)
- Self-declaration checkbox

This encapsulation makes the automation code testable, maintainable, and readable.

---

### Q: What is the Visual Simulation Tracker?
**A:** During headed verification runs, operators need visual proof of what the bot is doing. The tracker injects:
1. **Virtual cursor**: SVG cursor that smoothly animates to each target element
2. **Click ripple**: Expanding animated circle on mouse clicks
3. **ASP.NET target tooltip**: Shows the resolved PostBack target name

This is injected via `page.evaluate()` and is purely visual — `pointer-events: none` ensures it doesn't interfere with the actual form.

---

### Q: How does the Dracula Status Pill overlay work?
**A:** A floating badge injected into the GoaOnline portal DOM:
- Position: `fixed; top: 16px; right: 24px; z-index: 2147483647` (max z-index)
- `pointer-events: none` — clicks pass through to the form beneath
- Color-coded states: Purple (info), Orange (waiting for login), Cyan (working), Green (success)
- Updated via `page.evaluate()` during each automation step

---

### Q: How do you handle browser profile lock files?
**A:** When Playwright/Brave crashes, it leaves behind lock files (`SingletonLock`, `SingletonCookie`, `SingletonSocket`) in the profile directory. On next launch, Chromium sees these and refuses to start ("Profile in use" error).

**Solution:** On startup, `launchBravePortalContext()` automatically unlinks stale lock files before launching the browser.

---

## 9. GUI & UI/UX Design Questions

### Q: What is Immediate Mode GUI (IMGUI) and how does Raylib implement it?
**A:** Unlike **retained mode** GUI frameworks (React, Qt, WPF) that maintain a persistent widget tree, **immediate mode** GUIs recalculate and redraw the entire UI from scratch every single frame (60 FPS).

**Benefits:**
- No state synchronization bugs (UI always reflects current data)
- Near-zero memory footprint (<30 MB)
- Instant response to window resize (no layout reflow)
- Direct GPU texture binding

**Trade-off:** You must manually manage layout calculations, but for data-entry forms this is straightforward.

---

### Q: How does the High-DPI font rendering work?
**A:** Default Raylib bitmap fonts look pixelated on modern displays with 125-200% OS scaling.

**My solution:**
1. Load fonts at 48pt base size (high-resolution texture atlas)
2. Apply bilinear texture filtering: `rl.set_texture_filter(font.texture, TEXTURE_FILTER_BILINEAR)`
3. When rendering at 14-24pt UI sizes, the hardware downscales from the 48pt atlas with smooth interpolation
4. `measure_text_clean()` computes exact float horizontal dimensions for pixel-perfect centering

**Fallback chain:** JetBrains Mono → Cascadia Code → Consolas → Segoe UI

---

### Q: Explain the Window-in-Window architecture of the OCR Trainer
**A:** The OCR Trainer has 3 docked sub-windows inside a single Raylib window:

1. **Document Inspector (Left)**: Pan/zoom viewport with macOS-style colored titlebar dots, isolated drag handling (dragging the image doesn't drag the parent window)
2. **Live OCR Stream (Center)**: Monospace line-numbered gutter, hover highlighting, click-to-populate spell teaching
3. **Ground-Truth & Retraining (Right)**: Category selector, 1-5 star rating, 7 demographic fields, spell correction card

Each sub-window has its own:
- Titlebar with action buttons
- Scissor-clipped content area (preventing overflow)
- Independent scroll state
- Hover/click isolation

---

### Q: How does the Dynamic Signature Scaler work?
**A:** Scanned signatures vary wildly in size. A fixed-size box produces illegible or oversized signatures on legal documents.

**Controls:** `[-] 100% [+] [↺]`
- Scale range: 50% to 240%
- Default: 100% = 4.5cm × 1.5cm
- LaTeX sync: Scale adjustments modify `\includegraphics[width={w_cm}cm, height={h_cm}cm, keepaspectratio]`
- Instant visual preview in the GUI

---

## 10. Data Engineering & Pipeline Questions

### Q: What does `applicant_dossier.json` contain?
**A:** The unified output of the dossier synthesis pipeline:
```json
{
  "fullName": { "value": "John Doe", "confidence": 1.0, "source": "aadhaar_qr" },
  "dob": { "value": "14/08/1998", "confidence": 1.0, "source": "aadhaar_qr" },
  "age": { "value": 28, "confidence": 1.0, "source": "calculated" },
  "gender": { "value": "Male", "confidence": 1.0, "source": "aadhaar_qr" },
  "aadhaarNumber": { "value": "123456789012", "confidence": 1.0, "source": "aadhaar_qr" },
  "address": { ... },
  "yearsInGoa": { "value": 15, "confidence": 0.9, "source": "residence_cert_ocr" },
  "previousCertNumber": { ... },
  "documents": [ ... ]
}
```

Each field has a `value`, `confidence` score, and `source` identifier. This enables the system to display uncertainty to the operator.

---

### Q: How does the residency duration deduction work?
**A:** Three extraction heuristics with different confidence levels:
1. **Direct duration**: "for the last 15 years" → 15. Confidence: 0.9
2. **Since-year**: "since the year 2010" → currentYear - 2010. Confidence: 0.85
3. **Date spans**: "from 2015 to 2023" → 8 years. Confidence: 0.8

The system needs to establish ≥15 years continuous residency for REV05.

---

## 11. Security, Privacy & Compliance Questions

### Q: How do you handle Aadhaar data security?
**A:**
1. **No cloud transmission**: All processing happens locally on the operator's machine
2. **No Aadhaar storage**: Extracted data is written to local JSON files only
3. **Verhoeff validation**: Ensures only genuine Aadhaar numbers are processed
4. **Sandbox enforcement**: Browser automation uses `chromiumSandbox: true`
5. **Local GPU**: No document images leave the machine for OCR

---

### Q: Why manual login instead of automated credentials?
**A:** GoaOnline uses citizen authentication with OTP verification. Automating this would require:
1. Storing citizen credentials (security risk)
2. Intercepting OTPs (privacy violation)
3. Bypassing CAPTCHAs programmatically (potential ToS violation)

The human-in-the-loop design keeps the operator responsible for authentication.

---

## 12. Testing & Quality Assurance Questions (QA / SDET Focus)

### Q: What testing strategies and test levels did you use in this project?
**A:** I applied a multi-tier testing strategy adhering to the testing pyramid:
1. **Unit Testing:**
   - Algorithmic correctness: Verhoeff checksum algorithm for Aadhaar validation (verifying transposition errors and single-digit corruptions).
   - Data structures: Trie-based change buffer (insertion, prefix search, change accumulation, DFS traversal).
   - Resource thresholds: System Governor heuristics (RAM/VRAM/CPU boundary checks).
2. **Integration & Contract Testing:**
   - JSON-RPC over TCP IPC: Testing message serialization, malformed payloads, handshake verification, and daemon disconnect/reconnect handling.
   - Vision & Classification Pipeline: Testing end-to-end flow from scanned document ingestion → OCR extraction → synthesis into `applicant_dossier.json`.
3. **End-to-End (E2E) Browser Automation Testing:**
   - Built with Playwright: Automating navigation, 59-control form entry, dynamic dropdown cascading, and validation error detection on the live portal.
4. **Performance & Stress Testing:**
   - GPU daemon batch benchmarks: Measuring processing latency (<1.2s per doc target on RTX 4060) and monitoring for VRAM memory leaks.
   - File watcher debounce stress tests: Verifying rapid concurrent file drops don't trigger partial-write race conditions.
5. **Visual & Exploratory Testing:**
   - Headed browser runs and Safe Review Mode: Providing real-time visual tracking of field population for manual QA inspection.

---

### Q: How do you apply Test Design Techniques (Equivalence Partitioning & Boundary Value Analysis) to this project?
**A:**
- **Example 1: Residence Certificate Eligibility (Goa 15-Year Rule):**
  - **Equivalence Classes:**
    - Valid Class: Residency >= 15 years (Eligible).
    - Invalid Class: Residency < 15 years (Ineligible / Rejected).
  - **Boundary Values (BVA):**
    - 14 years (Boundary: Just below threshold -> Must trigger rejection or manual review flag).
    - 15 years (Boundary: Exact threshold -> Valid, passes check).
    - 16 years (Boundary: Just above threshold -> Valid, passes check).
    - Extreme/Negative inputs: 0, -1, >100, non-numeric values.
- **Example 2: Aadhaar 12-Digit Input:**
  - **Equivalence Classes:** Exactly 12 numeric digits with valid Verhoeff checksum vs non-12 digits vs invalid checksum.
  - **Boundaries:** 11 digits (fail), 12 digits (pass), 13 digits (fail), empty string.

---

### Q: What negative test cases and edge cases did you consider?
**A:**
1. **Corrupted or Partial File Writes:** A user uploads a multi-megabyte PDF over a slow disk write -> Debounce (800ms) and stability check (300ms) ensure incomplete files aren't picked up before they finish writing.
2. **Unreadable / Degraded Documents:** Low-DPI scans, extreme rotations, blurred signatures -> System flags confidence scores < 0.7 for manual operator review instead of failing silently.
3. **Tampered / Fake Aadhaar:** Aadhaar number with one flipped digit or swapped adjacent digits -> Caught instantly by the Verhoeff dihedral group D5 algorithm before hitting the portal.
4. **Cascading Dropdown Failures in ASP.NET:** Selecting "Taluka" triggers an async PostBack to populate "Village". If the village dropdown is clicked before the AJAX call resolves, tests fail -> Handled using explicit DOM response checks rather than hardcoded timers.
5. **Daemon Crash / IPC Disconnect:** If Python daemon runs out of VRAM or crashes mid-batch -> TypeScript orchestrator detects EOF/socket reset, emits a health alert, and triggers an automatic restart.

---

### Q: Why did you use the Page Object Model (POM) for browser automation?
**A:**
- The GoaOnline portal contains **25+ distinct fields** across applicant details, address modal dialogs, parentage, and declarations.
- Without POM, locator strings like `input#ctl00_ContentPlaceHolder1_txtApplicantName` would be duplicated across dozens of scripts. If the portal developers change an ID or structure, every script breaks.
- With POM:
  - **Centralized Locators:** All fields and selectors are mapped in a dedicated `GoaOnlineFormPage` class.
  - **Maintainability:** A portal markup change requires updating exactly one line in the POM.
  - **Readability & Reusability:** Test scripts read like high-level actions (`page.fillApplicantDetails(dossier)`, `page.selectTalukaAndVillage('Tiswadi', 'Panaji')`).

---

### Q: How do you prevent flaky tests and race conditions in Playwright?
**A:** Flakiness in web automation is almost always caused by improper wait conditions. In this project:
1. **Never use static `sleep()` / `waitForTimeout()`:** Arbitrary delays make tests slow on fast machines and fail on slow machines.
2. **Rely on Playwright's Auto-Waiting:** Playwright automatically waits for elements to be attached to DOM, visible, stable, enabled, and editable before clicking or typing.
3. **Handle ASP.NET AJAX `__doPostBack`:** Legacy ASP.NET portals replace DOM subtrees during partial postbacks. We wait for `page.waitForLoadState('networkidle')` or wait for specific target options to appear in dependent dropdowns after selecting a parent.
4. **Actionability checks & retry policies:** For critical form actions, verify element states (e.g., verifying `aria-busy` or checking that the loading spinner overlay is detached).

---

### Q: How do you choose your locators (ID vs CSS vs XPath vs Role)?
**A:**
1. **User-Facing / Accessibility-First (Best):** `getByRole('button', { name: 'Submit' })`, `getByLabel('Full Name')` — least likely to break during styling refactors.
2. **Stable IDs:** When working with legacy ASP.NET WebForms, IDs often look like `ctl00_ContentPlaceHolder1_ddlTaluka`. We use regex/attribute-contains locators (e.g. `[id$='ddlTaluka']`) so prefix changes don't break our automation.
3. **Avoid Fragile Absolute XPaths:** Never use `/html/body/div[2]/table/tr[3]/td[1]/input`. Any minor layout change completely breaks the test.

---

### Q: How do you test the IPC communication between the TypeScript orchestrator and Python daemon?
**A:**
- **Contract & Schema Testing:** Validated JSON-RPC 2.0 specs (`jsonrpc: "2.0"`, `method`, `params`, `id`, `result`, `error`).
- **Timeout Handling:** If the GPU daemon hangs on a huge image, the client must trigger an RPC timeout after a defined deadline (30 seconds) rather than hanging the entire pipeline.
- **Payload Fuzzing & Error Codes:** Sent malformed JSON, missing parameter blocks, and nonexistent file paths to verify the Python daemon returns standard JSON-RPC error objects (`-32600 Invalid Request`, `-32602 Invalid Params`) instead of unhandled fatal exceptions.

---

### Q: How do you test without corrupting production data or submitting false applications?
**A:**
1. **Safe Review Mode:** The bot executes the entire pipeline up to Screen 1 form entry and file attachment, but **never clicks the final `Submit` button**. It leaves the headed browser open for human inspection.
2. **Synthetic Test Data Generation:** Used synthetic Aadhaar QR payloads with valid mathematical Verhoeff checksums but designated mock numbers for local testing.
3. **API & DOM Mocking:** In CI/CD runs where the live government portal is unreachable or external network access is blocked, Playwright's `page.route()` intercepts network calls and serves recorded mock responses.

---

### Q: If an automated test fails on the live portal, what is your debugging & triaging process?
**A:**
1. **Analyze Failure Artifacts:**
   - Inspect **Playwright Trace Viewer**: Step-by-step DOM snapshots, console logs, network requests, and action timings.
   - Review automatically captured **screenshots** and **video recordings** at the exact millisecond of failure.
2. **Root Cause Categorization:**
   - **Type A: External/Environment Flake:** Portal down (503 Service Unavailable), CAPTCHA service failure, or network timeout.
   - **Type B: Application/Portal Change:** Portal updated DOM structure, changed dropdown IDs, or introduced new mandatory fields.
   - **Type C: Automation Script Defect:** Race condition or incorrect locator in the test script.
   - **Type D: Data Issue:** Malformed input document or unparseable scanned PDF.
3. **Bug Reporting:** Document reproduction steps, expected vs. actual behavior, trace file URL, and browser version.

---

### Q: How do you test for performance and memory leaks in the GPU daemon?
**A:**
1. **Baseline Measurement:** Benchmark single-document inference time (< 1.2s) and cold-start model load time (~4.5s).
2. **Sustained Load / Soak Testing:** Feed a batch of 50 consecutive documents and monitor VRAM allocation using `torch.cuda.memory_allocated()`.
3. **Leak Detection:** Ensure memory is properly freed between inference calls (calling `torch.cuda.empty_cache()` when thresholds exceed 90%).
4. **Governor Threshold Testing:** Artificially throttle available system RAM below 3.0 GB to verify that the `SystemGovernor` successfully pauses job ingestion rather than throwing an unhandled `Out Of Memory (OOM)` crash.

---

## 13. Behavioral & STAR Method Questions

### Q: Tell me about a time you had to learn a new technology quickly
**A (STAR):**
- **Situation**: I needed to decode Aadhaar Secure QR codes (V2/V3 format) but couldn't find any JavaScript/TypeScript library that handled the BigInt → Gzip → field extraction pipeline
- **Task**: Implement the decoder from scratch by reverse-engineering the UIDAI specification
- **Action**: I studied the UIDAI technical documentation, analyzed raw QR byte dumps, learned about Gzip magic bytes and zlib window configurations, and implemented the full decoder in Python with three fallback decompression strategies
- **Result**: The decoder handles both Legacy XML and Secure V2/V3 formats with 100% accuracy on test samples, extracting golden-source demographic data

---

### Q: Tell me about a time you made a difficult architectural decision
**A (STAR):**
- **Situation**: The project needed both GPU-accelerated ML (Python ecosystem) and browser automation (TypeScript/Playwright ecosystem)
- **Task**: Choose between a monolithic single-language architecture or a polyglot dual-process architecture
- **Action**: I evaluated: (1) Python-only with Selenium — poor browser automation, no Playwright equivalent; (2) TypeScript-only with native ML bindings — immature, fragile C++ addons; (3) Dual-process with JSON-RPC IPC — clean separation, best-of-breed for each domain
- **Result**: The dual-process architecture adds <5ms IPC latency while enabling the best tools for each job. The JSON-RPC bridge is only ~10 lines of code on each side.

---

### Q: Tell me about a time you optimized performance
**A (STAR):**
- **Situation**: Processing 20 documents took 90+ seconds because each one spawned a fresh Python process loading PyTorch models
- **Task**: Reduce batch processing time to under 20 seconds
- **Action**: Redesigned the system as a persistent daemon keeping models in GPU VRAM, with Named Pipe-based batch dispatching and VRAM caps
- **Result**: 20-document batches now complete in ~15 seconds — a 6× improvement

---

### Q: What would you do differently if you started over?
**A:**
1. **Shared Memory (`mmap`)**: If streaming high-FPS video frames across processes, shared memory would achieve true zero-copy
2. **Docker containerization**: Currently Windows-only. Docker would enable Linux deployment
3. **SQLite instead of JSON files**: For corrections, dossier data, and training samples — better querying and ACID guarantees
4. **React Native / Tauri for GUI**: If cross-platform were important, Raylib's Python bindings limit portability

---

## 14. Scalability & Future Scope Questions

### Q: How would you scale this to handle thousands of applications per day?
**A:**
1. **Worker pool**: Multiple GPU daemons on different machines, load-balanced via a task queue (Redis/RabbitMQ)
2. **Database backend**: Replace JSON files with PostgreSQL for concurrent access and ACID guarantees
3. **Containerization**: Dockerize each component (watcher, GPU daemon, portal bot) for horizontal scaling
4. **Queue-based architecture**: Replace the in-memory Trie buffer with a persistent message queue
5. **Multi-GPU**: Support for multiple GPUs with model parallelism

---

### Q: What's next for the project (Phase 3)?
**A:**
1. **Screen 2 DOM Survey**: Map document upload slots for GoaOnline's attachment page
2. **Automated file uploads**: Wire processed assets from the dossier folder to the portal's upload slots
3. **Fee & submission verification**: Complete the payment/acknowledgement generation stage
4. **Multi-service support**: Extend beyond Residence Certificates to other GoaOnline services (Income, Caste, Domicile)
5. **Mobile companion app**: Photo capture with QR scanning on-device

---

### Q: How would you add support for a new document type?
**A:**
1. Add keyword rules in `src/classifier/rules.ts` with weights and exclusions
2. Add extraction logic in `dossierExtractor.ts` for any new fields
3. Add training samples to `dataset/raw/<new_category>/`
4. Run `bun run data:retrain` to optimize keyword weights
5. The rest of the pipeline (OCR, classification, dossier synthesis) handles it automatically

---

## 15. Rapid-Fire Quick Recall Sheet

> **Memorize these numbers and facts:**

| Fact | Value |
|------|-------|
| Number of pipeline stages | **5** |
| GPU model | **NVIDIA GeForce RTX 4060** |
| VRAM cap | **90%** |
| Minimum free RAM threshold | **3.0 GB** |
| Maximum CPU threshold | **80%** |
| IPC transport | **Windows Named Pipe (`\\.\pipe\goaonauto_ipc`)** |
| File debounce interval | **800ms** |
| File stability check interval | **300ms** |
| Document categories | **15+** |
| Active form fields | **25+** |
| System Governor max wait | **15 seconds** |
| LaTeX compile time | **<2 seconds** |
| GPU inference target | **<1.2s per document** |
| Font atlas base size | **48pt** |
| Signature scale range | **50% to 240%** |
| Aadhaar digits | **12** |
| Aadhaar validation | **Verhoeff checksum (D5 group)** |
| IPC protocol | **Line-delimited JSON-RPC over Named Pipes** |
| GUI framework | **Raylib (Immediate Mode)** |
| GUI theme | **Dracula** |
| Browser | **Brave (Chromium engine)** |
| Automation library | **Playwright** |
| OCR engine | **EasyOCR (CRAFT + ResNet-BiLSTM)** |
| LaTeX engine | **MiKTeX pdflatex / XeLaTeX** |
| Font | **JetBrains Mono** |
| Runtime | **Bun 1.2+ (TypeScript), Python 3.13** |

---

> [!TIP]
> **Interview Strategy:**
> 1. **Start with the elevator pitch** (30 seconds)
> 2. **Draw the 5-stage pipeline** when asked about architecture
> 3. **Lead with the QR decoder story** for "hardest technical challenge"
> 4. **Lead with the PostBack bug** for "hardest debugging story"
> 5. **Lead with the persistent daemon optimization** for "performance improvement"
> 6. **Emphasize "human-in-the-loop"** for security/compliance questions
> 7. **Know your numbers** (59 controls, 15+ categories, 90% VRAM, 3GB RAM threshold)

---

> [!IMPORTANT]
> **Key differentiators to highlight:**
> - This is NOT just a script — it's a **full-stack production system** with GPU acceleration, desktop GUI, browser automation, and legal document generation
> - The **Aadhaar QR decoder** implements real cryptographic decoding (BigInt → Gzip → field extraction)
> - The **Trie-based change buffer** is a legitimate data structures contribution
> - The **dual-process architecture** demonstrates systems design thinking
> - The **continuous learning loop** shows ML engineering maturity
> - The **ASP.NET PostBack fix** demonstrates deep browser engine understanding
