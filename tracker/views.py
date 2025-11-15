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


class LeetCodeAPI:
    TIMEOUT = 30

    @staticmethod
    async def fetch_user_data(username: str):
        """Fetch comprehensive user data from LeetCode API"""
        timeout = aiohttp.ClientTimeout(total=LeetCodeAPI.TIMEOUT)
        
        profile_data = None
        submissions_data = None
        contest_data = None
        api_used = None
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # ===== FETCH PROFILE DATA =====
            # URL-encode username for inclusion in REST endpoints (prevents spaces/special-char issues)
            safe_username = quote(username, safe='')

            profile_endpoints = [
                f"https://leetcode-stats-api.herokuapp.com/{safe_username}",
                f"https://alfa-leetcode-api.onrender.com/userProfile/{safe_username}",
                f"https://alfa-leetcode-api.onrender.com/{safe_username}",
            ]
            
            for endpoint in profile_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=20), headers={
                        'User-Agent': 'LeetCode-Tracker/1.0',
                        'Referer': 'https://leetcode.com'
                    }) as response:
                        if response.status == 200:
                            profile_data = await response.json()
                            api_used = endpoint
                            break
                except Exception:
                    continue
            
            if not profile_data:
                return {"error": f"User '{username}' not found", "username": username}
            
            # ===== FETCH RECENT SUBMISSIONS =====
            submission_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/{safe_username}/submission",
                f"https://alfa-leetcode-api.onrender.com/{safe_username}/acSubmission",
            ]
            
            for sub_endpoint in submission_endpoints:
                try:
                    async with session.get(sub_endpoint, timeout=aiohttp.ClientTimeout(total=20), headers={
                        'User-Agent': 'LeetCode-Tracker/1.0',
                        'Referer': 'https://leetcode.com'
                    }) as sub_response:
                        if sub_response.status == 200:
                            temp_data = await sub_response.json()
                            if temp_data and isinstance(temp_data, dict) and 'submission' in temp_data:
                                submissions_data = temp_data
                                break
                            elif temp_data and isinstance(temp_data, list) and len(temp_data) > 0:
                                submissions_data = {'submission': temp_data}
                                break
                except Exception:
                    continue
            
            # GraphQL fallback for submissions
            if not submissions_data:
                try:
                    graphql_query = {
                        "query": """
                            query recentSubmissions($username: String!, $limit: Int!) {
                                recentSubmissionList(username: $username, limit: $limit) {
                                    title
                                    titleSlug
                                    timestamp
                                    statusDisplay
                                    lang
                                }
                            }
                        """,
                        "variables": {"username": username, "limit": 20}
                    }
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'Referer': 'https://leetcode.com'
                    }
                    
                    async with session.post(
                        "https://leetcode.com/graphql",
                        json=graphql_query,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as graphql_response:
                        if graphql_response.status == 200:
                            graphql_data = await graphql_response.json()
                            if 'data' in graphql_data and 'recentSubmissionList' in graphql_data['data']:
                                submissions_data = {
                                    'submission': graphql_data['data']['recentSubmissionList']
                                }
                except Exception as e:
                    pass
            
            # ===== FETCH CONTEST DATA =====
            contest_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/userContestRankingInfo/{safe_username}",
                f"https://alfa-leetcode-api.onrender.com/{safe_username}/contest",
            ]
            
            for contest_endpoint in contest_endpoints:
                try:
                    async with session.get(contest_endpoint, timeout=aiohttp.ClientTimeout(total=15), headers={
                        'User-Agent': 'LeetCode-Tracker/1.0',
                        'Referer': 'https://leetcode.com'
                    }) as contest_response:
                        if contest_response.status == 200:
                            temp_contest_data = await contest_response.json()
                            if temp_contest_data and isinstance(temp_contest_data, dict):
                                # Accept contest data if it has expected keys or is non-empty
                                contest_data = temp_contest_data
                                break
                except Exception as e:
                    continue
            
            return {
                "username": username,
                "profile": profile_data,
                "submissions": submissions_data,
                "contest": contest_data,
                "error": None,
                "api_used": api_used
            }


def calculate_streak_from_calendar(submission_calendar):
    """Calculate current and max streak from submission calendar"""
    if not submission_calendar:
        return 0, 0

    dates = []
    for timestamp_str in submission_calendar.keys():
        try:
            timestamp = int(timestamp_str)
            date = datetime.fromtimestamp(timestamp).date()
            dates.append(date)
        except:
            continue

    if not dates:
        return 0, 0

    dates = sorted(set(dates))
    current_streak = 0
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

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


def parse_user_stats(user_data: dict) -> dict:
    """Parse and organize user statistics"""
    if user_data.get("error"):
        return {
            "username": user_data.get("username", "Unknown"),
            "display_name": user_data.get("username", "Unknown"),
            "error": user_data["error"],
            "total_solved": 0,
            "easy": 0,
            "medium": 0,
            "hard": 0,
            "ranking": "N/A",
            "max_streak": 0,
            "current_streak": 0,
            "contest_rating": "N/A",
            "contests_attended": 0,
            "recent_submissions": [],
        }

    profile = user_data.get("profile", {})
    submissions = user_data.get("submissions", {})
    contest = user_data.get("contest", {})

    # Extract display name
    display_name = user_data.get("username", "Unknown")
    if "name" in profile and profile["name"]:
        display_name = profile["name"]
    elif "realName" in profile and profile["realName"]:
        display_name = profile["realName"]

    # Extract problem counts
    total_solved = profile.get("totalSolved", 0)
    easy_solved = profile.get("easySolved", 0)
    medium_solved = profile.get("mediumSolved", 0)
    hard_solved = profile.get("hardSolved", 0)

    # Extract ranking
    ranking = profile.get("ranking", "N/A")

    # Calculate streak from submissionCalendar
    current_streak = 0
    max_streak = 0

    if "submissionCalendar" in profile:
        current_streak, max_streak = calculate_streak_from_calendar(
            profile["submissionCalendar"]
        )

    # ===== RECENT SUBMISSIONS EXTRACTION =====
    recent_submissions = []

    # Method 1: submissions dict with 'submission' key
    if isinstance(submissions, dict) and 'submission' in submissions:
        sub_list = submissions['submission']
        if isinstance(sub_list, list):
            for sub in sub_list[:20]:
                recent_submissions.append({
                    "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                    "status": sub.get("statusDisplay", sub.get("status", "Unknown")),
                    "timestamp": sub.get("timestamp", ""),
                    "lang": sub.get("lang", "N/A")
                })

    # Method 2: submissions is directly a list
    elif isinstance(submissions, list):
        for sub in submissions[:20]:
            recent_submissions.append({
                "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                "status": sub.get("statusDisplay", sub.get("status", "Unknown")),
                "timestamp": sub.get("timestamp", ""),
                "lang": sub.get("lang", "N/A")
            })

    # Method 3: Check recentSubmissions in profile
    if not recent_submissions and "recentSubmissions" in profile:
        submissions_from_profile = profile["recentSubmissions"]
        if isinstance(submissions_from_profile, list):
            for sub in submissions_from_profile[:20]:
                recent_submissions.append({
                    "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                    "status": sub.get("statusDisplay", sub.get("status", "Unknown")),
                    "timestamp": sub.get("timestamp", ""),
                    "lang": sub.get("lang", "N/A")
                })

    # Method 4: Check for recentAcSubmissionList
    if not recent_submissions and "recentAcSubmissionList" in profile:
        ac_submissions = profile["recentAcSubmissionList"]
        if isinstance(ac_submissions, list):
            for sub in ac_submissions[:20]:
                recent_submissions.append({
                    "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                    "status": "Accepted",
                    "timestamp": sub.get("timestamp", ""),
                    "lang": sub.get("lang", "N/A")
                })

    # ===== IMPROVED CONTEST INFO EXTRACTION =====
    contest_rating = "N/A"
    contests_attended = 0

    # Helper function to safely convert to float and check if valid
    def safe_float(value):
        """Safely convert to float, return None if invalid"""
        if value is None:
            return None
        try:
            val = float(value)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    # Try ALL possible methods to extract contest rating
    extraction_methods = [
        # Method 1: Direct rating field in contest data
        lambda: (
            safe_float(contest.get("rating")) if contest else None,
            int(contest.get("attendedContestsCount", 0)) if contest and contest.get("attendedContestsCount") else 0
        ),
        # Method 2: contestRating field in contest data
        lambda: (
            safe_float(contest.get("contestRating")) if contest else None,
            int(contest.get("contestAttend", 0)) if contest and contest.get("contestAttend") else 0
        ),
        # Method 3: userContestRanking nested object in contest
        lambda: (
            safe_float(contest.get("userContestRanking", {}).get("rating")) if contest and contest.get("userContestRanking") else None,
            int(contest.get("userContestRanking", {}).get("attendedContestsCount", 0)) if contest and contest.get("userContestRanking") else 0
        ),
        # Method 4: From profile object (direct contestRating)
        lambda: (
            safe_float(profile.get("contestRating")) if profile else None,
            int(profile.get("contestAttend", 0)) if profile and profile.get("contestAttend") else 0
        ),
        # Method 5: From profile object (userContestRanking)
        lambda: (
            safe_float(profile.get("userContestRanking", {}).get("rating")) if profile and profile.get("userContestRanking") else None,
            int(profile.get("userContestRanking", {}).get("attendedContestsCount", 0)) if profile and profile.get("userContestRanking") else 0
        ),
        # Method 6: userContestRankingHistory array (get latest attended or highest rating)
        lambda: (
            safe_float(
                next(
                    (h.get("rating") for h in reversed(profile.get("userContestRankingHistory", [])) 
                     if h.get("attended")),
                    profile.get("userContestRankingHistory", [{}])[-1].get("rating") if profile.get("userContestRankingHistory") else None
                )
            ) if profile and profile.get("userContestRankingHistory") else None,
            sum(1 for h in profile.get("userContestRankingHistory", []) if h.get("attended")) if profile and profile.get("userContestRankingHistory") else 0
        ),
        # Method 7: Fallback - Any contest data from profile that might have been missed
        lambda: (
            safe_float(profile.get("ratingInfo", {}).get("rating")) if profile and profile.get("ratingInfo") else None,
            int(profile.get("ratingInfo", {}).get("attendedContestsCount", 0)) if profile and profile.get("ratingInfo") else 0
        ),
    ]

    for method in extraction_methods:
        try:
            rating, attended = method()
            if rating is not None and rating > 0:
                contest_rating = round(rating, 2)
                contests_attended = attended
                break
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            continue

    # Try to discover the canonical username returned by the API
    canonical_username = user_data.get("username") or profile.get("username") or profile.get("user_name") or profile.get("userSlug") or profile.get("user_slug")

    return {
        "username": canonical_username or user_data.get("username", "Unknown"),
        "display_name": display_name,
        "error": None,
        "correct_username": canonical_username if canonical_username and canonical_username.lower() != user_data.get("username", "").lower() else None,
        "ranking": ranking,
        "total_solved": total_solved,
        "easy": easy_solved,
        "medium": medium_solved,
        "hard": hard_solved,
        "max_streak": max_streak,
        "current_streak": current_streak,
        "contest_rating": contest_rating,
        "contests_attended": contests_attended,
        "recent_submissions": recent_submissions,
    }


# ============= VIEWS =============

def home(request):
    """Home page view - Shows all tracked users with statistics"""
    tracked_users = TrackedUser.objects.all()[:50]
    total_users = TrackedUser.objects.count()
    featured_users = TrackedUser.objects.filter(is_featured=True)[:6]
    top_performers = TrackedUser.objects.order_by('-total_solved')[:10]
    
    context = {
        'total_users': total_users,
        'tracked_users': tracked_users,
        'featured_users': featured_users,
        'top_performers': top_performers,
    }
    
    return render(request, 'tracker/home.html', context)


def profile(request, username):
    """Profile page view - Shows detailed user statistics"""
    tracked_user, created = TrackedUser.objects.get_or_create(
        username=username,
        defaults={'display_name': username}
    )
    
    tracked_user.increment_views()
    
    return render(request, 'tracker/profile.html', {'username': username})


def profiles(request):
    """Render a page showing multiple profiles supplied via ?usernames=a,b,c"""
    q = request.GET.get('usernames', '').strip()
    if not q:
        return render(request, 'tracker/home.html', {
            'total_users': 0,
            'tracked_users': [],
            'featured_users': [],
            'top_performers': [],
        })

    # Accept comma-separated or whitespace-separated lists, normalize them
    usernames = [u.strip() for u in re.split(r'[\s,]+', q) if u.strip()]
    # Limit to reasonable number
    usernames = usernames[:50]

    # Fetch stats for each username concurrently
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [get_user_data(u) for u in usernames]
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
    except Exception as e:
        results = [{'username': u, 'error': str(e)} for u in usernames]

    # Normalize results: ensure list of dicts and map keys to match template expectations
    users = []
    for r in results:
        if isinstance(r, Exception):
            users.append({
                'username': 'unknown',
                'display_name': 'Unknown',
                'total_solved': 0,
                'easy_solved': 0,
                'medium_solved': 0,
                'hard_solved': 0,
                'easy': 0,
                'medium': 0,
                'hard': 0,
                'ranking': None,
                'contest_rating': None,
                'view_count': 0,
                'is_featured': False,
                'recent_submissions': [],
                'invalid': True,
                'fetch_error': str(r),
                'error': str(r),
                'current_streak': 0,
                'max_streak': 0,
            })
        else:
            # r is stats dict from parse_user_stats
            # If parse_user_stats marked an error, propagate it; otherwise include None
            is_invalid = bool(r.get('error'))
            users.append({
                'username': r.get('username') or r.get('display_name') or 'unknown',
                'display_name': r.get('display_name', r.get('username')),
                'total_solved': r.get('total_solved', 0),
                'easy_solved': r.get('easy', r.get('easy_solved', 0)),
                'medium_solved': r.get('medium', r.get('medium_solved', 0)),
                'hard_solved': r.get('hard', r.get('hard_solved', 0)),
                'easy': r.get('easy', r.get('easy_solved', 0)),
                'medium': r.get('medium', r.get('medium_solved', 0)),
                'hard': r.get('hard', r.get('hard_solved', 0)),
                'ranking': r.get('ranking'),
                'contest_rating': r.get('contest_rating'),
                'view_count': getattr(r, 'view_count', 0) or r.get('view_count', 0),
                'is_featured': getattr(r, 'is_featured', False) or r.get('is_featured', False),
                'recent_submissions': r.get('recent_submissions', []),
                'invalid': is_invalid,
                'error': r.get('error') if is_invalid else None,
                'fetch_error': r.get('error') if is_invalid else None,
                'correct_username': r.get('correct_username'),
                'current_streak': r.get('current_streak', 0),
                'max_streak': r.get('max_streak', 0),
            })

    # Sort users: valid users first (by total_solved desc), then invalid usernames
    valid_users = [u for u in users if not u.get('invalid')]
    invalid_users = [u for u in users if u.get('invalid')]

    valid_users.sort(key=lambda x: x.get('total_solved', 0), reverse=True)
    # keep invalid users in the input order but ensure they are at the end
    users = valid_users + invalid_users

    context = {
        'total_users': len(users),
        'tracked_users': users,
        'featured_users': [],
        'top_performers': [],
    }

    return render(request, 'tracker/home.html', context)


async def get_user_data(username: str):
    """Async helper to fetch user data"""
    data = await LeetCodeAPI.fetch_user_data(username)
    stats = parse_user_stats(data)
    
    # Update tracked user in database
    if not stats.get('error'):
        try:
            # Use the canonical username returned by the API if available
            db_username = stats.get('username') or username

            tracked_user, created = await TrackedUser.objects.aget_or_create(
                username=db_username,
                defaults={'display_name': stats.get('display_name', db_username)}
            )

            # Ensure updates happen in a thread to avoid blocking the event loop
            await asyncio.to_thread(tracked_user.update_stats, stats)
        except Exception:
            # Fail silently on update errors in async path
            pass
    
    return stats


def api_user_data(request, username):
    """API endpoint to fetch user data"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        user_stats = loop.run_until_complete(get_user_data(username))
        loop.close()

        return JsonResponse(user_stats)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_user_data_multi(request):
    """API endpoint to fetch multiple users' data concurrently.

    Accepts either:
    - GET ?usernames=alice,bob,charlie
    - POST JSON { "usernames": ["alice","bob"] }

    Optional query param: limit (max users to process, default 20)
    """
    try:
        # Parse usernames from GET or POST
        usernames = []
        if request.method == 'POST':
            try:
                body = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                body = {}

            if isinstance(body, dict) and body.get('usernames'):
                usernames = list(body.get('usernames'))
        else:
            q = request.GET.get('usernames', '').strip()
            if q:
                # Accept comma-separated or whitespace-separated lists
                usernames = [u.strip() for u in re.split(r'[\s,]+', q) if u.strip()]

        if not usernames:
            return JsonResponse({'error': 'No usernames provided. Use ?usernames=a,b or POST {"usernames": [...]}'}, status=400)

        # Respect a reasonable limit to avoid overloading the server
        try:
            limit = int(request.GET.get('limit', 20))
        except Exception:
            limit = 20
        if limit <= 0:
            limit = 20

        usernames = usernames[:limit]

        # Run concurrent fetches
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [get_user_data(u) for u in usernames]
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()

        # Normalize exceptions
        out = []
        for u, r in zip(usernames, results):
            if isinstance(r, Exception):
                out.append({'username': u, 'error': str(r)})
            else:
                out.append(r)

        return JsonResponse({'count': len(out), 'results': out}, json_dumps_params={'indent': 2})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_users_list(request):
    """API endpoint to get list of all tracked users"""
    try:
        sort_by = request.GET.get('sort', 'views')
        limit = int(request.GET.get('limit', 20))
        search = request.GET.get('search', '').strip()
        
        users = TrackedUser.objects.all()
        
        if search:
            users = users.filter(
                Q(username__icontains=search) | 
                Q(display_name__icontains=search)
            )
        
        if sort_by == 'solved':
            users = users.order_by('-total_solved')
        elif sort_by == 'rating':
            users = users.order_by('-contest_rating')
        elif sort_by == 'recent':
            # Order by most recent submission, fall back to last_updated
            users = users.order_by('-last_submission', '-last_updated')
        else:
            users = users.order_by('-view_count')
        
        users = users[:limit]
        
        users_data = []
        for user in users:
            users_data.append({
                'username': user.username,
                'display_name': user.display_name or user.username,
                'total_solved': user.total_solved,
                'easy': user.easy_solved,
                'medium': user.medium_solved,
                'hard': user.hard_solved,
                'ranking': user.ranking,
                'contest_rating': user.contest_rating,
                'view_count': user.view_count,
                'is_featured': user.is_featured,
                'last_updated': user.last_updated.isoformat(),
                'current_streak': getattr(user, 'current_streak', 0) or 0,
                'max_streak': getattr(user, 'max_streak', 0) or 0,
            })
        
        return JsonResponse({
            'total': TrackedUser.objects.count(),
            'count': len(users_data),
            'users': users_data
        })
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_leaderboard(request):
    """API endpoint for leaderboard data"""
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
        
        leaderboard = []
        for rank, user in enumerate(users, 1):
            leaderboard.append({
                'rank': rank,
                'username': user.username,
                'display_name': user.display_name or user.username,
                'value': getattr(user, key),
                'total_solved': user.total_solved,
            })
        
        return JsonResponse({
            'category': category,
            'leaderboard': leaderboard
        })
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_debug_raw(request, username):
    """Debug endpoint to see raw API response"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        raw_data = loop.run_until_complete(LeetCodeAPI.fetch_user_data(username))
        loop.close()

        return JsonResponse(raw_data, json_dumps_params={'indent': 2})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)