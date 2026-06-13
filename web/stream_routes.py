import math
import secrets
import mimetypes
from info import BIN_CHANNEL, MAX_BTN, PREMIUM_PLANS, PAYMENT_QR_CODE, PAYMENT_ID, PAYMENT_TYPE, OWNER_USERNAME, TMDB_API_KEY
try:
    from info import OMDB_API_KEY
except ImportError:
    OMDB_API_KEY = None
try:
    from info import TVDB_API_KEY
except ImportError:
    TVDB_API_KEY = None
from utils import temp, get_size, handle_next_back, get_plan_name
from aiohttp import web
from web.utils.custom_dl import TGCustomYield, chunk_size, offset_fix
from web.utils.render_template import media_watch, error_tmplt, webapp_template, payment_template, no_tmdb_template
from database.ia_filterdb import get_search_results
from database.users_chats_db import db
import json, io, aiohttp
import re
import PTN
import asyncio
from difflib import SequenceMatcher
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

routes = web.RouteTableDef()

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p"
JIKAN_BASE = "https://api.jikan.moe/v4"
OMDB_BASE = "https://www.omdbapi.com/"
TVDB_BASE = "https://api4.thetvdb.com/v4"
TVDB_TOKEN = None

def normalize_title(value):
    value = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    noise = {
        "the", "a", "an", "movie", "series", "season", "episode", "complete",
        "hindi", "english", "tamil", "telugu", "malayalam", "kannada", "dual",
        "audio", "web", "dl", "webrip", "bluray", "hdrip", "x264", "x265",
        "hevc", "aac", "esub", "subs", "subtitle", "480p", "720p", "1080p", "2160p"
    }
    return " ".join(part for part in value.split() if part not in noise)

def fuzzy_ratio(left, right):
    left = normalize_title(left)
    right = normalize_title(right)
    if not left or not right:
        return 0
    if left == right:
        return 1
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    token_overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    return max(SequenceMatcher(None, left, right).ratio(), token_overlap)

def clean_filename_title(value):
    value = re.sub(r"\.[^.]+$", "", str(value or ""))
    value = re.sub(r"[\._\-\[\]\(\)]+", " ", value)
    return " ".join(value.split())

def split_trailing_year(title):
    match = re.search(r"\b((?:19|20)\d{2})$", str(title or "").strip())
    if not match:
        return title, None
    return title[:match.start()].strip(), int(match.group(1))

def parse_media_filename(name):
    raw_name = str(name or "")
    searchable = re.sub(r"[\._\-\[\]\(\)]+", " ", raw_name)

    season_episode = re.search(r"(?i)(?:^|\s)s(\d{1,2})\s*e(\d{1,4})(?:\s|$)", searchable)
    if season_episode:
        title, year = split_trailing_year(clean_filename_title(searchable[:season_episode.start()]))
        return {
            "title": title,
            "year": year,
            "season": int(season_episode.group(1)),
            "episode": int(season_episode.group(2)),
        }

    episode_only = re.search(r"(?i)(?:^|\s)(?:ep|episode)\s*(\d{1,5})(?:\s|$)", searchable)
    if episode_only:
        title, year = split_trailing_year(clean_filename_title(searchable[:episode_only.start()]))
        return {
            "title": title,
            "year": year,
            "season": None,
            "episode": int(episode_only.group(1)),
        }

    movie_year = re.search(r"(?:^|\s)((?:19|20)\d{2})(?:\s|$)", searchable)
    if movie_year:
        return {
            "title": clean_filename_title(searchable[:movie_year.start()]),
            "year": int(movie_year.group(1)),
            "season": None,
            "episode": None,
        }

    parsed = PTN.parse(raw_name)
    title = parsed.get("title") or raw_name
    season = parsed.get("season")
    episode = parsed.get("episode")
    year = parsed.get("year")
    return {
        "title": title,
        "year": int(year) if str(year).isdigit() else year,
        "season": int(season) if str(season).isdigit() else season,
        "episode": int(episode) if str(episode).isdigit() else episode,
    }

def file_model(file):
    name = file.get("file_name", "Unknown")
    parsed = parse_media_filename(name)
    return {
        "id": str(file["_id"]),
        "name": name,
        "size": get_size(file.get("file_size", 0)),
        "raw_size": file.get("file_size", 0),
        "title": parsed.get("title") or name,
        "year": parsed.get("year"),
        "season": parsed.get("season"),
        "episode": parsed.get("episode"),
    }

def match_file_to_tmdb(file, title, year=None, media_type=None):
    model = file_model(file)
    target = normalize_title(title)
    parsed_title = normalize_title(model["title"])
    if not target:
        model["match_score"] = 0
        return model

    similarity = fuzzy_ratio(parsed_title, target)
    if similarity < 0.72:
        model["match_score"] = 0
        return model

    score = similarity
    if media_type == "movie" and year and model.get("year") and str(model["year"]) != str(year):
        model["match_score"] = 0
        return model
    if year and model.get("year") and str(model["year"]) == str(year):
        score += 0.08
    if media_type == "tv" and model.get("season") is not None:
        score += 0.05
    if media_type == "movie" and model.get("season") is None:
        score += 0.03

    model["match_score"] = round(score, 4)
    return model

async def fetch_json(session, url, params=None, headers=None):
    async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
        if resp.status >= 400:
            return {}
        return await resp.json(content_type=None)

def tmdb_img(path, size="original"):
    return f"{TMDB_IMAGE}/{size}{path}" if path else None

def pick_tmdb_trailer(videos):
    items = videos.get("results", []) if isinstance(videos, dict) else []
    youtube = [v for v in items if v.get("site") == "YouTube" and v.get("key")]
    preferred = next((v for v in youtube if v.get("type") == "Trailer" and v.get("official")), None)
    preferred = preferred or next((v for v in youtube if v.get("type") == "Trailer"), None)
    preferred = preferred or (youtube[0] if youtube else None)
    if not preferred:
        return None
    return {
        "site": "YouTube",
        "key": preferred["key"],
        "name": preferred.get("name") or "Trailer",
        "embed": f"https://www.youtube.com/embed/{preferred['key']}?autoplay=0&rel=0",
        "url": f"https://www.youtube.com/watch?v={preferred['key']}"
    }

def fmt_tmdb_item(r, media_type=None):
    mt = media_type or r.get("media_type", "movie")
    title = r.get("title") or r.get("name", "")
    date = r.get("release_date") or r.get("first_air_date", "")
    return {
        "id": r["id"],
        "source": "tmdb",
        "title": title,
        "year": date[:4] if date else "",
        "type": mt,
        "rating": round(r.get("vote_average", 0), 1),
        "poster": tmdb_img(r.get("poster_path"), "w342"),
        "backdrop": tmdb_img(r.get("backdrop_path"), "w1280"),
        "overview": r.get("overview", ""),
        "genres": r.get("genre_ids", [])
    }

def fmt_mal_item(item):
    images = item.get("images", {}).get("jpg", {})
    aired = item.get("aired", {}) or {}
    year = item.get("year") or str(aired.get("from", ""))[:4]
    return {
        "id": item.get("mal_id"),
        "source": "mal",
        "title": item.get("title_english") or item.get("title") or "",
        "year": str(year or ""),
        "type": "anime",
        "rating": round(item.get("score") or 0, 1),
        "poster": images.get("large_image_url") or images.get("image_url"),
        "backdrop": images.get("large_image_url") or images.get("image_url"),
        "overview": item.get("synopsis") or "",
        "genres": [g.get("name") for g in item.get("genres", []) if g.get("name")]
    }

def compact_people(items, role_key="character", limit=14):
    people = []
    for p in (items or [])[:limit]:
        people.append({
            "name": p.get("name") or "",
            "role": p.get(role_key) or p.get("job") or "",
            "image": tmdb_img(p.get("profile_path"), "w185")
        })
    return people

async def get_tvdb_token(session):
    global TVDB_TOKEN
    if TVDB_TOKEN or not TVDB_API_KEY:
        return TVDB_TOKEN
    data = await fetch_json(session, f"{TVDB_BASE}/login", headers={"Content-Type": "application/json"}, params=None)
    return data.get("data", {}).get("token")

async def fetch_tvdb_data(session, title, year=None):
    if not TVDB_API_KEY:
        return None
    global TVDB_TOKEN
    if not TVDB_TOKEN:
        async with session.post(f"{TVDB_BASE}/login", json={"apikey": TVDB_API_KEY}, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            if resp.status >= 400:
                return None
            data = await resp.json(content_type=None)
            TVDB_TOKEN = data.get("data", {}).get("token")
    headers = {"Authorization": f"Bearer {TVDB_TOKEN}"}
    data = await fetch_json(session, f"{TVDB_BASE}/search", params={"query": title, "type": "series"}, headers=headers)
    first = next((x for x in data.get("data", []) if not year or str(year) in str(x.get("year", ""))), None)
    if not first:
        first = (data.get("data") or [None])[0]
    if not first:
        return None
    return {
        "id": first.get("tvdb_id"),
        "url": f"https://thetvdb.com/dereferrer/series/{first.get('tvdb_id')}" if first.get("tvdb_id") else None,
        "status": first.get("status"),
        "network": first.get("network"),
        "overview": first.get("overview"),
        "poster": first.get("image_url")
    }

async def fetch_omdb_data(session, imdb_id):
    if not OMDB_API_KEY or not imdb_id:
        return None
    data = await fetch_json(session, OMDB_BASE, params={"apikey": OMDB_API_KEY, "i": imdb_id, "plot": "full"})
    if data.get("Response") == "False":
        return None
    return {
        "imdb_id": imdb_id,
        "rating": data.get("imdbRating"),
        "votes": data.get("imdbVotes"),
        "rated": data.get("Rated"),
        "awards": data.get("Awards"),
        "box_office": data.get("BoxOffice"),
        "imdb_url": f"https://www.imdb.com/title/{imdb_id}/",
        "quote": data.get("Awards") if data.get("Awards") and data.get("Awards") != "N/A" else None,
        "poster": None if data.get("Poster") == "N/A" else data.get("Poster")
    }

async def build_tmdb_details(session, media_type, tmdb_id):
    data = await fetch_json(
        session,
        f"{TMDB_BASE}/{media_type}/{tmdb_id}",
        params={
            "api_key": TMDB_API_KEY,
            "append_to_response": "videos,credits,images,external_ids,reviews,keywords,watch/providers,content_ratings,release_dates"
        }
    )
    if not data:
        return {}
    title = data.get("title") or data.get("name") or ""
    date = data.get("release_date") or data.get("first_air_date") or ""
    trailer = pick_tmdb_trailer(data.get("videos", {}))
    imdb_id = data.get("external_ids", {}).get("imdb_id") or data.get("imdb_id")
    omdb, tvdb = await asyncio.gather(
        fetch_omdb_data(session, imdb_id),
        fetch_tvdb_data(session, title, date[:4] if date else None)
    )
    backdrops = [tmdb_img(x.get("file_path"), "w1280") for x in data.get("images", {}).get("backdrops", [])[:12]]
    posters = [tmdb_img(x.get("file_path"), "w500") for x in data.get("images", {}).get("posters", [])[:12]]
    keywords_data = data.get("keywords", {})
    keywords = keywords_data.get("keywords") or keywords_data.get("results") or []
    providers = ((data.get("watch/providers", {}).get("results") or {}).get("US") or {})
    return {
        "id": data.get("id"),
        "source": "tmdb",
        "type": media_type,
        "title": title,
        "year": date[:4] if date else "",
        "tagline": data.get("tagline") or "",
        "overview": data.get("overview") or "",
        "status": data.get("status"),
        "runtime": data.get("runtime") or (data.get("episode_run_time") or [None])[0],
        "rating": round(data.get("vote_average") or 0, 1),
        "votes": data.get("vote_count") or 0,
        "poster": tmdb_img(data.get("poster_path"), "w500") or (omdb or {}).get("poster"),
        "backdrop": tmdb_img(data.get("backdrop_path"), "w1280"),
        "trailer": trailer,
        "genres": [g.get("name") for g in data.get("genres", [])],
        "cast": compact_people(data.get("credits", {}).get("cast", [])),
        "crew": compact_people(data.get("credits", {}).get("crew", []), role_key="job", limit=8),
        "images": {"backdrops": [x for x in backdrops if x], "posters": [x for x in posters if x]},
        "reviews": [{
            "author": r.get("author"),
            "quote": (r.get("content") or "")[:260]
        } for r in data.get("reviews", {}).get("results", [])[:4]],
        "keywords": [k.get("name") for k in keywords[:14] if k.get("name")],
        "links": {
            "tmdb": f"https://www.themoviedb.org/{media_type}/{tmdb_id}",
            "imdb": f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None,
            "tvdb": (tvdb or {}).get("url")
        },
        "external": {"imdb": omdb, "tvdb": tvdb},
        "providers": {
            "link": providers.get("link"),
            "flatrate": [p.get("provider_name") for p in providers.get("flatrate", [])[:8]],
            "rent": [p.get("provider_name") for p in providers.get("rent", [])[:8]],
            "buy": [p.get("provider_name") for p in providers.get("buy", [])[:8]]
        }
    }

async def build_mal_details(session, mal_id):
    data = await fetch_json(session, f"{JIKAN_BASE}/anime/{mal_id}/full")
    anime = data.get("data") or {}
    chars_data = await fetch_json(session, f"{JIKAN_BASE}/anime/{mal_id}/characters")
    videos_data = await fetch_json(session, f"{JIKAN_BASE}/anime/{mal_id}/videos")
    images = anime.get("images", {}).get("jpg", {})
    trailer = anime.get("trailer", {}) or {}
    promo = next((v for v in (videos_data.get("data", {}).get("promo") or []) if v.get("trailer", {}).get("embed_url")), None)
    cast = []
    for c in (chars_data.get("data") or [])[:14]:
        character = c.get("character", {})
        cast.append({
            "name": character.get("name") or "",
            "role": c.get("role") or "",
            "image": (character.get("images", {}).get("jpg") or {}).get("image_url")
        })
    title = anime.get("title_english") or anime.get("title") or ""
    return {
        "id": anime.get("mal_id"),
        "source": "mal",
        "type": "anime",
        "title": title,
        "year": str(anime.get("year") or "") or str((anime.get("aired") or {}).get("from", ""))[:4],
        "tagline": anime.get("title_japanese") or "",
        "overview": anime.get("synopsis") or "",
        "status": anime.get("status"),
        "runtime": anime.get("duration"),
        "rating": round(anime.get("score") or 0, 1),
        "votes": anime.get("scored_by") or 0,
        "poster": images.get("large_image_url") or images.get("image_url"),
        "backdrop": images.get("large_image_url") or images.get("image_url"),
        "trailer": {
            "site": "YouTube",
            "key": trailer.get("youtube_id"),
            "name": "Trailer",
            "embed": trailer.get("embed_url"),
            "url": trailer.get("url")
        } if trailer.get("embed_url") else ({
            "site": "YouTube",
            "name": promo.get("title") or "Trailer",
            "embed": promo.get("trailer", {}).get("embed_url"),
            "url": promo.get("trailer", {}).get("url")
        } if promo else None),
        "genres": [g.get("name") for g in anime.get("genres", [])],
        "cast": cast,
        "crew": [{"name": p.get("name"), "role": "Producer", "image": None} for p in anime.get("producers", [])[:8]],
        "images": {"backdrops": [images.get("large_image_url") or images.get("image_url")], "posters": [images.get("large_image_url") or images.get("image_url")]},
        "reviews": [],
        "keywords": [x.get("name") for x in (anime.get("themes", []) + anime.get("demographics", [])) if x.get("name")],
        "links": {"mal": anime.get("url")},
        "external": {"myanimelist": {"rank": anime.get("rank"), "popularity": anime.get("popularity"), "members": anime.get("members")}},
        "providers": {}
    }

@routes.get("/watch/{message_id}")
async def watch_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return web.Response(text=await media_watch(message_id), content_type='text/html')
    except Exception as e:
        return web.Response(text=error_tmplt, content_type='text/html')

@routes.get("/download/{message_id}")
async def download_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return await media_download(request, message_id)
    except:
        return web.Response(text=error_tmplt, content_type='text/html')
        


@routes.get("/api/stream-file/{file_id}")
async def stream_file_handler(request):
    """Copy file to BIN_CHANNEL and redirect to /watch/{msg_id}"""
    try:
        file_id = request.match_info['file_id']
        msg = await temp.BOT.send_cached_media(chat_id=BIN_CHANNEL, file_id=file_id)
        raise web.HTTPFound(location=f"/watch/{msg.id}")
    except web.HTTPFound:
        raise
    except Exception as e:
        return web.Response(text=error_tmplt, content_type='text/html')


@routes.get("/api/tracks/{message_id}")
async def tracks_handler(request):
    """Use ffprobe to extract audio and subtitle track info from the stream URL."""
    import asyncio, subprocess, json as _json, urllib.parse as _up
    try:
        message_id = int(request.match_info['message_id'])
        stream_url = _up.urljoin(URL, f"download/{message_id}")

        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "a:s",
            stream_url,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)

        data = _json.loads(stdout.decode()) if stdout else {}
        streams = data.get("streams", [])

        audio = []
        subs  = []
        for i, s in enumerate(streams):
            codec_type = s.get("codec_type", "")
            tags = s.get("tags", {})
            label = tags.get("title") or tags.get("language") or s.get("codec_name", "")
            lang  = tags.get("language", "")
            idx   = s.get("index", i)
            if codec_type == "audio":
                audio.append({"index": idx, "label": label or f"Audio {len(audio)+1}", "language": lang})
            elif codec_type == "subtitle":
                subs.append({"index": idx, "label": label or f"Sub {len(subs)+1}", "language": lang})

        return web.json_response({"audio": audio, "subtitles": subs})
    except Exception as e:
        return web.json_response({"audio": [], "subtitles": [], "error": str(e)})

@routes.get("/", allow_head=True)
async def webapp_route_handler(request):
    if not TMDB_API_KEY:
        return web.Response(text=no_tmdb_template, content_type='text/html')
    return web.Response(text=webapp_template, content_type='text/html')


@routes.get("/activate-plan", allow_head=True)
async def activate_plan_handler(request):
    FRONTEND_PLANS = {}
    for days, details in PREMIUM_PLANS.items():
        nice_name = get_plan_name(days)
        FRONTEND_PLANS[str(days)] = [nice_name, details[0], details[1]]

    html_content = payment_template.replace('{{QR_IMG}}', PAYMENT_QR_CODE)
    html_content = html_content.replace('{{PAYM_ID}}', PAYMENT_ID)
    html_content = html_content.replace('{{PAYM_TYPE}}', PAYMENT_TYPE)
    html_content = html_content.replace('{{PLANS_JSON}}', json.dumps(FRONTEND_PLANS))
    
    return web.Response(text=html_content, content_type='text/html')

@routes.post("/submit-payment")
async def submit_payment_handler(request):
    try:
        data = await request.post()
        days_str = data.get('days') 
        user_id = data.get('user_id')
        user_name = data.get('user_name')
        slip_field = data.get('slip')
        plan_days = int(days_str) if days_str and days_str.isdigit() else 0
        
        if plan_days not in PREMIUM_PLANS:
            return web.json_response({"status": "error", "message": "Invalid plan selected."}, status=400)
            
        if not slip_field:
            return web.json_response({"status": "error", "message": "No slip uploaded."}, status=400)

        file_bytes = slip_field.file.read()
        if len(file_bytes) > 5242880:
            return web.json_response({"status": "error", "message": "Image too large. Max 5MB."}, status=413)
        
        photo_io = io.BytesIO(file_bytes)
        photo_io.name = f"{user_id}_payment_slip.jpg" 
        bot_plan_name = get_plan_name(plan_days)
        btn = [[
            InlineKeyboardButton('✅ Accept', callback_data=f'accept_payment-{user_id}-{plan_days}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'reject_payment-{user_id}-{plan_days}'),
        ]]
        text = f"""💰 New Payment Received!\n\nUser: <a href="tg://user?id={user_id}">{user_name}</a>\nUser ID: <code>{user_id}</code>\nPlan: {bot_plan_name} ({plan_days} Days)"""
        await temp.BOT.send_photo(chat_id=OWNER_USERNAME, photo=photo_io, caption=text, reply_markup=InlineKeyboardMarkup(btn))
        await temp.BOT.send_message(chat_id=int(user_id), text=f"Thank you! Your payment slip has been sent to the owner. Once it is verified, your Premium Plan [{bot_plan_name}] will be activated soon.\n\nSupport: @{OWNER_USERNAME}")
        
        return web.json_response({"status": "success"})
        
    except Exception as e:
        print(f"Server Error: {e}")
        return web.json_response({"status": "error", "message": "Server error processing payload."}, status=500)


@routes.get("/api/search")
async def api_search_handler(request):
    query = request.query.get('q', '').strip()
    media_type = request.query.get('type', '').strip()
    year = request.query.get('year', '').strip()
    offset = int(request.query.get('offset', 0))
  
    search_terms = [query]
    compact_query = re.sub(r"[^A-Za-z0-9 ]+", " ", query).strip()
    if compact_query and compact_query not in search_terms:
        search_terms.append(compact_query)
    for word in compact_query.split():
        if len(word) >= 4 and word.lower() not in {"the", "and", "with", "from"}:
            search_terms.append(word)

    found = {}
    for term in search_terms:
        for file in await get_search_results(term):
            found[file["_id"]] = file
    if not found and len(compact_query) >= 4:
        for file in await get_search_results(""):
            model = file_model(file)
            if fuzzy_ratio(model["title"], compact_query) >= 0.68:
                found[file["_id"]] = file

    ranked_files = [
        model for model in (
            match_file_to_tmdb(file, query, year=year, media_type=media_type)
            for file in found.values()
        )
        if model["match_score"] >= 0.42
    ]
    ranked_files.sort(key=lambda f: (
        f.get("season") if isinstance(f.get("season"), int) else 999,
        f.get("episode") if isinstance(f.get("episode"), int) else 999,
        -f["match_score"],
        f["name"].lower()
    ))

    total_results = len(ranked_files)
    files, next_offset, _ = await handle_next_back(ranked_files, offset=offset, max_results=MAX_BTN * 5)
    
    return web.json_response({
        "files": files,
        "next_offset": next_offset if next_offset != 0 else None,
        "total_results": total_results,
        "current_offset": offset,
        "max_btn": MAX_BTN * 5,
        "bot_username": temp.U_NAME
    })


@routes.get("/api/tmdb-search")
async def tmdb_search_handler(request):
    if not TMDB_API_KEY:
        return web.json_response({"results": [], "error": "TMDB API key not configured"}, status=503)
    query = request.query.get('q', '').strip()
    page = request.query.get('page', '1')
    if not query:
        return web.json_response({"results": []})
    try:
        corrected_query = None
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TMDB_BASE}/search/multi",
                params={"api_key": TMDB_API_KEY, "query": query, "page": page, "include_adult": "true"}
            ) as resp:
                data = await resp.json()
            anime_data = await fetch_json(session, f"{JIKAN_BASE}/anime", params={"q": query, "limit": 8, "sfw": "false"})
            if not data.get("results") and not anime_data.get("data"):
                recent_files = await get_search_results("")
                candidates = []
                for file in recent_files:
                    title = file_model(file).get("title")
                    score = fuzzy_ratio(query, title)
                    if title and score >= 0.55:
                        candidates.append((score, title))
                if candidates:
                    corrected_query = sorted(candidates, key=lambda x: -x[0])[0][1]
                    async with session.get(
                        f"{TMDB_BASE}/search/multi",
                        params={"api_key": TMDB_API_KEY, "query": corrected_query, "page": page, "include_adult": "true"}
                    ) as resp:
                        data = await resp.json()
                    anime_data = await fetch_json(session, f"{JIKAN_BASE}/anime", params={"q": corrected_query, "limit": 8, "sfw": "false"})
        results = []
        for r in data.get("results", []):
            if r.get("media_type") not in ["movie", "tv"]:
                continue
            results.append(fmt_tmdb_item(r))
        tmdb_titles = {normalize_title(x["title"]) for x in results}
        for anime in anime_data.get("data", []):
            item = fmt_mal_item(anime)
            if item["title"] and normalize_title(item["title"]) not in tmdb_titles:
                results.append(item)
        rank_query = corrected_query or query
        for item in results:
            item["match_score"] = round(fuzzy_ratio(rank_query, item.get("title")), 4)
        results.sort(key=lambda item: (
            -item.get("match_score", 0),
            0 if normalize_title(rank_query) == normalize_title(item.get("title")) else 1,
            -(item.get("rating") or 0)
        ))
        best = results[0] if results else None
        return web.json_response({
            "results": results,
            "total_pages": data.get("total_pages", 1),
            "corrected_query": corrected_query or (best.get("title") if best and best.get("match_score", 0) < 1 else None)
        })
    except Exception as e:
        return web.json_response({"results": [], "error": str(e)}, status=500)


@routes.get("/api/media-details")
async def media_details_handler(request):
    source = request.query.get("source", "tmdb").strip()
    media_type = request.query.get("type", "movie").strip()
    media_id = request.query.get("id", "").strip()
    if not media_id:
        return web.json_response({"error": "Missing id"}, status=400)
    try:
        async with aiohttp.ClientSession() as session:
            if source == "mal" or media_type == "anime":
                details = await build_mal_details(session, media_id)
            else:
                if media_type not in ["movie", "tv"]:
                    media_type = "movie"
                details = await build_tmdb_details(session, media_type, media_id)
        if not details:
            return web.json_response({"error": "No details found"}, status=404)
        return web.json_response(details)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/tmdb-trending")
async def tmdb_trending_handler(request):
    if not TMDB_API_KEY:
        return web.json_response({"error": "TMDB API key not configured"}, status=503)
    try:
        async with aiohttp.ClientSession() as session:
            urls = [
                (f"{TMDB_BASE}/trending/all/week", {"api_key": TMDB_API_KEY}),
                (f"{TMDB_BASE}/movie/popular", {"api_key": TMDB_API_KEY, "page": "1"}),
                (f"{TMDB_BASE}/tv/popular", {"api_key": TMDB_API_KEY, "page": "1"}),
                (f"{TMDB_BASE}/movie/top_rated", {"api_key": TMDB_API_KEY, "page": "1"}),
            ]
            responses = []
            for url, params in urls:
                async with session.get(url, params=params) as r:
                    responses.append(await r.json())
            anime_data = await fetch_json(session, f"{JIKAN_BASE}/top/anime", params={"filter": "bypopularity", "limit": 20})

        def fmt(items, media_type=None):
            out = []
            for r in items[:20]:
                out.append(fmt_tmdb_item(r, media_type))
            return out

        trending_all = fmt(responses[0].get("results", []))
        popular_movies = fmt(responses[1].get("results", []), "movie")
        popular_tv = fmt(responses[2].get("results", []), "tv")
        top_rated = fmt(responses[3].get("results", []), "movie")
        popular_anime = [fmt_mal_item(x) for x in anime_data.get("data", [])]

        hero = next((x for x in trending_all if x["backdrop"]), trending_all[0] if trending_all else None)

        return web.json_response({
            "hero": hero,
            "trending": trending_all,
            "popular_movies": popular_movies,
            "popular_tv": popular_tv,
            "popular_anime": popular_anime,
            "top_rated": top_rated,
            "bot_username": temp.U_NAME
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/repair-status")
async def repair_status_handler(request):
    repair = await db.get_repair_mode()
    return web.json_response({"repair_mode": repair})


@routes.get("/api/recently-added")
async def recently_added_handler(request):
    """Returns the 30 most recently indexed files from the bot's database,
    enriched with TMDB/MAL data where available for poster images."""
    limit = min(int(request.query.get("limit", 30)), 60)
    try:
        from database.ia_filterdb import collection, second_collection, SECOND_FILES_DATABASE_URL
        results = []
        cursor1 = collection.find({}).sort("_id", -1).limit(limit)
        docs = await cursor1.to_list(length=limit)
        results.extend(docs)

        if SECOND_FILES_DATABASE_URL and second_collection is not None and len(results) < limit:
            remaining = limit - len(results)
            cursor2 = second_collection.find({}).sort("_id", -1).limit(remaining)
            docs2 = await cursor2.to_list(length=remaining)
            results.extend(docs2)

        files = []
        for doc in results:
            model = file_model(doc)
            files.append({
                "id": model["id"],
                "name": model["name"],
                "size": model["size"],
                "title": model["title"],
                "year": model.get("year"),
                "season": model.get("season"),
                "episode": model.get("episode"),
            })

        # Enrich with TMDB poster/backdrop if API key available (best-effort, fast)
        enriched = []
        if TMDB_API_KEY and files:
            async with aiohttp.ClientSession() as session:
                # Batch: pick unique titles (up to 20) to avoid too many API calls
                seen_titles = set()
                title_meta = {}
                for f in files:
                    t = (f["title"] or "").strip().lower()
                    if t and t not in seen_titles and len(seen_titles) < 20:
                        seen_titles.add(t)
                        data = await fetch_json(
                            session,
                            f"{TMDB_BASE}/search/multi",
                            params={"api_key": TMDB_API_KEY, "query": f["title"], "page": "1"}
                        )
                        best = next((r for r in data.get("results", [])
                                     if r.get("media_type") in ("movie", "tv")
                                     and r.get("poster_path")), None)
                        if best:
                            mt = best.get("media_type", "movie")
                            title_meta[t] = {
                                "poster": tmdb_img(best.get("poster_path"), "w342"),
                                "backdrop": tmdb_img(best.get("backdrop_path"), "w780"),
                                "rating": round(best.get("vote_average") or 0, 1),
                                "type": mt,
                                "overview": best.get("overview") or "",
                                "tmdb_id": best.get("id"),
                            }

                for f in files:
                    t = (f["title"] or "").strip().lower()
                    meta = title_meta.get(t, {})
                    enriched.append({**f, **meta})
        else:
            enriched = [dict(f, poster=None, backdrop=None, rating=0,
                             type="movie", overview="", tmdb_id=None) for f in files]

        return web.json_response({"files": enriched})
    except Exception as e:
        return web.json_response({"files": [], "error": str(e)}, status=500)


@routes.get("/api/today-airing")
async def today_airing_handler(request):
    """Returns TV shows and anime airing today, with season/episode numbers and IDs for IMDb, TVDB, TMDB, and MAL."""
    if not TMDB_API_KEY:
        return web.json_response({"error": "TMDB API key not configured"}, status=503)
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        async with aiohttp.ClientSession() as session:
            # 1. TMDB: TV shows airing today
            tv_data = await fetch_json(
                session, f"{TMDB_BASE}/tv/airing_today",
                params={"api_key": TMDB_API_KEY, "page": "1"}
            )
            # 2. Jikan: anime airing today (schedule)
            # Use Jikan's schedules endpoint — day names in English
            day_name = datetime.now(timezone.utc).strftime("%A").lower()
            anime_sched = await fetch_json(
                session, f"{JIKAN_BASE}/schedules",
                params={"filter": day_name, "limit": 25}
            )
            # 3. TMDB: movies with digital/OTT release today (release_type 4=Digital, 6=Streaming)
            ott_data = await fetch_json(
                session, f"{TMDB_BASE}/discover/movie",
                params={
                    "api_key": TMDB_API_KEY,
                    "region": "US",
                    "with_release_type": "4|6",
                    "release_date.gte": today,
                    "release_date.lte": today,
                    "sort_by": "popularity.desc",
                    "page": "1"
                }
            )

        tv_shows = []
        for show in (tv_data.get("results") or [])[:25]:
            # Try to pull season/episode from TMDB external IDs quickly (non-blocking best-effort)
            imdb_id = None
            tvdb_id = None
            episode_name = None
            season_num = None
            episode_num = None
            network = None

            # Get network from origin_country / networks field if present
            if show.get("networks"):
                network = show["networks"][0].get("name") if show["networks"] else None
            elif show.get("origin_country"):
                network = show["origin_country"][0] if show["origin_country"] else None

            tv_shows.append({
                "tmdb_id": show.get("id"),
                "imdb_id": imdb_id,
                "tvdb_id": tvdb_id,
                "mal_id": None,
                "title": show.get("name") or show.get("original_name") or "",
                "year": (show.get("first_air_date") or "")[:4],
                "type": "tv",
                "rating": round(show.get("vote_average") or 0, 1),
                "poster": tmdb_img(show.get("poster_path"), "w342"),
                "overview": (show.get("overview") or "")[:200],
                "network": network,
                "season": season_num,
                "episode": episode_num,
                "episode_name": episode_name,
            })

        # For the top 10 shows, enrich with season/episode/IDs from TMDB details (async fan-out)
        async def enrich_tv(item):
            try:
                async with aiohttp.ClientSession() as s:
                    ext = await fetch_json(s, f"{TMDB_BASE}/tv/{item['tmdb_id']}/external_ids",
                                           params={"api_key": TMDB_API_KEY})
                    item["imdb_id"] = ext.get("imdb_id")
                    item["tvdb_id"] = ext.get("tvdb_id")
                    # Latest episode airing
                    detail = await fetch_json(s, f"{TMDB_BASE}/tv/{item['tmdb_id']}",
                                              params={"api_key": TMDB_API_KEY})
                    ep = detail.get("next_episode_to_air") or detail.get("last_episode_to_air") or {}
                    if ep:
                        item["season"]       = ep.get("season_number")
                        item["episode"]      = ep.get("episode_number")
                        item["episode_name"] = ep.get("name")
                    if not item.get("network") and detail.get("networks"):
                        item["network"] = detail["networks"][0].get("name") if detail["networks"] else None
            except Exception:
                pass
            return item

        enriched = await asyncio.gather(*[enrich_tv(show) for show in tv_shows[:10]])
        tv_shows[:10] = list(enriched)

        # Anime list
        anime_list = []
        for anime in (anime_sched.get("data") or [])[:25]:
            images = (anime.get("images") or {}).get("jpg") or {}
            aired = (anime.get("aired") or {})
            year = str(anime.get("year") or str(aired.get("from") or "")[:4])
            anime_list.append({
                "tmdb_id": None,
                "imdb_id": None,
                "tvdb_id": None,
                "mal_id": anime.get("mal_id"),
                "title": anime.get("title_english") or anime.get("title") or "",
                "year": year,
                "type": "anime",
                "rating": round(anime.get("score") or 0, 1),
                "poster": images.get("large_image_url") or images.get("image_url"),
                "overview": (anime.get("synopsis") or "")[:200],
                "network": (anime.get("broadcast") or {}).get("string"),
                "season": None,
                "episode": anime.get("episodes"),
                "episode_name": None,
            })

        return web.json_response({
            "date": today,
            "tv": tv_shows,
            "anime": anime_list
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def media_download(request, message_id: int):
    range_header = request.headers.get('Range', 0)
    media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
    media = getattr(media_msg, media_msg.media.value, None)
    file_size = media.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = request.http_range.stop or file_size - 1

    req_length = until_bytes - from_bytes

    new_chunk_size = await chunk_size(req_length)
    offset = await offset_fix(from_bytes, new_chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = (until_bytes % new_chunk_size) + 1
    part_count = math.ceil(req_length / new_chunk_size)
    body = TGCustomYield().yield_file(media_msg, offset, first_part_cut, last_part_cut, part_count,
                                      new_chunk_size)

    file_name = media.file_name if media.file_name \
        else f"{secrets.token_hex(2)}.jpeg"
    mime_type = media.mime_type if media.mime_type \
        else f"{mimetypes.guess_type(file_name)}"

    return_resp = web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        }
    )

    if return_resp.status == 200:
        return_resp.headers.add("Content-Length", str(file_size))

    return return_resp
