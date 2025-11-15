import asyncio
import aiohttp
import json
import re
from urllib.parse import quote
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta
from .models import TrackedUser

# ============= NORMALIZED API LAYER =============

class LeetCodeAPI:
    """Unified LeetCode API client with multiple fallback strategies."""
    TIMEOUT = 30

    @staticmethod
    async def fetch_user_data(username: str) -> dict:
        """
        Fetch comprehensive user data. Returns normalized dict:
        {
            "username": str,
            "display_name": str,
            "total_solved": int,
            "easy_solved": int,
            "medium_solved": int,
            "hard_solved": int,
            "ranking": int or None,
            "contest_rating": float or None,
            "current_streak": int,
            "max_streak": int,
            "recent_submissions": list,
            "error": str or None
        }
        """
        timeout = aiohttp.ClientTimeout(total=LeetCodeAPI.TIMEOUT)
        safe_username = quote(username, safe='')
        
        profile_data = None
        submissions_data = None
        contest_data = None
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Try REST profile endpoints
            profile_endpoints = [
                f"https://leetcode-stats-api.herokuapp.com/{safe_username}",
                f"https://alfa-leetcode-api.onrender.com/userProfile/{safe_username}",
                f"https://alfa-leetcode-api.onrender.com/{safe_username}",
            ]
            
            for endpoint in profile_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=15), headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': 'https://leetcode.com'
                    }) as resp:
                        if resp.status == 200:
                            profile_data = await resp.json()
                            break
                except Exception:
                    continue
            
            # Fallback: GraphQL matchedUser query
            if not profile_data:
                try:
                    gql_resp = await session.post(
                        "https://leetcode.com/graphql",
                        json={
                            "query": """
                                query u($username: String!) {
                                    matchedUser(username: $username) {
                                        username
                                        profile { realName userAvatar }
                                        submitStats { acSubmissionNum { difficulty count } }
                                        submissionCalendar
                                        ranking
                                    }
                                }
                            """,
                            "variables": {"username": username}
                        },
                        headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://leetcode.com'},
                        timeout=aiohttp.ClientTimeout(total=15)
                    )
                    if gql_resp.status == 200:
                        gql_data = await gql_resp.json()
                        m = (gql_data.get('data', {}) or {}).get('matchedUser')
                        if m:
                            profile_data = {
                                'username': m.get('username'),
                                'name': (m.get('profile') or {}).get('realName'),
                                'totalSolved': sum(
                                    item.get('count', 0) 
                                    for item in (m.get('submitStats', {}).get('acSubmissionNum') or [])
                                    if (item.get('difficulty') or '').lower() != 'all'
                                ),
                                'easySolved': next(
                                    (item.get('count', 0) for item in (m.get('submitStats', {}).get('acSubmissionNum') or [])
                                     if (item.get('difficulty') or '').lower() == 'easy'), 0
                                ),
                                'mediumSolved': next(
                                    (item.get('count', 0) for item in (m.get('submitStats', {}).get('acSubmissionNum') or [])
                                     if (item.get('difficulty') or '').lower() == 'medium'), 0
                                ),
                                'hardSolved': next(
                                    (item.get('count', 0) for item in (m.get('submitStats', {}).get('acSubmissionNum') or [])
                                     if (item.get('difficulty') or '').lower() == 'hard'), 0
                                ),
                                'ranking': m.get('ranking'),
                                'submissionCalendar': m.get('submissionCalendar')
                            }
                except Exception:
                    pass
            
            if not profile_data:
                return {"error": f"User '{username}' not found", "username": username}
            
            # Fetch submissions
            submission_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/{safe_username}/submission",
                f"https://alfa-leetcode-api.onrender.com/{safe_username}/acSubmission",
            ]
            
            for endpoint in submission_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=15), headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': 'https://leetcode.com'
                    }) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, dict) and 'submission' in data:
                                submissions_data = data.get('submission', [])
                            elif isinstance(data, list):
                                submissions_data = data
                            if submissions_data:
                                break
                except Exception:
                    continue
            
            # Fetch contest rating
            contest_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/userContestRankingInfo/{safe_username}",
                f"https://alfa-leetcode-api.onrender.com/{safe_username}/contest",
            ]
            
            for endpoint in contest_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=15), headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': 'https://leetcode.com'
                    }) as resp:
                        if resp.status == 200:
                            contest_data = await resp.json()
                            if contest_data:
                                break
                except Exception:
                    continue
        
        return {
            "username": username,
            "profile": profile_data or {},
            "submissions": submissions_data or [],
            "contest": contest_data or {},
            "error": None
        }


def normalize_timestamp(ts) -> int or None:
    """Convert timestamp to unix seconds."""
    if ts is None or ts == '':
        return None
    try:
        t = int(float(ts))
        return t if t < 10**11 else t // 1000
    except Exception:
        try:
            return int(datetime.fromisoformat(str(ts)).timestamp())
        except Exception:
            return None


def calculate_streak(submission_calendar) -> tuple:
    """Calculate current and max streak from submission calendar."""
    if not submission_calendar:
        return 0, 0
    
    dates = []
    for ts_str in submission_calendar.keys():
        try:
            t = int(ts_str)
            if t > 10**12:
                t = t // 1000
            dates.append(datetime.fromtimestamp(t).date())
        except Exception:
            continue
    
    if not dates:
        return 0, 0
    
    dates = sorted(set(dates))
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    current_streak = 0
    if today in dates or yesterday in dates:
        current_date = today if today in dates else yesterday
        current_streak = 1
        for i in range(1, len(dates)):
            prev_date = current_date - timedelta(days=1)
            if prev_date in dates:
                current_streak += 1
                current_date = prev_date
            else:
                break
    
    max_streak = 0
    temp_streak = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            temp_streak += 1
            max_streak = max(max_streak, temp_streak)
        else:
            temp_streak = 1
    
    max_streak = max(max_streak, temp_streak)
    return current_streak, max_streak


def parse_user_stats(raw_data: dict) -> dict:
    """Normalize raw API data to standard format."""
    if raw_data.get("error"):
        return {
            "username": raw_data.get("username", "Unknown"),
            "display_name": raw_data.get("username", "Unknown"),
            "total_solved": 0,
            "easy_solved": 0,
            "medium_solved": 0,
            "hard_solved": 0,
            "ranking": None,
            "contest_rating": None,
            "current_streak": 0,
            "max_streak": 0,
            "recent_submissions": [],
            "error": raw_data.get("error")
        }
    
    profile = raw_data.get("profile", {})
    submissions = raw_data.get("submissions", [])
    contest = raw_data.get("contest", {})
    
    # Extract display name
    display_name = profile.get("name") or profile.get("realName") or profile.get("username") or raw_data.get("username", "Unknown")
    
    # Extract stats
    total_solved = profile.get("totalSolved") or profile.get("total", 0)
    easy_solved = profile.get("easySolved") or profile.get("easy", 0)
    medium_solved = profile.get("mediumSolved") or profile.get("medium", 0)
    hard_solved = profile.get("hardSolved") or profile.get("hard", 0)
    ranking = profile.get("ranking")
    
    # Calculate streaks
    current_streak, max_streak = calculate_streak(profile.get("submissionCalendar"))
    
    # Parse recent submissions
    recent_submissions = []
    if isinstance(submissions, list):
        for sub in submissions[:20]:
            ts = normalize_timestamp(sub.get("timestamp"))
            recent_submissions.append({
                "title": sub.get("title") or sub.get("titleSlug") or "Unknown",
                "status": sub.get("statusDisplay") or sub.get("status") or "Unknown",
                "timestamp": ts,
                "lang": sub.get("lang") or sub.get("language") or "N/A"
            })
    
    # Extract contest rating
    contest_rating = None
    if isinstance(contest, dict):
        cr = contest.get("rating") or contest.get("contestRating")
        if cr and cr != 'N/A':
            try:
                contest_rating = float(cr)
            except Exception:
                pass
    
    return {
        "username": raw_data.get("username", "Unknown"),
        "display_name": display_name,
        "total_solved": total_solved or 0,
        "easy_solved": easy_solved or 0,
        "medium_solved": medium_solved or 0,
        "hard_solved": hard_solved or 0,
        "ranking": ranking,
        "contest_rating": contest_rating,
        "current_streak": current_streak,
        "max_streak": max_streak,
        "recent_submissions": recent_submissions,
        "error": None
    }


# ============= VIEWS =============

async def get_user_data(username: str):
    """Fetch and parse user data."""
    raw = await LeetCodeAPI.fetch_user_data(username)
    stats = parse_user_stats(raw)
    
    # Persist to DB
    if not stats.get("error"):
        try:
            db_user, _ = await TrackedUser.objects.aget_or_create(
                username=stats.get("username"),
                defaults={"display_name": stats.get("display_name")}
            )
            await asyncio.to_thread(db_user.update_stats, stats)
        except Exception:
            pass
    
    return stats


def home(request):
    """Home page with all tracked users."""
    users = TrackedUser.objects.all().order_by('-view_count', '-total_solved')
    featured = TrackedUser.objects.filter(is_featured=True)[:6]
    
    return render(request, 'tracker/home.html', {
        'total_users': users.count(),
        'tracked_users': users,
        'featured_users': featured,
        'top_performers': users[:10],
    })


def profile(request, username):
    """Profile page with server-side data fetch."""
    tracked_user, _ = TrackedUser.objects.get_or_create(
        username=username,
        defaults={'display_name': username}
    )
    tracked_user.increment_views()
    
    # Fetch data server-side
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(get_user_data(username))
        loop.close()
    except Exception as e:
        stats = {"error": str(e), "username": username, "display_name": username}
    
    # Fallback to DB cache
    if stats.get("error"):
        stats = {
            "username": tracked_user.username,
            "display_name": tracked_user.display_name or tracked_user.username,
            "total_solved": tracked_user.total_solved,
            "easy_solved": tracked_user.easy_solved,
            "medium_solved": tracked_user.medium_solved,
            "hard_solved": tracked_user.hard_solved,
            "ranking": tracked_user.ranking,
            "contest_rating": tracked_user.contest_rating,
            "current_streak": tracked_user.current_streak,
            "max_streak": tracked_user.max_streak,
            "recent_submissions": tracked_user.recent_submissions or [],
            "error": None
        }
    
    initial_json = json.dumps(stats, default=str)
    
    return render(request, 'tracker/profile.html', {
        'username': username,
        'initial_data_json': initial_json,
    })


def profiles(request):
    """Multi-user profiles page."""
    q = request.GET.get('usernames', '').strip()
    if not q:
        return render(request, 'tracker/home.html', {
            'total_users': 0,
            'tracked_users': [],
            'featured_users': [],
            'top_performers': [],
        })
    
    usernames = [u.strip() for u in re.split(r'[\s,]+', q) if u.strip()][:50]
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [get_user_data(u) for u in usernames]
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
    except Exception:
        results = [{"error": "Failed to fetch", "username": u} for u in usernames]
    
    users = []
    for idx, r in enumerate(results):
        if isinstance(r, Exception):
            r = {"error": str(r), "username": usernames[idx] if idx < len(usernames) else "unknown"}
        
        if r.get("error"):
            # Try DB fallback
            try:
                db = TrackedUser.objects.filter(username__iexact=usernames[idx] if idx < len(usernames) else "").first()
                if db:
                    r = {
                        "username": db.username,
                        "display_name": db.display_name or db.username,
                        "total_solved": db.total_solved,
                        "easy_solved": db.easy_solved,
                        "medium_solved": db.medium_solved,
                        "hard_solved": db.hard_solved,
                        "ranking": db.ranking,
                        "contest_rating": db.contest_rating,
                        "current_streak": db.current_streak,
                        "max_streak": db.max_streak,
                        "recent_submissions": db.recent_submissions or [],
                        "error": None
                    }
            except Exception:
                pass
        
        users.append(r)
    
    valid = [u for u in users if not u.get("error")]
    invalid = [u for u in users if u.get("error")]
    valid.sort(key=lambda x: x.get("total_solved", 0), reverse=True)
    users = valid + invalid
    
    return render(request, 'tracker/home.html', {
        'total_users': len(users),
        'tracked_users': users,
        'featured_users': [],
        'top_performers': [],
    })


def api_user_data(request, username):
    """API endpoint: single user data."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(get_user_data(username))
        loop.close()
        
        if stats.get("error"):
            try:
                db = TrackedUser.objects.filter(username__iexact=username).first()
                if db:
                    stats = {
                        "username": db.username,
                        "display_name": db.display_name or db.username,
                        "total_solved": db.total_solved,
                        "easy_solved": db.easy_solved,
                        "medium_solved": db.medium_solved,
                        "hard_solved": db.hard_solved,
                        "ranking": db.ranking,
                        "contest_rating": db.contest_rating,
                        "current_streak": db.current_streak,
                        "max_streak": db.max_streak,
                        "recent_submissions": db.recent_submissions or [],
                        "error": None
                    }
            except Exception:
                pass
        
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({"error": str(e), "username": username}, status=500)


def api_user_data_multi(request):
    """API endpoint: multiple users data."""
    usernames = []
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
            if isinstance(body, dict) and body.get('usernames'):
                usernames = list(body.get('usernames'))
        except Exception:
            pass
    else:
        q = request.GET.get('usernames', '').strip()
        if q:
            usernames = [u.strip() for u in re.split(r'[\s,]+', q) if u.strip()]
    
    if not usernames:
        return JsonResponse({'error': 'No usernames provided', 'results': []}, status=400)
    
    try:
        limit = int(request.GET.get('limit', 20))
    except Exception:
        limit = 20
    
    if limit and limit > 0:
        usernames = usernames[:limit]
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [get_user_data(u) for u in usernames]
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
    except Exception:
        results = [{"error": "Failed", "username": u} for u in usernames]
    
    out = []
    for r in results:
        if isinstance(r, Exception):
            r = {"error": str(r)}
        out.append(r)
    
    return JsonResponse({'count': len(out), 'results': out})


def api_users_list(request):
    """API endpoint: list all tracked users."""
    try:
        limit_param = request.GET.get('limit', '20')
        if isinstance(limit_param, str) and limit_param.lower() == 'all':
            limit = None
        else:
            limit = int(limit_param) if limit_param else 20
        
        if limit and limit <= 0:
            limit = None
        
        users = TrackedUser.objects.all().order_by('-view_count', '-total_solved')
        if limit:
            users = users[:limit]
        
        data = []
        for u in users:
            data.append({
                "username": u.username,
                "display_name": u.display_name or u.username,
                "total_solved": u.total_solved,
                "easy_solved": u.easy_solved,
                "medium_solved": u.medium_solved,
                "hard_solved": u.hard_solved,
                "ranking": u.ranking,
                "contest_rating": u.contest_rating,
                "current_streak": u.current_streak,
                "max_streak": u.max_streak,
                "view_count": u.view_count,
                "is_featured": u.is_featured,
            })
        
        return JsonResponse({
            "total": TrackedUser.objects.count(),
            "count": len(data),
            "users": data
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_leaderboard(request):
    """API endpoint: leaderboard."""
    try:
        category = request.GET.get('category', 'total')
        limit = int(request.GET.get('limit', 10))
        
        if category == 'easy':
            users = TrackedUser.objects.order_by('-easy_solved')[:limit]
            key = 'easy_solved'
        elif category == 'medium':
            users = TrackedUser.objects.order_by('-medium_solved')[:limit]
            key = 'medium_solved'
        elif category == 'hard':
            users = TrackedUser.objects.order_by('-hard_solved')[:limit]
            key = 'hard_solved'
        elif category == 'contest':
            users = TrackedUser.objects.filter(contest_rating__isnull=False).order_by('-contest_rating')[:limit]
            key = 'contest_rating'
        else:
            users = TrackedUser.objects.order_by('-total_solved')[:limit]
            key = 'total_solved'
        
        board = []
        for rank, u in enumerate(users, 1):
            board.append({
                "rank": rank,
                "username": u.username,
                "display_name": u.display_name or u.username,
                "value": getattr(u, key),
            })
        
        return JsonResponse({'category': category, 'leaderboard': board})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_debug_raw(request, username):
    """API endpoint: debug raw upstream response."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        raw = loop.run_until_complete(LeetCodeAPI.fetch_user_data(username))
        loop.close()
        return JsonResponse(raw, json_dumps_params={'indent': 2})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
