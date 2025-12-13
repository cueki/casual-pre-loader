#!/bin/sh

set -e

# shellcheck disable=SC2312
cd "$(dirname "$(dirname "$(realpath -s "${0}")")")" # one dir up

_log() (
	set -e

	level="${1}"
	fmt="%s ${2:-'%s %s\n'}"
	date="$(date '+[%Y-%m-%d %H:%M:%S]')"

	while read -r line; do
		# shellcheck disable=SC2059
		printf "${fmt}" "${date}" "${level}" "${line}"
	done >&2
)

_log_color() { _log "${1}" "\\033[${2}m%-${max_len_level}s\\033[0m\033[${2}m%s\\033[0m\\n"; }

max_len_level=0
for _level in debug:32 info:34 warning:33 err:31; do
	level="${_level%:*}"

	# shellcheck disable=SC2312
	max_len_level="$(printf '%s\n' "${max_len_level}" "${#level}" | sort -n | tail -n1)"

	# shellcheck disable=SC2312
	eval "${level}() { _log_color $(printf '%s' "${level}" | tr '[:lower:]' '[:upper:]') ${_level##*:}; }"
done
unset level _level
: $((max_len_level += 2)) # apply 2 spaces of padding

dep_missing() { printf '%s is not installed, please install it using your package manager\n' "${1}"; }

prompt() (
	[ -t 0 ] || return 1

	printf '%s' "${1}" >&2
	read -r REPLY
	printf '\n' >&2

	printf '%s' "${REPLY}"
)

prompt_yn() {
	! [ -t 0 ] && printf n && return

	set -- "${1}" "${2:-y}"
	# shellcheck disable=SC2015
	[ "${2}" = y ] &&
		set -- "${1} [Y/n]" "${2}" ||
		set -- "${1} [y/N]" "${2}"

	case "$(prompt "${1}")" in
	[yY]) printf y ;;
	[nN]) printf n ;;
	*) printf '%s' "${2}" ;;
	esac
}

check_python_version() {
	python3 -c 'import sys; vi = sys.version_info; exit(not (vi.major == 3 and vi.minor >= 11))'
}

ERR=false

# shellcheck disable=SC2310,SC2312
[ "$(id -u)" -eq 0 ] && printf "This script should not be run as root\n" | err && ERR=true

# shellcheck disable=SC2310
(
	set -e

	! command -v python3 >/dev/null 2>&1 &&
		dep_missing python3 | err && false # none of the other commands in this subshell will work without python

	# shellcheck disable=SC2312
	! check_python_version && ERR=true &&
		printf 'Your version of python (%s) is out of date, the minimum required version is Python 3.11\n' \
			"$(python3 -V)" | err

	! python3 -m pip --version >/dev/null 2>&1 && ERR=true &&
		dep_missing pip | err

	! python3 -c 'import venv, ensurepip' 2>/dev/null && ERR=true &&
		dep_missing 'python3-venv' | err

	! ${ERR}
) || ERR=true

# shellcheck disable=SC2310,SC2312
# check for wine
! command -v wine >/dev/null 2>&1 &&
	dep_missing wine | warning &&
	printf '%s\n' 'Wine is required to run studiomdl.exe for model precaching' | warning &&
	{ ${ERR} || [ "$(prompt_yn 'Continue anyway?' n)" != y ]; } && ERR=true

${ERR} && exit 1 # exit if errors were previously raised

git submodule update --init --recursive --remote # try to ensure that submodules ARE in fact, properly cloned

if [ -f 'requirements.txt' ]; then
	# shellcheck disable=SC2310,SC2312
	! [ -f '.venv/bin/activate' ] &&
		printf '%s\n' 'Creating virtual environment' | info &&
		python3 -m venv .venv

	. .venv/bin/activate

	# shellcheck disable=SC2310
	if ! check_python_version; then
		printf '%s\n' 'virtual environment is using an out-of-date version of python, attempting to recreate' | warning

		# shellcheck disable=SC2218
		deactivate

		rm -r .venv
		python3 -m venv .venv
		. .venv/bin/activate

		! check_python_version &&
			printf '%s\n' 'unable to recreate the virtual environment with an up-to-date version of python' | error &&
			exit 1
		printf '%s\n' 'managed to recreate the virtual environment with an up-to-date version of python' | warning
	fi

	printf '%s\n' 'Installing and/or updating dependencies' | info
	python3 -m pip -q install --upgrade pip
	python3 -m pip -q install --upgrade -r requirements.txt
fi

printf '%s\n' 'Starting Casual Preloader' | info
exec ./main.py
