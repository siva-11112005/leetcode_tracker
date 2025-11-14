import asyncio
import aiohttp
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta
from .models import TrackedUser


class LeetCodeAPI:
    TIMEOUT = 25

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
            profile_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/userProfile/{username}",
                f"https://alfa-leetcode-api.onrender.com/{username}",
            ]
            
            for endpoint in profile_endpoints:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            profile_data = await response.json()
                            api_used = endpoint
                            print(f"✅ Profile fetched from: {endpoint}")
                            break
                except Exception as e:
                    print(f"❌ Failed to fetch profile from {endpoint}: {e}")
                    continue
            
            if not profile_data:
                return {"error": f"User '{username}' not found", "username": username}
            
            # ===== FETCH RECENT SUBMISSIONS =====
            submission_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/{username}/submission",
                f"https://alfa-leetcode-api.onrender.com/userProfileUserQuestionProgressV2/{username}",
            ]
            
            for sub_endpoint in submission_endpoints:
                try:
                    async with session.get(sub_endpoint, timeout=aiohttp.ClientTimeout(total=15)) as sub_response:
                        if sub_response.status == 200:
                            submissions_data = await sub_response.json()
                            if submissions_data:
                                print(f"✅ Submissions fetched from: {sub_endpoint}")
                                break
                except Exception as e:
                    print(f"❌ Failed to fetch submissions from {sub_endpoint}: {e}")
                    continue
            
            # ===== FETCH CONTEST DATA =====
            contest_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/userContestRankingInfo/{username}",
                f"https://alfa-leetcode-api.onrender.com/{username}/contest",
            ]
            
            for contest_endpoint in contest_endpoints:
                try:
                    async with session.get(contest_endpoint, timeout=aiohttp.ClientTimeout(total=15)) as contest_response:
                        if contest_response.status == 200:
                            contest_data = await contest_response.json()
                            if contest_data and isinstance(contest_data, dict):
                                if any(key in contest_data for key in ['rating', 'contestRating', 'userContestRanking', 'attendedContestsCount']):
                                    print(f"✅ Contest data fetched from: {contest_endpoint}")
                                    break
                except Exception as e:
                    print(f"❌ Failed to fetch contest from {contest_endpoint}: {e}")
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

    # ===== IMPROVED RECENT SUBMISSIONS EXTRACTION =====
    recent_submissions = []
    
    print(f"\n🔍 Debug Submissions for {user_data.get('username')}:")
    print(f"Submissions type: {type(submissions)}")
    
    # Method 1: Check if submissions is a dict with 'submission' key
    if isinstance(submissions, dict) and 'submission' in submissions:
        sub_list = submissions['submission']
        if isinstance(sub_list, list):
            for sub in sub_list[:10]:
                recent_submissions.append({
                    "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                    "status": sub.get("statusDisplay", "Unknown"),
                    "timestamp": sub.get("timestamp", ""),
                    "lang": sub.get("lang", "N/A")
                })
            print(f"✅ Method 1: Found {len(recent_submissions)} submissions")
    
    # Method 2: Check if submissions is directly a list
    elif isinstance(submissions, list):
        for sub in submissions[:10]:
            recent_submissions.append({
                "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                "status": sub.get("statusDisplay", "Unknown"),
                "timestamp": sub.get("timestamp", ""),
                "lang": sub.get("lang", "N/A")
            })
        print(f"✅ Method 2: Found {len(recent_submissions)} submissions")
    
    # Method 3: Check recentSubmissions in profile
    elif "recentSubmissions" in profile:
        submissions_from_profile = profile["recentSubmissions"]
        if isinstance(submissions_from_profile, list):
            for sub in submissions_from_profile[:10]:
                recent_submissions.append({
                    "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                    "status": sub.get("statusDisplay", "Unknown"),
                    "timestamp": sub.get("timestamp", ""),
                    "lang": sub.get("lang", "N/A")
                })
            print(f"✅ Method 3: Found {len(recent_submissions)} submissions")
    
    if not recent_submissions:
        print(f"❌ No submissions found. Submissions data: {submissions}")

    # ===== CONTEST INFO EXTRACTION =====
    contest_rating = "N/A"
    contests_attended = 0

    extraction_methods = [
        lambda: (
            round(float(contest.get("rating")), 2) if contest.get("rating") else None,
            int(contest.get("attendedContestsCount", 0))
        ),
        lambda: (
            round(float(contest.get("contestRating")), 2) if contest.get("contestRating") else None,
            int(contest.get("contestAttend", 0))
        ),
        lambda: (
            round(float(contest.get("userContestRanking", {}).get("rating")), 2) if contest.get("userContestRanking", {}).get("rating") else None,
            int(contest.get("userContestRanking", {}).get("attendedContestsCount", 0))
        ),
        lambda: (
            round(float(profile.get("contestRating")), 2) if profile.get("contestRating") else None,
            int(profile.get("contestAttend", 0))
        ),
    ]

    for i, method in enumerate(extraction_methods, 1):
        try:
            rating, attended = method()
            if rating is not None and rating > 0:
                contest_rating = rating
                contests_attended = attended
                break
        except (ValueError, TypeError, KeyError, AttributeError):
            continue

    return {
        "username": user_data.get("username", "Unknown"),
        "display_name": display_name,
        "error": None,
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


async def get_user_data(username: str):
    """Async helper to fetch user data"""
    data = await LeetCodeAPI.fetch_user_data(username)
    stats = parse_user_stats(data)
    
    # Update tracked user in database
    if not stats.get('error'):
        try:
            tracked_user, created = await TrackedUser.objects.aget_or_create(
                username=username
            )
            
            await asyncio.to_thread(tracked_user.update_stats, stats)
        except Exception as e:
            print(f"Error updating tracked user: {e}")
    
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