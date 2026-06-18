import aiohttp
import asyncio
import re
import logging

logger = logging.getLogger(__name__)

MULTIMOVIES_BASE = "https://multimoviesapis.vercel.app"


def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


async def _get(path: str, params: dict = None, timeout: int = 10):
    url = f"{MULTIMOVIES_BASE}{path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.warning(f"MultiMoviesAPI request failed [{path}]: {e}")
    return None


async def search(query: str) -> list:
    data = await _get("/api/search", params={"q": query})
    if data and data.get("success"):
        return data.get("results", [])
    return []


async def search_suggest(query: str) -> list:
    data = await _get("/api/search/suggest", params={"q": query})
    if data and data.get("success"):
        return data.get("results", [])
    return []


async def get_movie(slug: str) -> dict | None:
    data = await _get(f"/api/movies/{slug}")
    if data and data.get("success"):
        return data.get("results")
    return None


async def get_tvshow(slug: str) -> dict | None:
    data = await _get(f"/api/tvshows/{slug}")
    if data and data.get("success"):
        return data.get("results")
    return None


async def get_trending(type_: str = "movie") -> list:
    data = await _get("/api/trending", params={"type": type_})
    if data and data.get("success"):
        return data.get("results", [])
    return []


async def get_popular(type_: str = "movie") -> list:
    data = await _get("/api/popular", params={"type": type_})
    if data and data.get("success"):
        return data.get("results", [])
    return []


async def get_recently_added(type_: str = "movie") -> list:
    data = await _get("/api/recently-added", params={"type": type_})
    if data and data.get("success"):
        return data.get("results", [])
    return []


async def get_featured() -> list:
    data = await _get("/api/featured")
    if data and data.get("success"):
        return data.get("results", [])
    return []


def build_player_url(slug: str, type_: str = "movie", title: str = None,
                     season: int = None, episode: int = None) -> str:
    from urllib.parse import quote_plus
    params = [f"type={type_}"]
    if title:
        params.append(f"title={quote_plus(title)}")
    if season is not None:
        params.append(f"season={season}")
    if episode is not None:
        params.append(f"episode={episode}")
    return f"{MULTIMOVIES_BASE}/api/player/{slug}?{'&'.join(params)}"


async def find_best_match(query: str) -> dict | None:
    results = await search(query)
    if not results:
        return None
    query_lower = query.lower().strip()
    for item in results:
        title = (item.get("title") or item.get("name") or "").lower().strip()
        if title == query_lower:
            return item
    return results[0] if results else None


def get_item_info(item: dict) -> dict:
    slug = item.get("slug", "")
    title = item.get("title") or item.get("name") or "Unknown"
    type_ = "tv" if item.get("type") in ("tv", "tvshow", "series") else "movie"
    year = item.get("year") or item.get("release_year") or ""
    poster = item.get("poster") or item.get("thumbnail") or item.get("image") or ""
    genres = item.get("genres") or []
    if isinstance(genres, list):
        genres = ", ".join(g.get("name", g) if isinstance(g, dict) else str(g) for g in genres)
    rating = item.get("rating") or item.get("imdb_rating") or ""
    return {
        "slug": slug,
        "title": title,
        "type": type_,
        "year": year,
        "poster": poster,
        "genres": genres,
        "rating": rating,
        "player_url": build_player_url(slug, type_, title),
    }
