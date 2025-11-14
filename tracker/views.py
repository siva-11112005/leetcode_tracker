import asyncio
import aiohttp
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
            profile_endpoints = [
                f"https://leetcode-stats-api.herokuapp.com/{username}",
                f"https://alfa-leetcode-api.onrender.com/userProfile/{username}",
                f"https://alfa-leetcode-api.onrender.com/{username}",
            ]
            
            for endpoint in profile_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=20)) as response:
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
                f"https://alfa-leetcode-api.onrender.com/{username}/acSubmission",
            ]
            
            for sub_endpoint in submission_endpoints:
                try:
                    async with session.get(sub_endpoint, timeout=aiohttp.ClientTimeout(total=20)) as sub_response:
                        if sub_response.status == 200:
                            temp_data = await sub_response.json()
                            if temp_data and isinstance(temp_data, dict) and 'submission' in temp_data:
                                submissions_data = temp_data
                                print(f"✅ Submissions fetched from: {sub_endpoint}")
                                break
                            elif temp_data and isinstance(temp_data, list) and len(temp_data) > 0:
                                submissions_data = {'submission': temp_data}
                                print(f"✅ Submissions fetched from: {sub_endpoint}")
                                break
                except Exception as e:
                    print(f"❌ Failed to fetch submissions from {sub_endpoint}: {e}")
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
                                print(f"✅ Submissions fetched from GraphQL")
                except Exception as e:
                    print(f"❌ GraphQL submission fetch failed: {e}")
            
            # ===== FETCH CONTEST DATA =====
            contest_endpoints = [
                f"https://alfa-leetcode-api.onrender.com/userContestRankingInfo/{username}",
                f"https://alfa-leetcode-api.onrender.com/{username}/contest",
            ]
            
            for contest_endpoint in contest_endpoints:
                try:
                    async with session.get(contest_endpoint, timeout=aiohttp.ClientTimeout(total=15)) as contest_response:
                        if contest_response.status == 200:
                            temp_contest_data = await contest_response.json()
                            if temp_contest_data and isinstance(temp_contest_data, dict):
                                # Accept contest data if it has expected keys or is non-empty
                                if any(key in temp_contest_data for key in ['rating', 'contestRating', 'userContestRanking', 'attendedContestsCount']):
                                    contest_data = temp_contest_data
                                    print(f"✅ Contest data fetched from: {contest_endpoint}")
                                    break
                                else:
                                    # Even if structure is different, still try to use it
                                    contest_data = temp_contest_data
                                    print(f"⚠️ Contest data fetched but structure different: {contest_endpoint}")
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

    # ===== RECENT SUBMISSIONS EXTRACTION =====
    recent_submissions = []
    
    print(f"\n🔍 Debug Submissions for {user_data.get('username')}:")
    
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
            print(f"✅ Method 1: Found {len(recent_submissions)} submissions")
    
    # Method 2: submissions is directly a list
    elif isinstance(submissions, list):
        for sub in submissions[:20]:
            recent_submissions.append({
                "title": sub.get("title", sub.get("titleSlug", "Unknown")),
                "status": sub.get("statusDisplay", sub.get("status", "Unknown")),
                "timestamp": sub.get("timestamp", ""),
                "lang": sub.get("lang", "N/A")
            })
        print(f"✅ Method 2: Found {len(recent_submissions)} submissions")
    
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
            print(f"✅ Method 3: Found {len(recent_submissions)} submissions")
    
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
            print(f"✅ Method 4: Found {len(recent_submissions)} AC submissions")
    
    if not recent_submissions:
        print(f"❌ No submissions found")
    else:
        print(f"✅ Total submissions extracted: {len(recent_submissions)}")

    # ===== IMPROVED CONTEST INFO EXTRACTION =====
    contest_rating = "N/A"
    contests_attended = 0

    print(f"\n🏆 Debug Contest Data for {user_data.get('username')}:")
    print(f"Contest object: {contest}")
    print(f"Profile object keys: {profile.keys() if profile else 'None'}")

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

    for i, method in enumerate(extraction_methods, 1):
        try:
            rating, attended = method()
            if rating is not None and rating > 0:
                contest_rating = round(rating, 2)
                contests_attended = attended
                print(f"✅ Method {i} SUCCESS: Rating={contest_rating}, Attended={attended}")
                break
            else:
                print(f"❌ Method {i} returned None or <= 0 (rating={rating}, attended={attended})")
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            print(f"❌ Method {i} failed with exception: {type(e).__name__}: {e}")
            continue
    else:
        print(f"⚠️  All extraction methods failed. Contest rating remains '{contest_rating}', attended={contests_attended}")

    print(f"Final Contest Rating: {contest_rating}, Attended: {contests_attended}\n")

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