import math
import secrets
import mimetypes
from info import BIN_CHANNEL, MAX_BTN, PREMIUM_PLANS, PAYMENT_QR_CODE, PAYMENT_ID, PAYMENT_TYPE, OWNER_USERNAME, TMDB_API_KEY, QUALITY, LANGUAGES
from utils import temp, get_size, handle_next_back, get_plan_name
from aiohttp import web
from web.utils.custom_dl import TGCustomYield, chunk_size, offset_fix
from web.utils.render_template import media_watch, error_tmplt, webapp_template, payment_template, no_tmdb_template
from database.ia_filterdb import get_search_results
from database.users_chats_db import db
import json, io, aiohttp
import re
import PTN
from datetime import datetime, timezone
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

routes = web.RouteTableDef()

TMDB_BASE = "https://api.themoviedb.org/3"
JIKAN_BASE = "https://api.jikan.moe/v4"

LANGUAGE_LABELS = {language.lower(): language.title() for language in LANGUAGES}
LANGUAGE_LABELS.update({
    "hin": "Hindi", "eng": "English", "tam": "Tamil", "tel": "Telugu",
    "mal": "Malayalam", "kan": "Kannada", "jpn": "Japanese", "japanese": "Japanese",
    "multi": "Multi", "dual": "Dual Audio", "dual audio": "Dual Audio"
})

def normalize_title(value):
    value = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    noise = {
        "the", "a", "an", "movie", "series", "season", "episode", "complete",
        "hindi", "english", "tamil", "telugu", "malayalam", "kannada", "dual",
        "audio", "web", "dl", "webrip", "bluray", "hdrip", "x264", "x265",
        "hevc", "aac", "esub", "subs", "subtitle", "480p", "720p", "1080p", "2160p"
    }
    return " ".join(part for part in value.split() if part not in noise)

def clean_filename_title(value):
    value = re.sub(r"\.[^.]+$", "", str(value or ""))
    value = re.sub(r"[\._\-\[\]\(\)]+", " ", value)
    return " ".join(value.split())

def split_trailing_year(title):
    match = re.search(r"\b((?:19|20)\d{2})$", str(title or "").strip())
    if not match:
        return title, None
    return title[:match.start()].strip(), int(match.group(1))

def detect_quality(*values):
    haystack = " ".join(str(value or "") for value in values).lower()
    for quality in sorted(QUALITY, key=len, reverse=True):
        if re.search(rf"(?<!\d){re.escape(quality.lower())}(?!\d)", haystack):
            return quality.lower()
    if re.search(r"\b4k\b|\buhd\b", haystack):
        return "2160p"
    return "Unknown"

def detect_language(*values):
    haystack = " ".join(str(value or "") for value in values).lower()
    found = []
    for key, label in LANGUAGE_LABELS.items():
        if re.search(rf"\b{re.escape(key)}\b", haystack) and label not in found:
            found.append(label)
    return ", ".join(found[:3]) if found else "Unknown"

def format_runtime(minutes):
    try:
        total = int(minutes or 0)
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return ""
    hours, mins = divmod(total, 60)
    if hours and mins:
        return f"{hours}hr {mins}min"
    if hours:
        return f"{hours}hr"
    return f"{mins}min"

def format_date(value, with_time=False):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return str(value)
    if with_time and (dt.hour or dt.minute):
        return dt.strftime("%d %b, %I:%M %p").replace(" 0", " ")
    return dt.strftime("%d %b").replace(" 0", " ")

def unique_media(items):
    seen = set()
    output = []
    for item in items:
        key = (item.get("source", "tmdb"), item.get("type"), item.get("id"), item.get("title"))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output

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
    caption = file.get("caption", "")
    parsed = parse_media_filename(name)
    return {
        "id": str(file["_id"]),
        "name": name,
        "caption": caption,
        "size": get_size(file.get("file_size", 0)),
        "raw_size": file.get("file_size", 0),
        "title": parsed.get("title") or name,
        "year": parsed.get("year"),
        "season": parsed.get("season"),
        "episode": parsed.get("episode"),
        "quality": detect_quality(name, caption),
        "language": detect_language(name, caption),
    }

def match_file_to_tmdb(file, title, year=None, media_type=None):
    model = file_model(file)
    target = normalize_title(title)
    parsed_title = normalize_title(model["title"])
    if not target:
        model["match_score"] = 0
        return model

    if parsed_title != target:
        model["match_score"] = 0
        return model

    score = 1.0
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
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TMDB_BASE}/search/multi",
                params={"api_key": TMDB_API_KEY, "query": query, "page": page, "include_adult": "true"}
            ) as resp:
                data = await resp.json()
        results = []
        for r in data.get("results", []):
            if r.get("media_type") not in ["movie", "tv"]:
                continue
            title = r.get("title") or r.get("name", "")
            date = r.get("release_date") or r.get("first_air_date", "")
            year = date[:4] if date else ""
            poster = f"https://image.tmdb.org/t/p/w342{r['poster_path']}" if r.get("poster_path") else None
            backdrop = f"https://image.tmdb.org/t/p/w1280{r['backdrop_path']}" if r.get("backdrop_path") else None
            results.append({
                "id": r["id"],
                "title": title,
                "year": year,
                "type": r["media_type"],
                "rating": round(r.get("vote_average", 0), 1),
                "poster": poster,
                "backdrop": backdrop,
                "overview": r.get("overview", ""),
                "genres": r.get("genre_ids", [])
            })
        return web.json_response({"results": results, "total_pages": data.get("total_pages", 1)})
    except Exception as e:
        return web.json_response({"results": [], "error": str(e)}, status=500)


def tmdb_image(path, size="w342"):
    return f"https://image.tmdb.org/t/p/{size}{path}" if path else None

def tmdb_item(r, media_type=None, source="TMDB"):
    mt = media_type or r.get("media_type", "movie")
    title = r.get("title") or r.get("name", "")
    date = r.get("release_date") or r.get("first_air_date", "")
    return {
        "id": r["id"],
        "title": title,
        "year": date[:4] if date else "",
        "type": mt,
        "source": source,
        "rating": round(r.get("vote_average", 0), 1),
        "poster": tmdb_image(r.get("poster_path"), "w342"),
        "backdrop": tmdb_image(r.get("backdrop_path"), "w1280"),
        "overview": r.get("overview", ""),
        "genres": r.get("genre_ids", [])
    }

def jikan_item(r):
    images = r.get("images", {}).get("jpg", {})
    aired = r.get("aired", {}).get("from", "") or ""
    return {
        "id": r.get("mal_id"),
        "title": r.get("title_english") or r.get("title") or "",
        "year": aired[:4] if aired else "",
        "type": "anime",
        "source": "MyAnimeList",
        "rating": round(r.get("score") or 0, 1),
        "poster": images.get("large_image_url") or images.get("image_url"),
        "backdrop": images.get("large_image_url") or images.get("image_url"),
        "overview": r.get("synopsis", ""),
        "genres": []
    }

def provider_name(providers):
    for region in ("IN", "US"):
        region_data = providers.get("results", {}).get(region, {})
        for key in ("flatrate", "rent", "buy"):
            if region_data.get(key):
                return region_data[key][0].get("provider_name", "")
    return ""

def movie_ott_label(details):
    platform = provider_name(details.get("watch/providers", {}))
    release_date = ""
    for country in details.get("release_dates", {}).get("results", []):
        if country.get("iso_3166_1") not in ("IN", "US"):
            continue
        for release in country.get("release_dates", []):
            if release.get("type") in (4, 6, 3):
                release_date = format_date(release.get("release_date"))
                break
        if release_date:
            break
    if release_date and platform:
        return f"{release_date} ({platform})"
    return release_date or (f"Available ({platform})" if platform else details.get("status", ""))

def pick_trailer(videos):
    for video in videos.get("results", []):
        if video.get("site") == "YouTube" and video.get("type") in ("Trailer", "Teaser"):
            return video.get("key")
    return ""

def fmt_episode(episode):
    if not episode:
        return None
    return {
        "name": episode.get("name") or "Upcoming episode",
        "season": episode.get("season_number"),
        "episode": episode.get("episode_number"),
        "air_date": format_date(episode.get("air_date")),
        "runtime": format_runtime(episode.get("runtime")),
        "overview": episode.get("overview", ""),
        "still": tmdb_image(episode.get("still_path"), "w300"),
    }

def detail_episode_label(episode):
    if not episode:
        return "New episode"
    season = episode.get("season")
    ep = episode.get("episode")
    if season is not None and ep is not None:
        return f"S{season}|E{ep}"
    if ep is not None:
        return f"E{ep}"
    return "New episode"

@routes.get("/api/media-details")
async def media_details_handler(request):
    if not TMDB_API_KEY:
        return web.json_response({"error": "TMDB API key not configured"}, status=503)
    media_id = request.query.get("id", "").strip()
    media_type = request.query.get("type", "movie").strip()
    if media_type == "anime":
        media_type = "tv"
    if media_type not in ("movie", "tv") or not media_id:
        return web.json_response({"error": "Invalid media"}, status=400)
    append = "videos,watch/providers,external_ids"
    append += ",release_dates" if media_type == "movie" else ",content_ratings"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TMDB_BASE}/{media_type}/{media_id}",
                params={"api_key": TMDB_API_KEY, "append_to_response": append}
            ) as resp:
                details = await resp.json()
        if details.get("success") is False:
            return web.json_response({"error": details.get("status_message", "Not found")}, status=404)
        payload = {
            "id": details.get("id"),
            "title": details.get("title") or details.get("name"),
            "type": media_type,
            "year": (details.get("release_date") or details.get("first_air_date") or "")[:4],
            "rating": round(details.get("vote_average") or 0, 1),
            "runtime": format_runtime(details.get("runtime") or (details.get("episode_run_time") or [0])[0]),
            "genres": [genre.get("name") for genre in details.get("genres", [])],
            "overview": details.get("overview", ""),
            "tagline": details.get("tagline", ""),
            "status": details.get("status", ""),
            "ott_status": movie_ott_label(details) if media_type == "movie" else "",
            "first_air_date": format_date(details.get("first_air_date")),
            "next_episode": fmt_episode(details.get("next_episode_to_air")),
            "last_episode": fmt_episode(details.get("last_episode_to_air")),
            "seasons": details.get("number_of_seasons"),
            "episodes": details.get("number_of_episodes"),
            "trailer_key": pick_trailer(details.get("videos", {})),
            "external_ids": details.get("external_ids", {}),
            "providers": provider_name(details.get("watch/providers", {})),
        }
        return web.json_response(payload)
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
                (f"{TMDB_BASE}/discover/tv", {"api_key": TMDB_API_KEY, "with_genres": "16", "sort_by": "popularity.desc", "page": "1"}),
            ]
            responses = []
            for url, params in urls:
                async with session.get(url, params=params) as r:
                    responses.append(await r.json())
            try:
                async with session.get(f"{JIKAN_BASE}/top/anime", params={"filter": "airing", "limit": "20"}) as r:
                    mal_response = await r.json()
            except Exception:
                mal_response = {"data": []}

        def fmt(items, media_type=None):
            return [tmdb_item(r, media_type) for r in items[:20]]

        trending_all = fmt(responses[0].get("results", []))
        popular_movies = fmt(responses[1].get("results", []), "movie")
        popular_tv = fmt(responses[2].get("results", []), "tv")
        top_rated = fmt(responses[3].get("results", []), "movie")
        popular_anime = unique_media(fmt(responses[4].get("results", []), "anime") + [jikan_item(r) for r in mal_response.get("data", []) if r.get("mal_id")])
        mixed_trending = unique_media(trending_all + popular_anime[:8])

        hero = next((x for x in mixed_trending if x["backdrop"]), mixed_trending[0] if mixed_trending else None)

        return web.json_response({
            "hero": hero,
            "trending": mixed_trending,
            "popular_movies": popular_movies,
            "popular_tv": popular_tv,
            "popular_anime": popular_anime,
            "top_rated": top_rated,
            "bot_username": temp.U_NAME
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.get("/api/airing-today")
async def airing_today_handler(request):
    if not TMDB_API_KEY:
        return web.json_response({"results": [], "error": "TMDB API key not configured"}, status=503)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TMDB_BASE}/tv/airing_today", params={"api_key": TMDB_API_KEY, "page": "1"}) as resp:
                tmdb_data = await resp.json()
            try:
                async with session.get(f"{JIKAN_BASE}/seasons/now", params={"limit": "20"}) as resp:
                    mal_data = await resp.json()
            except Exception:
                mal_data = {"data": []}
        today = datetime.now(timezone.utc).date().isoformat()
        results = []
        for item in tmdb_data.get("results", [])[:16]:
            model = tmdb_item(item, "tv")
            details = {}
            try:
                async with session.get(f"{TMDB_BASE}/tv/{item.get('id')}", params={"api_key": TMDB_API_KEY}) as detail_resp:
                    details = await detail_resp.json()
            except Exception:
                details = {}
            next_episode = fmt_episode(details.get("next_episode_to_air") or details.get("last_episode_to_air"))
            network = next((network.get("name") for network in details.get("networks", []) if network.get("name")), "")
            model.update({
                "episode_label": detail_episode_label(next_episode) if next_episode else "New episode",
                "episode_name": next_episode.get("name") if next_episode else item.get("name", ""),
                "air_time": next_episode.get("air_date") if next_episode else format_date(item.get("first_air_date")),
                "platform": network or "TMDB",
            })
            results.append(model)
        for item in mal_data.get("data", [])[:20]:
            model = jikan_item(item)
            broadcast = item.get("broadcast", {}) or {}
            model.update({
                "episode_label": f"S{item.get('season') or ''}|E{item.get('episodes') or '?'}".replace("S|", "S?|" ),
                "episode_name": item.get("title_japanese") or item.get("title") or "",
                "air_time": broadcast.get("time") or broadcast.get("day") or today,
                "platform": "MyAnimeList",
            })
            results.append(model)
        return web.json_response({"results": results[:35]})
    except Exception as e:
        return web.json_response({"results": [], "error": str(e)}, status=500)


@routes.get("/api/repair-status")
async def repair_status_handler(request):
    repair = await db.get_repair_mode()
    return web.json_response({"repair_mode": repair})


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
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        }
    )

    if return_resp.status == 200:
        return_resp.headers.add("Content-Length", str(file_size))

    return return_resp
