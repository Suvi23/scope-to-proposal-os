"""
ui/styles.py

Clean, professional pastel design system for Scope-to-Proposal AI OS.

Principles
----------
- Sober, restrained, business-appropriate
- Muted pastel accents (dusty blue, sage, sand, rose)
- Full-width layout, natural scrolling
- Simple horizontal stepper
- Minimal centered modals
"""


def inject_css() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        /* ============================================================
           FONT
           ============================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* ============================================================
           DESIGN TOKENS
           ============================================================ */
        :root {
            --bg:            #f6f7fa;
            --surface:       #ffffff;
            --surface-alt:   #fbfcfd;

            --border:        #e5e8ee;
            --border-strong: #d3d8e2;

            --ink-900: #1e2532;
            --ink-700: #3f4757;
            --ink-500: #6b7383;
            --ink-400: #8d95a5;
            --ink-300: #aab1be;

            --accent:        #6b7db3;
            --accent-hover:  #5c6da1;
            --accent-tint:   #eef1f8;
            --accent-border: #ccd5e9;

            --sage:          #7fa88a;
            --sage-tint:     #eff5f1;
            --sage-border:   #cfe0d5;
            --sage-ink:      #416b50;

            --sand:          #c9a15f;
            --sand-tint:     #faf5ea;
            --sand-border:   #ecdcbe;
            --sand-ink:      #8a6520;

            --rose:          #c08494;
            --rose-tint:     #f9f0f2;
            --rose-border:   #ecd3d9;
            --rose-ink:      #8f4356;

            --sky:           #7d9bbd;
            --sky-tint:      #eff4f9;
            --sky-border:    #d2e0ed;
            --sky-ink:       #3d6285;

            --sh-xs: 0 1px 2px rgba(30, 37, 50, 0.05);
            --sh-sm: 0 1px 3px rgba(30, 37, 50, 0.07), 0 1px 2px rgba(30, 37, 50, 0.04);
            --sh-md: 0 4px 10px rgba(30, 37, 50, 0.07), 0 1px 3px rgba(30, 37, 50, 0.05);
            --sh-lg: 0 12px 32px rgba(30, 37, 50, 0.13), 0 4px 10px rgba(30, 37, 50, 0.06);

            --r-xs: 6px;
            --r-sm: 8px;
            --r-md: 10px;
            --r-lg: 14px;
            --r-pill: 100px;

            --tr: 0.16s ease;
        }

        /* ============================================================
           HIDE STREAMLIT CHROME
           (removes the hover-shifting "Running" indicator)
           ============================================================ */
        #MainMenu,
        footer,
        [data-testid="stStatusWidget"],
        [data-testid="stToolbar"],
        [data-testid="stToolbarActions"],
        [data-testid="stDecoration"],
        .stDeployButton,
        .stAppDeployButton {
            display: none !important;
            visibility: hidden !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            pointer-events: none !important;
        }

        section[data-testid="stSidebar"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
        }

        /* ============================================================
           LAYOUT — FULL WIDTH, NORMAL SCROLLING
           ============================================================ */
        .stApp {
            background: var(--bg) !important;
        }

        [data-testid="stAppViewContainer"] {
            margin-left: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        [data-testid="stAppViewContainer"] > .main,
        .main {
            margin-left: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        .main .block-container,
        .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding-top: 1.5rem !important;
            padding-bottom: 5rem !important;
            padding-left: 2.75rem !important;
            padding-right: 2.75rem !important;
        }

        /* Ensure position:fixed works for modals */
        [data-testid="stAppViewContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stHorizontalBlock"],
        [data-testid="element-container"],
        .main,
        .block-container,
        .stMarkdown {
            transform: none !important;
            filter: none !important;
            perspective: none !important;
            will-change: auto !important;
        }

        /* ============================================================
           TYPOGRAPHY
           ============================================================ */
        .stApp h1 {
            color: var(--ink-900) !important;
            font-weight: 700 !important;
            font-size: 1.75rem !important;
            letter-spacing: -0.024em !important;
            margin-bottom: 0.3rem !important;
            line-height: 1.25 !important;
        }

        .stApp h2 {
            color: var(--ink-900) !important;
            font-weight: 600 !important;
            font-size: 1.25rem !important;
            letter-spacing: -0.016em !important;
        }

        .stApp h3 {
            color: var(--ink-900) !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            letter-spacing: -0.008em !important;
            margin-top: 1.9rem !important;
            margin-bottom: 0.7rem !important;
            padding-bottom: 0.45rem !important;
            border-bottom: 1px solid var(--border) !important;
        }

        .stApp p, .stApp li, .stApp .stMarkdown {
            color: var(--ink-700) !important;
            line-height: 1.66 !important;
            font-size: 0.9rem !important;
        }

        code {
            background: var(--accent-tint) !important;
            color: var(--accent-hover) !important;
            padding: 1px 6px !important;
            border-radius: 4px !important;
            font-size: 0.82em !important;
            font-weight: 500 !important;
        }

        /* ============================================================
           HEADER BAR
           ============================================================ */
        .appbar {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 22px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--r-md);
            box-shadow: var(--sh-xs);
            margin-bottom: 14px;
            flex-wrap: wrap;
        }

        .appbar .ab-mark {
            width: 34px;
            height: 34px;
            border-radius: var(--r-sm);
            background: var(--accent);
            color: #fff;
            display: grid;
            place-items: center;
            font-size: 15px;
            font-weight: 700;
            flex-shrink: 0;
            letter-spacing: -0.03em;
        }

        .appbar .ab-name {
            font-size: 0.94rem;
            font-weight: 650;
            color: var(--ink-900);
            letter-spacing: -0.015em;
            line-height: 1.25;
        }

        .appbar .ab-tag {
            font-size: 0.66rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-400);
            margin-top: 1px;
        }

        .appbar .ab-gap { flex: 1 1 auto; min-width: 6px; }

        .appbar .ab-stage {
            padding: 6px 14px;
            border-radius: var(--r-pill);
            background: var(--accent-tint);
            border: 1px solid var(--accent-border);
            color: var(--accent-hover);
            font-size: 0.72rem;
            font-weight: 600;
            white-space: nowrap;
        }

        /* ============================================================
           STEPPER
           ============================================================ */
        .stepper-wrap {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--r-md);
            box-shadow: var(--sh-xs);
            padding: 20px 22px 14px 22px;
            margin-bottom: 26px;
            overflow-x: auto;
        }

        .stepper {
            display: flex;
            align-items: flex-start;
            width: 100%;
            min-width: 720px;
        }

        .stp {
            flex: 1 1 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            text-align: center;
            padding: 0 3px;
        }

        .stp::before {
            content: "";
            position: absolute;
            top: 15px;
            left: -50%;
            width: 100%;
            height: 2px;
            background: var(--border-strong);
            z-index: 0;
        }

        .stp:first-child::before { display: none; }

        .stp.done::before { background: var(--sage); }
        .stp.now::before  { background: var(--sage); }

        .stp .dot {
            position: relative;
            z-index: 1;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            font-size: 12px;
            font-weight: 700;
            background: var(--surface);
            border: 2px solid var(--border-strong);
            color: var(--ink-300);
            transition: var(--tr);
        }

        .stp .lbl {
            margin-top: 9px;
            font-size: 0.7rem;
            font-weight: 500;
            color: var(--ink-400);
            line-height: 1.3;
            max-width: 100px;
        }

        .stp .num {
            display: block;
            font-size: 0.58rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            color: var(--ink-300);
            margin-bottom: 1px;
        }

        .stp.done .dot {
            background: var(--sage);
            border-color: var(--sage);
            color: #fff;
        }
        .stp.done .lbl { color: var(--sage-ink); font-weight: 600; }
        .stp.done .num { color: var(--sage); }

        .stp.now .dot {
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
            box-shadow: 0 0 0 4px var(--accent-tint);
        }
        .stp.now .lbl { color: var(--accent-hover); font-weight: 650; }
        .stp.now .num { color: var(--accent); }

        .stp.lock .dot { opacity: 0.45; }
        .stp.lock .lbl { opacity: 0.45; }

        /* ============================================================
           CARDS
           ============================================================ */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--r-md) !important;
            box-shadow: var(--sh-xs) !important;
            padding: 6px 4px !important;
            margin-bottom: 12px !important;
            transition: var(--tr) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: var(--border-strong) !important;
            box-shadow: var(--sh-sm) !important;
        }

        /* ============================================================
           BUTTONS
           ============================================================ */
        .stButton > button {
            border-radius: var(--r-sm) !important;
            font-weight: 550 !important;
            font-size: 0.875rem !important;
            padding: 10px 20px !important;
            transition: var(--tr) !important;
            letter-spacing: -0.005em !important;
            box-shadow: none !important;
        }

        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
            background: var(--accent) !important;
            color: #ffffff !important;
            border: 1px solid var(--accent) !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {
            background: var(--accent-hover) !important;
            border-color: var(--accent-hover) !important;
        }

        .stButton > button[kind="primary"]:disabled {
            background: #e8ebf1 !important;
            border-color: #e8ebf1 !important;
            color: var(--ink-300) !important;
        }

        .stButton > button[kind="secondary"] {
            background: var(--surface) !important;
            color: var(--ink-500) !important;
            border: 1px solid var(--border-strong) !important;
        }

        .stButton > button[kind="secondary"]:hover {
            background: var(--surface-alt) !important;
            color: var(--ink-900) !important;
            border-color: var(--accent-border) !important;
        }

        /* ============================================================
           FORMS
           ============================================================ */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            background: var(--surface) !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: var(--r-sm) !important;
            color: var(--ink-900) !important;
            font-size: 0.9rem !important;
            padding: 10px 13px !important;
            transition: var(--tr) !important;
            box-shadow: none !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px var(--accent-tint) !important;
        }

        .stTextInput > div > div,
        .stTextArea > div > div {
            background: transparent !important;
            border: none !important;
        }

        .stSelectbox > div > div {
            background: var(--surface) !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: var(--r-sm) !important;
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label {
            color: var(--ink-500) !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
        }

        /* ============================================================
           ALERTS
           ============================================================ */
        div[data-testid="stAlert"] {
            border-radius: var(--r-sm) !important;
            border: 1px solid var(--border) !important;
            font-size: 0.875rem !important;
            padding: 12px 16px !important;
            box-shadow: none !important;
        }

        div[data-testid="stAlert"] p {
            font-size: 0.875rem !important;
            margin-bottom: 0 !important;
        }

        /* ============================================================
           METRIC
           ============================================================ */
        [data-testid="stMetric"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--r-md) !important;
            padding: 16px 20px !important;
            box-shadow: var(--sh-xs) !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--ink-900) !important;
            font-weight: 700 !important;
            font-size: 1.6rem !important;
            letter-spacing: -0.02em !important;
        }

        [data-testid="stMetricLabel"] {
            color: var(--ink-400) !important;
            font-size: 0.68rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.09em !important;
        }

        /* ============================================================
           DIVIDER / CAPTION / CHECKBOX / EXPANDER
           ============================================================ */
        hr {
            border: none !important;
            border-top: 1px solid var(--border) !important;
            margin: 26px 0 !important;
        }

        .stCaption, [data-testid="stCaptionContainer"], small {
            color: var(--ink-400) !important;
            font-size: 0.76rem !important;
            line-height: 1.5 !important;
        }

        .stCheckbox label span {
            color: var(--ink-500) !important;
            font-size: 0.83rem !important;
        }

        [data-testid="stExpander"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--r-md) !important;
            box-shadow: none !important;
        }

        [data-testid="stExpander"] summary {
            font-size: 0.83rem !important;
            font-weight: 600 !important;
            color: var(--ink-500) !important;
        }

        /* ============================================================
           DOWNLOAD BUTTON
           ============================================================ */
        [data-testid="stDownloadButton"] > button {
            background: var(--sage) !important;
            color: #ffffff !important;
            border: 1px solid var(--sage) !important;
            border-radius: var(--r-sm) !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 13px 24px !important;
            box-shadow: none !important;
            transition: var(--tr) !important;
        }

        [data-testid="stDownloadButton"] > button:hover {
            background: var(--sage-ink) !important;
            border-color: var(--sage-ink) !important;
        }

        /* ============================================================
           MODAL — CENTERED, SCROLL-SAFE
           ============================================================ */
        .ov {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 24px !important;
            box-sizing: border-box !important;
            background: rgba(30, 37, 50, 0.34) !important;
            -webkit-backdrop-filter: blur(3px);
            backdrop-filter: blur(3px);
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            z-index: 2147483000 !important;
            animation: ovIn 0.18s ease both;
        }

        /* Success overlay never blocks clicks or scrolling */
        .ov.soft {
            pointer-events: none !important;
            background: rgba(30, 37, 50, 0.26) !important;
            animation: ovIn 0.18s ease both, ovOut 2.4s ease forwards;
        }

        @keyframes ovIn {
            from { opacity: 0; }
            to   { opacity: 1; }
        }

        @keyframes ovOut {
            0%, 80% { opacity: 1; visibility: visible; }
            100%    { opacity: 0; visibility: hidden; }
        }

        .mdl {
            width: 100%;
            max-width: 380px;
            max-height: calc(100vh - 48px);
            overflow-y: auto;
            box-sizing: border-box;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--r-lg);
            padding: 32px 30px 28px 30px;
            text-align: center;
            box-shadow: var(--sh-lg);
            animation: mdlIn 0.22s cubic-bezier(0.2, 0, 0.2, 1) both;
        }

        @keyframes mdlIn {
            from { opacity: 0; transform: translateY(10px) scale(0.98); }
            to   { opacity: 1; transform: translateY(0)    scale(1);    }
        }

        .mdl .m-title {
            font-size: 1.04rem;
            font-weight: 650;
            color: var(--ink-900);
            letter-spacing: -0.018em;
            margin: 18px 0 7px 0;
            line-height: 1.35;
        }

        .mdl .m-sub {
            font-size: 0.83rem;
            color: var(--ink-500);
            line-height: 1.6;
            margin: 0;
        }

        .mdl .m-tag {
            display: inline-block;
            margin-top: 18px;
            padding: 5px 13px;
            border-radius: var(--r-pill);
            background: var(--accent-tint);
            border: 1px solid var(--accent-border);
            color: var(--accent-hover);
            font-size: 0.66rem;
            font-weight: 650;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        /* Spinner */
        .m-spin {
            width: 40px;
            height: 40px;
            margin: 0 auto;
            border-radius: 50%;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            animation: spin 0.75s linear infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .m-bar {
            width: 100%;
            height: 3px;
            margin-top: 20px;
            border-radius: 3px;
            background: var(--border);
            overflow: hidden;
        }

        .m-bar i {
            display: block;
            width: 38%;
            height: 100%;
            border-radius: 3px;
            background: var(--accent);
            animation: slide 1.35s ease-in-out infinite;
        }

        @keyframes slide {
            0%   { transform: translateX(-100%); }
            100% { transform: translateX(310%);  }
        }

        /* Check */
        .m-check {
            width: 46px;
            height: 46px;
            margin: 0 auto;
            border-radius: 50%;
            background: var(--sage-tint);
            border: 2px solid var(--sage);
            display: grid;
            place-items: center;
            animation: pop 0.32s cubic-bezier(0.2, 1.3, 0.4, 1) both;
        }

        @keyframes pop {
            0%   { transform: scale(0.5); opacity: 0; }
            100% { transform: scale(1);   opacity: 1; }
        }

        .m-check::after {
            content: "\\2713";
            color: var(--sage-ink);
            font-size: 22px;
            font-weight: 700;
            line-height: 1;
        }

        /* ============================================================
           PILLS / BADGES / NOTICES
           ============================================================ */
        .pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: var(--r-pill);
            background: var(--accent-tint);
            border: 1px solid var(--accent-border);
            color: var(--accent-hover);
            font-size: 0.66rem;
            font-weight: 650;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 13px;
            border-radius: var(--r-pill);
            background: var(--sage-tint);
            border: 1px solid var(--sage-border);
            color: var(--sage-ink);
            font-size: 0.72rem;
            font-weight: 600;
        }

        .note {
            border-radius: var(--r-sm);
            padding: 13px 17px;
            font-size: 0.86rem;
            line-height: 1.6;
            margin-bottom: 12px;
            border: 1px solid;
        }
        .note strong { font-weight: 650; }

        .note.ok   { background: var(--sage-tint); border-color: var(--sage-border); color: var(--sage-ink); }
        .note.warn { background: var(--sand-tint); border-color: var(--sand-border); color: var(--sand-ink); }
        .note.err  { background: var(--rose-tint); border-color: var(--rose-border); color: var(--rose-ink); }
        .note.info { background: var(--sky-tint);  border-color: var(--sky-border);  color: var(--sky-ink);  }

        .hero {
            background: var(--sage-tint);
            border: 1px solid var(--sage-border);
            border-radius: var(--r-lg);
            padding: 26px 24px;
            text-align: center;
            margin-bottom: 20px;
        }
        .hero .h-ic  { font-size: 30px; line-height: 1; margin-bottom: 8px; }
        .hero .h-tt  { font-size: 1.06rem; font-weight: 650; color: var(--sage-ink);
                       letter-spacing: -0.018em; margin-bottom: 4px; }
        .hero .h-sb  { font-size: 0.85rem; color: #5b7f68; }

        /* ============================================================
           SCROLLBAR
           ============================================================ */
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: #ccd2dd;
            border-radius: 8px;
            border: 3px solid var(--bg);
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--ink-300); }

        /* ============================================================
           RESPONSIVE
           ============================================================ */
        @media (max-width: 1100px) {
            .main .block-container, .block-container {
                padding-left: 1.75rem !important;
                padding-right: 1.75rem !important;
            }
        }

        @media (max-width: 820px) {
            .main .block-container, .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .stApp h1 { font-size: 1.5rem !important; }
            .stepper { min-width: 660px; }
            .stp .lbl { font-size: 0.64rem; max-width: 76px; }
            .stp .dot { width: 26px; height: 26px; font-size: 11px; }
            .stp::before { top: 13px; }
        }

        @media (max-width: 560px) {
            .appbar { padding: 12px 15px; }
            .appbar .ab-stage { font-size: 0.66rem; padding: 5px 11px; }
            .stepper-wrap { padding: 15px 12px 10px 12px; }
            .stepper { min-width: 600px; }
            .mdl { padding: 26px 22px 24px 22px; max-width: 320px; }
            .mdl .m-title { font-size: 0.96rem; }
            .stApp h1 { font-size: 1.32rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )