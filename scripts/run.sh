#!/bin/sh

set -e

cd "$(realpath "$(dirname "${0}")/..")" # two dirs up

_log() (
	level="${1}"
	fmt="%s ${2:-"%s\\t%s\\n"}"

	while read -r line; do
		printf "${fmt}" "$(date '+[%Y-%m-%d %H:%M:%S %Z%z]')" "${level}" "${line}"
	done >&2
)

_log_color() { _log "${1}" "\\033[${2}m[%s]\\033[0m\\t\033[${2}m%s\\033[0m\\n"; }

debug() { _log_color DEBUG 32; }
info() { _log_color INFO 34; }
warn() { _log_color WARNING 33; }
err() { _log_color ERROR 31; }

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
	[ "${2}" = y ] &&
		set -- "${1} [Y/n]" "${2}" ||
		set -- "${1} [y/N]" "${2}"

	case "$(prompt "${1}")" in
	[yY]) printf y ;;
	[nN]) printf n ;;
	*) printf '%s' "${2}" ;;
	esac
}

ERR=false

(
	set -e

	! command -v python3 >/dev/null 2>&1 &&
		dep_missing python3 | err && false # none of the other commands in this subshell will work without python

	! python3 -c 'import sys; vi = sys.version_info; exit(not (vi.major == 3 and vi.minor >= 11))' && ERR=true &&
		printf 'Your version of python (%s) is out of date, the minimum required version is Python 3.11\n' \
			"$(python3 -V)" | err

	! python3 -m pip --version >/dev/null 2>&1 && ERR=true &&
		dep_missing pip | err

	! python3 -c 'import venv, ensurepip' 2>/dev/null && ERR=true &&
		dep_missing 'python3-venv' | err

	! ${ERR}
) || ERR=true

# check for wine
! command -v wine >/dev/null 2>&1 &&
	dep_missing wine | warn &&
	printf '%s\n' 'Wine is required to run studiomdl.exe for model precaching' | warn &&
	{ ${ERR} || [ "$(prompt_yn 'Continue anyway?' n)" != y ]; } && ERR=true

${ERR} && exit 1 # exit if errors were previously raised

if [ -f 'requirements.txt' ]; then
	! [ -f '.venv/bin/activate' ] &&
		printf '%s\n' 'Creating virtual environment' | info &&
		python3 -m venv .venv

	. .venv/bin/activate

	printf '%s\n' 'Installing and/or updating dependencies' | info
	pip -q install --upgrade pip
	pip -q install --upgrade -r requirements.txt
fi

printf '%s\n' 'Starting Casual Preloader' | info
exec ./main.py
