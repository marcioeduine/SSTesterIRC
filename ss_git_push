#!/bin/bash

function	ss_git_push()
{
	local	file
	local	msg
	local	comments

	git add .
	file=$(git diff --name-only --cached)
	if [ -n "$file" ]; then
		msg=$'UPDATED FILE:\n'
		while IFS= read -r current; do
			comments=$(sed -n 's/^[[:space:]]*\(\/\/\|#\/\/\) SS_COMMIT:[[:space:]]*//p' "$current")
			if [ -n "$comments" ]; then
				msg+=$'\n\n - '"$current"':'
				while IFS= read -r line; do
					msg+=$'\n   • '"$line"
				done <<< "$comments"
			else
				msg+=$'\n - '"$current"
			fi
		done <<< "$file"
		git commit -m "$msg"
	else
		echo "Nothing to commit!"
	fi
}
