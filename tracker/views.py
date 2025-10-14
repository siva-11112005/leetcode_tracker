# import asyncio
# import aiohttp
# from django.shortcuts import render
# from django.http import JsonResponse
# from datetime import datetime, timedelta
# import json

# class LeetCodeAPI:
#     BASE_URL = "https://leetcode-api-pied.vercel.app"
#     TIMEOUT = 15
    
#     @staticmethod
#     async def fetch_user_data(username: str):
#         """Fetch comprehensive user data from LeetCode API"""
#         timeout = aiohttp.ClientTimeout(total=LeetCodeAPI.TIMEOUT)
        
#         try:
#             async with aiohttp.ClientSession(timeout=timeout) as session:
#                 # Fetch user profile
#                 async with session.get(f"{LeetCodeAPI.BASE_URL}/user/{username}") as response:
#                     if response.status != 200:
#                         return {"error": f"User not found (Status: {response.status})", "username": username}
#                     profile_data = await response.json()
                
#                 # Fetch submissions
#                 async with session.get(f"{LeetCodeAPI.BASE_URL}/user/{username}/submissions?limit=100") as response:
#                     submissions_data = await response.json() if response.status == 200 else None
                
#                 # Fetch contests
#                 async with session.get(f"{LeetCodeAPI.BASE_URL}/user/{username}/contests") as response:
#                     contests_data = await response.json() if response.status == 200 else None
                
#                 return {
#                     "username": username,
#                     "profile": profile_data,
#                     "submissions": submissions_data,
#                     "contests": contests_data,
#                     "error": None
#                 }
#         except asyncio.TimeoutError:
#             return {"error": "Request timeout", "username": username}
#         except Exception as e:
#             return {"error": str(e), "username": username}

# def parse_user_stats(user_data: dict) -> dict:
#     """Parse and organize user statistics"""
#     if user_data.get("error"):
#         return {
#             "username": user_data.get("username", "Unknown"),
#             "error": user_data["error"],
#             "total_solved": 0,
#             "easy": 0,
#             "medium": 0,
#             "hard": 0,
#         }
    
#     profile = user_data.get("profile", {})
#     submissions = user_data.get("submissions", {})
#     contests = user_data.get("contests", {})
    
#     # Extract display name
#     display_name = user_data.get("username", "Unknown")
#     if "profile" in profile and isinstance(profile["profile"], dict):
#         nested_profile = profile["profile"]
#         if "realName" in nested_profile and nested_profile["realName"]:
#             display_name = nested_profile["realName"]
    
#     # Extract problem counts
#     total_solved = profile.get("totalSolved", 0)
#     easy_solved = profile.get("easySolved", 0)
#     medium_solved = profile.get("mediumSolved", 0)
#     hard_solved = profile.get("hardSolved", 0)
    
#     # Extract ranking
#     ranking = "N/A"
#     if "ranking" in profile and profile["ranking"] is not None:
#         ranking = profile["ranking"]
#     elif "profile" in profile and isinstance(profile["profile"], dict):
#         nested = profile["profile"]
#         if "ranking" in nested and nested["ranking"] is not None:
#             ranking = nested["ranking"]
    
#     # Extract streak info
#     max_streak = 0
#     if "userCalendar" in profile:
#         calendar = profile.get("userCalendar", {})
#         if isinstance(calendar, dict):
#             max_streak = calendar.get("streak", 0)
    
#     # Recent submissions
#     recent_submissions = []
#     if submissions:
#         sub_list = submissions if isinstance(submissions, list) else submissions.get("submission", [])
#         for sub in sub_list[:10]:  # Get last 10 submissions
#             recent_submissions.append({
#                 "title": sub.get("title", "Unknown"),
#                 "status": sub.get("statusDisplay", "Unknown"),
#                 "timestamp": sub.get("timestamp"),
#                 "lang": sub.get("lang", "N/A")
#             })
    
#     # Contest info
#     contest_rating = "N/A"
#     contests_attended = 0
#     if contests:
#         contest_ranking = contests.get("userContestRanking", {})
#         if contest_ranking:
#             rating = contest_ranking.get("rating")
#             if rating:
#                 contest_rating = round(rating, 2)
#             contests_attended = contest_ranking.get("attendedContestsCount", 0)
    
#     return {
#         "username": user_data.get("username", "Unknown"),
#         "display_name": display_name,
#         "error": None,
#         "ranking": ranking,
#         "total_solved": total_solved,
#         "easy": easy_solved,
#         "medium": medium_solved,
#         "hard": hard_solved,
#         "max_streak": max_streak,
#         "contest_rating": contest_rating,
#         "contests_attended": contests_attended,
#         "recent_submissions": recent_submissions,
#     }

# def home(request):
#     """Home page view"""
#     return render(request, 'tracker/home.html')

# def profile(request, username):
#     """Profile page view"""
#     return render(request, 'tracker/profile.html', {'username': username})

# async def get_user_data(username: str):
#     """Async helper to fetch user data"""
#     data = await LeetCodeAPI.fetch_user_data(username)
#     return parse_user_stats(data)

# def api_user_data(request, username):
#     """API endpoint to fetch user data"""
#     try:
#         # Run async function in sync context
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         user_stats = loop.run_until_complete(get_user_data(username))
#         loop.close()
        
#         return JsonResponse(user_stats)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)

# import asyncio
# import aiohttp
# from django.shortcuts import render
# from django.http import JsonResponse
# from datetime import datetime, timedelta

# class LeetCodeAPI:
#     BASE_URL = "https://leetcode-api-pied.vercel.app"
#     TIMEOUT = 15
    
#     @staticmethod
#     async def fetch_user_data(username: str):
#         """Fetch comprehensive user data from LeetCode API"""
#         timeout = aiohttp.ClientTimeout(total=LeetCodeAPI.TIMEOUT)
        
#         try:
#             async with aiohttp.ClientSession(timeout=timeout) as session:
#                 # Fetch user profile
#                 async with session.get(f"{LeetCodeAPI.BASE_URL}/{username}") as response:
#                     if response.status != 200:
#                         return {"error": f"User not found (Status: {response.status})", "username": username}
#                     profile_data = await response.json()
                
#                 return {
#                     "username": username,
#                     "profile": profile_data,
#                     "error": None
#                 }
#         except asyncio.TimeoutError:
#             return {"error": "Request timeout", "username": username}
#         except Exception as e:
#             return {"error": str(e), "username": username}

# def parse_user_stats(user_data: dict) -> dict:
#     """Parse and organize user statistics"""
#     if user_data.get("error"):
#         return {
#             "username": user_data.get("username", "Unknown"),
#             "display_name": user_data.get("username", "Unknown"),
#             "error": user_data["error"],
#             "total_solved": 0,
#             "easy": 0,
#             "medium": 0,
#             "hard": 0,
#             "ranking": "N/A",
#             "max_streak": 0,
#             "contest_rating": "N/A",
#             "contests_attended": 0,
#             "recent_submissions": [],
#             "acceptance_rate": 0,
#         }
    
#     profile = user_data.get("profile", {})
    
#     # Extract display name - try multiple locations
#     display_name = user_data.get("username", "Unknown")
#     if "name" in profile and profile["name"]:
#         display_name = profile["name"]
#     elif "realName" in profile and profile["realName"]:
#         display_name = profile["realName"]
    
#     # Extract problem counts - CHECK MULTIPLE POSSIBLE API STRUCTURES
#     total_solved = 0
#     easy_solved = 0
#     medium_solved = 0
#     hard_solved = 0
    
#     # Method 1: Direct fields (most common in this API)
#     if "totalSolved" in profile:
#         total_solved = profile.get("totalSolved", 0)
#         easy_solved = profile.get("easySolved", 0)
#         medium_solved = profile.get("mediumSolved", 0)
#         hard_solved = profile.get("hardSolved", 0)
    
#     # Method 2: Check submitStats
#     elif "submitStats" in profile:
#         submit_stats = profile["submitStats"]
#         if "acSubmissionNum" in submit_stats:
#             ac_submissions = submit_stats["acSubmissionNum"]
#             if isinstance(ac_submissions, list) and len(ac_submissions) > 0:
#                 # Index 0 is usually "All"
#                 if len(ac_submissions) > 0:
#                     total_solved = ac_submissions[0].get("count", 0)
#                 if len(ac_submissions) > 1:
#                     easy_solved = ac_submissions[1].get("count", 0)
#                 if len(ac_submissions) > 2:
#                     medium_solved = ac_submissions[2].get("count", 0)
#                 if len(ac_submissions) > 3:
#                     hard_solved = ac_submissions[3].get("count", 0)
    
#     # Method 3: Check submitStatsGlobal
#     elif "submitStatsGlobal" in profile:
#         stats = profile["submitStatsGlobal"]
#         if "acSubmissionNum" in stats:
#             ac_submissions = stats["acSubmissionNum"]
#             if isinstance(ac_submissions, list) and len(ac_submissions) > 0:
#                 if len(ac_submissions) > 0:
#                     total_solved = ac_submissions[0].get("count", 0)
#                 if len(ac_submissions) > 1:
#                     easy_solved = ac_submissions[1].get("count", 0)
#                 if len(ac_submissions) > 2:
#                     medium_solved = ac_submissions[2].get("count", 0)
#                 if len(ac_submissions) > 3:
#                     hard_solved = ac_submissions[3].get("count", 0)
    
#     # Extract ranking
#     ranking = "N/A"
#     if "ranking" in profile and profile["ranking"] is not None:
#         ranking = profile["ranking"]
    
#     # Extract streak info
#     max_streak = 0
#     current_streak = 0
    
#     if "streak" in profile:
#         max_streak = profile.get("streak", 0)
    
#     if "userCalendar" in profile:
#         calendar = profile.get("userCalendar", {})
#         if isinstance(calendar, dict):
#             max_streak = calendar.get("streak", max_streak)
#             current_streak = calendar.get("currentStreak", 0)
    
#     # Recent submissions
#     recent_submissions = []
#     if "recentSubmissions" in profile:
#         submissions = profile.get("recentSubmissions", [])
#         if isinstance(submissions, list):
#             for sub in submissions[:10]:
#                 recent_submissions.append({
#                     "title": sub.get("title", "Unknown"),
#                     "status": sub.get("statusDisplay", sub.get("status", "Unknown")),
#                     "timestamp": sub.get("timestamp", ""),
#                     "lang": sub.get("lang", "N/A")
#                 })
    
#     # Contest info
#     contest_rating = "N/A"
#     contests_attended = 0
    
#     if "contestRating" in profile:
#         rating = profile.get("contestRating")
#         if rating:
#             contest_rating = round(rating, 2)
    
#     if "contestAttend" in profile:
#         contests_attended = profile.get("contestAttend", 0)
    
#     # Calculate acceptance rate
#     acceptance_rate = 0
#     if "acceptanceRate" in profile:
#         acceptance_rate = round(profile.get("acceptanceRate", 0), 1)
    
#     return {
#         "username": user_data.get("username", "Unknown"),
#         "display_name": display_name,
#         "error": None,
#         "ranking": ranking,
#         "total_solved": total_solved,
#         "easy": easy_solved,
#         "medium": medium_solved,
#         "hard": hard_solved,
#         "max_streak": max_streak,
#         "current_streak": current_streak,
#         "contest_rating": contest_rating,
#         "contests_attended": contests_attended,
#         "recent_submissions": recent_submissions,
#         "acceptance_rate": acceptance_rate,
#     }

# def home(request):
#     """Home page view"""
#     return render(request, 'tracker/home.html')

# def profile(request, username):
#     """Profile page view"""
#     return render(request, 'tracker/profile.html', {'username': username})

# async def get_user_data(username: str):
#     """Async helper to fetch user data"""
#     data = await LeetCodeAPI.fetch_user_data(username)
#     return parse_user_stats(data)

# def api_user_data(request, username):
#     """API endpoint to fetch user data"""
#     try:
#         # Run async function in sync context
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         user_stats = loop.run_until_complete(get_user_data(username))
#         loop.close()
        
#         return JsonResponse(user_stats)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)

import asyncio
import aiohttp
from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime, timedelta

class LeetCodeAPI:
    TIMEOUT = 15
    
    @staticmethod
    async def fetch_user_data(username: str):
        """Fetch comprehensive user data from LeetCode API"""
        timeout = aiohttp.ClientTimeout(total=LeetCodeAPI.TIMEOUT)
        
        endpoints_to_try = [
            f"https://alfa-leetcode-api.onrender.com/userProfile/{username}",
            f"https://alfa-leetcode-api.onrender.com/{username}",
            f"https://leetcode-stats-api.herokuapp.com/{username}",
        ]
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for endpoint in endpoints_to_try:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            profile_data = await response.json()
                            return {
                                "username": username,
                                "profile": profile_data,
                                "error": None,
                                "api_used": endpoint
                            }
                except Exception:
                    continue
            
            return {"error": f"User '{username}' not found", "username": username}

def calculate_streak_from_calendar(submission_calendar):
    """Calculate current and max streak from submission calendar"""
    if not submission_calendar:
        return 0, 0
    
    # Convert timestamps to dates
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
    
    # Sort dates
    dates = sorted(set(dates))
    
    # Calculate current streak
    current_streak = 0
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Check if user submitted today or yesterday
    if today in dates or yesterday in dates:
        current_date = today if today in dates else yesterday
        current_streak = 1
        
        # Count backwards
        for i in range(1, len(dates)):
            prev_date = current_date - timedelta(days=1)
            if prev_date in dates:
                current_streak += 1
                current_date = prev_date
            else:
                break
    
    # Calculate max streak
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
    
    # Extract display name
    display_name = user_data.get("username", "Unknown")
    if "name" in profile and profile["name"]:
        display_name = profile["name"]
    elif "realName" in profile and profile["realName"]:
        display_name = profile["realName"]
    
    # Extract problem counts - use the correct field names from API
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
    
    # Recent submissions - use recentSubmissions field
    recent_submissions = []
    if "recentSubmissions" in profile:
        submissions = profile["recentSubmissions"]
        if isinstance(submissions, list):
            for sub in submissions[:10]:
                recent_submissions.append({
                    "title": sub.get("title", "Unknown"),
                    "status": sub.get("statusDisplay", "Unknown"),
                    "timestamp": sub.get("timestamp", ""),
                    "lang": sub.get("lang", "N/A")
                })
    
    # Contest info - check if available
    contest_rating = "N/A"
    contests_attended = 0
    
    # Try to get contest data from profile
    if "contestRating" in profile and profile["contestRating"]:
        try:
            contest_rating = round(float(profile["contestRating"]), 2)
        except:
            pass
    
    if "contestAttend" in profile:
        contests_attended = profile["contestAttend"]
    
    # Check userContestRanking if exists
    if "userContestRanking" in profile:
        contest_data = profile["userContestRanking"]
        if isinstance(contest_data, dict):
            if "rating" in contest_data and contest_data["rating"]:
                try:
                    contest_rating = round(float(contest_data["rating"]), 2)
                except:
                    pass
            if "attendedContestsCount" in contest_data:
                contests_attended = contest_data["attendedContestsCount"]
    
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

def home(request):
    """Home page view"""
    return render(request, 'tracker/home.html')

def profile(request, username):
    """Profile page view"""
    return render(request, 'tracker/profile.html', {'username': username})

async def get_user_data(username: str):
    """Async helper to fetch user data"""
    data = await LeetCodeAPI.fetch_user_data(username)
    return parse_user_stats(data)

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