#!/usr/bin/env bash
set -eu

die() {
    printf "\033[31;1mFATAL: %s\033[0m\n" "$*" >> /dev/stderr
    printf "Usage: %s\n" "$(basename "$0") NEW_VERSION" >/dev/stderr
    exit 1
}
ROOT="$(dirname "$0")/../"


newVersion="${1:-}"
if ! grep -q -E '^[0-9]\.[0-9]$' <<< "$newVersion"; then
    die "Please supply a new version in the form x.y"
fi

currentVersion=$(poetry version -s | sed -nre 's/^(.+).0-pre$/\1/p')
codeVersion=$(sed -nre 's/VERSION_TUPLE\s*=\s*.*\("",\s*([^,]+),\s*([^,]+),\s*-1\)/\1.\2/p' <"$ROOT/quodlibet/const.py")

[ -n "$currentVersion" ] || die "Couldn't get current version from Poetry ($(poetry version -s))"
[ -n "$codeVersion" ] || die "Couldn't get current version from code"
[ "$codeVersion" == "$currentVersion" ] || die "Existing QL versions disagree: $codeVersion (code) vs $currentVersion (Poetry)"
[ "$currentVersion" == "$newVersion" ] && die "Already at version quodlibet-$newVersion"

newBranch="quodlibet-$currentVersion"
git rev-parse --quiet --verify "origin/$newBranch" && die "$newBranch branch already exists in Git remote. Wrong version?"
newCodeVersion=$(sed -nr 's/^([^.]+)\.([^.]*)$/\1, \2, -1/p'<<< "$newVersion")

# Safety - too many bad things can happen on dev setups otherwise
if ! git diff-index --quiet HEAD; then
    git status -s
    echo
    die "Unclean Git status (see above) - commit or stash?"
fi

echo "⚠️ About to create a branch for $currentVersion ($newBranch)"
echo "...and move main version to $newVersion-pre aka ($newCodeVersion) ⚠️"
echo
echo "Enter to continue, or ctrl-c to cancel"
read -r _

git checkout -b "$newBranch"
git checkout main

# Update version in ``const.py`` to ``(X, Y + 1, -1)``
sed -r -i "s/^\s*(VERSION_TUPLE\s*=\s*.+\(\"\",\s*)(.*)(\)\s*)/\1${newCodeVersion}\3/g" "../quodlibet/const.py"
poetry version "$newVersion.0-pre"

# Commit these in main
git add "$ROOT/pyproject.toml" "$ROOT/quodlibet/const.py"
git commit -m "version bump"



# Just for safety
GIT_PAGER="" git diff origin/main
echo "🔎 Changes for review above 🔎"
echo "Enter to push to origin, or ctrl-c to cancel"
read -r _

# Now push everything
git push origin HEAD
git push origin "$newBranch"

echo "✔ Success!"
