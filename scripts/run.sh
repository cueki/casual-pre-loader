#!/bin/sh
set -e

# shellcheck disable=SC2312
cd "$(dirname "$(dirname "$(realpath -s "${0}")")")" # one dir up

# Always prefer repo tools (notably scripts/wine)
export PATH="$(pwd)/scripts:${PATH}"

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

dep_missing() {
  printf '%s is not installed, please install it using your package manager\n' "${1}"
}

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
  [ "${2}" = y ] && set -- "${1} [Y/n]" "${2}" || set -- "${1} [y/N]" "${2}"
  case "$(prompt "${1}")" in
    [yY]) printf y ;;
    [nN]) printf n ;;
    *) printf '%s' "${2}" ;;
  esac
}

check_python_version() {
  python3 -c 'import sys; vi = sys.version_info; exit(not (vi.major == 3 and vi.minor >= 11))'
}

is_steamdeck() {
  # SteamOS ID check
  if [ -r /etc/os-release ] && grep -q '^ID=steamos' /etc/os-release; then
    return 0
  fi

  # Hardware DMI check (commonly "Jupiter" or "Steam Deck")
  if [ -r /sys/devices/virtual/dmi/id/product_name ]; then
    case "$(cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null)" in
      *Jupiter*|*Steam\ Deck*) return 0 ;;
    esac
  fi

  return 1
}

ON_STEAMDECK=false
is_steamdeck && ON_STEAMDECK=true

ERR=false

# shellcheck disable=SC2310,SC2312
[ "$(id -u)" -eq 0 ] && printf "This script should not be run as root\n" | err && ERR=true

# shellcheck disable=SC2310
(
  set -e
  ! command -v python3 >/dev/null 2>&1 && dep_missing python3 | err && false

  # none of the other commands in this subshell will work without python
  # shellcheck disable=SC2312
  ! check_python_version && ERR=true && printf 'Your version of python (%s) is out of date, the minimum required version is Python 3.11\n' \
    "$(python3 -V)" | err

  # venv + ensurepip are required (SteamOS-friendly)
  # shellcheck disable=SC2312
  ! python3 -c 'import venv, ensurepip' 2>/dev/null && ERR=true && dep_missing 'python3-venv' | err

  # Upstream behavior off Steam Deck: require system pip
  if [ "${ON_STEAMDECK}" != true ]; then
    # shellcheck disable=SC2312
    ! python3 -m pip --version 2>/dev/null && ERR=true && dep_missing pip | err
  fi

  ! ${ERR}
) || ERR=true

# Wine check:
# - We always have scripts/wine on PATH, but it may fall through to missing host wine.
# - Validate "usable wine" by running `wine --version`.
if ! command -v wine >/dev/null 2>&1; then
  dep_missing wine | warning
  printf '%s\n' 'Wine is required to run studiomdl.exe for model precaching' | warning
  ! { ${ERR} || [ "$(prompt_yn 'Continue anyway?' n)" != y ]; } && ERR=true
else
  if ! wine --version >/dev/null 2>&1; then
    dep_missing wine | warning
    printf '%s\n' 'Wine was found but is not usable.' | warning

    if [ "${ON_STEAMDECK}" = true ] && command -v flatpak >/dev/null 2>&1; then
      printf '%s\n' 'On Steam Deck, the recommended option is Flatpak Wine (org.winehq.Wine).' | warning
      if [ "$(prompt_yn 'Attempt to install Flatpak Wine (org.winehq.Wine)?' n)" = y ]; then
        flatpak install -y flathub org.winehq.Wine || true
      fi
    fi

    ! wine --version >/dev/null 2>&1 && { ${ERR} || [ "$(prompt_yn 'Continue anyway?' n)" != y ]; } && ERR=true
  fi
fi

${ERR} && exit 1 # exit if errors were previously raised

git submodule update --init --recursive --remote # try to ensure that submodules ARE in fact, properly cloned

if [ -f 'requirements.txt' ]; then
  # shellcheck disable=SC2310,SC2312
  ! [ -f '.venv/bin/activate' ] && printf '%s\n' 'Creating virtual environment' | info && python3 -m venv .venv

  . .venv/bin/activate

  # shellcheck disable=SC2310
  if ! check_python_version; then
    printf '%s\n' 'virtual environment is using an out-of-date version of python, attempting to recreate' | warning
    # shellcheck disable=SC2218
    deactivate
    rm -r .venv
    python3 -m venv .venv
    . .venv/bin/activate
    ! check_python_version && printf '%s\n' 'unable to recreate the virtual environment with an up-to-date version of python' | err && exit 1
    printf '%s\n' 'managed to recreate the virtual environment with an up-to-date version of python' | warning
  fi

  printf '%s\n' 'Installing and/or updating dependencies' | info

  if [ "${ON_STEAMDECK}" = true ]; then
    # SteamOS-friendly: bootstrap pip inside the venv (system pip may be externally-managed)
    python3 -m ensurepip --upgrade >/dev/null 2>&1 || true
    python3 -m pip -q install --upgrade pip
    python3 -m pip -q install --upgrade -r requirements.txt
  else
    # Upstream behavior
    python3 -m pip -q install --upgrade -r requirements.txt
  fi
fi

printf '%s\n' 'Starting Casual Preloader' | info
exec ./main.py
