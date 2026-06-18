import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    CallbackQuery, LinkPreviewOptions
)
from multimovies_api import (
    search, get_trending, get_popular, get_recently_added,
    get_featured, get_item_info, build_player_url, find_best_match
)

MULTIMOVIES_BASE = "https://multimoviesapis.vercel.app"

MAX_RESULTS = 8


def _result_buttons(items: list, show_type: bool = False) -> list:
    btn = []
    for item in items[:MAX_RESULTS]:
        info = get_item_info(item)
        if not info["slug"]:
            continue
        label_type = f"[{info['type'].upper()}] " if show_type else ""
        year = f" ({info['year']})" if info['year'] else ""
        label = f"🎬 {label_type}{info['title']}{year}"
        btn.append([
            InlineKeyboardButton(label[:64], url=info["player_url"])
        ])
    return btn


def _format_list(items: list, heading: str) -> tuple[str, list]:
    if not items:
        return f"<b>{heading}</b>\n\nNo results found.", []
    lines = [f"<b>{heading}</b>\n"]
    for i, item in enumerate(items[:MAX_RESULTS], 1):
        info = get_item_info(item)
        year = f" ({info['year']})" if info['year'] else ""
        rating = f" ⭐ {info['rating']}" if info['rating'] else ""
        lines.append(f"{i}. <b>{info['title']}</b>{year}{rating}")
    text = "\n".join(lines)
    btn = _result_buttons(items, show_type=True)
    btn.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])
    return text, btn


@Client.on_message(filters.command("online") & (filters.group | filters.private))
async def online_search(client, message):
    query = " ".join(message.command[1:]).strip()
    if not query:
        return await message.reply_text(
            "<b>🌐 Online Search</b>\n\nUsage: <code>/online &lt;movie or show title&gt;</code>\n\n"
            "Searches across thousands of movies & TV shows via MultiMoviesAPI and gives you a direct ad-blocked player link.",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

    s = await message.reply_text(f"<b>🔎 Searching online for: <code>{query}</code>...</b>")
    results = await search(query)
    if not results:
        await s.edit_text(
            f"<b>❌ No online results found for <code>{query}</code>.</b>\n\n"
            "Try a different spelling or use /trending to explore content.",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return

    text, btn = _format_list(results, f"🌐 Online Results for \"{query}\"")
    text += "\n\n<i>Tap a button to open the ad-blocked player.</i>"
    await s.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn) if btn else None,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )


@Client.on_message(filters.command("trending") & (filters.group | filters.private))
async def trending_command(client, message):
    args = message.command[1:]
    type_ = "tv" if args and args[0].lower() in ("tv", "show", "series") else "movie"

    s = await message.reply_text(f"<b>📈 Fetching trending {'TV Shows' if type_ == 'tv' else 'Movies'}...</b>")
    items = await get_trending(type_)
    label = "📈 Trending TV Shows" if type_ == "tv" else "📈 Trending Movies"
    text, btn = _format_list(items, label)

    toggle_type = "tv" if type_ == "movie" else "movie"
    toggle_label = "Switch to TV Shows 📺" if type_ == "movie" else "Switch to Movies 🎬"
    btn.insert(0, [InlineKeyboardButton(toggle_label, callback_data=f"trending_type#{toggle_type}")])

    await s.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )


@Client.on_callback_query(filters.regex(r"^trending_type#"))
async def trending_type_cb(client, query: CallbackQuery):
    _, type_ = query.data.split("#")
    items = await get_trending(type_)
    label = "📈 Trending TV Shows" if type_ == "tv" else "📈 Trending Movies"
    text, btn = _format_list(items, label)

    toggle_type = "tv" if type_ == "movie" else "movie"
    toggle_label = "Switch to TV Shows 📺" if type_ == "movie" else "Switch to Movies 🎬"
    btn.insert(0, [InlineKeyboardButton(toggle_label, callback_data=f"trending_type#{toggle_type}")])

    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )
    await query.answer()


@Client.on_message(filters.command("popular") & (filters.group | filters.private))
async def popular_command(client, message):
    args = message.command[1:]
    type_ = "tv" if args and args[0].lower() in ("tv", "show", "series") else "movie"

    s = await message.reply_text(f"<b>🔥 Fetching popular {'TV Shows' if type_ == 'tv' else 'Movies'}...</b>")
    items = await get_popular(type_)
    label = "🔥 Popular TV Shows" if type_ == "tv" else "🔥 Popular Movies"
    text, btn = _format_list(items, label)

    toggle_type = "tv" if type_ == "movie" else "movie"
    toggle_label = "Switch to TV Shows 📺" if type_ == "movie" else "Switch to Movies 🎬"
    btn.insert(0, [InlineKeyboardButton(toggle_label, callback_data=f"popular_type#{toggle_type}")])

    await s.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )


@Client.on_callback_query(filters.regex(r"^popular_type#"))
async def popular_type_cb(client, query: CallbackQuery):
    _, type_ = query.data.split("#")
    items = await get_popular(type_)
    label = "🔥 Popular TV Shows" if type_ == "tv" else "🔥 Popular Movies"
    text, btn = _format_list(items, label)

    toggle_type = "tv" if type_ == "movie" else "movie"
    toggle_label = "Switch to TV Shows 📺" if type_ == "movie" else "Switch to Movies 🎬"
    btn.insert(0, [InlineKeyboardButton(toggle_label, callback_data=f"popular_type#{toggle_type}")])

    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )
    await query.answer()


@Client.on_message(filters.command("newmovies") & (filters.group | filters.private))
async def recently_added_command(client, message):
    args = message.command[1:]
    type_ = "tv" if args and args[0].lower() in ("tv", "show", "series") else "movie"

    s = await message.reply_text(f"<b>🆕 Fetching recently added {'TV Shows' if type_ == 'tv' else 'Movies'}...</b>")
    items = await get_recently_added(type_)
    label = "🆕 Recently Added TV Shows" if type_ == "tv" else "🆕 Recently Added Movies"
    text, btn = _format_list(items, label)
    btn.append([InlineKeyboardButton("Switch to TV Shows 📺" if type_ == "movie" else "Switch to Movies 🎬",
                                      callback_data=f"newmovies_type#{'tv' if type_ == 'movie' else 'movie'}")])

    await s.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )


@Client.on_callback_query(filters.regex(r"^newmovies_type#"))
async def newmovies_type_cb(client, query: CallbackQuery):
    _, type_ = query.data.split("#")
    items = await get_recently_added(type_)
    label = "🆕 Recently Added TV Shows" if type_ == "tv" else "🆕 Recently Added Movies"
    text, btn = _format_list(items, label)
    btn.append([InlineKeyboardButton("Switch to TV Shows 📺" if type_ == "movie" else "Switch to Movies 🎬",
                                      callback_data=f"newmovies_type#{'tv' if type_ == 'movie' else 'movie'}")])

    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(btn),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        parse_mode="html"
    )
    await query.answer()
