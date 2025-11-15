#!/usr/bin/env bash
# LeetCode Tracker - Pre-Deployment Checklist & Commands

echo "================================"
echo "LeetCode Tracker - Deployment Checklist"
echo "================================"
echo ""

# 1. Verify Django setup
echo "1. Running Django system check..."
cd "$(dirname "$0")/leetcode_tracker"
python manage.py check
if [ $? -eq 0 ]; then
    echo "✅ Django system check passed"
else
    echo "❌ Django system check failed"
    exit 1
fi
echo ""

# 2. Verify requirements.txt
echo "2. Checking requirements.txt..."
if grep -q "Django==5.2.5" requirements.txt && \
   grep -q "aiohttp==3.9.5" requirements.txt && \
   grep -q "gunicorn==21.2.0" requirements.txt; then
    echo "✅ All required packages in requirements.txt"
else
    echo "❌ Missing packages in requirements.txt"
    exit 1
fi
echo ""

# 3. Verify runtime.txt
echo "3. Checking runtime.txt..."
if grep -q "python-3.11" runtime.txt; then
    echo "✅ Python 3.11 specified in runtime.txt"
else
    echo "❌ Python version not correct"
    exit 1
fi
echo ""

# 4. Verify Procfile
echo "4. Checking Procfile..."
if grep -q "gunicorn leetcode_tracker.wsgi" Procfile; then
    echo "✅ Procfile configured for gunicorn"
else
    echo "❌ Procfile not configured correctly"
    exit 1
fi
echo ""

# 5. Verify build.sh
echo "5. Checking build.sh..."
if grep -q "python manage.py collectstatic" build.sh && \
   grep -q "python manage.py migrate" build.sh; then
    echo "✅ build.sh has all required steps"
else
    echo "❌ build.sh missing steps"
    exit 1
fi
echo ""

# 6. Check git status
echo "6. Checking git status..."
if git status --porcelain | grep -q .; then
    echo "⚠️  Uncommitted changes detected:"
    git status --short
    echo ""
    echo "Run: git add -A && git commit -m 'Complete code rewrite'"
else
    echo "✅ All changes committed"
fi
echo ""

# 7. Final summary
echo "================================"
echo "✅ All checks passed!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. git push origin main"
echo "2. Go to Render.com dashboard"
echo "3. Deploy your app"
echo "4. Visit: https://your-app-url.onrender.com/profile/sivasakthivel__11/"
echo ""
