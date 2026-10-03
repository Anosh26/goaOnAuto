"""
GoaOnAuto Architecture SVG Generator
Generates a comprehensive, modular, high-density SVG visual architecture map
covering every subsystem, process, protocol, and data flow in GoaOnAuto.
"""
import os
import sys
import xml.sax.saxutils as saxutils

def escape_xml(s: str) -> str:
    return saxutils.escape(str(s))

def build_architecture_svg() -> str:
    # 2800 x 2100 ultra-crisp scalable canvas
    width = 2800
    height = 2100

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background-color: #080c14; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;">')

    # Definitions: Gradients, Filters, Markers
    svg.append('''
  <defs>
    <!-- Background Grid -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#111927" stroke-width="1"/>
    </pattern>
    <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#1e293b" />
    </pattern>

    <!-- Card Shadow Filters -->
    <filter id="card-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
    <filter id="glow-emerald" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="glow-purple" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>

    <!-- Arrow Markers -->
    <marker id="arrow-emerald" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#10b981" />
    </marker>
    <marker id="arrow-purple" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#a855f7" />
    </marker>
    <marker id="arrow-amber" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#f59e0b" />
    </marker>
    <marker id="arrow-pink" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#ec4899" />
    </marker>
    <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#38bdf8" />
    </marker>
    <marker id="arrow-cyan" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#06b6d4" />
    </marker>

    <!-- Linear Gradients for Category Headers -->
    <linearGradient id="grad-title" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#ec4899" />
    </linearGradient>

    <linearGradient id="grad-col1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#10b981" stop-opacity="0.15" />
      <stop offset="100%" stop-color="#0b0f17" stop-opacity="0.9" />
    </linearGradient>
    <linearGradient id="grad-col2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.15" />
      <stop offset="100%" stop-color="#0b0f17" stop-opacity="0.9" />
    </linearGradient>
    <linearGradient id="grad-col3" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.15" />
      <stop offset="100%" stop-color="#0b0f17" stop-opacity="0.9" />
    </linearGradient>
    <linearGradient id="grad-col4" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ec4899" stop-opacity="0.15" />
      <stop offset="100%" stop-color="#0b0f17" stop-opacity="0.9" />
    </linearGradient>
    <linearGradient id="grad-col5" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.15" />
      <stop offset="100%" stop-color="#0b0f17" stop-opacity="0.9" />
    </linearGradient>
  </defs>
''')

    # Background canvas
    svg.append(f'<rect width="{width}" height="{height}" fill="#080c14" />')
    svg.append(f'<rect width="{width}" height="{height}" fill="url(#grid)" />')
    svg.append(f'<rect width="{width}" height="{height}" fill="url(#dots)" opacity="0.7"/>')

    # =========================================================================
    # 1. TOP HEADER BANNER
    # =========================================================================
    svg.append('''
  <g id="header-banner" transform="translate(60, 40)">
    <!-- Header Background Box -->
    <rect width="2680" height="110" rx="16" fill="#0d1527" stroke="#1e293b" stroke-width="1.5" filter="url(#card-shadow)"/>
    
    <!-- Title & Subtitle -->
    <text x="32" y="48" font-size="34" font-weight="900" fill="url(#grad-title)" letter-spacing="1.2">
      GOAONAUTO — FULL SYSTEM ARCHITECTURE &amp; DATA PIPELINE
    </text>
    <text x="32" y="84" font-size="16" font-weight="500" fill="#94a3b8">
      High-Throughput Citizen Service Automation: GPU Neural Vision, Aadhaar QR Decompression, Raylib GUI Studio &amp; Playwright WebForms Driver
    </text>

    <!-- Stack Badges -->
    <g transform="translate(1620, 36)">
      <!-- Badge 1: Bun / TS -->
      <rect x="0" y="0" width="160" height="38" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="1.2"/>
      <text x="80" y="24" font-size="13" font-weight="700" fill="#38bdf8" text-anchor="middle">⚡ Bun &amp; TypeScript</text>

      <!-- Badge 2: PyTorch CUDA -->
      <rect x="175" y="0" width="180" height="38" rx="8" fill="#1e293b" stroke="#a855f7" stroke-width="1.2"/>
      <text x="265" y="24" font-size="13" font-weight="700" fill="#c084fc" text-anchor="middle">🔥 PyTorch CUDA 12.4</text>

      <!-- Badge 3: Raylib Static 6.0 -->
      <rect x="370" y="0" width="170" height="38" rx="8" fill="#1e293b" stroke="#ec4899" stroke-width="1.2"/>
      <text x="455" y="24" font-size="13" font-weight="700" fill="#f472b6" text-anchor="middle">🎨 Raylib GUI (C/Py)</text>

      <!-- Badge 4: Playwright + Brave -->
      <rect x="555" y="0" width="180" height="38" rx="8" fill="#1e293b" stroke="#f59e0b" stroke-width="1.2"/>
      <text x="645" y="24" font-size="13" font-weight="700" fill="#fbbf24" text-anchor="middle">🦁 Playwright &amp; Brave</text>

      <!-- Badge 5: XeLaTeX Engine -->
      <rect x="750" y="0" width="170" height="38" rx="8" fill="#1e293b" stroke="#10b981" stroke-width="1.2"/>
      <text x="835" y="24" font-size="13" font-weight="700" fill="#34d399" text-anchor="middle">📄 XeLaTeX Compiler</text>

      <!-- Badge 6: EasyOCR -->
      <rect x="935" y="0" width="100" height="38" rx="8" fill="#1e293b" stroke="#64748b" stroke-width="1.2"/>
      <text x="985" y="24" font-size="13" font-weight="700" fill="#94a3b8" text-anchor="middle">EasyOCR</text>
    </g>
  </g>
''')

    # =========================================================================
    # HELPER FUNCTION TO DRAW STANDARDIZED COMPONENT CARDS
    # =========================================================================
    def draw_card(x, y, w, h, title, subtitle, file_path, points, accent_color, tag_text="", tag_color=""):
        res = []
        res.append(f'<g transform="translate({x}, {y})">')
        # Card Background
        res.append(f'  <rect width="{w}" height="{h}" rx="12" fill="#0f172a" stroke="{accent_color}" stroke-width="1.6" filter="url(#card-shadow)"/>')
        # Header strip
        res.append(f'  <path d="M 0 12 Q 0 0 12 0 L {w-12} 0 Q {w} 0 {w} 12 L {w} 38 L 0 38 Z" fill="{accent_color}" fill-opacity="0.12"/>')
        res.append(f'  <line x1="0" y1="38" x2="{w}" y2="38" stroke="{accent_color}" stroke-opacity="0.3" stroke-width="1"/>')
        
        # Title
        res.append(f'  <text x="16" y="25" font-size="15" font-weight="800" fill="#ffffff" letter-spacing="0.3">{escape_xml(title)}</text>')
        if tag_text:
            t_col = tag_color or accent_color
            res.append(f'  <rect x="{w - 110}" y="8" width="96" height="22" rx="6" fill="#1e293b" stroke="{t_col}" stroke-width="1"/>')
            res.append(f'  <text x="{w - 62}" y="23" font-size="10" font-weight="800" fill="{t_col}" text-anchor="middle">{escape_xml(tag_text)}</text>')
        
        # Subtitle & File path
        res.append(f'  <text x="16" y="58" font-size="12" font-weight="600" fill="#94a3b8">{escape_xml(subtitle)}</text>')
        if file_path:
            res.append(f'  <rect x="16" y="68" width="{w - 32}" height="22" rx="4" fill="#090d16" stroke="#334155" stroke-width="0.8"/>')
            res.append(f'  <text x="24" y="83" font-size="10" font-family="monospace" font-weight="600" fill="{accent_color}">{escape_xml(file_path)}</text>')

        # Bullet points
        pt_start_y = 108 if file_path else 85
        for i, pt in enumerate(points):
            cur_y = pt_start_y + (i * 20)
            res.append(f'  <circle cx="22" cy="{cur_y - 4}" r="3" fill="{accent_color}"/>')
            res.append(f'  <text x="32" y="{cur_y}" font-size="11.5" font-weight="450" fill="#cbd5e1">{escape_xml(pt)}</text>')

        res.append('</g>')
        return "\n".join(res)

    # Column Layout Definitions
    # Col 1: Ingress & Orchestration (x: 60, w: 490)
    # Col 2: GPU Vision & Biometrics (x: 590, w: 500)
    # Col 3: Classifier & Dossier (x: 1130, w: 500)
    # Col 4: Raylib Studio & LaTeX (x: 1670, w: 510)
    # Col 5: Portal Automation & Execution (x: 2220, w: 520)

    # =========================================================================
    # COLUMN 1: INGRESS, TRIGGERS & ORCHESTRATION (EMERALD ACCENT #10b981)
    # =========================================================================
    svg.append('''
  <!-- Column 1 Container -->
  <g id="col-ingress">
    <rect x="60" y="180" width="500" height="1420" rx="16" fill="url(#grad-col1)" stroke="#10b981" stroke-width="1.8" stroke-opacity="0.4"/>
    <text x="80" y="215" font-size="20" font-weight="800" fill="#10b981" letter-spacing="0.8">1. INGRESS &amp; ORCHESTRATION</text>
    <text x="80" y="235" font-size="12" font-weight="500" fill="#64748b">Event ingestion, filesystem watchdogs &amp; pipeline dispatch</text>
''')

    # Card 1.1: Context Menu & Explorer Ingress
    svg.append(draw_card(
        x=75, y=255, w=470, h=175,
        title="Windows Shell Integration",
        subtitle="Desktop & Explorer Action Triggers",
        file_path="tools/context-menu/register_unified_context_menu.ps1",
        points=[
            "Direct right-click directory ingestion (6 actions)",
            "Auto-dispatches OCR scan, dossier build & portal autofill",
            "Registers cascading context keys under Windows HKCU registry",
            "Zero command-line barrier for administrative non-technical operators"
        ],
        accent_color="#10b981", tag_text="SHELL HOOK", tag_color="#10b981"
    ))

    # Card 1.2: System Tray Background Service
    svg.append(draw_card(
        x=75, y=450, w=470, h=165,
        title="Background Tray Service",
        subtitle="Headless Daemon Manager & Status Tray",
        file_path="tools/tray/tray_service.py",
        points=[
            "Pystray icon living in Windows notification area",
            "Monitors GPU Worker daemon health & TCP port 50051",
            "One-click daemon startup, graceful shutdown & log inspection",
            "Launches work directory watcher as non-blocking background child"
        ],
        accent_color="#10b981", tag_text="SYSTEM TRAY", tag_color="#10b981"
    ))

    # Card 1.3: Work Directory Watcher & DFS Queue
    svg.append(draw_card(
        x=75, y=635, w=470, h=220,
        title="Work Directory Watcher",
        subtitle="Recursive Chokidar Watchdog & DFS Buffer",
        file_path="src/workDirectoryWatcher.ts",
        points=[
            "Chokidar recursive file watcher on applicant root directories",
            "Dirty-bit buffer & 800ms debounce prevents partial read crashes",
            "DFS recursive folder resolution for nested client scans",
            "Automatic pipeline trigger upon PDF / image batch drop",
            "Maintains task isolation & status telemetry state across folders"
        ],
        accent_color="#10b981", tag_text="EVENT DISPATCH", tag_color="#10b981"
    ))

    # Card 1.4: Master Pipeline Orchestrator
    svg.append(draw_card(
        x=75, y=875, w=470, h=220,
        title="Extract & Declare Orchestrator",
        subtitle="End-to-End Execution Pipeline Coordinator",
        file_path="src/automation/extractAndDeclare.ts",
        points=[
            "Master workflow orchestrator uniting Vision, Classifier & GUI",
            "Executes batch OCR -> Classifier -> Dossier synthesis in order",
            "Detects missing mandatory documents & prompts operator",
            "Conditionally routes to AI Background Remover or Declaration GUI",
            "Passes structured IPC payload to Raylib progress window"
        ],
        accent_color="#10b981", tag_text="COORDINATOR", tag_color="#10b981"
    ))

    # Card 1.5: Desktop GUI IPC Bridges
    svg.append(draw_card(
        x=75, y=1115, w=470, h=245,
        title="Native GUI IPC Bridges",
        subtitle="Subprocess IPC Adapters (TypeScript -> Raylib GUI)",
        file_path="src/gui/progressBridge.ts | confirmationBridge.ts",
        points=[
            "progressBridge.ts: Streams live scan percentages & step state",
            "confirmationBridge.ts: Operator confirmation dialog bridge",
            "ocrTrainerBridge.ts: Launches interactive ground-truth GUI",
            "Non-blocking stdio JSON streaming with automatic teardown",
            "Prevents Node / Bun event loop stalls during heavy graphical UI"
        ],
        accent_color="#10b981", tag_text="STDIO IPC", tag_color="#10b981"
    ))

    # Card 1.6: Developer CLI & Task Palettes
    svg.append(draw_card(
        x=75, y=1380, w=470, h=190,
        title="Developer Task Palette",
        subtitle="High-Speed Bun & TSX Execution Targets",
        file_path="package.json (bun scripts)",
        points=[
            "bun run ocr:scan [dir] -> Standalone batch scanner & renaming",
            "bun run portal:fill [dir] -> Playwright auto-fill runner",
            "bun run data:retrain -> Classifier weight re-tuning",
            "bun run menu:register -> Instant Windows Context Menu installer"
        ],
        accent_color="#10b981", tag_text="CLI RUNNER", tag_color="#10b981"
    ))

    svg.append('  </g>')

    # =========================================================================
    # COLUMN 2: VISION & GPU ACCELERATED INTELLIGENCE (PURPLE ACCENT #a855f7)
    # =========================================================================
    svg.append('''
  <!-- Column 2 Container -->
  <g id="col-gpu-vision">
    <rect x="590" y="180" width="510" height="1420" rx="16" fill="url(#grad-col2)" stroke="#a855f7" stroke-width="1.8" stroke-opacity="0.4"/>
    <text x="610" y="215" font-size="20" font-weight="800" fill="#c084fc" letter-spacing="0.8">2. GPU VISION &amp; AI DAEMON</text>
    <text x="610" y="235" font-size="12" font-weight="500" fill="#64748b">PyTorch CUDA inference, Aadhaar QR unpack &amp; biometrics</text>
''')

    # Card 2.1: GPU Daemon Client (TypeScript)
    svg.append(draw_card(
        x=605, y=255, w=480, h=185,
        title="GPU Daemon Client",
        subtitle="High-Throughput IPC Socket Client",
        file_path="src/scanner/gpuDaemonClient.ts",
        points=[
            "Persistent JSON-RPC socket connection over 127.0.0.1:50051",
            "Batches document image paths for concurrent tensor execution",
            "Sub-50ms roundtrip overhead via persistent socket buffer",
            "Automatic daemon auto-launch fallback if worker daemon is offline"
        ],
        accent_color="#a855f7", tag_text="JSON-RPC TCP", tag_color="#a855f7"
    ))

    # Card 2.2: Python GPU Worker Daemon
    svg.append(draw_card(
        x=605, y=460, w=480, h=220,
        title="Python GPU Worker Daemon",
        subtitle="CUDA Neural Model Host & Server Loop",
        file_path="python/daemons/gpu_worker_daemon.py",
        points=[
            "Preloads PyTorch, EasyOCR & OpenCV models into VRAM once",
            "Eliminates 6-8s Python cold-start latency per document",
            "Multi-threaded request dispatcher handling image batches",
            "NVIDIA RTX 4060 hardware acceleration via CUDA 12.4 FP16",
            "Graceful GPU memory recycling & cache clearing prevents leaks"
        ],
        accent_color="#a855f7", tag_text="PERSISTENT VRAM", tag_color="#a855f7"
    ))

    # Card 2.3: Neural OCR Inference Engine
    svg.append(draw_card(
        x=605, y=700, w=480, h=225,
        title="GPU OCR Inference Engine",
        subtitle="EasyOCR Deep Learning & Tesseract Hybrid",
        file_path="python/ocr/gpu_ocr_engine.py",
        points=[
            "CRAFT Text Detection + ResNet-BiLSTM-CTC Recognition",
            "Batch tensor inference across arbitrary resolutions and rotations",
            "Automatic contrast enhancement, deskewing & unsharp masking",
            "Fallback to Tesseract OCR with PSM-6/11 for dense tabular pages",
            "Returns character bounding boxes, normalized lines & confidences"
        ],
        accent_color="#a855f7", tag_text="CUDA RTX 4060", tag_color="#a855f7"
    ))

    # Card 2.4: Aadhaar QR Decompression Engine
    svg.append(draw_card(
        x=605, y=945, w=480, h=240,
        title="Aadhaar QR Decompression Engine",
        subtitle="Secure V2/V3 Compressed & XML Aadhaar Decoder",
        file_path="python/vision/aadhaar_qr.py",
        points=[
            "Decodes pyzbar raw high-density 2D barcode scan",
            "Extracts binary BigInt byte array from V2/V3 secure QR codes",
            "Decompresses via zlib with header detection & bit-stream parsing",
            "Zero-error extraction: Full Name, DOB, Gender, CareOf, Address",
            "Bypasses noisy optical OCR on Aadhaar cards with 100% precision",
            "Verhoeff 12-digit UID checksum validation"
        ],
        accent_color="#a855f7", tag_text="ZLIB BIT-UNPACK", tag_color="#a855f7"
    ))

    # Card 2.5: Passport Photo & Signature Detectors
    svg.append(draw_card(
        x=605, y=1205, w=480, h=215,
        title="Biometric Feature Detectors",
        subtitle="OpenCV Passport Photo & Signature Extractors",
        file_path="python/vision/photo_detector.py | signature_detector.py",
        points=[
            "Photo: Haar Cascade & DNN face localization with 3.5x4.5cm ratio",
            "Signature: Morphological dilation & connected component labeling",
            "Filters ink stroke density to isolate signatures from document text",
            "Saves cropped transparent alpha signatures ready for LaTeX insertion",
            "Auto-crops passport photo to 350x450px ready for background removal"
        ],
        accent_color="#a855f7", tag_text="CV VISION", tag_color="#a855f7"
    ))

    # Card 2.6: AI Background Remover
    svg.append(draw_card(
        x=605, y=1440, w=480, h=140,
        title="AI Background Removal Service",
        subtitle="Deep Learning Portrait Matting",
        file_path="python/vision/ai_remove_bg.py",
        points=[
            "U2-Net / BiRefNet neural segmentation for portrait photos",
            "Replaces background with compliant pure solid white backdrop",
            "Compresses output under strictly enforced portal limit (50KB JPEG)"
        ],
        accent_color="#a855f7", tag_text="U2-NET", tag_color="#a855f7"
    ))

    svg.append('  </g>')

    # =========================================================================
    # COLUMN 3: CLASSIFIER, SYNTHESIS & DOSSIER CORE (AMBER ACCENT #f59e0b)
    # =========================================================================
    svg.append('''
  <!-- Column 3 Container -->
  <g id="col-classifier">
    <rect x="1130" y="180" width="510" height="1420" rx="16" fill="url(#grad-col3)" stroke="#f59e0b" stroke-width="1.8" stroke-opacity="0.4"/>
    <text x="1150" y="215" font-size="20" font-weight="800" fill="#fbbf24" letter-spacing="0.8">3. CLASSIFICATION &amp; DOSSIER</text>
    <text x="1150" y="235" font-size="12" font-weight="500" fill="#64748b">OCR cleanup, rule-based classification &amp; verified dossier synthesis</text>
''')

    # Card 3.1: OCR Post-Processor
    svg.append(draw_card(
        x=1145, y=255, w=480, h=190,
        title="OCR Post-Processor",
        subtitle="Lexical Normalizer & Confusion Matrix Corrector",
        file_path="src/scanner/ocrPostProcessor.ts",
        points=[
            "Repairs classic OCR optical confusions: O->0, l->1, S->5, B->8",
            "Normalizes Goa-specific terminology: 'TALUKA', 'VILLAGE', 'MAMLATDAR'",
            "Learned dictionary corrections loaded from dataset/spell_corrections.json",
            "Standardizes inconsistent Indian date strings (DD/MM/YYYY, DD-MM-YY)"
        ],
        accent_color="#f59e0b", tag_text="LEXICAL CLEANUP", tag_color="#f59e0b"
    ))

    # Card 3.2: Multi-Class Rule-Based Classifier
    svg.append(draw_card(
        x=1145, y=465, w=480, h=250,
        title="Multi-Class Document Classifier",
        subtitle="Weighted Keyword Scoring & Regex Rules",
        file_path="src/classifier/documentClassifier.ts | rules.ts",
        points=[
            "Classifies 15+ official government document types in Goa",
            "Target Classes: Aadhaar Card, Birth Certificate, Talathi Residence,",
            "  School Leaving / Bonafide, Caste / OBC Certificate, Ration Card,",
            "  Electricity / Water Utility Bills, Marriage Certificate, Passport",
            "Weighted scoring engine balances positive keywords & negative penalties",
            "Automatically renames raw camera files into clean, predictable standards"
        ],
        accent_color="#f59e0b", tag_text="MULTI-CLASS", tag_color="#f59e0b"
    ))

    # Card 3.3: Name Extractor & Entity Parser
    svg.append(draw_card(
        x=1145, y=735, w=480, h=180,
        title="Entity & Name Extractor",
        subtitle="Applicant & Relative Name Deductions",
        file_path="src/classifier/nameExtractor.ts",
        points=[
            "Extracts Applicant Full Name, Father's Name & Spouse Name",
            "Handles Goan naming conventions (Portuguese & Konkani patronymics)",
            "Filters government headers ('GOVERNMENT OF GOA', 'DIRECTORATE')",
            "Resolves divergence when Aadhaar name differs from Birth Certificate"
        ],
        accent_color="#f59e0b", tag_text="NER PARSER", tag_color="#f59e0b"
    ))

    # Card 3.4: Dossier Synthesizer
    svg.append(draw_card(
        x=1145, y=935, w=480, h=260,
        title="Applicant Dossier Synthesizer",
        subtitle="Multi-Source Identity Aggregation Engine",
        file_path="src/classifier/dossierExtractor.ts",
        points=[
            "Unifies Aadhaar QR data, OCR extractions & filename signals",
            "Calculates exact chronological age from DOB string automatically",
            "Deduces years of continuous residence in Goa from school & bills",
            "Verifies Aadhaar 12-digit number via Verhoeff Modulo-10 checksum",
            "Extracts complete residential address: House No, Village, Taluka, Pin",
            "Emits applicant_dossier.json: The Verified Single Source of Truth"
        ],
        accent_color="#f59e0b", tag_text="SYNTHESIZER", tag_color="#f59e0b"
    ))

    # Card 3.5: Master Dossier Data Model
    svg.append(draw_card(
        x=1145, y=1215, w=480, h=365,
        title="Unified Applicant Dossier",
        subtitle="The Single Source of Truth JSON Schema",
        file_path="applicant_dossier.json",
        points=[
            "applicant: { name, dob, age, gender, maritalStatus, mobile, email }",
            "identity: { aadhaarNumber, isVerhoeffValid: true, aadhaarPath }",
            "residence: { houseNo, locality, taluka, village, district, pincode }",
            "stayDuration: { yearsInGoa: 15+, stayFromDate: 'YYYY-MM-DD' }",
            "child: { name, dob, age, relation: 'Son' | 'Daughter' }",
            "assets: { photoPath, sigPath, declarationPdfPath }",
            "classifiedFiles: { birthCertificate, schoolLeaving, talathiReport }",
            "verification: { isVerified: true, extractedAt: 'ISO_TIMESTAMP' }"
        ],
        accent_color="#f59e0b", tag_text="DATA MODEL", tag_color="#f59e0b"
    ))

    svg.append('  </g>')

    # =========================================================================
    # COLUMN 4: RAYLIB DESKTOP GUI SUITE & LATEX (PINK ACCENT #ec4899)
    # =========================================================================
    svg.append('''
  <!-- Column 4 Container -->
  <g id="col-raylib-gui">
    <rect x="1670" y="180" width="520" height="1420" rx="16" fill="url(#grad-col4)" stroke="#ec4899" stroke-width="1.8" stroke-opacity="0.4"/>
    <text x="1690" y="215" font-size="20" font-weight="800" fill="#f472b6" letter-spacing="0.8">4. RAYLIB STUDIO &amp; LATEX PIPELINE</text>
    <text x="1690" y="235" font-size="12" font-weight="500" fill="#64748b">High-DPI native hardware GUI &amp; XeLaTeX legal declaration generation</text>
''')

    # Card 4.1: Raylib Declaration Studio
    svg.append(draw_card(
        x=1685, y=255, w=490, h=250,
        title="Declaration Desktop App",
        subtitle="Hardware-Accelerated Raylib C/Python GUI Studio",
        file_path="python/gui/declaration_app.py",
        points=[
            "60 FPS GPU-rendered immediate mode GUI via Raylib Static 6.0",
            "Dracula Design System: crisp dark mode, high contrast & custom fonts",
            "Dual Layout: Wide Dual-Column OR Narrow Multitasking Tab Mode",
            "Full text editing: cursor positioning, Ctrl+Arrow word jumping, paste",
            "Tab / Shift+Tab keyboard field cycling with auto-scroll tracking",
            "Live dirty-state tracking with automatic TeX re-synthesis"
        ],
        accent_color="#ec4899", tag_text="RAYLIB 6.0", tag_color="#ec4899"
    ))

    # Card 4.2: Interactive Signature Scaler
    svg.append(draw_card(
        x=1685, y=525, w=490, h=190,
        title="Dynamic Signature Scaler",
        subtitle="Real-Time Visual & Dimension Synchronizer",
        file_path="python/gui/core/widgets.py | declarations/base.py",
        points=[
            "Interactive UI Modifier: [-] 100% [+] [↺] (3.2x1.1cm)",
            "Dynamic preview scaling inside Raylib texture card (50% to 240%)",
            "Synchronizes mathematical dimensions into LaTeX generation string",
            "Calculates: width={w_cm}cm, height={h_cm}cm, rule={rule_cm}cm",
            "Eliminates misaligned or oversized signature prints on official forms"
        ],
        accent_color="#ec4899", tag_text="LIVE SCALER", tag_color="#ec4899"
    ))

    # Card 4.3: Polymorphic Declaration Suite
    svg.append(draw_card(
        x=1685, y=735, w=490, h=250,
        title="Modular Declaration Generators",
        subtitle="Extensible OOP Declaration Classes",
        file_path="python/gui/declarations/ (residence, obc, divergence)",
        points=[
            "BaseDeclaration: Abstract base class handling dossier loading & TeX inject",
            "ResidenceDeclaration: Self vs. Child mode with dynamic age math",
            "OBCDeclaration: Caste credentials, sub-caste & income declarations",
            "DivergenceDeclaration: Name difference affidavit & alias binding",
            "Dynamic field mapping: generates inputs based on selected declaration",
            "Auto-saves both form state JSON and updates applicant dossier"
        ],
        accent_color="#ec4899", tag_text="OOP MODULES", tag_color="#ec4899"
    ))

    # Card 4.4: LaTeX XeTeX Compilation Pipeline
    svg.append(draw_card(
        x=1685, y=1005, w=490, h=240,
        title="LaTeX XeTeX Compiler Pipeline",
        subtitle="Publication-Quality Legal PDF Synthesis",
        file_path="templates/latex/ (residence.tex, obc.tex, divergence.tex)",
        points=[
            "Injects applicant photo (1.2x1.5in) & scaled signature image",
            "Escapes LaTeX special characters (&, %, $, #, _) to prevent crashes",
            "Invokes xelatex / pdflatex non-interactively with batchmode",
            "Generates print-ready high-resolution legal declaration PDF",
            "One-click 'Open PDF' in native Windows PDF viewer from GUI footer",
            "Output: residence_declaration.pdf ready for portal upload"
        ],
        accent_color="#ec4899", tag_text="XELATEX PDF", tag_color="#ec4899"
    ))

    # Card 4.5: Auxiliary Native Raylib Tools
    svg.append(draw_card(
        x=1685, y=1265, w=490, h=315,
        title="Auxiliary Raylib Tool Suite",
        subtitle="Specialized Native Graphical Windows",
        file_path="python/gui/ (bg_remover_gui.py, progress_gui.py, ...)",
        points=[
            "bg_remover_gui.py: Interactive pan/zoom crop tool with live rembg preview",
            "progress_gui.py: Floating non-blocking progress bar with step status",
            "confirmation_gui.py: Operator verification modal for high-stakes fields",
            "ocr_trainer_gui.py: OCR word-box visualizer & rating interface",
            "Ultra-lightweight static binaries (PyRay) with zero heavy Electron bloat"
        ],
        accent_color="#ec4899", tag_text="NATIVE TOOLS", tag_color="#ec4899"
    ))

    svg.append('  </g>')

    # =========================================================================
    # COLUMN 5: PORTAL AUTOMATION & EXECUTION (BLUE ACCENT #38bdf8)
    # =========================================================================
    svg.append('''
  <!-- Column 5 Container -->
  <g id="col-portal">
    <rect x="2220" y="180" width="520" height="1420" rx="16" fill="url(#grad-col5)" stroke="#38bdf8" stroke-width="1.8" stroke-opacity="0.4"/>
    <text x="2240" y="215" font-size="20" font-weight="800" fill="#38bdf8" letter-spacing="0.8">5. BROWSER PORTAL AUTOMATION</text>
    <text x="2240" y="235" font-size="12" font-weight="500" fill="#64748b">Playwright Brave automation, ASP.NET postbacks &amp; Screen 1-2 auto-fill</text>
''')

    # Card 5.1: Brave Session Manager
    svg.append(draw_card(
        x=2235, y=255, w=490, h=250,
        title="Brave Portal Session Manager",
        subtitle="Persistent Citizen Session & Browser Context",
        file_path="src/automation/services/portalSessionManager.ts",
        points=[
            "Launches Brave browser with persistent user profile (.brave_automation_profile)",
            "Retains citizen login tokens, cookies & site permissions across runs",
            "Cleans stale SingletonLock files preventing profile-in-use crashes",
            "Enforces chromiumSandbox: true & ignoreDefaultArgs: ['--no-sandbox']",
            "Auto-accepts browser alert/confirm dialogs via context.on('dialog')",
            "Closes orphan about:blank tabs automatically"
        ],
        accent_color="#38bdf8", tag_text="PLAYWRIGHT BRAVE", tag_color="#38bdf8"
    ))

    # Card 5.2: Phase 1 Authentication & Navigation Handshake
    svg.append(draw_card(
        x=2235, y=525, w=490, h=240,
        title="Citizen Auth &amp; Navigation",
        subtitle="Human-in-the-Loop Login & ASP.NET Postback Bridge",
        file_path="src/automation/scripts/phase1_browser_login.ts",
        points=[
            "Detects manual citizen OTP authentication on GoaOnline portal",
            "Phase 1 Breakthrough: Solves ASP.NET WebForms javascript: navigation",
            "Dispatches native page.evaluate() on #cphBody_gvService_lnkProceedApply_0",
            "Invokes window.__doPostBack('ctl00$cphBody$gvService$ctl02$lnkProceedApply')",
            "Strict URL transition polling to verify entry into REV05 service"
        ],
        accent_color="#38bdf8", tag_text="POSTBACK BRIDGE", tag_color="#38bdf8"
    ))

    # Card 5.3: Page Object Model — Residence Screen 1
    svg.append(draw_card(
        x=2235, y=785, w=490, h=300,
        title="Residence Form Automation",
        subtitle="Comprehensive 59-Control DOM Page Object Model",
        file_path="src/automation/pages/residenceFormPage.ts",
        points=[
            "Application Mode: Self (#id6a) vs Relative / Child (#id6b)",
            "Personal Data: Name, DOB, Age, Gender, Marital Status, Mobile, Email",
            "Aadhaar Input with live 12-digit Verhoeff modulo-10 validation",
            "Dynamic AJAX Address Modal: Triggers #btnaddnew, waits for modal",
            "Cascading Selectors: District -> waits AJAX -> Taluka -> Village",
            "Address Save & Confirm: Dispatches #id4f & confirms #id4d dialog",
            "Self-Declaration Checkbox (#id41) & Safe Review Mode preservation"
        ],
        accent_color="#38bdf8", tag_text="POM SCREEN 1", tag_color="#38bdf8"
    ))

    # Card 5.4: Reverse-Engineering & Telemetry Suite
    svg.append(draw_card(
        x=2235, y=1105, w=490, h=220,
        title="DOM Survey & Action Tracker",
        subtitle="WebForms Reverse-Engineering & Blueprint Recorder",
        file_path="tools/surveyScreen1.ts | tools/portalActionTracker.ts",
        points=[
            "surveyScreen1.ts: Live DOM inventory extractor (59 controls indexed)",
            "Generates screen1_survey_latest.md with complete element metadata",
            "portalActionTracker.ts: Visual overlay recording human operator actions",
            "Generates 291-step simulation blueprint mapping every click & keypress",
            "Provides ground truth for bulletproof Playwright locator resilience"
        ],
        accent_color="#38bdf8", tag_text="TELEMETRY", tag_color="#38bdf8"
    ))

    # Card 5.5: Phase 3 Document Attachment & Final Submission
    svg.append(draw_card(
        x=2235, y=1345, w=490, h=235,
        title="Document Upload & Submission",
        subtitle="Phase 3 Attachment Uploader & Review",
        file_path="src/automation/fillResidencePortal.ts (Phase 3)",
        points=[
            "Upload Slot 1: Applicant Passport Photo (< 50KB Solid White BG)",
            "Upload Slot 2: Generated & Signed Residence Declaration PDF",
            "Upload Slot 3: Identity Proof (Classified Aadhaar / Voter Card)",
            "Upload Slot 4: Age Proof (Birth Certificate / School Leaving)",
            "Upload Slot 5: 15-Year Residence Proofs (Electricity / Water / Ration)",
            "Leaves final confirmation window open for human operator review"
        ],
        accent_color="#38bdf8", tag_text="PHASE 3 UPLOAD", tag_color="#38bdf8"
    ))

    svg.append('  </g>')

    # =========================================================================
    # BOTTOM ZONE: FEEDBACK LOOP, OCR TRAINER & DATASET (GOLD ACCENT #eab308)
    # =========================================================================
    svg.append('''
  <!-- Bottom Zone: Continuous Feedback & Training Loop -->
  <g id="bottom-feedback-loop" transform="translate(60, 1630)">
    <rect width="2680" height="380" rx="16" fill="#0c111d" stroke="#eab308" stroke-width="1.8" stroke-opacity="0.5" filter="url(#card-shadow)"/>
    
    <!-- Zone Header -->
    <path d="M 0 16 Q 0 0 16 0 L 2664 0 Q 2680 0 2680 16 L 2680 44 L 0 44 Z" fill="#eab308" fill-opacity="0.12"/>
    <line x1="0" y1="44" x2="2680" y2="44" stroke="#eab308" stroke-opacity="0.3" stroke-width="1"/>
    <text x="24" y="28" font-size="18" font-weight="800" fill="#facc15" letter-spacing="0.8">
      6. CONTINUOUS LEARNING, RETRAINING &amp; GROUND-TRUTH FEEDBACK LOOP
    </text>
    <text x="760" y="28" font-size="13" font-weight="500" fill="#94a3b8">
      Human-in-the-loop review, automated spell-correction training, dynamic keyword weight re-tuning &amp; regression prevention
    </text>
''')

    # Card B.1: Interactive OCR Trainer
    svg.append(draw_card(
        x=20, y=60, w=630, h=290,
        title="Interactive OCR Trainer & Rater",
        subtitle="Human-in-the-Loop Text Correction & Rating Studio",
        file_path="tools/runOcrTrainer.ts | python/gui/ocr_trainer_gui.py",
        points=[
            "Scans applicant document and displays bounding boxes with recognized text",
            "Operator reviews extracted tokens, corrects OCR mistakes & enters ground truth",
            "Rate extraction quality (1 to 5 stars) per document field",
            "Automatically generates spell correction pairs into dataset/spell_corrections.json",
            "Progressively improves OCR accuracy without expensive model re-training"
        ],
        accent_color="#eab308", tag_text="OCR TRAINER", tag_color="#eab308"
    ))

    # Card B.2: Classifier Retrainer
    svg.append(draw_card(
        x=680, y=60, w=630, h=290,
        title="Classifier Weight Retrainer",
        subtitle="Automated Keyword Scoring Optimization Engine",
        file_path="tools/retrain_classifier.ts | dataset/rules_learned.json",
        points=[
            "Analyzes labeled document corpus in dataset/training_samples/",
            "Computes TF-IDF frequencies & keyword discrimination scores across 15 categories",
            "Adjusts positive weights and negative penalty rules automatically",
            "Eliminates misclassification edge cases (e.g. distinguishing Birth vs Death certs)",
            "Generates optimized rules directly deployed to src/classifier/rules.ts"
        ],
        accent_color="#eab308", tag_text="TF-IDF RETRAIN", tag_color="#eab308"
    ))

    # Card B.3: Dataset Evaluator & Regression Benchmarks
    svg.append(draw_card(
        x=1340, y=60, w=630, h=290,
        title="Dataset Evaluator & Benchmarks",
        subtitle="Continuous Regression Testing & GPU Profiler",
        file_path="tests/datasetEvaluator.ts | tests/gpuBatchBenchmark.ts",
        points=[
            "Automated test harness executing across 100+ multi-page test fixtures",
            "Calculates precision, recall & F1-score across all 15 certificate categories",
            "gpuBatchBenchmark.ts: Measures batch tensor throughput vs single-image latency",
            "Validates Verhoeff checksum pass rate and age calculation edge cases",
            "Strict CI threshold prevents accuracy regression before portal deployment"
        ],
        accent_color="#eab308", tag_text="BENCHMARKS", tag_color="#eab308"
    ))

    # Card B.4: Persistent Knowledge & Dataset Store
    svg.append(draw_card(
        x=2000, y=60, w=660, h=290,
        title="Ground-Truth Dataset Store",
        subtitle="Curated Golden Records & Dictionaries",
        file_path="dataset/ (dataset_manifest.json, spell_corrections.json, ...)",
        points=[
            "dataset_manifest.json: Ground-truth labeled documents with verified text",
            "spell_corrections.json: Dictionary of Goan administrative term corrections",
            "rules_learned.json: Calibrated keyword weights and confidence thresholds",
            "applicant_dossier.json: Standardized schema templates for all certificate types",
            "Guarantees deterministic, reproducible extraction across diverse scanner hardware"
        ],
        accent_color="#eab308", tag_text="GROUND TRUTH", tag_color="#eab308"
    ))

    svg.append('  </g>')

    # =========================================================================
    # PIPELINES & DATA FLOW CONNECTORS (GLOWING BEZIER CURVES & LABELS)
    # =========================================================================
    svg.append('''
  <!-- Visual Connectors & Data Pipelines -->
  <g id="pipeline-connectors">
    <!-- 1. Ingress -> GPU Daemon Client -->
    <path d="M 545 985 C 570 985, 580 345, 605 345" fill="none" stroke="#10b981" stroke-width="2.8" marker-end="url(#arrow-emerald)"/>
    <rect x="555" y="650" width="85" height="22" rx="4" fill="#090d16" stroke="#10b981" stroke-width="1"/>
    <text x="597" y="665" font-size="10" font-weight="700" fill="#10b981" text-anchor="middle">Image Paths</text>

    <!-- 2. GPU Daemon Client -> GPU Worker Daemon (JSON-RPC) -->
    <path d="M 845 440 L 845 460" fill="none" stroke="#a855f7" stroke-width="3" marker-end="url(#arrow-purple)"/>
    <rect x="800" y="442" width="90" height="18" rx="4" fill="#1e102e" stroke="#a855f7" stroke-width="1"/>
    <text x="845" y="455" font-size="9" font-weight="800" fill="#c084fc" text-anchor="middle">TCP 50051</text>

    <!-- 3. GPU Worker Daemon -> OCR Engine & QR Unpack -->
    <path d="M 845 680 L 845 700" fill="none" stroke="#a855f7" stroke-width="3" marker-end="url(#arrow-purple)"/>
    <path d="M 845 925 L 845 945" fill="none" stroke="#a855f7" stroke-width="3" marker-end="url(#arrow-purple)"/>

    <!-- 4. GPU Vision -> OCR Post-Processor (Column 2 to Column 3) -->
    <path d="M 1085 810 C 1110 810, 1120 350, 1145 350" fill="none" stroke="#f59e0b" stroke-width="2.8" marker-end="url(#arrow-amber)"/>
    <rect x="1090" y="565" width="85" height="22" rx="4" fill="#1c1917" stroke="#f59e0b" stroke-width="1"/>
    <text x="1132" y="580" font-size="10" font-weight="700" fill="#fbbf24" text-anchor="middle">Raw OCR Text</text>

    <!-- 5. QR Engine -> Dossier Synthesizer (Direct High-Precision Path) -->
    <path d="M 1085 1065 L 1145 1065" fill="none" stroke="#a855f7" stroke-width="3.2" stroke-dasharray="6,4" marker-end="url(#arrow-purple)"/>
    <rect x="1088" y="1035" width="88" height="22" rx="4" fill="#1e102e" stroke="#a855f7" stroke-width="1"/>
    <text x="1132" y="1050" font-size="10" font-weight="800" fill="#c084fc" text-anchor="middle">100% Aadhaar QR</text>

    <!-- 6. PostProcessor -> Classifier -> Entity Parser -> Dossier -->
    <path d="M 1385 445 L 1385 465" fill="none" stroke="#f59e0b" stroke-width="2.8" marker-end="url(#arrow-amber)"/>
    <path d="M 1385 715 L 1385 735" fill="none" stroke="#f59e0b" stroke-width="2.8" marker-end="url(#arrow-amber)"/>
    <path d="M 1385 915 L 1385 935" fill="none" stroke="#f59e0b" stroke-width="2.8" marker-end="url(#arrow-amber)"/>
    <path d="M 1385 1195 L 1385 1215" fill="none" stroke="#f59e0b" stroke-width="2.8" marker-end="url(#arrow-amber)"/>

    <!-- 7. Unified Dossier -> Raylib Declaration Studio (Column 3 to Column 4) -->
    <path d="M 1625 1395 C 1650 1395, 1660 380, 1685 380" fill="none" stroke="#ec4899" stroke-width="3" marker-end="url(#arrow-pink)"/>
    <rect x="1632" y="870" width="105" height="24" rx="4" fill="#240c1d" stroke="#ec4899" stroke-width="1"/>
    <text x="1684" y="886" font-size="10" font-weight="800" fill="#f472b6" text-anchor="middle">Dossier JSON</text>

    <!-- 8. Raylib Studio -> LaTeX XeTeX Compiler -->
    <path d="M 1930 505 L 1930 525" fill="none" stroke="#ec4899" stroke-width="2.8" marker-end="url(#arrow-pink)"/>
    <path d="M 1930 715 L 1930 735" fill="none" stroke="#ec4899" stroke-width="2.8" marker-end="url(#arrow-pink)"/>
    <path d="M 1930 985 L 1930 1005" fill="none" stroke="#ec4899" stroke-width="2.8" marker-end="url(#arrow-pink)"/>

    <!-- 9. Dossier & Generated PDF -> Browser Portal Automation (Col 3/4 to Col 5) -->
    <path d="M 2175 1125 C 2200 1125, 2210 935, 2235 935" fill="none" stroke="#38bdf8" stroke-width="3.2" marker-end="url(#arrow-blue)"/>
    <rect x="2180" y="1015" width="115" height="24" rx="4" fill="#0c1e33" stroke="#38bdf8" stroke-width="1"/>
    <text x="2237" y="1031" font-size="10" font-weight="800" fill="#38bdf8" text-anchor="middle">Dossier + Signed PDF</text>

    <!-- 10. Playwright Browser -> Portal Action Tracker Telemetry -->
    <path d="M 2480 1085 L 2480 1105" fill="none" stroke="#38bdf8" stroke-width="2.8" marker-end="url(#arrow-blue)"/>

    <!-- 11. Feedback Loop: Telemetry & OCR Trainer Back to Dataset (Bottom Return Path) -->
    <path d="M 1385 1580 L 1385 1630" fill="none" stroke="#eab308" stroke-width="2.8" stroke-dasharray="6,4" marker-end="url(#arrow-amber)"/>
  </g>
''')

    # Close SVG
    svg.append('</svg>')
    return "\n".join(svg)

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "architecture")
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.abspath(os.path.join(target_dir, "goaonauto_architecture.svg"))

    svg_content = build_architecture_svg()
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"✅ Architecture SVG successfully generated at:\n   {target_file}")
    print(f"   Size: {len(svg_content):,} bytes")

if __name__ == "__main__":
    main()
