from info import BIN_CHANNEL, URL
from utils import temp
from web.utils.custom_dl import TGCustomYield
import urllib.parse
import html
import re


webapp_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Filmotainment</title>
    <meta name="description" content="Browse trending movies and TV shows. Find and download files instantly.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg: #0a0a0f;
            --bg2: #111118;
            --card: #16161f;
            --card2: #1e1e2a;
            --border: rgba(255,255,255,0.07);
            --accent: #e50914;
            --accent2: #ff0f1b;
            --gold: #f5c518;
            --text: #ffffff;
            --text2: #b0b0c0;
            --text3: #666680;
            --glass: rgba(10,10,20,0.85);
            --radius: 12px;
            --radius-sm: 8px;
        }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        html { scroll-behavior: smooth; }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* ── NAVBAR ── */
        .navbar {
            position: fixed; top: 0; left: 0; right: 0; z-index: 100;
            display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 12px;
            padding: env(safe-area-inset-top, 0px) 14px 0; height: calc(64px + env(safe-area-inset-top, 0px));
            background: linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, transparent 100%);
            transition: background 0.3s;
        }
        .navbar.solid { background: var(--bg); border-bottom: 1px solid var(--border); }
        .nav-logo {
            font-size: 18px; font-weight: 900; letter-spacing: -0.3px;
            background: linear-gradient(135deg, #fff 0%, var(--accent) 60%, var(--accent2) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            white-space: nowrap;
        }
        .nav-right { display: flex; align-items: center; gap: 6px; }
        .nav-search-pill {
            min-width: 0; width: 100%; height: 40px; border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.08);
            color: var(--text2); display: flex; align-items: center; gap: 10px;
            padding: 0 12px; font-family: 'Outfit', sans-serif; font-size: 13px; font-weight: 600;
            cursor: pointer; transition: background 0.2s, border-color 0.2s, color 0.2s;
        }
        .nav-search-pill:hover { background: var(--card2); border-color: rgba(229,9,20,0.35); color: #fff; }
        .nav-search-pill svg { flex: 0 0 auto; color: var(--text3); }
        .nav-search-pill span {
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .nav-search-toggle {
            background: none; border: none; color: var(--text2); cursor: pointer;
            width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;
            border-radius: 50%; transition: background 0.2s, color 0.2s;
        }
        .nav-search-toggle:hover { background: var(--card2); color: #fff; }

        /* ── SEARCH OVERLAY ── */
        .search-overlay {
            position: fixed; inset: 0; z-index: 200;
            background: rgba(10,10,15,0.95); backdrop-filter: blur(32px);
            display: flex; flex-direction: column;
            opacity: 0; visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
            padding: 0;
        }
        .search-overlay.open { opacity: 1; visibility: visible; }
        /* Top bar: search input + cancel button side-by-side */
        .search-top-bar {
            display: flex; align-items: center; gap: 10px;
            /* Use safe-area fallback; in Telegram add extra top space */
            padding: calc(58px + env(safe-area-inset-top, 0px)) 16px 12px;
            flex-shrink: 0;
        }
        .search-field-wrap {
            display: flex; align-items: center; gap: 12px;
            background: var(--card2); border-radius: var(--radius);
            border: 1px solid var(--border); padding: 0 16px;
            flex: 1; min-width: 0;
            transition: border-color 0.25s, box-shadow 0.25s;
        }
        .search-field-wrap:focus-within {
            border-color: rgba(229, 9, 20, 0.4);
            box-shadow: 0 0 14px rgba(229, 9, 20, 0.25);
        }
        .search-field-wrap svg { color: var(--text3); flex-shrink: 0; }
        .search-field {
            flex: 1; background: none; border: none; outline: none;
            color: #fff; font-family: 'Outfit', sans-serif; font-size: 18px;
            padding: 17px 0; min-width: 0;
        }
        .search-field::placeholder { color: var(--text3); }
        .search-close {
            background: none; border: none; color: var(--accent); cursor: pointer;
            font-size: 15px; font-weight: 700; white-space: nowrap;
            padding: 8px 4px; flex-shrink: 0;
            transition: opacity 0.2s, transform 0.15s;
        }
        .search-close:hover { opacity: 0.8; }
        .search-close:active { transform: scale(0.96); }
        .search-suggestion {
            grid-column: 1 / -1; color: var(--text2); font-size: 13px;
            background: rgba(255,255,255,0.04); border: 1px solid var(--border);
            border-radius: var(--radius-sm); padding: 10px 12px; line-height: 1.4;
        }
        .search-suggestion b { color: #fff; }

        /* Search meta bar */
        .search-meta-bar {
            padding: 0 16px 12px; flex-shrink: 0;
            font-size: 12px; color: var(--text3); letter-spacing: 0.2px;
        }
        .search-meta-bar b { color: var(--text2); }

        /* Premium search results grid (3 columns on mobile) */
        .search-results-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px; overflow-y: auto; flex: 1;
            padding: 0 16px 60px; align-content: start;
        }

        /* Override poster card styles when inside search grid to make them fluid */
        .search-results-grid .poster-card {
            width: 100%;
            margin: 0 !important; /* Reset horizontal scroll margin spacing */
        }
        .search-results-grid .poster-img-wrap {
            width: 100%;
            height: 0;
            padding-bottom: 150%; /* Strict 2:3 portrait aspect ratio */
            position: relative;
            border-radius: var(--radius-sm);
            overflow: hidden;
        }
        .search-results-grid .poster-img-wrap img,
        .search-results-grid .poster-img-wrap .poster-placeholder {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .search-hint {
            text-align: center; color: var(--text3); font-size: 14px;
            padding: 60px 20px; grid-column: 1 / -1;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
        }
        .search-hint svg { display: block; margin: 0 auto 16px; opacity: 0.25; }

        /* ── HERO ── */
        .hero {
            position: relative; width: 100%;
            /* tall enough to show behind navbar + full content */
            height: calc(75vw + 60px); max-height: 560px; min-height: 400px;
            overflow: hidden; margin-top: 0;
        }
        .hero-bg {
            position: absolute; inset: 0;
            background-size: cover; background-position: center top;
            transition: opacity 1s ease;
        }
        .hero-gradient {
            position: absolute; inset: 0;
            background: linear-gradient(
                0deg,
                var(--bg) 0%,
                rgba(10,10,15,0.7) 40%,
                rgba(10,10,15,0.2) 70%,
                rgba(10,10,15,0.5) 100%
            );
        }
        .hero-gradient-side {
            position: absolute; inset: 0;
            background: linear-gradient(90deg, rgba(10,10,15,0.8) 0%, transparent 50%);
        }
        .hero-content {
            position: absolute; bottom: 0; left: 0; right: 0;
            padding: 0 20px 32px;
        }
        .hero-badge {
            display: inline-flex; align-items: center; gap: 5px;
            background: var(--accent); color: #fff;
            font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
            padding: 3px 10px; border-radius: 3px; text-transform: uppercase;
            margin-bottom: 10px;
        }
        .hero-title {
            font-size: clamp(22px, 6vw, 38px); font-weight: 800;
            line-height: 1.1; letter-spacing: -0.5px;
            text-shadow: 0 2px 20px rgba(0,0,0,0.8);
            margin-bottom: 8px;
            max-width: 75%;
        }
        .hero-meta {
            display: flex; align-items: center; gap: 10px;
            font-size: 13px; color: var(--text2); margin-bottom: 16px;
        }
        .hero-meta .rating { color: var(--gold); font-weight: 700; }
        .hero-meta .dot { width: 3px; height: 3px; border-radius: 50%; background: var(--text3); }
        .hero-overview {
            font-size: 13px; color: var(--text2); line-height: 1.5;
            max-width: 75%; display: -webkit-box;
            -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
            margin-bottom: 16px;
        }
        .hero-btn {
            display: inline-flex; align-items: center; gap: 8px;
            background: var(--accent); color: #fff;
            padding: 12px 26px; border-radius: var(--radius);
            font-family: 'Outfit', sans-serif; font-size: 14px; font-weight: 700;
            border: none; cursor: pointer;
            transition: background 0.25s, transform 0.15s, box-shadow 0.25s;
            text-transform: uppercase; letter-spacing: 0.5px;
            box-shadow: 0 4px 14px rgba(229, 9, 20, 0.3);
        }
        .hero-btn:hover { background: #ff0f1b; box-shadow: 0 6px 20px rgba(229, 9, 20, 0.45); }
        .hero-btn:active { transform: scale(0.97); }
        .hero-dots {
            display: flex; gap: 6px; margin-top: 16px;
        }
        .hero-dot {
            width: 24px; height: 3px; border-radius: 2px;
            background: rgba(255,255,255,0.25); cursor: pointer;
            transition: background 0.3s, width 0.3s;
        }
        .hero-dot.active { background: var(--accent); width: 36px; }

        /* ── MAIN CONTENT ── */
        .main { padding: 0 0 20px; }

        /* ── ROWS ── */
        .row-section { margin-bottom: 32px; }
        .row-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 20px; margin-bottom: 14px;
        }
        .row-title {
            font-size: 17px; font-weight: 700; letter-spacing: -0.2px;
            color: #fff;
        }
        .row-title span {
            display: inline-block; width: 4px; height: 16px;
            background: var(--accent); border-radius: 2px; margin-right: 8px;
            vertical-align: middle;
        }
        .row-see-all {
            font-size: 12px; color: var(--text3); cursor: pointer;
            font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
        }
        /* PC: show thin custom scrollbar, mobile: hide */
        .poster-scroll {
            display: flex; gap: 12px; overflow-x: auto;
            padding: 12px 16px 20px;
            scroll-snap-type: x mandatory;
            scroll-padding: 0 16px;
            cursor: grab;
            scrollbar-width: thin;
            scrollbar-color: rgba(229,9,20,0.4) transparent;
        }
        .poster-scroll:active { cursor: grabbing; }
        .poster-scroll::-webkit-scrollbar { height: 4px; }
        .poster-scroll::-webkit-scrollbar-track { background: transparent; }
        .poster-scroll::-webkit-scrollbar-thumb { background: rgba(229,9,20,0.4); border-radius: 2px; }
        @media (pointer: coarse) {
            .poster-scroll { scrollbar-width: none; }
            .poster-scroll::-webkit-scrollbar { display: none; }
        }

        /* ── POSTER CARD ── */
        .poster-card {
            flex-shrink: 0; width: 120px; scroll-snap-align: start;
            cursor: pointer; position: relative;
            transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s ease;
        }
        .poster-card:hover {
            transform: translateY(-5px) scale(1.04);
            z-index: 5;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
        }
        .poster-card:active { transform: scale(0.97); }
        .poster-img-wrap {
            width: 120px; height: 178px; border-radius: var(--radius-sm);
            overflow: hidden; background: var(--card2);
            position: relative;
            border: 1px solid var(--border);
            transition: border-color 0.3s ease;
        }
        .poster-card:hover .poster-img-wrap {
            border-color: rgba(229, 9, 20, 0.4);
        }
        .poster-img {
            width: 100%; height: 100%; object-fit: cover;
            transition: transform 0.5s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        .poster-card:hover .poster-img {
            transform: scale(1.06);
        }
        .poster-placeholder {
            width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, #1e1e2f 0%, #11111d 100%);
            border: 1px solid rgba(255, 255, 255, 0.03);
            color: var(--text3); font-size: 30px;
            border-radius: var(--radius-sm);
        }
        .poster-rating {
            position: absolute; top: 6px; right: 6px;
            background: rgba(0,0,0,0.8); backdrop-filter: blur(8px);
            color: var(--gold); font-size: 10px; font-weight: 700;
            padding: 2px 6px; border-radius: 4px;
            display: flex; align-items: center; gap: 3px;
        }
        .poster-type-badge {
            position: absolute; bottom: 6px; left: 6px;
            background: rgba(0,0,0,0.75); backdrop-filter: blur(8px);
            color: var(--text2); font-size: 9px; font-weight: 600;
            padding: 2px 6px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .poster-title {
            font-size: 11px; font-weight: 600; color: var(--text2);
            margin-top: 7px; line-height: 1.3;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .poster-year { font-size: 10px; color: var(--text3); margin-top: 2px; }

        /* ── FILE MODAL ── */
        .modal-backdrop {
            position: fixed; inset: 0; z-index: 300;
            background: rgba(0,0,0,0.88); backdrop-filter: blur(16px);
            display: flex; align-items: flex-end; justify-content: center;
            opacity: 0; visibility: hidden;
            transition: opacity 0.3s, visibility 0.3s;
        }
        .modal-backdrop.open { opacity: 1; visibility: visible; }
        .modal-sheet {
            background: var(--card); border-radius: 20px 20px 0 0;
            width: 100%; max-width: 780px; max-height: 92vh;
            display: flex; flex-direction: column;
            transform: translateY(100%); transition: transform 0.35s cubic-bezier(0.4,0,0.2,1);
            overflow: hidden;
        }
        .modal-backdrop.open .modal-sheet { transform: translateY(0); }
        .modal-handle {
            width: 36px; height: 4px; background: var(--text3);
            border-radius: 2px; margin: 14px auto 0; flex-shrink: 0;
        }
        .modal-header {
            display: flex; align-items: flex-start; gap: 14px;
            padding: 16px 20px; flex-shrink: 0;
        }
        .detail-scroll {
            overflow-y: auto; flex: 1; padding-bottom: 96px;
        }
        .detail-media {
            position: relative; width: 100%; aspect-ratio: 16 / 9;
            background: #050508; overflow: hidden; border-bottom: 1px solid var(--border);
        }
        .detail-media iframe,
        .detail-media img {
            position: absolute; inset: 0; width: 100%; height: 100%; border: 0;
            object-fit: cover;
        }
        .detail-media::after {
            content: ''; position: absolute; inset: auto 0 0; height: 35%;
            background: linear-gradient(to top, rgba(22,22,31,0.9), transparent);
            pointer-events: none;
        }
        .detail-source-row {
            display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 20px 0;
        }
        .source-chip {
            color: var(--text2); border: 1px solid var(--border); background: rgba(255,255,255,0.04);
            font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.7px;
            padding: 5px 8px; border-radius: 6px; text-decoration: none;
        }
        .detail-section { padding: 16px 20px 0; }
        .detail-section-title {
            font-size: 12px; color: var(--text3); text-transform: uppercase;
            letter-spacing: 1px; font-weight: 800; margin-bottom: 10px;
        }
        .detail-grid {
            display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px;
        }
        .detail-stat {
            background: rgba(255,255,255,0.035); border: 1px solid var(--border);
            border-radius: var(--radius-sm); padding: 10px;
        }
        .detail-stat-label { color: var(--text3); font-size: 10px; text-transform: uppercase; font-weight: 800; margin-bottom: 4px; }
        .detail-stat-value { color: #fff; font-size: 13px; font-weight: 700; line-height: 1.35; }
        .detail-strip {
            display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px;
            scrollbar-width: none;
        }
        .detail-strip::-webkit-scrollbar { display: none; }
        .person-card { width: 92px; flex: 0 0 auto; }
        .person-photo {
            width: 92px; height: 118px; border-radius: var(--radius-sm);
            object-fit: cover; background: var(--card2); border: 1px solid var(--border);
        }
        .person-name { font-size: 11px; font-weight: 700; margin-top: 6px; color: #fff; line-height: 1.25; }
        .person-role { font-size: 10px; color: var(--text3); line-height: 1.25; margin-top: 2px; }
        .image-thumb {
            width: 180px; height: 102px; flex: 0 0 auto; border-radius: var(--radius-sm);
            object-fit: cover; background: var(--card2); border: 1px solid var(--border);
        }
        .quote-card {
            border-left: 3px solid var(--accent); background: rgba(255,255,255,0.035);
            padding: 12px; border-radius: var(--radius-sm); color: var(--text2);
            font-size: 12px; line-height: 1.55; margin-bottom: 8px;
        }
        .file-action-bar {
            position: sticky; bottom: 0; z-index: 4; background: rgba(22,22,31,0.96);
            border-top: 1px solid var(--border); backdrop-filter: blur(18px);
            padding: 12px 14px calc(12px + env(safe-area-inset-bottom, 0px));
            display: none; gap: 10px; align-items: center;
        }
        .file-action-bar.show { display: flex; }
        .selected-file-name {
            flex: 1; min-width: 0; font-size: 11px; color: var(--text2); line-height: 1.35;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        }
        .action-pill {
            border: 0; border-radius: var(--radius-sm); color: #fff; font-family: 'Outfit', sans-serif;
            font-size: 12px; font-weight: 800; padding: 11px 13px; cursor: pointer;
            text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
            white-space: nowrap;
        }
        .watch-pill { background: var(--accent); }
        .download-pill { background: var(--card2); border: 1px solid var(--border); }
        .modal-poster {
            width: 64px; height: 95px; border-radius: var(--radius-sm);
            object-fit: cover; flex-shrink: 0; background: var(--card2);
        }
        .modal-poster-placeholder {
            width: 64px; height: 95px; border-radius: var(--radius-sm);
            background: var(--card2); display: flex; align-items: center;
            justify-content: center; font-size: 24px; flex-shrink: 0;
        }
        .modal-info { flex: 1; min-width: 0; }
        .modal-title {
            font-size: 18px; font-weight: 800; line-height: 1.2;
            margin-bottom: 5px; letter-spacing: -0.3px;
        }
        .modal-meta {
            display: flex; align-items: center; gap: 8px;
            font-size: 12px; color: var(--text2); margin-bottom: 8px;
        }
        .modal-meta .rating { color: var(--gold); font-weight: 700; }
        .modal-overview {
            font-size: 12px; color: var(--text3); line-height: 1.5;
            display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .modal-close-btn {
            width: 32px; height: 32px; flex-shrink: 0; background: var(--card2);
            border: none; border-radius: 50%; cursor: pointer; color: var(--text2);
            display: flex; align-items: center; justify-content: center;
            transition: background 0.2s, color 0.2s, transform 0.2s;
        }
        .modal-close-btn:hover { background: var(--border); color: #fff; transform: rotate(90deg); }
        .modal-divider { height: 1px; background: var(--border); flex-shrink: 0; }
        .modal-files-label {
            padding: 14px 20px 10px; font-size: 12px; font-weight: 700;
            color: var(--text3); text-transform: uppercase; letter-spacing: 1px;
            flex-shrink: 0;
        }
        .modal-files {
            overflow-y: auto; flex: 1; padding: 0 12px 20px;
        }
        .file-item {
            display: flex; align-items: center; gap: 12px;
            padding: 14px 12px; border-radius: var(--radius);
            cursor: pointer; transition: background 0.2s, transform 0.1s;
            border-bottom: 1px solid var(--border);
            margin-bottom: 4px;
        }
        .file-item:last-child { border-bottom: none; }
        .file-item:hover { background: var(--card2); transform: translateX(2px); }
        .file-item:active { background: rgba(229,9,20,0.1); transform: scale(0.99); }
        .file-item.selected { background: rgba(229,9,20,0.14); border-color: rgba(229,9,20,0.38); }
        
        /* Genre pills in modal */
        .modal-genres {
            display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0;
        }
        .genre-pill {
            background: rgba(255,255,255,0.04); border: 1px solid var(--border);
            color: var(--text2); font-size: 10px; font-weight: 600;
            padding: 3px 8px; border-radius: 20px;
            letter-spacing: 0.2px;
        }
        .file-icon {
            width: 38px; height: 38px; border-radius: var(--radius-sm);
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
        }
        .file-item-info { flex: 1; min-width: 0; }
        .file-item-name {
            font-size: 13px; font-weight: 600; color: #fff;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            overflow: hidden; line-height: 1.4; margin-bottom: 3px;
        }
        .file-item-size { font-size: 11px; color: var(--text3); font-weight: 500; }
        .file-item-get {
            width: 30px; height: 30px; flex-shrink: 0;
            background: rgba(229,9,20,0.15); border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            color: var(--accent);
        }
        .season-strip {
            display: flex; gap: 8px; overflow-x: auto;
            padding: 0 8px 12px; margin: 0 0 8px;
            scroll-snap-type: x mandatory;
            scrollbar-width: none;
        }
        .season-strip::-webkit-scrollbar { display: none; }
        .season-btn {
            flex: 0 0 auto; scroll-snap-align: start;
            border: 1px solid var(--border); background: var(--card2);
            color: var(--text2); border-radius: 999px;
            padding: 9px 14px; font-family: 'Outfit', sans-serif;
            font-size: 12px; font-weight: 700; cursor: pointer;
            white-space: nowrap; transition: background 0.2s, color 0.2s, border-color 0.2s;
        }
        .season-btn.active {
            background: var(--accent); color: #fff;
            border-color: rgba(229,9,20,0.75);
        }
        .episode-panel { display: flex; flex-direction: column; gap: 4px; }
        .episode-kicker {
            font-size: 11px; font-weight: 700; color: var(--text3);
            text-transform: uppercase; letter-spacing: 0.7px;
            padding: 2px 12px 8px;
        }
        .episode-number {
            width: 38px; height: 38px; border-radius: var(--radius-sm);
            background: rgba(229,9,20,0.13); color: var(--accent);
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; font-size: 12px; font-weight: 800;
            border: 1px solid rgba(229,9,20,0.18);
        }
        .modal-loading {
            text-align: center; padding: 40px 20px; color: var(--text3);
            font-size: 14px;
        }
        .modal-empty {
            text-align: center; padding: 40px 20px;
        }
        .modal-empty-icon { font-size: 40px; margin-bottom: 12px; }
        .modal-empty-title { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
        .modal-empty-sub { font-size: 13px; color: var(--text3); line-height: 1.5; }

        /* ── FILE SEARCH BAR ── */
        .file-search-wrap {
            padding: 10px 14px 6px;
            flex-shrink: 0;
        }
        .file-search-input {
            width: 100%; padding: 9px 14px 9px 36px;
            border-radius: var(--radius-sm); border: 1px solid var(--border);
            background: var(--card2); color: #fff;
            font-family: 'Outfit', sans-serif; font-size: 13px;
            outline: none; transition: border-color 0.2s;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%23666680' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: 12px center;
        }
        .file-search-input::placeholder { color: var(--text3); }
        .file-search-input:focus { border-color: rgba(229,9,20,0.4); }
        .file-filter-row {
            display: flex; gap: 6px; flex-wrap: wrap;
            padding: 4px 14px 8px;
        }
        .file-filter-chip {
            border: 1px solid var(--border); background: rgba(255,255,255,.04);
            color: var(--text2); font-size: 11px; font-weight: 600;
            padding: 3px 10px; border-radius: 20px; cursor: pointer;
            font-family: 'Outfit', sans-serif;
            transition: background .15s, border-color .15s, color .15s;
        }
        .file-filter-chip.active {
            background: var(--accent); color: #fff; border-color: var(--accent);
        }
        .file-filter-chip:hover:not(.active) { background: rgba(255,255,255,.08); color: #fff; }
        .file-search-count {
            font-size: 11px; color: var(--text3); padding: 0 14px 6px;
        }

        /* ── REPAIR OVERLAY ── */
        .repair-overlay {
            position: fixed; inset: 0; z-index: 500;
            background: var(--bg);
            display: none; align-items: center; justify-content: center;
            flex-direction: column; text-align: center; padding: 40px 30px;
        }
        .repair-overlay.show { display: flex; }
        .repair-icon { font-size: 72px; margin-bottom: 24px; }
        .repair-title { font-size: 26px; font-weight: 800; margin-bottom: 10px; }
        .repair-sub { font-size: 15px; color: var(--text2); line-height: 1.6; max-width: 320px; }

        /* ── SKELETON ── */
        .skel { background: linear-gradient(90deg, var(--card) 25%, var(--card2) 50%, var(--card) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; border-radius: var(--radius-sm); }
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        .skel-poster { width: 120px; height: 178px; border-radius: var(--radius-sm); flex-shrink: 0; }
        .skel-text { height: 12px; border-radius: 6px; margin-top: 8px; }

        /* ── SPINNER ── */
        .spinner {
            width: 28px; height: 28px; border: 3px solid var(--border);
            border-top-color: var(--accent); border-radius: 50%;
            animation: spin 0.7s linear infinite; margin: 0 auto 12px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── FADE ANIMATIONS ── */
        @keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        .fade-up { animation: fadeUp 0.4s ease both; }

        /* ── TOAST ── */
        .toast {
            position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px);
            background: var(--card2); border: 1px solid var(--border);
            color: #fff; font-size: 13px; font-weight: 600;
            padding: 10px 20px; border-radius: 20px;
            opacity: 0; transition: opacity 0.3s, transform 0.3s; z-index: 999;
            white-space: nowrap;
        }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

        /* ── FOOTER ── */
        .site-footer {
            background: linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 100%);
            border-top: 1px solid var(--border);
            padding: 36px 24px 40px;
            text-align: center;
            margin-top: 10px;
        }
        .footer-logo {
            font-size: 20px; font-weight: 900; letter-spacing: -0.3px;
            background: linear-gradient(135deg, #fff 0%, var(--accent) 60%, var(--accent2) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            display: inline-block; margin-bottom: 8px;
        }
        .footer-tagline {
            font-size: 12px; color: var(--text3); margin-bottom: 20px; letter-spacing: 0.3px;
        }
        .footer-links {
            display: flex; align-items: center; justify-content: center;
            gap: 20px; margin-bottom: 20px; flex-wrap: wrap;
        }
        .footer-link {
            font-size: 12px; color: var(--text2); text-decoration: none; font-weight: 600;
            letter-spacing: 0.3px; transition: color 0.2s;
        }
        .footer-link:hover { color: var(--accent); }
        .footer-divider {
            width: 40px; height: 2px; border-radius: 1px;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            margin: 0 auto 16px;
        }
        .footer-copy {
            font-size: 11px; color: var(--text3); line-height: 1.6;
        }
        .footer-powered {
            display: inline-flex; align-items: center; gap: 5px;
            font-size: 11px; color: var(--text3); margin-top: 6px;
        }
        .footer-powered a { color: var(--accent); text-decoration: none; font-weight: 700; }
        .footer-tmdb {
            font-size: 10px; color: var(--text3); margin-top: 8px; opacity: 0.6;
        }

        /* ── TODAY AIRING PANEL ── */
        .today-panel {
            position: fixed; inset: 0; z-index: 250;
            background: rgba(10,10,15,0.97); backdrop-filter: blur(32px);
            display: flex; flex-direction: column;
            opacity: 0; visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }
        .today-panel.open { opacity: 1; visibility: visible; }
        .today-panel-header {
            display: flex; align-items: center; gap: 12px;
            padding: calc(env(safe-area-inset-top, 0px) + 16px) 16px 14px;
            border-bottom: 1px solid var(--border); flex-shrink: 0;
            background: rgba(10,10,15,0.9);
        }
        .today-panel-title {
            flex: 1; font-size: 16px; font-weight: 800; letter-spacing: -0.2px;
        }
        .today-panel-close {
            width: 34px; height: 34px; background: var(--card2); border: none;
            border-radius: 50%; cursor: pointer; color: var(--text2);
            display: flex; align-items: center; justify-content: center;
            transition: background 0.2s, color 0.2s;
        }
        .today-panel-close:hover { background: var(--border); color: #fff; }
        .today-tabs {
            display: flex; gap: 0; overflow-x: auto; flex-shrink: 0;
            border-bottom: 1px solid var(--border);
            scrollbar-width: none;
        }
        .today-tabs::-webkit-scrollbar { display: none; }
        .today-tab {
            flex: 0 0 auto; padding: 12px 16px;
            background: none; border: none; border-bottom: 2px solid transparent;
            color: var(--text3); font-family: 'Outfit', sans-serif;
            font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap;
            transition: color 0.2s, border-color 0.2s;
        }
        .today-tab.active { color: #fff; border-bottom-color: var(--accent); }
        .today-list {
            overflow-y: auto; flex: 1; padding: 12px 0 40px;
        }
        .today-item {
            display: flex; align-items: flex-start; gap: 12px;
            padding: 12px 16px; cursor: pointer;
            transition: background 0.2s; border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .today-item:hover { background: var(--card2); }
        .today-thumb {
            width: 70px; height: 100px; border-radius: 8px; flex-shrink: 0;
            object-fit: cover; background: var(--card2); border: 1px solid var(--border);
        }
        .today-thumb-placeholder {
            width: 70px; height: 100px; border-radius: 8px; flex-shrink: 0;
            background: var(--card2); display: flex; align-items: center;
            justify-content: center; font-size: 22px; border: 1px solid var(--border);
        }
        .today-info { flex: 1; min-width: 0; padding-top: 2px; }
        .today-item-title {
            font-size: 14px; font-weight: 700; color: #fff; line-height: 1.3;
            margin-bottom: 5px;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        }
        .today-ep-badge {
            display: inline-flex; align-items: center; gap: 5px;
            background: rgba(229,9,20,0.15); border: 1px solid rgba(229,9,20,0.3);
            color: var(--accent); font-size: 11px; font-weight: 800;
            padding: 3px 8px; border-radius: 6px; margin-bottom: 5px;
            letter-spacing: 0.2px;
        }
        .today-meta-row {
            display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
        }
        .today-source-chip {
            font-size: 10px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.5px; padding: 2px 7px; border-radius: 4px; border: 1px solid;
        }
        .chip-imdb  { color: #f5c518; border-color: rgba(245,197,24,0.35); background: rgba(245,197,24,0.08); }
        .chip-tvdb  { color: #5bade0; border-color: rgba(91,173,224,0.35); background: rgba(91,173,224,0.08); }
        .chip-tmdb  { color: #01d277; border-color: rgba(1,210,119,0.35);  background: rgba(1,210,119,0.08); }
        .chip-mal   { color: #2e51a2; border-color: rgba(46,81,162,0.5);   background: rgba(46,81,162,0.15); color: #7b9fd4; }
        .today-rating { font-size: 11px; color: var(--gold); font-weight: 700; }
        .today-network { font-size: 11px; color: var(--text3); }
        .today-empty {
            text-align: center; padding: 60px 20px; color: var(--text3); font-size: 14px;
        }
        .today-spinner {
            display: flex; align-items: center; justify-content: center; padding: 60px 20px;
        }

        /* Today Airing nav button */
        .nav-today-btn {
            background: rgba(229,9,20,0.12); border: 1px solid rgba(229,9,20,0.3);
            color: var(--accent); border-radius: 8px;
            padding: 0 10px; height: 40px;
            display: flex; align-items: center; gap: 6px;
            font-family: 'Outfit', sans-serif; font-size: 12px; font-weight: 800;
            cursor: pointer; white-space: nowrap;
            transition: background 0.2s, border-color 0.2s;
            letter-spacing: 0.2px;
        }
        .nav-today-btn:hover { background: rgba(229,9,20,0.22); border-color: rgba(229,9,20,0.5); }
        .nav-today-dot {
            width: 7px; height: 7px; border-radius: 50%; background: var(--accent);
            box-shadow: 0 0 8px var(--accent);
            animation: pulse2 2s cubic-bezier(.4,0,.6,1) infinite;
        }
        @keyframes pulse2 { 50% { opacity: .35; box-shadow: none; } }

        /* ── RECENTLY ADDED ROW ── */
        .live-badge {
            display: inline-flex; align-items: center; gap: 5px;
            background: rgba(229,9,20,.14); border: 1px solid rgba(229,9,20,.32);
            color: var(--accent); font-size: 9px; font-weight: 800;
            letter-spacing: .08em; text-transform: uppercase;
            padding: 2px 8px; border-radius: 20px; flex-shrink: 0;
        }
        .live-dot {
            width: 5px; height: 5px; border-radius: 50%; background: var(--accent);
            box-shadow: 0 0 6px var(--accent);
            animation: pulse2 1.6s cubic-bezier(.4,0,.6,1) infinite;
            flex-shrink: 0;
        }

        /* ── TODAY RELEASED SECTION ── */
        .today-released-section { margin: 0 0 32px; }
        .today-released-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 20px; margin-bottom: 10px;
        }
        .today-released-title {
            font-size: 17px; font-weight: 700; letter-spacing: -0.2px; color: #fff;
        }
        .today-released-title span {
            display: inline-block; width: 4px; height: 16px;
            background: var(--gold); border-radius: 2px; margin-right: 8px;
            vertical-align: middle;
        }
        .today-filter-row {
            display: flex; gap: 7px; padding: 0 20px 12px; overflow-x: auto;
            scrollbar-width: none;
        }
        .today-filter-row::-webkit-scrollbar { display: none; }
        .today-tag {
            border: 1px solid var(--border); background: rgba(255,255,255,.04);
            color: var(--text2); font-size: 11px; font-weight: 700;
            padding: 5px 13px; border-radius: 20px; cursor: pointer; flex-shrink: 0;
            transition: background .2s, border-color .2s, color .2s;
        }
        .today-tag.active { background: var(--accent); color: #fff; border-color: var(--accent); }
        .today-tag:hover:not(.active) { background: rgba(255,255,255,.08); color: #fff; }

        @media (min-width: 600px) {
            .poster-card { width: 150px; }
            .poster-img-wrap { width: 150px; height: 224px; }
            .skel-poster { width: 150px; height: 224px; }
            .search-top-bar { padding-top: 80px; padding-left: 24px; padding-right: 24px; }
            .search-results-grid { padding-left: 24px; padding-right: 24px; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 16px; }
        }
        @media (min-width: 900px) {
            .poster-card { width: 170px; }
            .poster-img-wrap { width: 170px; height: 255px; }
            .skel-poster { width: 170px; height: 255px; }
            .row-header { padding: 0 36px; }
            .poster-scroll { padding: 12px 24px 20px; scroll-padding: 0 24px; }
            .hero-content { padding: 0 48px 44px; }
            .hero-title { font-size: 52px; max-width: 58%; }
            .hero-overview { max-width: 52%; font-size: 15px; }
            .search-results-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }
        }
    </style>
</head>
<body>

<!-- REPAIR MODE OVERLAY -->
<div class="repair-overlay" id="repairOverlay">
    <div class="repair-icon">🔧</div>
    <div class="repair-title">Under Maintenance</div>
    <div class="repair-sub">Sorry for the inconvenience, we are under Maintenance. We'll be back soon!</div>
</div>

<!-- NAVBAR -->
<nav class="navbar" id="navbar">
    <div class="nav-logo">Filmotainment</div>
    <button class="nav-search-pill" onclick="openSearch()" title="Search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <span>Search movies, series, anime</span>
    </button>
    <div class="nav-right">
        <button class="nav-today-btn" onclick="openTodayPanel()" title="Today Airing">
            <span class="nav-today-dot"></span>
            Today
        </button>
        <button class="nav-search-toggle" id="searchToggle" onclick="openSearch()" title="Search">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
    </div>
</nav>

<!-- SEARCH OVERLAY -->
<div class="search-overlay" id="searchOverlay">
    <!-- Top bar: input + cancel always inline -->
    <div class="search-top-bar">
        <div class="search-field-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input class="search-field" id="searchField" type="text" placeholder="Search movies, series, anime..." autocomplete="off">
        </div>
        <button class="search-close" onclick="closeSearch()">Cancel</button>
    </div>
    <div class="search-results-grid" id="searchResultsGrid">
        <div class="search-hint" style="grid-column:1/-1">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Search for movies, TV shows and anime
        </div>
    </div>
</div>

<!-- TODAY AIRING PANEL -->
<div class="today-panel" id="todayPanel">
    <div class="today-panel-header">
        <div class="today-panel-title">📅 Today Airing</div>
        <button class="today-panel-close" onclick="closeTodayPanel()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
    </div>
    <div class="today-tabs" id="todayTabs">
        <button class="today-tab active" data-tab="tv" onclick="switchTodayTab('tv')">TV Shows</button>
        <button class="today-tab" data-tab="anime" onclick="switchTodayTab('anime')">Anime</button>
    </div>
    <div class="today-list" id="todayList">
        <div class="today-spinner"><div class="spinner"></div></div>
    </div>
</div>

<!-- HERO SECTION -->
<section class="hero" id="hero">
    <div class="hero-bg" id="heroBg"></div>
    <div class="hero-gradient"></div>
    <div class="hero-gradient-side"></div>
    <div class="hero-content">
        <div class="hero-badge">🔥 Trending</div>
        <div class="hero-title" id="heroTitle">Loading...</div>
        <div class="hero-meta" id="heroMeta"></div>
        <div class="hero-overview" id="heroOverview"></div>
        <button class="hero-btn" id="heroBtn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg>
            Get Files
        </button>
        <div class="hero-dots" id="heroDots"></div>
    </div>
</section>

<!-- MAIN CONTENT ROWS -->
<main class="main" id="main">

    <!-- ── TODAY RELEASED (TV Series · Anime · OTT Movies) ── -->
    <section class="today-released-section fade-up" id="todayReleasedSection">
        <div class="today-released-header">
            <div class="today-released-title">
                <span></span>Today's Releases
            </div>
            <div class="live-badge"><span class="live-dot"></span>Live</div>
        </div>
        <div class="today-filter-row" id="todayFilterRow">
            <button class="today-tag active" data-filter="all"   onclick="filterTodayReleased('all')">All</button>
            <button class="today-tag"        data-filter="tv"    onclick="filterTodayReleased('tv')">TV Series</button>
            <button class="today-tag"        data-filter="anime" onclick="filterTodayReleased('anime')">Anime</button>
            <button class="today-tag"        data-filter="movie" onclick="filterTodayReleased('movie')">OTT Movies</button>
        </div>
        <div class="poster-scroll" id="rowTodayReleased">
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

    <!-- ── RECENTLY ADDED (bot database) ── -->
    <section class="row-section fade-up" id="recentlyAddedSection">
        <div class="row-header">
            <div class="row-title" style="display:flex;align-items:center;gap:8px">
                <span></span>Recently Added
                <div class="live-badge"><span class="live-dot"></span>New</div>
            </div>
        </div>
        <div class="poster-scroll" id="rowRecentlyAdded">
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

    <!-- Trending Row -->
    <section class="row-section fade-up">
        <div class="row-header">
            <div class="row-title"><span></span>Trending This Week</div>
        </div>
        <div class="poster-scroll" id="rowTrending">
            <!-- skeleton -->
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

    <!-- Popular Movies Row -->
    <section class="row-section fade-up" style="animation-delay:0.08s">
        <div class="row-header">
            <div class="row-title"><span></span>Popular Movies</div>
        </div>
        <div class="poster-scroll" id="rowMovies">
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

    <!-- Popular TV Row -->
    <section class="row-section fade-up" style="animation-delay:0.16s">
        <div class="row-header">
            <div class="row-title"><span></span>Popular TV Shows</div>
        </div>
        <div class="poster-scroll" id="rowTV">
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

    <!-- Top Rated Row -->
    <section class="row-section fade-up" style="animation-delay:0.24s">
        <div class="row-header">
            <div class="row-title"><span></span>Top Rated</div>
        </div>
        <div class="poster-scroll" id="rowTopRated">
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

    <!-- Popular Anime Row -->
    <section class="row-section fade-up" style="animation-delay:0.32s">
        <div class="row-header">
            <div class="row-title"><span></span>Popular Anime</div>
        </div>
        <div class="poster-scroll" id="rowAnime">
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div><div class="skel skel-poster"></div>
            <div class="skel skel-poster"></div>
        </div>
    </section>

</main>

<!-- PREMIUM FOOTER -->
<footer class="site-footer">
    <div class="footer-logo">Filmotainment</div>
    <div class="footer-tagline">Your premium media discovery platform</div>
    <div class="footer-divider"></div>
    <div class="footer-links">
        <a href="https://t.me/FT_Channels" class="footer-link" target="_blank">Telegram Channel</a>
        <a href="https://t.me/TeamYoonseri" class="footer-link" target="_blank">Support</a>
        <a href="https://www.themoviedb.org" class="footer-link" target="_blank">TMDB</a>
    </div>
    <div class="footer-copy">&copy; <span id="footerYear"></span> Filmotainment. All rights reserved.</div>
    <div class="footer-powered">Powered by <a href="https://t.me/FT_Channels" target="_blank">Filmotainment</a></div>
    <div class="footer-tmdb">This product uses the TMDB API but is not endorsed or certified by TMDB.</div>
</footer>

<!-- FILE MODAL -->
<div class="modal-backdrop" id="modalBackdrop" onclick="handleBackdropClick(event)">
    <div class="modal-sheet" id="modalSheet">
        <div class="modal-handle"></div>
        <div class="detail-scroll" id="detailScroll">
        <div class="detail-media" id="detailMedia"></div>
        <div class="modal-header" id="modalHeader">
            <div class="modal-poster-placeholder" id="modalPosterWrap">🎬</div>
            <div class="modal-info" id="modalInfo"></div>
            <button class="modal-close-btn" onclick="closeModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        </div>
        <div class="detail-source-row" id="detailSources"></div>
        <div class="detail-section" id="detailStats"></div>
        <div class="detail-section" id="detailCast"></div>
        <div class="detail-section" id="detailImages"></div>
        <div class="detail-section" id="detailQuotes"></div>
        <div class="modal-divider"></div>
        <div class="modal-files-label">Available Files</div>
        <div class="file-search-wrap">
            <input class="file-search-input" id="fileSearchInput" type="text" placeholder="Search episode, language, resolution..." autocomplete="off">
        </div>
        <div class="file-filter-row" id="fileFilterRow"></div>
        <div class="file-search-count" id="fileSearchCount"></div>
        <div class="modal-files" id="modalFiles"></div>
        </div>
        <div class="file-action-bar" id="fileActionBar">
            <div class="selected-file-name" id="selectedFileName"></div>
            <a class="action-pill watch-pill" id="watchAction" target="_blank" rel="noopener">Watch</a>
            <button class="action-pill download-pill" id="downloadAction" type="button">Download</button>
        </div>
    </div>
</div>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<script>
function imgError(img) {
    var p = img.parentElement;
    if (p) { img.style.display='none'; var d = document.createElement('div'); d.className='poster-placeholder'; d.textContent='🎬'; p.appendChild(d); }
}
function imgErrorThumb(img) {
    img.style.display='none';
    var sib = img.nextElementSibling;
    if (sib) sib.style.display='flex';
}
// ── INIT ──────────────────────────────────────────────────────────────────
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand();
    tg.setBackgroundColor('#0a0a0f');
    tg.setHeaderColor('#0a0a0f');
}
const user = tg?.initDataUnsafe?.user;
const userId = user?.id || 'unknown';
let botUsername = '';

// Auto-update copyright year
document.getElementById('footerYear').textContent = new Date().getFullYear();

// Navbar: always solid in Telegram Mini App, scroll-driven in browser
const navEl = document.getElementById('navbar');
if (tg) {
    navEl.classList.add('solid'); // always opaque in Telegram
} else {
    window.addEventListener('scroll', () => {
        navEl.classList.toggle('solid', window.scrollY > 20);
    }, { passive: true });
}

// ── MOUSE-DRAG HORIZONTAL SCROLL (PC) ─────────────────────────────────────
function enableDragScroll(el) {
    let isDown = false, startX, scrollLeft;
    el.addEventListener('mousedown', e => {
        isDown = true; el.classList.add('active');
        startX = e.pageX - el.offsetLeft;
        scrollLeft = el.scrollLeft;
        e.preventDefault();
    });
    el.addEventListener('mouseleave', () => { isDown = false; el.classList.remove('active'); });
    el.addEventListener('mouseup',    () => { isDown = false; el.classList.remove('active'); });
    el.addEventListener('mousemove', e => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - el.offsetLeft;
        const walk = (x - startX) * 1.5;
        el.scrollLeft = scrollLeft - walk;
    });
}
// Apply to existing rows (also called after dynamic render)
document.querySelectorAll('.poster-scroll').forEach(enableDragScroll);

// ── HERO ──────────────────────────────────────────────────────────────────
let heroItems = [];
let heroIndex = 0;
let heroTimer = null;

function setHero(item) {
    const bg = document.getElementById('heroBg');
    const title = document.getElementById('heroTitle');
    const meta = document.getElementById('heroMeta');
    const overview = document.getElementById('heroOverview');
    const btn = document.getElementById('heroBtn');

    if (item.backdrop) {
        bg.style.backgroundImage = `url('${item.backdrop}')`;
        bg.style.opacity = '1';
    } else {
        bg.style.opacity = '0';
    }
    title.textContent = item.title;
    overview.textContent = item.overview || '';
    meta.innerHTML = `
        ${item.rating > 0 ? `<span class="rating">⭐ ${item.rating}</span><span class="dot"></span>` : ''}
        <span>${item.year || ''}</span>
        ${item.year ? '<span class="dot"></span>' : ''}
        <span style="text-transform:capitalize">${typeLabel(item.type)}</span>
    `;
    btn.onclick = () => openModal(item);
}

function updateDots() {
    const dots = document.getElementById('heroDots');
    [...dots.children].forEach((d, i) => {
        d.classList.toggle('active', i === heroIndex);
    });
}

function startHeroRotation() {
    if (heroItems.length <= 1) return;
    clearInterval(heroTimer);
    heroTimer = setInterval(() => {
        heroIndex = (heroIndex + 1) % Math.min(heroItems.length, 6);
        setHero(heroItems[heroIndex]);
        updateDots();
    }, 5000);
}

// ── RENDER ROW ────────────────────────────────────────────────────────────
function renderRow(containerId, items) {
    const el = document.getElementById(containerId);
    el.innerHTML = '';
    items.forEach((item, i) => {
        const card = document.createElement('div');
        card.className = 'poster-card';
        card.style.animationDelay = `${i * 0.04}s`;
        const posterHTML = item.poster
            ? `<img class="poster-img" src="${item.poster}" alt="${item.title}" loading="lazy" onerror="imgError(this)">`
            : `<div class="poster-placeholder">🎬</div>`;
        card.innerHTML = `
            <div class="poster-img-wrap">
                ${posterHTML}
                ${item.rating > 0 ? `<div class="poster-rating">⭐ ${item.rating}</div>` : ''}
                <div class="poster-type-badge">${item.type === 'tv' ? 'TV' : (item.type === 'anime' ? 'Anime' : 'Movie')}</div>
            </div>
            <div class="poster-title">${item.title}</div>
            ${item.year ? `<div class="poster-year">${item.year}</div>` : ''}
        `;
        card.onclick = () => openModal(item);
        el.appendChild(card);
    });
}

// ── LOAD HOME ─────────────────────────────────────────────────────────────
async function loadHome() {
    // 1. Check repair mode first
    try {
        const rs = await fetch('/api/repair-status');
        const rd = await rs.json();
        if (rd.repair_mode) {
            document.getElementById('repairOverlay').classList.add('show');
            return;
        }
    } catch(e) {}

    // 2. Load trending immediately — this is the critical first paint
    let trendingMovies = [];
    try {
        const resp = await fetch('/api/tmdb-trending');
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        botUsername = data.bot_username || botUsername;

        heroItems = (data.trending || []).filter(x => x.backdrop).slice(0, 6);
        if (!heroItems.length) heroItems = (data.trending || []).slice(0, 6);
        if (heroItems.length > 0) {
            setHero(heroItems[0]);
            const dotsEl = document.getElementById('heroDots');
            dotsEl.innerHTML = '';
            heroItems.slice(0, 6).forEach((_, i) => {
                const d = document.createElement('div');
                d.className = 'hero-dot' + (i === 0 ? ' active' : '');
                d.onclick = () => { heroIndex = i; setHero(heroItems[i]); updateDots(); clearInterval(heroTimer); startHeroRotation(); };
                dotsEl.appendChild(d);
            });
            startHeroRotation();
        }

        if (data.trending)       { renderRow('rowTrending',  data.trending);       enableDragScroll(document.getElementById('rowTrending')); }
        if (data.popular_movies) { renderRow('rowMovies',    data.popular_movies); enableDragScroll(document.getElementById('rowMovies')); trendingMovies = data.popular_movies; }
        if (data.popular_tv)     { renderRow('rowTV',        data.popular_tv);     enableDragScroll(document.getElementById('rowTV')); }
        if (data.top_rated)      { renderRow('rowTopRated',  data.top_rated);      enableDragScroll(document.getElementById('rowTopRated')); }
        if (data.popular_anime)  { renderRow('rowAnime',     data.popular_anime);  enableDragScroll(document.getElementById('rowAnime')); }
    } catch(e) {
        console.error('Trending load failed:', e);
        document.getElementById('heroTitle').textContent = 'Could not load content';
        document.getElementById('heroOverview').textContent = 'Check your TMDB API key or network connection.';
        const emptyMsg = '<div style="padding:20px 16px;color:var(--text3);font-size:13px">Could not load. Check connection.</div>';
        ['rowTrending','rowMovies','rowTV','rowTopRated','rowAnime'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = emptyMsg;
        });
    }

    // 3. Load today-airing + recently-added in background — won't block main rows
    loadTodayReleased(trendingMovies);
    loadRecentlyAdded();
}

async function loadTodayReleased(trendingMovies) {
    try {
        const resp = await fetch('/api/today-airing');
        const td   = await resp.json();
        const tvItems    = (td.tv    || []).map(x => ({...x, type: 'tv'}));
        const animeItems = (td.anime || []).map(x => ({...x, type: 'anime'}));
        const ottMovies  = (trendingMovies || []).slice(0, 10).map(x => ({...x, type: 'movie'}));

        window._todayAllItems = {
            all:   [...tvItems, ...animeItems, ...ottMovies],
            tv:    tvItems,
            anime: animeItems,
            movie: ottMovies,
        };
        renderTodayReleasedRow('all');
        enableDragScroll(document.getElementById('rowTodayReleased'));
    } catch(e) {
        console.error('Today released load failed:', e);
        const el = document.getElementById('rowTodayReleased');
        if (el) el.innerHTML = '<div style="padding:20px;color:var(--text3);font-size:13px">Could not load today releases.</div>';
    }
}

let _recentlyAddedIds = new Set();

async function loadRecentlyAdded() {
    try {
        const resp  = await fetch('/api/recently-added');
        const data  = await resp.json();
        const files = data.files || [];
        if (files.length > 0) {
            files.forEach(f => _recentlyAddedIds.add(f.id));
            renderRecentlyAdded(files);
            enableDragScroll(document.getElementById('rowRecentlyAdded'));
        } else {
            const sec = document.getElementById('recentlyAddedSection');
            if (sec) sec.style.display = 'none';
        }
    } catch(e) {
        console.error('Recently added load failed:', e);
        const sec = document.getElementById('recentlyAddedSection');
        if (sec) sec.style.display = 'none';
    }
    // Poll every 10 seconds for new files
    setTimeout(pollRecentlyAdded, 10000);
}

async function pollRecentlyAdded() {
    try {
        const resp = await fetch('/api/recently-added?limit=30&_t=' + Date.now());
        const data = await resp.json();
        const files = (data.files || []).filter(f => !_recentlyAddedIds.has(f.id));
        if (files.length > 0) {
            files.forEach(f => _recentlyAddedIds.add(f.id));
            const row = document.getElementById('rowRecentlyAdded');
            if (row) {
                // Prepend new cards with a highlight
                const tmp = document.createElement('div');
                renderRecentlyAddedInto(tmp, files);
                Array.from(tmp.children).reverse().forEach(card => {
                    card.style.outline = '2px solid var(--accent)';
                    card.style.outlineOffset = '2px';
                    row.prepend(card);
                    setTimeout(() => { card.style.outline = ''; card.style.outlineOffset = ''; }, 4000);
                });
                const sec = document.getElementById('recentlyAddedSection');
                if (sec) sec.style.display = '';
            }
        }
    } catch(e) {}
    setTimeout(pollRecentlyAdded, 10000);
}

// ── TODAY RELEASED ROW ────────────────────────────────────────────────────
function renderTodayReleasedRow(filter) {
    const items = (window._todayAllItems || {})[filter] || [];
    const el = document.getElementById('rowTodayReleased');
    if (!items.length) {
        el.innerHTML = '<div style="padding:20px 16px;color:var(--text3);font-size:13px">Nothing scheduled for today in this category.</div>';
        return;
    }
    el.innerHTML = '';
    items.forEach((item, i) => {
        const card = document.createElement('div');
        card.className = 'poster-card';
        card.style.animationDelay = `${i * 0.04}s`;
        const posterSrc = item.poster || item.image || null;
        const posterHTML = posterSrc
            ? `<img class="poster-img" src="${posterSrc}" alt="${escapeHTML(item.title || item.name || '')}" loading="lazy" onerror="imgError(this)">`
            : `<div class="poster-placeholder">🎬</div>`;
        const typeStr = item.type === 'tv' ? 'TV' : (item.type === 'anime' ? 'Anime' : 'Movie');
        let epText = '';
        if (item.season && item.episode) epText = `S${String(item.season).padStart(2,'0')}E${String(item.episode).padStart(2,'0')}`;
        else if (item.episode) epText = `Ep ${item.episode}`;
        const ratingVal = item.rating || 0;
        card.innerHTML = `
            <div class="poster-img-wrap">
                ${posterHTML}
                ${ratingVal > 0 ? `<div class="poster-rating">⭐ ${ratingVal}</div>` : ''}
                <div class="poster-type-badge">${epText ? epText : typeStr}</div>
            </div>
            <div class="poster-title">${escapeHTML(item.title || item.name || '')}</div>
            ${item.year ? `<div class="poster-year">${item.year}</div>` : ''}
        `;
        card.onclick = () => openModal({
            id: item.tmdb_id || item.mal_id || item.id,
            source: (item.mal_id && !item.tmdb_id) ? 'mal' : 'tmdb',
            title: item.title || item.name || '',
            type: item.type || 'movie',
            year: item.year || '',
            rating: ratingVal,
            poster: posterSrc,
            overview: item.overview || '',
        });
        el.appendChild(card);
    });
}

function filterTodayReleased(filter) {
    // Update active pill
    document.querySelectorAll('#todayFilterRow .today-tag').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    renderTodayReleasedRow(filter);
}

// ── RECENTLY ADDED ROW ────────────────────────────────────────────────────
function renderRecentlyAdded(files) {
    const el = document.getElementById('rowRecentlyAdded');
    el.innerHTML = '';
    files.forEach((file, i) => {
        const card = document.createElement('div');
        card.className = 'poster-card';
        card.style.animationDelay = `${i * 0.03}s`;
        const posterSrc = file.poster || null;
        const posterHTML = posterSrc
            ? `<img class="poster-img" src="${posterSrc}" alt="${escapeHTML(file.title || file.name)}" loading="lazy" onerror="imgError(this)">`
            : `<div class="poster-placeholder">🎬</div>`;
        let typeStr = file.type === 'tv' ? 'TV' : (file.type === 'anime' ? 'Anime' : 'Movie');
        let epText = '';
        if (file.season != null && file.episode != null)
            epText = `S${String(file.season).padStart(2,'0')}E${String(file.episode).padStart(2,'0')}`;
        else if (file.season != null)
            epText = `S${String(file.season).padStart(2,'0')}`;
        const badgeText = epText || typeStr;
        const ratingVal = file.rating || 0;
        card.innerHTML = `
            <div class="poster-img-wrap">
                ${posterHTML}
                ${ratingVal > 0 ? `<div class="poster-rating">⭐ ${ratingVal}</div>` : ''}
                <div class="poster-type-badge">${badgeText}</div>
            </div>
            <div class="poster-title">${escapeHTML(file.title || file.name)}</div>
            ${file.year ? `<div class="poster-year">${file.year}</div>` : ''}
        `;
        card.onclick = () => {
            if (file.tmdb_id || (file.type && file.poster)) {
                openModal({
                    id: file.tmdb_id,
                    source: 'tmdb',
                    title: file.title || file.name,
                    type: file.type || 'movie',
                    year: file.year || '',
                    rating: ratingVal,
                    poster: posterSrc,
                    overview: file.overview || '',
                });
            } else {
                // No TMDB data — go direct to watch/download via file ID
                selectFileById(file);
            }
        };
        el.appendChild(card);
    });
}

function renderRecentlyAddedInto(container, files) {
    files.forEach((file, i) => {
        const card = document.createElement('div');
        card.className = 'poster-card fade-up';
        card.style.animationDelay = `${i * 0.03}s`;
        const posterSrc = file.poster || null;
        const posterHTML = posterSrc
            ? `<img class="poster-img" src="${posterSrc}" alt="${escapeHTML(file.title || file.name)}" loading="lazy" onerror="imgError(this)">`
            : `<div class="poster-placeholder">🎬</div>`;
        let typeStr = file.type === 'tv' ? 'TV' : (file.type === 'anime' ? 'Anime' : 'Movie');
        let epText = '';
        if (file.season != null && file.episode != null)
            epText = `S${String(file.season).padStart(2,'0')}E${String(file.episode).padStart(2,'0')}`;
        else if (file.season != null)
            epText = `S${String(file.season).padStart(2,'0')}`;
        const badgeText = epText || typeStr;
        const ratingVal = file.rating || 0;
        card.innerHTML = `
            <div class="poster-img-wrap">
                ${posterHTML}
                ${ratingVal > 0 ? `<div class="poster-rating">⭐ ${ratingVal}</div>` : ''}
                <div class="poster-type-badge">${badgeText}</div>
            </div>
            <div class="poster-title">${escapeHTML(file.title || file.name)}</div>
            ${file.year ? `<div class="poster-year">${file.year}</div>` : ''}
        `;
        card.onclick = () => {
            if (file.tmdb_id || (file.type && file.poster)) {
                openModal({ id: file.tmdb_id, source: 'tmdb', title: file.title || file.name, type: file.type || 'movie', year: file.year || '', rating: ratingVal, poster: posterSrc, overview: file.overview || '' });
            } else {
                selectFileById(file);
            }
        };
        container.appendChild(card);
    });
}

function selectFileById(file) {
    // Show a toast and open download directly
    showToast(`Opening: ${file.name}`);
    window.open(`/api/stream-file/${file.id}`, '_blank');
}

// ── SEARCH ────────────────────────────────────────────────────────────────
let searchTimer = null;

function openSearch() {
    document.getElementById('searchOverlay').classList.add('open');
    setTimeout(() => document.getElementById('searchField').focus(), 300);
}

function closeSearch() {
    document.getElementById('searchOverlay').classList.remove('open');
    document.getElementById('searchField').value = '';
    document.getElementById('searchResultsGrid').innerHTML = `
        <div class="search-hint" style="grid-column:1/-1">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Search for movies, TV shows and anime
        </div>`;
}

// Close search on Escape
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSearch(); });

document.getElementById('searchField').addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    if (!q) {
        closeSearch();
        openSearch();
        return;
    }
    document.getElementById('searchResultsGrid').innerHTML = `
        <div class="search-hint" style="grid-column:1/-1">
            <div class="spinner"></div>Searching...
        </div>`;
    searchTimer = setTimeout(() => doSearch(q), 400);
});

document.getElementById('searchField').addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSearch();
});

async function doSearch(q) {
    try {
        const resp = await fetch(`/api/tmdb-search?q=${encodeURIComponent(q)}`);
        const data = await resp.json();
        const grid = document.getElementById('searchResultsGrid');
        grid.innerHTML = '';
        if (!data.results || data.results.length === 0) {
            grid.innerHTML = `<div class="search-hint" style="grid-column:1/-1">No results found for "<b>${q}</b>"</div>`;
            return;
        }
        if (data.corrected_query && data.corrected_query.toLowerCase() !== q.toLowerCase()) {
            const suggestion = document.createElement('div');
            suggestion.className = 'search-suggestion';
            suggestion.innerHTML = `Showing best matches for <b>${escapeHTML(data.corrected_query)}</b>`;
            grid.appendChild(suggestion);
        }
        // Results count bar
        const bar = document.createElement('div');
        bar.className = 'search-meta-bar';
        bar.style.gridColumn = '1 / -1';
        bar.innerHTML = `Found <b>${data.results.length}</b> results for "<b>${escapeHTML(q)}</b>"`;
        grid.appendChild(bar);
        // Render premium cards using the same poster-card structure
        data.results.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'poster-card';
            card.style.animationDelay = `${Math.min(idx * 0.04, 0.5)}s`;
            const posterHTML = item.poster
                ? `<img class="poster-img" src="${item.poster}" alt="${item.title}" loading="lazy" onerror="imgError(this)">`
                : `<div class="poster-placeholder">🎬</div>`;
            card.innerHTML = `
                <div class="poster-img-wrap">
                    ${posterHTML}
                    ${item.rating > 0 ? `<div class="poster-rating">⭐ ${item.rating}</div>` : ''}
                    <div class="poster-type-badge">${item.type === 'tv' ? 'TV' : (item.type === 'anime' ? 'Anime' : 'Movie')}</div>
                </div>
                <div class="poster-title">${item.title}</div>
                ${item.year ? `<div class="poster-year">${item.year}</div>` : ''}
            `;
            card.onclick = () => { closeSearch(); openModal(item); };
            grid.appendChild(card);
        });
    } catch(e) {
        document.getElementById('searchResultsGrid').innerHTML = `<div class="search-hint" style="grid-column:1/-1">Search failed. Please try again.</div>`;
    }
}

// ── MODAL ─────────────────────────────────────────────────────────────────
let currentItem = null;
let selectedFile = null;

async function openModal(item) {
    currentItem = item;
    selectedFile = null;
    hideFileActions();
    resetDetailSections();
    document.getElementById('detailMedia').innerHTML = item.backdrop
        ? `<img src="${item.backdrop}" alt="${escapeHTML(item.title)} backdrop">`
        : `<div class="modal-loading">Loading details...</div>`;
    document.getElementById('detailScroll').scrollTop = 0;
    // Populate header
    const posterWrap = document.getElementById('modalPosterWrap');
    const info = document.getElementById('modalInfo');
    if (item.poster) {
        posterWrap.innerHTML = `<img class="modal-poster" src="${item.poster}" alt="${item.title}">`;
    } else {
        posterWrap.innerHTML = `<div class="modal-poster-placeholder">🎬</div>`;
    }
    
    // Client-side Genre Lookup mapping
    const genreMap = {
        28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
        99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
        27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi',
        10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western',
        10759: 'Action & Adventure', 10762: 'Kids', 10763: 'News', 10764: 'Reality',
        10765: 'Sci-Fi & Fantasy', 10766: 'Soap', 10767: 'Talk', 10768: 'War & Politics'
    };
    let genrePills = '';
    if (item.genres && item.genres.length > 0) {
        genrePills = `<div class="modal-genres">` + item.genres.slice(0, 3).map(id => `<span class="genre-pill">${genreMap[id] || id || 'Media'}</span>`).join('') + `</div>`;
    }
    
    info.innerHTML = `
        <div class="modal-title">${item.title}</div>
        <div class="modal-meta">
            ${item.rating > 0 ? `<span class="rating">⭐ ${item.rating}</span>` : ''}
            ${item.year ? `<span>${item.year}</span>` : ''}
            <span style="text-transform:capitalize">${typeLabel(item.type)}</span>
        </div>
        ${genrePills}
        ${item.overview ? `<div class="modal-overview">${item.overview}</div>` : ''}
    `;
    // Show modal
    document.getElementById('modalBackdrop').classList.add('open');
    document.body.style.overflow = 'hidden';
    await Promise.all([loadDetailsForItem(item), loadFilesForItem(item)]);
}

function closeModal() {
    document.getElementById('modalBackdrop').classList.remove('open');
    document.body.style.overflow = '';
    currentItem = null;
    selectedFile = null;
    hideFileActions();
}

function handleBackdropClick(e) {
    if (e.target === document.getElementById('modalBackdrop')) closeModal();
}

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

function typeLabel(type) {
    if (type === 'tv') return 'TV Show';
    if (type === 'anime') return 'Anime';
    return 'Movie';
}

function resetDetailSections() {
    ['detailSources', 'detailStats', 'detailCast', 'detailImages', 'detailQuotes'].forEach(id => {
        document.getElementById(id).innerHTML = '';
    });
}

function renderDetailMedia(details) {
    const media = document.getElementById('detailMedia');
    if (details.trailer && details.trailer.embed) {
        // Autoplay muted — YouTube requires autoplay=1&mute=1 together
        let embedUrl = details.trailer.embed;
        try {
            const u = new URL(embedUrl);
            u.searchParams.set('autoplay', '1');
            u.searchParams.set('mute', '1');
            u.searchParams.set('rel', '0');
            u.searchParams.set('modestbranding', '1');
            embedUrl = u.toString();
        } catch(e) {
            embedUrl += (embedUrl.includes('?') ? '&' : '?') + 'autoplay=1&mute=1&rel=0';
        }
        media.innerHTML = `<iframe src="${embedUrl}" title="${escapeHTML(details.title)} trailer" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>`;
    } else if (details.backdrop || details.poster) {
        media.innerHTML = `<img src="${details.backdrop || details.poster}" alt="${escapeHTML(details.title)} image">`;
    } else {
        media.innerHTML = `<div class="modal-loading">No trailer or backdrop available.</div>`;
    }
}

function renderSources(details) {
    const links = details.links || {};
    const chips = [];
    if (links.imdb) chips.push(`<a class="source-chip" href="${links.imdb}" target="_blank" rel="noopener">IMDb</a>`);
    if (links.tvdb) chips.push(`<a class="source-chip" href="${links.tvdb}" target="_blank" rel="noopener">TVDB</a>`);
    if (links.mal) chips.push(`<a class="source-chip" href="${links.mal}" target="_blank" rel="noopener">MyAnimeList</a>`);
    if (links.tmdb) chips.push(`<a class="source-chip" href="${links.tmdb}" target="_blank" rel="noopener">TMDB</a>`);
    document.getElementById('detailSources').innerHTML = chips.join('');
}

function renderStats(details) {
    const imdb = details.external?.imdb || {};
    const tvdb = details.external?.tvdb || {};
    const mal = details.external?.myanimelist || {};
    const values = [
        ['Rating', details.rating ? `${details.rating}/10${details.votes ? ` (${details.votes} votes)` : ''}` : 'Not rated'],
        ['IMDb', imdb.rating ? `${imdb.rating}/10${imdb.votes ? ` (${imdb.votes})` : ''}` : 'Not available'],
        ['Status', details.status || tvdb.status || 'Unknown'],
        ['Runtime', details.runtime || 'Unknown'],
        ['Quote', imdb.quote || details.tagline || 'None listed'],
        ['Rank', mal.rank ? `#${mal.rank}` : (mal.popularity ? `Popularity #${mal.popularity}` : 'Not listed')]
    ];
    document.getElementById('detailStats').innerHTML = `
        <div class="detail-section-title">Details</div>
        <div class="detail-grid">
            ${values.map(([label, value]) => `<div class="detail-stat"><div class="detail-stat-label">${label}</div><div class="detail-stat-value">${escapeHTML(value)}</div></div>`).join('')}
        </div>
        ${details.keywords?.length ? `<div class="modal-genres" style="margin-top:12px">${details.keywords.map(x => `<span class="genre-pill">${escapeHTML(x)}</span>`).join('')}</div>` : ''}
    `;
}

function renderPeople(details) {
    if (!details.cast?.length) return;
    document.getElementById('detailCast').innerHTML = `
        <div class="detail-section-title">Cast</div>
        <div class="detail-strip">
            ${details.cast.map(p => `
                <div class="person-card">
                    ${p.image ? `<img class="person-photo" src="${p.image}" alt="${escapeHTML(p.name)}">` : `<div class="person-photo poster-placeholder">?</div>`}
                    <div class="person-name">${escapeHTML(p.name)}</div>
                    <div class="person-role">${escapeHTML(p.role)}</div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderImages(details) {
    const images = [...(details.images?.backdrops || []), ...(details.images?.posters || [])].filter(Boolean).slice(0, 16);
    if (!images.length) return;
    document.getElementById('detailImages').innerHTML = `
        <div class="detail-section-title">Images</div>
        <div class="detail-strip">
            ${images.map(src => `<img class="image-thumb" src="${src}" alt="${escapeHTML(details.title)} image" loading="lazy">`).join('')}
        </div>
    `;
}

function renderQuotes(details) {
    // Only show tagline and IMDb quote — no user reviews
    const quotes = [];
    if (details.tagline) quotes.push({author: details.title, quote: details.tagline});
    if (details.external?.imdb?.quote) quotes.push({author: 'IMDb', quote: details.external.imdb.quote});
    if (!quotes.length) return;
    document.getElementById('detailQuotes').innerHTML = `
        <div class="detail-section-title">Quote</div>
        ${quotes.map(q => `<div class="quote-card">"${escapeHTML(q.quote)}"<br><b>${escapeHTML(q.author || '')}</b></div>`).join('')}
    `;
}

async function loadDetailsForItem(item) {
    try {
        const params = new URLSearchParams({
            source: item.source || 'tmdb',
            type: item.type || 'movie',
            id: item.id
        });
        const resp = await fetch(`/api/media-details?${params.toString()}`);
        const details = await resp.json();
        if (!resp.ok) throw new Error(details.error || 'Details failed');
        currentItem = {...item, ...details};
        renderDetailMedia(currentItem);
        renderSources(currentItem);
        renderStats(currentItem);
        renderPeople(currentItem);
        renderImages(currentItem);
        renderQuotes(currentItem);
    } catch(e) {
        renderDetailMedia(item);
        document.getElementById('detailStats').innerHTML = `<div class="modal-empty-sub" style="padding:0 0 10px">Extra details could not be loaded. Showing available info.</div>`;
    }
}

function episodeLabel(file) {
    if (file.episode !== null && file.episode !== undefined && file.episode !== '') {
        return `E${String(file.episode).padStart(2, '0')}`;
    }
    return 'File';
}

function seasonLabel(season) {
    return season === 'other' ? 'Other' : `Season ${season}`;
}

function renderFileRow(file, compact=false) {
    const el = document.createElement('div');
    el.className = 'file-item';
    const lead = compact
        ? `<div class="episode-number">${episodeLabel(file)}</div>`
        : `<div class="file-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
        </div>`;
    el.innerHTML = `
        ${lead}
        <div class="file-item-info">
            <div class="file-item-name">${escapeHTML(file.name)}</div>
            <div class="file-item-size">${escapeHTML(file.size)}</div>
        </div>
        <div class="file-item-get">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
        </div>
    `;
    el.onclick = () => selectFile(file, el);
    return el;
}

async function fetchFilesForItem(item) {
    let offset = 0;
    let files = [];
    for (let page = 0; page < 10; page++) {
        const params = new URLSearchParams({
            q: item.title,
            type: item.type || '',
            year: item.year || '',
            offset: String(offset)
        });
        const resp = await fetch(`/api/search?${params.toString()}`);
        const data = await resp.json();
        botUsername = data.bot_username || botUsername;
        files = files.concat(data.files || []);
        if (!data.next_offset) break;
        offset = data.next_offset;
    }
    return files;
}

function renderSeasonFiles(filesEl, files) {
    const seasons = new Map();
    files.forEach(file => {
        const key = Number.isInteger(file.season) ? file.season : 'other';
        if (!seasons.has(key)) seasons.set(key, []);
        seasons.get(key).push(file);
    });

    const keys = Array.from(seasons.keys()).sort((a, b) => {
        if (a === 'other') return 1;
        if (b === 'other') return -1;
        return a - b;
    });
    let active = keys[0];

    const strip = document.createElement('div');
    strip.className = 'season-strip';
    const panel = document.createElement('div');
    panel.className = 'episode-panel';

    function drawSeason(key, query='') {
        active = key;
        strip.querySelectorAll('.season-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.season === String(key));
        });
        let seasonFiles = [...seasons.get(key)].sort((a, b) => {
            const epA = Number.isInteger(a.episode) ? a.episode : 9999;
            const epB = Number.isInteger(b.episode) ? b.episode : 9999;
            return epA - epB || a.name.localeCompare(b.name);
        });
        // Filter by search query
        if (query) {
            const q = query.toLowerCase();
            seasonFiles = seasonFiles.filter(f =>
                f.name.toLowerCase().includes(q) ||
                (f.episode !== null && f.episode !== undefined && String(f.episode).includes(q))
            );
        }
        panel.innerHTML = `<div class="episode-kicker">${seasonFiles.length} file${seasonFiles.length === 1 ? '' : 's'}${query ? ' matching' : ''} in ${seasonLabel(key)}</div>`;
        if (seasonFiles.length === 0) {
            panel.innerHTML += `<div style="padding:20px;text-align:center;color:var(--text3);font-size:13px">No episodes match your search.</div>`;
        }
        seasonFiles.forEach(file => panel.appendChild(renderFileRow(file, true)));
        document.getElementById('fileSearchCount').textContent = query ? `${seasonFiles.length} result${seasonFiles.length === 1 ? '' : 's'}` : '';
    }

    keys.forEach(key => {
        const btn = document.createElement('button');
        btn.className = 'season-btn';
        btn.dataset.season = String(key);
        btn.textContent = `${seasonLabel(key)} (${seasons.get(key).length})`;
        btn.onclick = () => {
            const q = (document.getElementById('fileSearchInput').value || '').trim();
            drawSeason(key, q);
        };
        strip.appendChild(btn);
    });

    filesEl.innerHTML = '';
    filesEl.appendChild(strip);
    filesEl.appendChild(panel);
    drawSeason(active);

    // Wire up search for TV — filters episodes in current season
    const input = document.getElementById('fileSearchInput');
    input.oninput = () => {
        const q = input.value.trim();
        drawSeason(active, q);
    };
    // Clear filter chips for TV mode
    document.getElementById('fileFilterRow').innerHTML = '';
}

function extractFileMeta(files) {
    // Extract unique resolutions and languages from filenames
    const resRe = /\b(240p|360p|480p|576p|720p|1080p|1440p|2160p|4k|8k)\b/i;
    const langRe = /\b(hindi|english|tamil|telugu|malayalam|kannada|punjabi|bengali|marathi|urdu|korean|japanese|chinese|spanish|french|portuguese|italian|turkish|arabic|russian|german|dual[ ._-]?audio|multi[ ._-]?audio)\b/i;
    const resolutions = new Set();
    const languages  = new Set();
    files.forEach(f => {
        const rm = f.name.match(resRe);
        if (rm) resolutions.add(rm[1].toUpperCase());
        const lm = f.name.match(new RegExp(langRe.source, 'gi'));
        if (lm) lm.forEach(l => languages.add(l.charAt(0).toUpperCase() + l.slice(1).toLowerCase()));
    });
    return {
        resolutions: Array.from(resolutions).sort(),
        languages: Array.from(languages).sort()
    };
}

function renderMovieFiles(filesEl, files) {
    const meta = extractFileMeta(files);
    let activeFilters = new Set();
    let searchQuery = '';

    const filterRow = document.getElementById('fileFilterRow');
    const countEl   = document.getElementById('fileSearchCount');

    function buildChips() {
        filterRow.innerHTML = '';
        [...meta.resolutions, ...meta.languages].forEach(tag => {
            const chip = document.createElement('button');
            chip.className = 'file-filter-chip' + (activeFilters.has(tag) ? ' active' : '');
            chip.textContent = tag;
            chip.onclick = () => {
                if (activeFilters.has(tag)) activeFilters.delete(tag);
                else activeFilters.add(tag);
                buildChips();
                drawFiles();
            };
            filterRow.appendChild(chip);
        });
    }

    function drawFiles() {
        let filtered = files.filter(f => {
            const name = f.name.toLowerCase();
            // Text search
            if (searchQuery && !name.includes(searchQuery.toLowerCase())) return false;
            // Chip filters — all active chips must match
            for (const tag of activeFilters) {
                if (!name.toLowerCase().includes(tag.toLowerCase())) return false;
            }
            return true;
        });
        filesEl.innerHTML = '';
        countEl.textContent = (searchQuery || activeFilters.size) ? `${filtered.length} of ${files.length} files` : '';
        if (filtered.length === 0) {
            filesEl.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text3);font-size:13px">No files match your filter.</div>`;
        } else {
            filtered.forEach(file => filesEl.appendChild(renderFileRow(file)));
        }
    }

    buildChips();
    drawFiles();

    // Wire search input for movies
    const input = document.getElementById('fileSearchInput');
    input.oninput = () => {
        searchQuery = input.value.trim();
        drawFiles();
    };
}

async function loadFilesForItem(item) {
    const filesEl = document.getElementById('modalFiles');
    filesEl.innerHTML = `<div class="modal-loading"><div class="spinner"></div>Searching files...</div>`;
    // Reset search UI
    const searchInput = document.getElementById('fileSearchInput');
    const filterRow   = document.getElementById('fileFilterRow');
    const countEl     = document.getElementById('fileSearchCount');
    if (searchInput) { searchInput.value = ''; searchInput.oninput = null; }
    if (filterRow)   filterRow.innerHTML = '';
    if (countEl)     countEl.textContent = '';
    try {
        const files = await fetchFilesForItem(item);
        if (!files.length) {
            filesEl.innerHTML = `
                <div class="modal-empty">
                    <div class="modal-empty-icon">📭</div>
                    <div class="modal-empty-title">No files found</div>
                    <div class="modal-empty-sub">We don't have files for "<b>${escapeHTML(item.title)}</b>" yet. Request it in our group!</div>
                </div>`;
            return;
        }
        if (item.type === 'tv' || item.type === 'anime') {
            renderSeasonFiles(filesEl, files);
        } else {
            filesEl.innerHTML = '';
            renderMovieFiles(filesEl, files);
        }
    } catch(e) {
        filesEl.innerHTML = `<div class="modal-empty"><div class="modal-empty-icon">⚠️</div><div class="modal-empty-title">Error</div><div class="modal-empty-sub">Failed to load files.</div></div>`;
    }
}

function selectFile(file, el) {
    selectedFile = file;
    document.querySelectorAll('.file-item.selected').forEach(x => x.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('selectedFileName').textContent = `${file.name} (${file.size})`;
    document.getElementById('watchAction').href = `/api/stream-file/${file.id}`;
    document.getElementById('downloadAction').onclick = () => getFile(file.id);
    document.getElementById('fileActionBar').classList.add('show');
    showToast('File selected');
}

function hideFileActions() {
    document.getElementById('fileActionBar').classList.remove('show');
    document.getElementById('selectedFileName').textContent = '';
    document.getElementById('watchAction').removeAttribute('href');
}

function getFile(fileId) {
    const link = `https://t.me/${botUsername}?start=file_0_${fileId}`;
    if (userId === 'unknown' || !tg?.openTelegramLink) {
        window.open(link, '_blank');
    } else {
        tg.openTelegramLink(link);
        setTimeout(() => { tg.close(); }, 200);
    }
    showToast('Opening Telegram...');
}

// ── TOAST ─────────────────────────────────────────────────────────────────
function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// ── TODAY AIRING ──────────────────────────────────────────────────────────
let todayData = null;
let todayActiveTab = 'tv';

async function openTodayPanel() {
    document.getElementById('todayPanel').classList.add('open');
    document.body.style.overflow = 'hidden';
    if (!todayData) {
        await loadTodayAiring();
    } else {
        renderTodayTab(todayActiveTab);
    }
}

function closeTodayPanel() {
    document.getElementById('todayPanel').classList.remove('open');
    document.body.style.overflow = '';
}

function switchTodayTab(tab) {
    todayActiveTab = tab;
    document.querySelectorAll('.today-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    renderTodayTab(tab);
}

async function loadTodayAiring() {
    document.getElementById('todayList').innerHTML = `<div class="today-spinner"><div class="spinner"></div></div>`;
    try {
        const resp = await fetch('/api/today-airing');
        todayData = await resp.json();
        renderTodayTab(todayActiveTab);
    } catch(e) {
        document.getElementById('todayList').innerHTML = `<div class="today-empty">Could not load today's schedule. Try again later.</div>`;
    }
}

function renderTodayTab(tab) {
    const list = document.getElementById('todayList');
    const items = tab === 'anime' ? (todayData?.anime || []) : (todayData?.tv || []);
    if (!items.length) {
        list.innerHTML = `<div class="today-empty">No ${tab === 'anime' ? 'anime' : 'TV shows'} airing today.</div>`;
        return;
    }
    list.innerHTML = '';
    items.forEach(item => {
        const el = document.createElement('div');
        el.className = 'today-item';
        const thumb = item.poster
            ? `<img class="today-thumb" src="${escapeHTML(item.poster)}" alt="${escapeHTML(item.title)}" loading="lazy" onerror="imgErrorThumb(this)">`
              + `<div class="today-thumb-placeholder" style="display:none">🎬</div>`
            : `<div class="today-thumb-placeholder">🎬</div>`;

        // Episode badge
        let epBadge = '';
        if (item.season && item.episode) {
            epBadge = `<div class="today-ep-badge">S${String(item.season).padStart(2,'0')} E${String(item.episode).padStart(2,'0')}${item.episode_name ? ' · ' + escapeHTML(item.episode_name.slice(0,30)) : ''}</div>`;
        } else if (item.episode) {
            epBadge = `<div class="today-ep-badge">Ep ${item.episode}${item.episode_name ? ' · ' + escapeHTML(item.episode_name.slice(0,30)) : ''}</div>`;
        }

        // Source chips
        const chips = [];
        if (item.imdb_id)  chips.push(`<span class="today-source-chip chip-imdb">IMDb</span>`);
        if (item.tvdb_id)  chips.push(`<span class="today-source-chip chip-tvdb">TVDB</span>`);
        if (item.tmdb_id)  chips.push(`<span class="today-source-chip chip-tmdb">TMDB</span>`);
        if (item.mal_id)   chips.push(`<span class="today-source-chip chip-mal">MAL</span>`);

        el.innerHTML = `
            ${thumb}
            <div class="today-info">
                <div class="today-item-title">${escapeHTML(item.title)}</div>
                ${epBadge}
                <div class="today-meta-row">
                    ${item.rating ? `<span class="today-rating">⭐ ${item.rating}</span>` : ''}
                    ${item.network ? `<span class="today-network">${escapeHTML(item.network)}</span>` : ''}
                    ${chips.join('')}
                </div>
            </div>
        `;
        el.onclick = () => {
            closeTodayPanel();
            openModal({
                id: item.tmdb_id || item.mal_id,
                source: item.mal_id && !item.tmdb_id ? 'mal' : 'tmdb',
                title: item.title,
                type: item.type || tab,
                year: item.year || '',
                rating: item.rating || 0,
                poster: item.poster || null,
                overview: item.overview || ''
            });
        };
        list.appendChild(el);
    });
}

// ── BOOT ──────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', loadHome);
</script>
</body>
</html>
"""

# ── NO TMDB KEY PAGE ──────────────────────────────────────────────────────
no_tmdb_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebApp Unavailable</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { box-sizing:border-box; margin:0; padding:0; }
        body {
            font-family:'Outfit',sans-serif; background:#0a0a0f; color:#fff;
            min-height:100vh; display:flex; align-items:center; justify-content:center;
            padding:30px 24px; text-align:center;
            background-image: radial-gradient(ellipse at 50% 0%, rgba(229,9,20,0.08) 0%, transparent 60%);
        }
        .wrap { max-width:380px; }
        .icon {
            width:90px; height:90px; border-radius:24px; margin:0 auto 28px;
            background:linear-gradient(135deg,#1a1a2e,#16213e);
            border:1px solid rgba(229,9,20,0.3);
            display:flex; align-items:center; justify-content:center; font-size:40px;
            box-shadow: 0 0 40px rgba(229,9,20,0.1);
        }
        h1 { font-size:26px; font-weight:800; margin-bottom:12px; letter-spacing:-0.5px; }
        p { font-size:15px; color:#888; line-height:1.7; }
        code {
            display:inline-block; background:#1e1e2a; color:#e50914;
            padding:3px 10px; border-radius:6px; font-size:14px;
            border:1px solid rgba(229,9,20,0.25); margin:4px 0;
            font-family:monospace;
        }
        .divider {
            width:60px; height:2px; background:linear-gradient(90deg,transparent,#e50914,transparent);
            margin:24px auto;
        }
        .note { font-size:12px; color:#444; margin-top:16px; }
    </style>
</head>
<body>
<div class="wrap">
    <div class="icon">🔑</div>
    <h1>WebApp Unavailable</h1>
    <div class="divider"></div>
    <p>The WebApp requires a <b>TMDB API Key</b> to function.</p>
    <p style="margin-top:12px">If you're an admin, set the environment variable:</p>
    <p style="margin-top:10px"><code>TMDB_API_KEY</code></p>
    <p style="margin-top:14px; color:#555">Get your free API key at<br><span style="color:#e50914">themoviedb.org/settings/api</span></p>
    <div class="note">This message is only shown when the key is not configured.</div>
</div>
<script>
    const tg = window.Telegram?.WebApp;
    if (tg) { tg.expand(); tg.setBackgroundColor('#0a0a0f'); }
</script>
</body>
</html>
"""
# ─────────────────────────────────────────────────────────────────────────────
# WATCH PAGE TEMPLATE  (route: /watch/{id})
# ─────────────────────────────────────────────────────────────────────────────
watch_tmplt = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css">
    <style>
        .plyr__progress, .plyr__volume { --plyr-color-main: #e50914; }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: #0a0a0a; color: #e5e5e5;
            font-family: 'Poppins', 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh; display: flex; flex-direction: column;
            -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
            animation: fadeIn 0.3s ease-out both;
        }

        @keyframes fadeIn   { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp  { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideDown{ from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes scaleIn  { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }
        @keyframes popIn    { 0% { opacity: 0; transform: scale(0.85); } 70% { transform: scale(1.03); } 100% { opacity: 1; transform: scale(1); } }
        @keyframes shimmer  { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
        @keyframes glowPulse{ 0%,100% { box-shadow: 0 0 0 0 rgba(229,9,20,0); } 50% { box-shadow: 0 0 8px 2px rgba(229,9,20,0.25); } }
        @keyframes tabSlideIn { from { opacity: 0; transform: translateX(8px); } to { opacity: 1; transform: translateX(0); } }

        .header {
            background: #141414; padding: 14px 20px;
            display: flex; align-items: center; gap: 12px;
            animation: slideDown 0.25s ease-out both;
        }
        .header-icon {
            width: 32px; height: 32px; background: #e50914; border-radius: 8px;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
            transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1);
        }
        .header-icon:hover { transform: scale(1.1) rotate(-3deg); }
        .header-icon svg { width: 18px; height: 18px; fill: white; transition: transform 0.2s ease; }
        .header-icon:hover svg { transform: scale(1.15); }
        .file-name {
            font-size: clamp(0.85rem, 2.5vw, 1rem); font-weight: 500; color: #ffffff;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0;
        }
        .telegram-logo-link {
            width: 38px; height: 38px; background: #24a1de; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
            transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), background-color 0.2s ease, box-shadow 0.2s ease;
            text-decoration: none; box-shadow: 0 2px 10px rgba(36,161,222,0.3);
            animation: popIn 0.3s ease-out both; animation-delay: 0.1s;
        }
        .telegram-logo-link:hover { transform: scale(1.12) rotate(-5deg); background-color: #2cb3f2; box-shadow: 0 4px 15px rgba(36,161,222,0.55); }
        .telegram-logo-link svg { width: 22px; height: 22px; fill: white; transition: transform 0.2s ease; }
        .telegram-logo-link:hover svg { transform: scale(1.08); }

        .player-wrapper { flex: 1; display: flex; align-items: flex-start; justify-content: center; padding: clamp(8px,1.5vw,16px) clamp(12px,3vw,32px); }
        .player-resizable-wrapper {
            position: relative; padding: 8px; box-sizing: border-box;
            width: 70vw; max-width: 1400px; margin: 0 auto;
            animation: scaleIn 0.35s cubic-bezier(0.22,1,0.36,1) both; animation-delay: 0.08s;
        }
        .player-container {
            width: 100%; height: 100%; border-radius: 10px; overflow: hidden;
            box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05);
            display: flex; flex-direction: column;
        }
        .player-container .plyr { height: 100% !important; width: 100% !important; flex: 1; }
        .player-container video {
            max-width: 100% !important; max-height: 100% !important;
            width: var(--video-width, 100%) !important; height: var(--video-height, 100%) !important;
            object-fit: var(--video-object-fit, contain) !important;
            aspect-ratio: var(--video-aspect-ratio, auto) !important; margin: auto;
        }

        .resize-handle { position: absolute; z-index: 100; user-select: none; transition: background 0.2s ease, box-shadow 0.2s ease; touch-action: none; }
        .resize-handle.handle-n { top:0;left:8px;right:8px;height:8px;cursor:ns-resize; }
        .resize-handle.handle-s { bottom:0;left:8px;right:8px;height:8px;cursor:ns-resize; }
        .resize-handle.handle-w { left:0;top:8px;bottom:8px;width:8px;cursor:ew-resize; }
        .resize-handle.handle-e { right:0;top:8px;bottom:8px;width:8px;cursor:ew-resize; }
        .resize-handle.handle-nw { top:0;left:0;width:10px;height:10px;cursor:nwse-resize; }
        .resize-handle.handle-ne { top:0;right:0;width:10px;height:10px;cursor:nesw-resize; }
        .resize-handle.handle-sw { bottom:0;left:0;width:10px;height:10px;cursor:nesw-resize; }
        .resize-handle.handle-se { bottom:0;right:0;width:10px;height:10px;cursor:nwse-resize; }
        .resize-handle:hover, .player-resizable-wrapper.resizing .active-handle { background: rgba(229,9,20,0.4); box-shadow: 0 0 8px rgba(229,9,20,0.6); }

        .below-player { width: 70vw; max-width: 1400px; margin: 0 auto; padding: 0 clamp(12px,3vw,32px) clamp(16px,3vw,32px); }

        .action-row { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; animation: slideUp 0.3s ease-out both; animation-delay: 0.2s; }
        .action-btn {
            flex: 1; min-width: 120px; display: inline-flex; align-items: center; justify-content: center;
            gap: 8px; padding: 11px 16px; background: #141414; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; color: #ccc; font-family: inherit; font-size: 0.82rem; font-weight: 500;
            cursor: pointer; position: relative; overflow: hidden;
            transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), background 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
            text-decoration: none;
        }
        .action-btn::after { content:''; position:absolute; inset:0; background: radial-gradient(circle at var(--ripple-x,50%) var(--ripple-y,50%), rgba(255,255,255,0.15) 0%, transparent 60%); opacity:0; transition: opacity 0.3s ease; pointer-events: none; }
        .action-btn:active::after { opacity: 1; }
        .action-btn:hover { transform: translateY(-2px); background: #1a1a1a; border-color: rgba(229,9,20,0.3); color: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .action-btn:active { transform: scale(0.96); }
        .action-btn svg { width: 16px; height: 16px; fill: currentColor; flex-shrink: 0; transition: transform 0.2s ease; }
        .action-btn:hover svg { transform: scale(1.1); }
        .action-btn.primary {
            background: linear-gradient(135deg, #e50914 0%, #b20710 100%);
            border-color: transparent; color: #fff; box-shadow: 0 2px 16px rgba(229,9,20,0.35);
        }
        .action-btn.primary::before { content:''; position:absolute; inset:0; background: linear-gradient(90deg,transparent 0%,rgba(255,255,255,0.15) 50%,transparent 100%); background-size:200% 100%; animation: shimmer 2.5s ease-in-out infinite; pointer-events:none; }
        .action-btn.primary:hover { box-shadow: 0 6px 24px rgba(229,9,20,0.5); }
        .action-btn.copied { background: #1a3a1a; border-color: rgba(34,197,94,0.4); color: #22c55e; }

        .openin-card { background: #141414; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; overflow: hidden; animation: slideUp 0.3s ease-out both; animation-delay: 0.3s; }
        .openin-header { padding: 14px 20px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .openin-header svg { width: 18px; height: 18px; fill: #e50914; }
        .openin-title { font-size: 0.9rem; color: #ccc; font-weight: 500; }
        .openin-tabs { display: flex; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .openin-tab { flex:1; padding:10px 16px; background:none; border:none; color:#666; font-family:inherit; font-size:0.8rem; font-weight:500; cursor:pointer; position:relative; transition: color 0.2s ease, background 0.2s ease; }
        .openin-tab:hover { color: #aaa; background: rgba(255,255,255,0.03); }
        .openin-tab.active { color: #e50914; }
        .openin-tab.active::after { content:''; position:absolute; bottom:0; left:16px; right:16px; height:2px; background:#e50914; border-radius:2px 2px 0 0; animation: glowPulse 2s ease-in-out infinite; }
        .openin-content { display: none; padding: 14px; }
        .openin-content.active { display: block; animation: tabSlideIn 0.2s ease-out both; }
        .player-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
        .player-btn {
            display: flex; align-items: center; gap: 10px; padding: 10px 14px;
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px; color: #bbb; font-family: inherit; font-size: 0.78rem;
            font-weight: 500; cursor: pointer; text-decoration: none;
            transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), background 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
            animation: popIn 0.3s ease-out both;
        }
        .player-btn:hover { transform: translateY(-3px) scale(1.02); background: rgba(229,9,20,0.1); border-color: rgba(229,9,20,0.35); color: #fff; box-shadow: 0 6px 20px rgba(229,9,20,0.15); }
        .player-btn:active { transform: scale(0.96); }
        .player-btn .p-icon { width:28px;height:28px;border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1rem;font-weight:700;transition:transform 0.2s cubic-bezier(0.34,1.56,0.64,1); }
        .player-btn:hover .p-icon { transform: scale(1.15) rotate(-3deg); }
        .player-btn .p-icon.vlc { background:#ff6600;color:#fff; }
        .player-btn .p-icon.pot { background:#4a90d9;color:#fff; }
        .player-btn .p-icon.mpv { background:#555;color:#fff; }
        .player-btn .p-icon.kmp { background:#8b5cf6;color:#fff; }
        .player-btn .p-icon.mpc { background:#3b82f6;color:#fff; }
        .player-btn .p-icon.mx  { background:#00bcd4;color:#fff; }
        .player-btn .p-icon.np  { background:#4caf50;color:#fff; }
        .player-btn .p-icon.infuse { background:#f59e0b;color:#fff; }
        .player-btn .p-icon.iina { background:#1a1a2e;color:#e50914; }
        .player-btn .p-icon.sp  { background:#ff4081;color:#fff; }
        .player-btn .p-icon.nxt { background:#009688;color:#fff; }
        .player-btn .p-icon.nova{ background:#673ab7;color:#fff; }
        .player-btn .p-icon.jp  { background:#607d8b;color:#fff; }

        footer {
            background: #141414; border-top: 1px solid rgba(255,255,255,0.06);
            padding: 12px 20px; text-align: center; font-size: 0.75rem; color: #555;
            letter-spacing: 0.3px; animation: slideUp 0.25s ease-out both; animation-delay: 0.4s; margin-top: auto;
        }
        footer a { color: #e50914; text-decoration: none; transition: color 0.2s ease, text-shadow 0.2s ease; }
        footer a:hover { color: #ff3d47; text-shadow: 0 0 8px rgba(229,9,20,0.4); }

        /* ── Custom Audio Track Selector ── */
        .plyr__audio-selector { position: relative; display: inline-block; }
        .plyr__audio-btn { background:transparent;border:0;border-radius:4px;color:#dbdbdb;cursor:pointer;padding:7px;transition:background 0.3s ease,color 0.3s ease;display:flex;align-items:center;justify-content:center;width:32px;height:32px; }
        .plyr__audio-btn:hover { background:rgba(255,255,255,0.1);color:#fff; }
        .plyr__audio-btn svg { width:18px;height:18px;fill:currentColor; }
        .plyr__audio-dropdown { position:absolute;bottom:45px;left:50%;transform:translateX(-50%) translateY(10px);background:rgba(20,20,20,0.95);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.08);border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,0.5);width:260px;max-height:250px;overflow-y:auto;z-index:10;opacity:0;pointer-events:none;transition:opacity 0.2s ease,transform 0.2s ease; }
        .plyr__audio-dropdown.show { opacity:1;pointer-events:auto;transform:translateX(-50%) translateY(0); }
        .plyr__audio-option { display:block;width:100%;padding:10px 14px;background:transparent;border:0;color:#ccc;font-family:inherit;font-size:12px;text-align:left;cursor:pointer;transition:background 0.2s ease,color 0.2s ease;border-bottom:1px solid rgba(255,255,255,0.03);white-space:normal;word-break:break-word; }
        .plyr__audio-option:last-child { border-bottom:0; }
        .plyr__audio-option:hover { background:rgba(255,255,255,0.05);color:#fff; }
        .plyr__audio-option.active { background:rgba(229,9,20,0.15);color:#e50914;font-weight:500; }

        /* ── Custom Subtitle Selector ── */
        .plyr__sub-selector { position: relative; display: inline-block; }
        .plyr__sub-btn { background:transparent;border:0;border-radius:4px;color:#dbdbdb;cursor:pointer;padding:7px;transition:background 0.3s ease,color 0.3s ease;display:flex;align-items:center;justify-content:center;width:32px;height:32px; }
        .plyr__sub-btn:hover { background:rgba(255,255,255,0.1);color:#fff; }
        .plyr__sub-btn svg { width:18px;height:18px;fill:currentColor; }
        .plyr__sub-dropdown { position:absolute;bottom:45px;left:50%;transform:translateX(-50%) translateY(10px);background:rgba(20,20,20,0.95);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.08);border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,0.5);width:260px;max-height:250px;overflow-y:auto;z-index:10;opacity:0;pointer-events:none;transition:opacity 0.2s ease,transform 0.2s ease; }
        .plyr__sub-dropdown.show { opacity:1;pointer-events:auto;transform:translateX(-50%) translateY(0); }
        .plyr__sub-option { display:block;width:100%;padding:10px 14px;background:transparent;border:0;color:#ccc;font-family:inherit;font-size:12px;text-align:left;cursor:pointer;transition:background 0.2s ease,color 0.2s ease;border-bottom:1px solid rgba(255,255,255,0.03);white-space:normal;word-break:break-word; }
        .plyr__sub-option:last-child { border-bottom:0; }
        .plyr__sub-option:hover { background:rgba(255,255,255,0.05);color:#fff; }
        .plyr__sub-option.active { background:rgba(229,9,20,0.15);color:#e50914;font-weight:500; }

        /* ── Custom Aspect Ratio Selector ── */
        .plyr__aspect-selector { position: relative; display: inline-block; }
        .plyr__aspect-btn { background:transparent;border:0;border-radius:4px;color:#dbdbdb;cursor:pointer;padding:7px;transition:background 0.3s ease,color 0.3s ease;display:flex;align-items:center;justify-content:center;width:32px;height:32px; }
        .plyr__aspect-btn:hover { background:rgba(255,255,255,0.1);color:#fff; }
        .plyr__aspect-btn svg { width:18px;height:18px;fill:currentColor; }
        .plyr__aspect-dropdown { position:absolute;bottom:45px;left:50%;transform:translateX(-50%) translateY(10px);background:rgba(20,20,20,0.95);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.08);border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,0.5);width:180px;max-height:250px;overflow-y:auto;z-index:10;opacity:0;pointer-events:none;transition:opacity 0.2s ease,transform 0.2s ease; }
        .plyr__aspect-dropdown.show { opacity:1;pointer-events:auto;transform:translateX(-50%) translateY(0); }
        .plyr__aspect-option { display:block;width:100%;padding:10px 14px;background:transparent;border:0;color:#ccc;font-family:inherit;font-size:12px;text-align:left;cursor:pointer;transition:background 0.2s ease,color 0.2s ease;border-bottom:1px solid rgba(255,255,255,0.03);white-space:normal;word-break:break-word; }
        .plyr__aspect-option:last-child { border-bottom:0; }
        .plyr__aspect-option:hover { background:rgba(255,255,255,0.05);color:#fff; }
        .plyr__aspect-option.active { background:rgba(229,9,20,0.15);color:#e50914;font-weight:500; }

        @media (max-width: 768px) {
            .player-wrapper { padding: 0; flex: none; }
            .player-resizable-wrapper { width: 100%; max-width: 100%; height: auto; padding: 10px; }
            .player-container { width: 100%; height: 100%; border-radius: 0; }
            .resize-handle.handle-n,.resize-handle.handle-s { height:12px; }
            .resize-handle.handle-w,.resize-handle.handle-e { width:12px; }
            .resize-handle.handle-nw,.resize-handle.handle-ne,.resize-handle.handle-sw,.resize-handle.handle-se { width:16px;height:16px; }
            .plyr { border-radius: 0; }
            .plyr__control { padding: 10px !important; }
            .plyr__volume input[type="range"] { display: none !important; }
            .plyr__control[data-plyr="download"],.plyr__control[data-plyr="pip"],.plyr__control[data-plyr="airplay"] { display: none !important; }
            .header { padding: 10px 12px; gap: 8px; }
            .file-name { font-size: 0.8rem; }
            .telegram-logo-link { width: 32px; height: 32px; }
            .telegram-logo-link svg { width: 18px; height: 18px; }
            .below-player { width: 100%; padding: 12px 12px 16px; }
            .action-row { gap: 8px; }
            .action-btn { min-width: 100px; padding: 10px 12px; font-size: 0.78rem; }
            .player-grid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 6px; }
            .player-btn { padding: 8px 10px; font-size: 0.75rem; }
            .player-btn .p-icon { width: 24px; height: 24px; font-size: 0.85rem; }
        }
        @media (max-width: 480px) {
            .header { padding: 8px 10px; }
            .player-container { border-radius: 0; }
            .plyr { border-radius: 0; }
            .plyr__controls { padding: 6px !important; }
            .plyr__control { padding: 6px !important; }
            .plyr__control[data-plyr="rewind"],.plyr__control[data-plyr="fast-forward"] { display: none !important; }
            .plyr__time { font-size: 10px !important; }
            .plyr__controls > * { margin-left: 2px !important; }
            .plyr__controls > *:first-child { margin-left: 0 !important; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-icon">
            <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </div>
        <div class="file-name">{file_name}</div>
        <a class="telegram-logo-link" href="https://t.me/FT_Channels" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.87-2.11 5.85-2.52 2.78-1.16 3.36-1.36 3.74-1.36.08 0 .27.02.39.12.1.08.13.19.14.27.01.06.01.24 0 .24z"/></svg>
        </a>
    </div>

    <div class="player-wrapper">
        <div class="player-resizable-wrapper">
            <div class="player-container">
                <video src="{src}" class="player" crossorigin="anonymous" playsinline preload="metadata"></video>
            </div>
            <div class="resize-handle handle-n"></div>
            <div class="resize-handle handle-s"></div>
            <div class="resize-handle handle-e"></div>
            <div class="resize-handle handle-w"></div>
            <div class="resize-handle handle-nw"></div>
            <div class="resize-handle handle-ne"></div>
            <div class="resize-handle handle-sw"></div>
            <div class="resize-handle handle-se"></div>
        </div>
    </div>

    <div class="below-player">
        <div class="action-row">
            <a class="action-btn primary" id="dl-btn" href="{src}" download>
                <svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                Download
            </a>
            <button class="action-btn" id="copy-btn" onclick="copyLink()">
                <svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                Copy Link
            </button>
            <button class="action-btn" id="reset-size-btn" onclick="resetPlayerSize()" style="display:none">
                <svg viewBox="0 0 24 24"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/></svg>
                Reset Size
            </button>
        </div>

        <div class="openin-card">
            <div class="openin-header">
                <svg viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
                <span class="openin-title">Open in External Player</span>
            </div>
            <div class="openin-tabs">
                <button class="openin-tab active" onclick="switchTab(this, 'desktop')">Desktop</button>
                <button class="openin-tab" onclick="switchTab(this, 'mobile')">Android</button>
                <button class="openin-tab" onclick="switchTab(this, 'ios')">iOS</button>
            </div>
            <div class="openin-content active" id="tab-desktop">
                <div class="player-grid" id="grid-desktop"></div>
            </div>
            <div class="openin-content" id="tab-mobile">
                <div class="player-grid" id="grid-mobile"></div>
            </div>
            <div class="openin-content" id="tab-ios">
                <div class="player-grid" id="grid-ios"></div>
            </div>
        </div>
    </div>

    <footer>Powered by <a href="https://t.me/FT_Channels" target="_blank" rel="noopener">Filmotainment</a></footer>

    <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
    <script>
        var STREAM_URL = '{src}';
        var FILE_NAME  = '{file_name}';
        var MSG_ID     = '{message_id}';

        var player;
        var fetchedTracks = null;
        var currentAudioIdx = 0;
        var currentSubIdx   = 'off';

        /* ── Plyr init ── */
        document.addEventListener('DOMContentLoaded', function() {
            player = new Plyr('.player', {
                controls: [
                    'play-large','rewind','play','fast-forward',
                    'progress','current-time','duration',
                    'mute','volume',
                    'settings','pip','airplay','download','fullscreen'
                ],
                settings: ['captions','speed','loop'],
                speed: { selected:1, options:[0.25,0.5,0.75,1,1.25,1.5,1.75,2] },
                seekTime: 10,
                tooltips: { controls:true, seek:true },
                keyboard: { focused:true, global:true },
                invertTime: false,
                toggleInvert: false,
                fullscreen: { enabled:true, fallback:true, iosNative:true },
                storage: { enabled:true, key:'plyr' }
            });

            /* ── Keyboard shortcuts ── */
            document.addEventListener('keydown', function(e) {
                if (e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA') return;
                switch(e.key.toLowerCase()) {
                    case 'k': case ' ': e.preventDefault(); player.playing?player.pause():player.play(); break;
                    case 'j': e.preventDefault(); player.rewind(); break;
                    case 'l': e.preventDefault(); player.forward(); break;
                    case 'm': e.preventDefault(); player.muted=!player.muted; break;
                    case 'f': e.preventDefault(); player.fullscreen.toggle(); break;
                    case 'arrowleft':  e.preventDefault(); player.currentTime-=5; break;
                    case 'arrowright': e.preventDefault(); player.currentTime+=5; break;
                    case 'arrowup':    e.preventDefault(); player.volume=Math.min(1,player.volume+0.05); break;
                    case 'arrowdown':  e.preventDefault(); player.volume=Math.max(0,player.volume-0.05); break;
                    case '0':case '1':case '2':case '3':case '4':
                    case '5':case '6':case '7':case '8':case '9':
                        e.preventDefault(); player.currentTime=player.duration*(parseInt(e.key)/10); break;
                }
            });

            player.on('ready', function() {
                tryInsertAudioSelector();
                tryInsertSubSelector();
                tryInsertAspectSelector();
            });

            /* ── Fetch audio + subtitle tracks ── */
            fetch('/api/tracks/' + MSG_ID)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var audio = data.audio || [];
                    var subs  = data.subtitles || [];
                    if (audio.length > 0 || subs.length > 0) {
                        fetchedTracks = { audio: audio, subtitles: subs };
                        tryInsertAudioSelector();
                        tryInsertSubSelector();
                    }
                })
                .catch(function(err) { console.error('Track fetch failed:', err); });

            /* ── Auto-rotate to landscape on fullscreen (mobile) ── */
            player.on('enterfullscreen', function() {
                try { if (screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(function(){}); } catch(e){}
            });
            player.on('exitfullscreen', function() {
                try { if (screen.orientation && screen.orientation.unlock) screen.orientation.unlock(); } catch(e){}
            });

            initResizing();
        });

        /* ── Language map for track labels ── */
        var LANG_MAP = {
            eng:'English',en:'English',hin:'Hindi',hi:'Hindi',
            tam:'Tamil',ta:'Tamil',tel:'Telugu',te:'Telugu',
            mal:'Malayalam',ml:'Malayalam',kan:'Kannada',kn:'Kannada',
            ben:'Bengali',bn:'Bengali',pan:'Punjabi',pa:'Punjabi',
            guj:'Gujarati',gu:'Gujarati',mar:'Marathi',mr:'Marathi',
            fre:'French',fra:'French',fr:'French',spa:'Spanish',es:'Spanish',
            ger:'German',deu:'German',de:'German',rus:'Russian',ru:'Russian',
            chi:'Chinese',zho:'Chinese',zh:'Chinese',jpn:'Japanese',ja:'Japanese',
            kor:'Korean',ko:'Korean',ara:'Arabic',ar:'Arabic',
            por:'Portuguese',pt:'Portuguese',ita:'Italian',it:'Italian',
            tur:'Turkish',tr:'Turkish',dut:'Dutch',nld:'Dutch',nl:'Dutch'
        };

        function resolveTrackLabel(track, idx) {
            var lang = (track.language || '').toLowerCase().trim();
            var label = track.label || '';
            var name = LANG_MAP[lang] || '';
            if (name) {
                return idx === 0 ? name + ' (Default)' : name;
            }
            if (label) return label;
            return idx === 0 ? 'Default' : 'Track ' + (idx + 1);
        }

        /* ── Audio Track Selector (in Plyr controls) ── */
        function tryInsertAudioSelector() {
            if (!fetchedTracks || fetchedTracks.audio.length < 2) return;
            var plyr = document.querySelector('.plyr');
            if (!plyr || plyr.querySelector('.plyr__audio-selector')) return;
            var volCtrl = plyr.querySelector('.plyr__volume');
            if (!volCtrl) return;

            var wrapper = document.createElement('div');
            wrapper.className = 'plyr__audio-selector';
            var btn = document.createElement('button');
            btn.className = 'plyr__audio-btn'; btn.type = 'button'; btn.title = 'Audio Tracks';
            btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>';
            var dropdown = document.createElement('div');
            dropdown.className = 'plyr__audio-dropdown';

            wrapper.appendChild(btn);
            wrapper.appendChild(dropdown);

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                closeAllDropdowns(dropdown);
                dropdown.classList.toggle('show');
            });
            document.addEventListener('click', function() { dropdown.classList.remove('show'); });

            fetchedTracks.audio.forEach(function(track, idx) {
                var opt = document.createElement('button');
                opt.className = 'plyr__audio-option' + (idx === 0 ? ' active' : '');
                opt.textContent = resolveTrackLabel(track, idx);
                opt.addEventListener('click', function() {
                    dropdown.querySelectorAll('.plyr__audio-option').forEach(function(o) { o.classList.remove('active'); });
                    opt.classList.add('active');
                    dropdown.classList.remove('show');
                    switchAudioTrack(idx);
                });
                dropdown.appendChild(opt);
            });

            volCtrl.parentNode.insertBefore(wrapper, volCtrl.nextSibling);
        }

        /* ── Subtitle Selector (in Plyr controls) ── */
        function tryInsertSubSelector() {
            if (!fetchedTracks || fetchedTracks.subtitles.length < 1) return;
            var plyr = document.querySelector('.plyr');
            if (!plyr || plyr.querySelector('.plyr__sub-selector')) return;
            var audioSel = plyr.querySelector('.plyr__audio-selector');
            var volCtrl = plyr.querySelector('.plyr__volume');
            var insertAfter = audioSel || volCtrl;
            if (!insertAfter) return;

            var wrapper = document.createElement('div');
            wrapper.className = 'plyr__sub-selector';
            var btn = document.createElement('button');
            btn.className = 'plyr__sub-btn'; btn.type = 'button'; btn.title = 'Subtitles';
            btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM6 10h2v2H6v-2zm0 4h8v2H6v-2zm10 0h2v2h-2v-2zm-6-4h8v2h-8v-2z"/></svg>';
            var dropdown = document.createElement('div');
            dropdown.className = 'plyr__sub-dropdown';

            wrapper.appendChild(btn);
            wrapper.appendChild(dropdown);

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                closeAllDropdowns(dropdown);
                dropdown.classList.toggle('show');
            });
            document.addEventListener('click', function() { dropdown.classList.remove('show'); });

            /* Off option */
            var offOpt = document.createElement('button');
            offOpt.className = 'plyr__sub-option active';
            offOpt.textContent = 'Off';
            offOpt.addEventListener('click', function() {
                dropdown.querySelectorAll('.plyr__sub-option').forEach(function(o) { o.classList.remove('active'); });
                offOpt.classList.add('active');
                dropdown.classList.remove('show');
                switchSubTrack('off');
            });
            dropdown.appendChild(offOpt);

            fetchedTracks.subtitles.forEach(function(track, idx) {
                var opt = document.createElement('button');
                opt.className = 'plyr__sub-option';
                opt.textContent = resolveTrackLabel(track, idx);
                opt.addEventListener('click', function() {
                    dropdown.querySelectorAll('.plyr__sub-option').forEach(function(o) { o.classList.remove('active'); });
                    opt.classList.add('active');
                    dropdown.classList.remove('show');
                    switchSubTrack(idx);
                });
                dropdown.appendChild(opt);
            });

            insertAfter.parentNode.insertBefore(wrapper, insertAfter.nextSibling);
        }

        /* ── Audio track switching (source reload with ?audio=N) ── */
        function switchAudioTrack(idx) {
            if (idx === currentAudioIdx) return;
            currentAudioIdx = idx;
            var ct = player.currentTime;
            var wp = player.playing;
            var newSrc = STREAM_URL + '?audio=' + idx;
            if (currentSubIdx !== 'off') newSrc += '&sub=' + currentSubIdx;
            player.source = { type:'video', sources:[{ src:newSrc, type:'{mime_type}' }] };
            player.once('loadedmetadata', function() {
                player.currentTime = ct;
                if (wp) player.play();
            });
        }

        /* ── Subtitle track switching ── */
        function switchSubTrack(idx) {
            currentSubIdx = idx;
            if (idx === 'off' && currentAudioIdx === 0) {
                var ct = player.currentTime;
                var wp = player.playing;
                player.source = { type:'video', sources:[{ src:STREAM_URL, type:'{mime_type}' }] };
                player.once('loadedmetadata', function() {
                    player.currentTime = ct;
                    if (wp) player.play();
                });
                return;
            }
            var ct2 = player.currentTime;
            var wp2 = player.playing;
            var newSrc = STREAM_URL + '?audio=' + currentAudioIdx;
            if (idx !== 'off') newSrc += '&sub=' + idx;
            player.source = { type:'video', sources:[{ src:newSrc, type:'{mime_type}' }] };
            player.once('loadedmetadata', function() {
                player.currentTime = ct2;
                if (wp2) player.play();
            });
        }

        /* ── Aspect Ratio Selector ── */
        var activeAspect = 'fit';
        var aspectModes = [
            { id:'fit',     label:'Fit (Default)',    width:'100%',height:'100%',fit:'contain',ratio:'auto' },
            { id:'stretch', label:'Stretch',          width:'100%',height:'100%',fit:'fill',   ratio:'auto' },
            { id:'zoom',    label:'Zoom / Crop',      width:'100%',height:'100%',fit:'cover',  ratio:'auto' },
            { id:'16-9',    label:'16:9 Widescreen',  width:'auto',height:'auto',fit:'fill',   ratio:'16/9' },
            { id:'9-16',    label:'9:16 Vertical',    width:'auto',height:'auto',fit:'fill',   ratio:'9/16' },
            { id:'4-3',     label:'4:3 Standard',     width:'auto',height:'auto',fit:'fill',   ratio:'4/3' },
            { id:'1-1',     label:'1:1 Square',       width:'auto',height:'auto',fit:'fill',   ratio:'1/1' },
            { id:'21-9',    label:'21:9 Widescreen',  width:'auto',height:'auto',fit:'fill',   ratio:'21/9' },
            { id:'2.35-1',  label:'2.35:1 Cinema',    width:'auto',height:'auto',fit:'fill',   ratio:'2.35/1' },
            { id:'4-5',     label:'4:5 Portrait',     width:'auto',height:'auto',fit:'fill',   ratio:'4/5' }
        ];

        function tryInsertAspectSelector() {
            var plyr = document.querySelector('.plyr');
            if (!plyr || plyr.querySelector('.plyr__aspect-selector')) return;
            var volCtrl = plyr.querySelector('.plyr__volume');
            if (!volCtrl) return;

            var wrapper = document.createElement('div');
            wrapper.className = 'plyr__aspect-selector';
            var btn = document.createElement('button');
            btn.className = 'plyr__aspect-btn'; btn.type = 'button'; btn.title = 'Aspect Ratio';
            btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M19 12h-2v3h-3v2h5v-5zM7 9h3V7H5v5h2V9zm14-6H3c-1.1 0-2 .9-2 2v14c0 1.1.89 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"/></svg>';
            var dropdown = document.createElement('div');
            dropdown.className = 'plyr__aspect-dropdown';

            wrapper.appendChild(btn);
            wrapper.appendChild(dropdown);

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                closeAllDropdowns(dropdown);
                dropdown.classList.toggle('show');
            });
            document.addEventListener('click', function() { dropdown.classList.remove('show'); });

            aspectModes.forEach(function(mode) {
                var opt = document.createElement('button');
                opt.className = 'plyr__aspect-option' + (mode.id === activeAspect ? ' active' : '');
                opt.textContent = mode.label;
                opt.addEventListener('click', function() {
                    dropdown.querySelectorAll('.plyr__aspect-option').forEach(function(o) { o.classList.remove('active'); });
                    opt.classList.add('active');
                    dropdown.classList.remove('show');
                    setAspectRatio(mode.id);
                });
                dropdown.appendChild(opt);
            });

            /* Insert after subtitle or audio selector, or volume */
            var subSel = plyr.querySelector('.plyr__sub-selector');
            var audSel = plyr.querySelector('.plyr__audio-selector');
            var target = subSel || audSel || volCtrl;
            target.parentNode.insertBefore(wrapper, target.nextSibling);
        }

        function setAspectRatio(modeId) {
            activeAspect = modeId;
            var mode = aspectModes.find(function(m) { return m.id === modeId; });
            if (!mode) return;
            var vid = document.querySelector('.player-container video');
            if (!vid) return;
            vid.style.setProperty('--video-width', mode.width);
            vid.style.setProperty('--video-height', mode.height);
            vid.style.setProperty('--video-object-fit', mode.fit);
            vid.style.setProperty('--video-aspect-ratio', mode.ratio);
        }

        /* ── Close all custom dropdowns except the given one ── */
        function closeAllDropdowns(except) {
            document.querySelectorAll('.plyr__audio-dropdown,.plyr__sub-dropdown,.plyr__aspect-dropdown').forEach(function(d) {
                if (d !== except) d.classList.remove('show');
            });
        }

        /* ── Copy Link ── */
        function copyLink() {
            navigator.clipboard.writeText(STREAM_URL).then(function() {
                var btn = document.getElementById('copy-btn');
                btn.classList.add('copied');
                btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg> Copied!';
                setTimeout(function() {
                    btn.classList.remove('copied');
                    btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg> Copy Link';
                }, 2000);
            });
        }

        /* ── External Player tabs ── */
        function switchTab(el, tab) {
            document.querySelectorAll('.openin-tab').forEach(function(t) { t.classList.remove('active'); });
            document.querySelectorAll('.openin-content').forEach(function(c) { c.classList.remove('active'); });
            el.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }

        function buildPlayerLinks() {
            var url = STREAM_URL;
            var encoded = encodeURIComponent(url);
            var fileName = encodeURIComponent(FILE_NAME);
            var intentBase = 'intent:' + url + '#Intent;action=android.intent.action.VIEW;type=video/*;';

            var desktop = [
                { href:'vlc://'+url,       icon:'vlc', letter:'V', label:'VLC' },
                { href:'potplayer://'+url,  icon:'pot', letter:'P', label:'PotPlayer' },
                { href:'mpv://'+url,        icon:'mpv', letter:'M', label:'MPV' },
                { href:'kmplayer://'+url,   icon:'kmp', letter:'K', label:'KMPlayer' },
                { href:'mpc://'+url,        icon:'mpc', letter:'M', label:'MPC-HC' },
                { href:'iina://weblink?url='+encoded, icon:'iina', letter:'I', label:'IINA' }
            ];
            var mobile = [
                { href:intentBase+'package=org.videolan.vlc;end', icon:'vlc', letter:'V', label:'VLC' },
                { href:intentBase+'package=com.mxtech.videoplayer.ad;S.title='+fileName+';end', icon:'mx', letter:'MX', label:'MX Player' },
                { href:intentBase+'package=com.mxtech.videoplayer.pro;S.title='+fileName+';end', icon:'mx', letter:'MX', label:'MX Player Pro' },
                { href:intentBase+'package=com.young.simple.player;end', icon:'sp', letter:'S', label:'Splayer' },
                { href:intentBase+'package=dev.anilbeesetti.nextplayer;S.title='+fileName+';end', icon:'nxt', letter:'N', label:'Next Player' },
                { href:intentBase+'package=org.courville.nova;S.title='+fileName+';end', icon:'nova', letter:'N', label:'Nova Player' },
                { href:intentBase+'package=is.xyz.mpv;S.title='+fileName+';end', icon:'mpv', letter:'M', label:'MPV Android' },
                { href:intentBase+'package=com.brouken.player;end', icon:'jp', letter:'J', label:'Just Player' },
                { href:intentBase+'package=com.newin.nplayer.pro;end', icon:'np', letter:'N', label:'nPlayer' }
            ];
            var ios = [
                { href:'vlc-x-callback://x-callback-url/stream?url='+encoded, icon:'vlc', letter:'V', label:'VLC' },
                { href:'infuse://x-callback-url/play?url='+encoded, icon:'infuse', letter:'I', label:'Infuse' },
                { href:'nplayer://weblink?url='+encoded, icon:'np', letter:'N', label:'nPlayer' },
                { href:'iina://weblink?url='+encoded, icon:'iina', letter:'I', label:'IINA' }
            ];

            function renderGrid(gridId, items) {
                var grid = document.getElementById(gridId);
                if (!grid) return;
                items.forEach(function(p, i) {
                    var a = document.createElement('a');
                    a.className = 'player-btn';
                    a.href = p.href;
                    a.style.animationDelay = (0.35 + i * 0.05) + 's';
                    a.innerHTML = '<div class="p-icon ' + p.icon + '">' + p.letter + '</div>' + p.label;
                    grid.appendChild(a);
                });
            }
            renderGrid('grid-desktop', desktop);
            renderGrid('grid-mobile', mobile);
            renderGrid('grid-ios', ios);
        }
        buildPlayerLinks();

        /* ── Resizable player ── */
        function resetPlayerSize() {
            var wrapper = document.querySelector('.player-resizable-wrapper');
            var belowPlayer = document.querySelector('.below-player');
            if (wrapper) { wrapper.style.width=''; wrapper.style.height=''; wrapper.style.maxWidth=''; }
            if (belowPlayer) { belowPlayer.style.width=''; belowPlayer.style.maxWidth=''; }
            localStorage.removeItem('player-container-width');
            localStorage.removeItem('player-container-height');
            var resetBtn = document.getElementById('reset-size-btn');
            if (resetBtn) resetBtn.style.display = 'none';
        }

        function initResizing() {
            var wrapper = document.querySelector('.player-resizable-wrapper');
            if (!wrapper) return;

            var savedW = localStorage.getItem('player-container-width');
            var savedH = localStorage.getItem('player-container-height');
            if (savedW && savedH) {
                var maxW = window.innerWidth - (window.innerWidth<=768?20:40);
                var maxH = window.innerHeight - (window.innerWidth<=768?80:100);
                var w = Math.min(parseInt(savedW), maxW);
                var h = Math.min(parseInt(savedH), maxH);
                wrapper.style.width = w+'px'; wrapper.style.height = h+'px'; wrapper.style.maxWidth = '100%';
                var bp = document.querySelector('.below-player');
                if (bp) { bp.style.width = w+'px'; bp.style.maxWidth = '100%'; }
                var rb = document.getElementById('reset-size-btn');
                if (rb) rb.style.display = 'inline-flex';
            }

            wrapper.querySelectorAll('.resize-handle').forEach(function(handle) {
                handle.addEventListener('pointerdown', onPointerDown);
                handle.addEventListener('dblclick', resetPlayerSize);
            });

            function onPointerDown(e) {
                if (e.pointerType==='mouse' && e.button!==0) return;
                e.preventDefault();
                var handle = e.target;
                var direction = '';
                ['n','s','e','w','nw','ne','sw','se'].forEach(function(d) { if (handle.classList.contains('handle-'+d)) direction=d; });
                var startX=e.clientX, startY=e.clientY, startW=wrapper.offsetWidth, startH=wrapper.offsetHeight;
                wrapper.classList.add('resizing'); handle.classList.add('active-handle');
                var overlay = document.createElement('div');
                overlay.style.cssText = 'position:absolute;inset:0;z-index:90;cursor:'+window.getComputedStyle(handle).cursor;
                wrapper.appendChild(overlay);

                function onMove(me) {
                    var dx=me.clientX-startX, dy=me.clientY-startY;
                    var nw=startW, nh=startH;
                    if (direction.includes('e')) nw=startW+dx; else if (direction.includes('w')) nw=startW-dx;
                    if (direction.includes('s')) nh=startH+dy; else if (direction.includes('n')) nh=startH-dy;
                    var minW=window.innerWidth<=768?280:320, minH=window.innerWidth<=768?150:180;
                    var maxW2=window.innerWidth-(window.innerWidth<=768?20:40), maxH2=window.innerHeight-(window.innerWidth<=768?80:100);
                    nw=Math.max(minW,Math.min(nw,maxW2)); nh=Math.max(minH,Math.min(nh,maxH2));
                    wrapper.style.width=nw+'px'; wrapper.style.height=nh+'px'; wrapper.style.maxWidth='100%';
                    var bp=document.querySelector('.below-player');
                    if (bp) { bp.style.width=nw+'px'; bp.style.maxWidth='100%'; }
                }
                function onUp() {
                    wrapper.classList.remove('resizing'); handle.classList.remove('active-handle');
                    if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
                    localStorage.setItem('player-container-width', wrapper.offsetWidth);
                    localStorage.setItem('player-container-height', wrapper.offsetHeight);
                    var rb=document.getElementById('reset-size-btn'); if (rb) rb.style.display='inline-flex';
                    document.removeEventListener('pointermove',onMove);
                    document.removeEventListener('pointerup',onUp);
                    document.removeEventListener('pointercancel',onUp);
                }
                document.addEventListener('pointermove',onMove);
                document.addEventListener('pointerup',onUp);
                document.addEventListener('pointercancel',onUp);
            }
        }
    </script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# ERROR PAGE TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────
error_tmplt = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error — Filmotainment</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
    <style>
        :root {
            --p:#818cf8; --p2:#6366f1; --sec:#a78bfa; --acc:#ff0f1b;
            --txt:#f1f5f9; --txt2:#94a3b8;
            --bg:#020617; --glass:rgba(10,18,38,.8); --gb:rgba(129,140,248,.13);
            --err:#f43f5e; --err2:rgba(244,63,94,.15);
        }
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family:'Inter',sans-serif;
            background:var(--bg);
            color:var(--txt);
            min-height:100vh;
            display:flex; flex-direction:column;
            overflow-x:hidden;
        }
        body::before {
            content:''; position:fixed; inset:0; z-index:-1;
            background:
                radial-gradient(ellipse 65% 45% at 50% 40%, rgba(244,63,94,.07) 0%, transparent 62%),
                radial-gradient(ellipse 75% 50% at 10% 20%, rgba(99,102,241,.10) 0%, transparent 58%),
                linear-gradient(160deg, #020617 0%, #070c1b 45%, #0f172a 100%);
        }

        /* Header */
        header {
            padding:.8rem 1.5rem;
            backdrop-filter:blur(24px) saturate(180%);
            -webkit-backdrop-filter:blur(24px) saturate(180%);
            background:var(--glass);
            border-bottom:1px solid var(--gb);
            box-shadow:0 1px 32px rgba(0,0,0,.45);
            display:flex; justify-content:center; align-items:center;
            animation:fadeDown .45s ease both;
        }
        @keyframes fadeDown {
            from { opacity:0; transform:translateY(-12px); }
            to   { opacity:1; transform:translateY(0); }
        }
        .header-logo {
            font-size:1rem; font-weight:800; letter-spacing:-.01em;
            background:linear-gradient(90deg,#e2e8f0 0%,var(--p) 50%,var(--acc) 100%);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
        }

        /* Error layout */
        main {
            flex:1; display:flex; align-items:center; justify-content:center;
            padding:3rem 1.25rem;
        }
        .error-card {
            background:var(--glass);
            border:1px solid rgba(244,63,94,.22);
            border-radius:20px;
            padding:2.5rem 2rem;
            text-align:center;
            max-width:440px; width:100%;
            box-shadow:
                0 0 0 1px rgba(255,255,255,.04),
                0 12px 48px rgba(0,0,0,.5),
                0 0 45px rgba(244,63,94,.09);
            backdrop-filter:blur(20px);
            animation:cardIn .5s ease both;
        }
        @keyframes cardIn {
            from { opacity:0; transform:translateY(22px) scale(.97); }
            to   { opacity:1; transform:translateY(0) scale(1); }
        }

        /* Error icon */
        .err-icon {
            width:66px; height:66px; border-radius:50%;
            margin:0 auto 1.4rem;
            background:var(--err2);
            border:1px solid rgba(244,63,94,.28);
            display:flex; align-items:center; justify-content:center;
            box-shadow:0 0 28px rgba(244,63,94,.18);
        }
        .err-icon svg { color:var(--err); }

        .err-label {
            font-size:.65rem; font-weight:700; letter-spacing:.1em;
            text-transform:uppercase; color:var(--err); margin-bottom:.55rem;
        }
        .error-card h2 {
            font-size:1.6rem; font-weight:800; letter-spacing:-.02em;
            margin-bottom:.65rem;
        }
        .error-card p {
            font-size:.88rem; color:var(--txt2); line-height:1.7;
            margin-bottom:1.75rem;
        }

        /* Buttons */
        .err-btns { display:flex; flex-direction:column; gap:.75rem; width:100%; align-items:center; }
        .ebtn {
            display:flex; align-items:center; justify-content:center; gap:.5rem;
            width:100%; max-width:280px;
            padding:.85rem 1.5rem; border-radius:12px;
            font-family:'Inter',sans-serif; font-size:.9rem; font-weight:700;
            cursor:pointer; text-decoration:none; color:#fff; border:none;
            transition:transform .2s, box-shadow .2s, filter .2s;
            background:linear-gradient(135deg,var(--p2),var(--p),var(--sec));
            box-shadow:0 4px 20px rgba(99,102,241,.45);
        }
        .ebtn:hover {
            transform:scale(1.02);
            box-shadow:0 6px 24px rgba(99,102,241,.55);
            filter:brightness(1.08);
        }
        .ebtn:active { transform:scale(.98); }

        /* Footer */
        footer {
            padding:.85rem 1.5rem; text-align:center;
            color:var(--txt2); font-size:.73rem;
        }
        footer::before {
            content:''; display:block;
            width:90px; height:1px;
            background:linear-gradient(90deg,transparent,rgba(129,140,248,.25),transparent);
            margin:0 auto .7rem;
        }
        .ha-link {
            color:var(--p); text-decoration:none; font-weight:600;
            transition:opacity .2s;
        }
        .ha-link:hover { opacity:.7; }
    </style>
</head>
<body>

<header>
    <span class="header-logo">Filmotainment</span>
</header>

<main>
  <div class="error-card">

    <div class="err-icon">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    </div>

    <div class="err-label">Error</div>
    <h2>Something went wrong</h2>
    <p>We couldn't load this file. It may have expired or there was a temporary issue.</p>

    <div class="err-btns">
      <button class="ebtn" onclick="location.reload()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
        Try Again
      </button>
      <a href="https://t.me/FTAdminbot" class="ebtn" target="_blank" rel="noopener">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
        Support Group
      </a>
    </div>

  </div>
</main>

<footer>
  <p>Powered by <a href="https://t.me/FT_Channels" class="ha-link" target="_blank" rel="noopener">Filmotainment</a></p>
</footer>
</body>
</html>
"""



payment_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Activate Premium</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--tg-theme-bg-color, #121212);
            color: var(--tg-theme-text-color, #ffffff);
            margin: 0; padding: 20px; text-align: center;
        }
        
        #block-screen { display: none; margin-top: 50px; color: #ff4d4d; }
        #app-content { display: none; } 

        .profile-pic { 
            border-radius: 50%; width: 80px; height: 80px; object-fit: cover; 
            border: 2px solid var(--tg-theme-button-color, #3390ec); margin-bottom: 10px;
        }
        .user-name { font-size: 20px; font-weight: 600; margin-bottom: 25px; }

        .plan-btn, .action-btn {
            display: block; width: 100%; padding: 16px; margin: 10px 0;
            background-color: var(--tg-theme-button-color, #3390ec);
            color: var(--tg-theme-button-text-color, #ffffff);
            border: none; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
        }
        .plan-btn:active, .action-btn:active { transform: scale(0.98); opacity: 0.8; }
        .action-btn { background-color: #34c759; } 
        .action-btn:disabled { background-color: #555; cursor: not-allowed; }
        
        #payment-section, #slip-section { display: none; margin-top: 15px; }
        .qr-img { width: 220px; max-width: 100%; border-radius: 12px; margin: 15px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .instruction-text { font-size: 15px; opacity: 0.85; margin: 5px 0 15px 0; }

        .copy-box {
            background-color: var(--tg-theme-secondary-bg-color, #2c2c2e);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
            padding: 14px; margin: 15px 0; display: flex; align-items: center;
            justify-content: space-between; cursor: pointer; word-break: break-all;
        }
        .copy-text { font-family: monospace; font-size: 14px; text-align: left; flex: 1; margin-right: 10px; color: var(--tg-theme-text-color, #fff); }
        .copy-icon { width: 20px; height: 20px; fill: var(--tg-theme-button-color, #3390ec); flex-shrink: 0; }
        
        .file-upload-wrapper { margin: 20px 0; }
        input[type="file"] {
            background: var(--tg-theme-secondary-bg-color, #2c2c2e);
            padding: 12px; border-radius: 8px; width: 90%; color: var(--tg-theme-text-color, #fff);
        }
    </style>
</head>
<body>

    <div id="block-screen">
        <h2>Access Denied 🛑</h2>
        <p>Please open this inside the Telegram App.</p>
    </div>

    <div id="app-content">
        <img id="user-pic" class="profile-pic" alt="Profile">
        <div id="user-name" class="user-name">Loading...</div>

        <!-- Step 1: Plans Configuration Layout -->
        <div id="plans-section">
            <h3>Select a Premium Plan</h3>
            <div id="buttons-container"></div>
        </div>

        <!-- Step 2: Payment Details Layout -->
        <div id="payment-section">
            <h3>Complete Your Payment</h3>
            <p class="instruction-text">Selected: <strong id="selected-plan-text"></strong></p>
            
            <img src="{{QR_IMG}}" alt="Payment QR" class="qr-img">
            
            <p class="instruction-text">Scan the QR code or tap below to copy the <strong>{{PAYM_TYPE}}</strong> credentials:</p>
            
            <div class="copy-box" onclick="copyAddress()">
                <div class="copy-text" id="pay-address">{{PAYM_ID}}</div>
                <svg class="copy-icon" viewBox="0 0 24 24">
                    <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                </svg>
            </div>
            
            <button class="action-btn" onclick="goToSlipSection()">I Have Paid, Next Step</button>
            <button class="plan-btn" style="background-color: transparent; border: 1px solid gray;" onclick="goBackToPlans()">Cancel</button>
        </div>

        <!-- Step 3: Transaction Upload Layout -->
        <div id="slip-section">
            <h3>Upload Payment Slip</h3>
            <p class="instruction-text">Please provide a confirmation screenshot of your transfer.</p>
            <div class="file-upload-wrapper">
                <input type="file" id="slip-file" accept="image/png, image/jpeg, image/webp">
            </div>
            <button id="submit-btn" class="action-btn" onclick="submitPayment()">Submit for Verification</button>
        </div>
    </div>

    <script>
        // ── Fallback avatar: inline SVG, no external request needed ──────────
        const FALLBACK_AVATAR = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Crect width='80' height='80' rx='40' fill='%233390ec'/%3E%3Ccircle cx='40' cy='30' r='16' fill='%23fff'/%3E%3Cellipse cx='40' cy='70' rx='26' ry='20' fill='%23fff'/%3E%3C/svg%3E";

        const tg = window.Telegram.WebApp;
        tg.expand(); 

        if (!tg.initData) {
            document.getElementById('block-screen').style.display = 'block';
        } else {
            document.getElementById('app-content').style.display = 'block';
        }

        let currentPlanDays = "0"; 
        let tgUserId = "unknown";
        let tgUserName = "User";

        const userPicEl = document.getElementById('user-pic');

        const user = tg.initDataUnsafe?.user;
        if (user) {
            tgUserId   = user.id;
            tgUserName = user.first_name + (user.last_name ? ' ' + user.last_name : '');
            document.getElementById('user-name').innerText = tgUserName;

            if (user.photo_url) {
                // Try loading the real photo; fall back to SVG if it fails
                userPicEl.src = user.photo_url;
                userPicEl.onerror = () => { userPicEl.src = FALLBACK_AVATAR; };
            } else {
                userPicEl.src = FALLBACK_AVATAR;
            }
        } else {
            userPicEl.src = FALLBACK_AVATAR;
        }

        const plans = {{PLANS_JSON}};
        const container = document.getElementById('buttons-container');

        for (const [daysStr, details] of Object.entries(plans)) {
            const planName = details[0];
            const currency = details[1];
            const price    = details[2];
            
            const btn = document.createElement('button');
            btn.className = 'plan-btn';
            btn.innerText = `${planName.toUpperCase()} - ${currency} ${price}`;
            
            btn.onclick = () => {
                currentPlanDays = daysStr; 
                document.getElementById('plans-section').style.display  = 'none';
                document.getElementById('payment-section').style.display = 'block';
                document.getElementById('selected-plan-text').innerText  = `${planName} (${currency} ${price})`;
            };
            container.appendChild(btn);
        }

        function copyAddress() {
            const address = document.getElementById('pay-address').innerText;
            navigator.clipboard.writeText(address).then(() => {
                tg.showAlert("✅ Copied to clipboard!");
            }).catch(err => {
                console.error("Failed to copy", err);
            });
        }

        function goToSlipSection() {
            document.getElementById('payment-section').style.display = 'none';
            document.getElementById('slip-section').style.display    = 'block';
        }
        
        function goBackToPlans() {
            document.getElementById('payment-section').style.display = 'none';
            document.getElementById('plans-section').style.display   = 'block';
        }

        async function submitPayment() {
            const fileInput = document.getElementById('slip-file');
            if (!fileInput.files.length) {
                tg.showAlert("⚠️ Please upload a screenshot of your payment.");
                return;
            }

            const file = fileInput.files[0];
            if (file.size > 5 * 1024 * 1024) {
                tg.showAlert("⚠️ File is too large. Please upload an image under 5MB.");
                return;
            }

            const submitBtn = document.getElementById('submit-btn');
            submitBtn.innerText  = "⏳ Uploading... Please wait";
            submitBtn.disabled   = true;

            const formData = new FormData();
            formData.append("days",      currentPlanDays); 
            formData.append("user_id",   tgUserId);
            formData.append("user_name", tgUserName);
            formData.append("slip",      file);

            try {
                const response = await fetch("/submit-payment", {
                    method: "POST",
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.status === "success") {
                    tg.showAlert("✅ Slip uploaded successfully! Your plan will be activated after verification.", () => {
                        tg.close();
                    });
                } else {
                    tg.showAlert("❌ " + (result.message || "Error uploading slip. Please try again."));
                    resetButton();
                }
            } catch (error) {
                tg.showAlert("🔌 Network error. Please check your connection and try again.");
                resetButton();
            }
            
            function resetButton() {
                submitBtn.innerText = "Submit for Verification";
                submitBtn.disabled  = false;
            }
        }
    </script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Backend helpers
# ─────────────────────────────────────────────────────────────────────────────
async def media_watch(message_id):
    import logging
    logger = logging.getLogger(__name__)
    try:
        media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
    except Exception as e:
        logger.error(f"[media_watch] get_messages failed for id={message_id}: {e}")
        return error_tmplt

    # Guard: message must exist and have media
    if not media_msg or not media_msg.media:
        logger.warning(f"[media_watch] message {message_id} not found or has no media in BIN_CHANNEL={BIN_CHANNEL}")
        return error_tmplt

    media = getattr(media_msg, media_msg.media.value, None)
    if not media:
        logger.warning(f"[media_watch] could not extract media object from message {message_id}")
        return error_tmplt

    src = urllib.parse.urljoin(URL, f'download/{message_id}')

    # Determine if this is a playable video file.
    # Telegram sometimes reports mime as application/octet-stream or leaves it empty
    # for MKV/AVI/etc, so we also check the file extension as a fallback.
    mime = getattr(media, 'mime_type', '') or ''
    file_name = getattr(media, 'file_name', None) or f'video_{message_id}.mp4'
    tag = mime.split('/')[0].strip().lower()
    ext = re.sub(r'^.*\.', '', file_name.lower()) if '.' in file_name else ''

    VIDEO_MIMES = {'video', 'application/octet-stream'}
    VIDEO_EXTS  = {'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'ts', 'mpeg', 'mpg', '3gp', 'ogv'}

    is_video = (tag == 'video') or (mime in VIDEO_MIMES) or (ext in VIDEO_EXTS)
    if not is_video:
        logger.warning(f"[media_watch] message {message_id} rejected: mime='{mime}' ext='{ext}' — not a recognised video")
        return error_tmplt

    # Resolve the real MIME type for the player (Telegram often sends octet-stream for MKV/AVI)
    import mimetypes as _mt
    mime_map = {
        'mkv': 'video/x-matroska', 'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',  'wmv': 'video/x-ms-wmv',
        'flv': 'video/x-flv',     'webm': 'video/webm',
        'm4v': 'video/x-m4v',     'ts': 'video/mp2t',
        'mpeg': 'video/mpeg',      'mpg': 'video/mpeg',
        '3gp': 'video/3gpp',       'ogv': 'video/ogg',
        'mp4': 'video/mp4',
    }
    if mime and mime != 'application/octet-stream':
        resolved_mime = mime
    else:
        resolved_mime = _mt.guess_type(file_name)[0] or mime_map.get(ext, 'video/mp4')

    # Browsers/Plyr reject non-standard MIME types like video/x-matroska before even
    # trying to play. Use video/mp4 as the declared source type universally — the actual
    # bytes and codec negotiation happen at the HTTP level regardless.
    player_mime = 'video/mp4'

    file_name_safe = html.escape(file_name)
    heading   = html.escape(f'Watch \u2014 {file_name}')

    # Replace template tokens — {heading} and {file_name} before {src}
    # to avoid any partial re-substitution if values ever contain braces.
    html_ = (watch_tmplt
             .replace('{heading}',    heading)
             .replace('{file_name}',  file_name_safe)
             .replace('{message_id}', str(message_id))
             .replace('{mime_type}',  player_mime)
             .replace('{src}',        src))
    return html_
