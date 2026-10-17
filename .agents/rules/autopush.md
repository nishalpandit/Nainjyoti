# Automatic Git Commit and Push

Whenever coding changes or features are successfully implemented and verified:
1. Ensure system checks and tests pass with 0 errors.
2. Automatically stage all relevant changes (`git add .` or target files).
3. Commit with a clear, descriptive conventional commit message (`feat: ...`, `fix: ...`, `docs: ...`).
4. Automatically push the commit to GitHub (`git push origin main` or current branch) without requiring the user to prompt for it.
5. Strictly adhere to the manual verification rule: NEVER open Chrome or launch browser automation tools.
