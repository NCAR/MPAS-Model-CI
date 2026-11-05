#!/usr/bin/env bash
# Apply config_<name>=<value> overrides to an MPAS namelist file.
# Usage: apply-namelist-overrides.sh <namelist> "<overrides>"
#   overrides: one option per line, or ';'-separated. Values are written verbatim
#   (quote strings yourself). Existing keys are replaced; new keys are added to &physics.
set -euo pipefail

NAMELIST="${1:?namelist file required}"
OVERRIDES="${2:-}"
[ -f "${NAMELIST}" ] || { echo "::error::${NAMELIST} not found"; exit 1; }

while IFS= read -r entry; do
  entry="$(echo "${entry}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  [ -z "${entry}" ] && continue
  key="$(echo "${entry%%=*}" | sed -E 's/[[:space:]]+$//')"
  val="$(echo "${entry#*=}" | sed -E 's/^[[:space:]]+//')"
  if [[ "${entry}" != *=* || ! "${key}" =~ ^config_[A-Za-z0-9_]+$ || -z "${val}" ]]; then
    echo "::error::Bad namelist override '${entry}' (expected config_name=value)"
    exit 1
  fi
  esc="$(printf '%s' "${val}" | sed -e 's/[\\&|]/\\&/g')"
  if grep -qiE "^[[:space:]]*${key}[[:space:]]*=" "${NAMELIST}"; then
    sed -i -E "s|^[[:space:]]*${key}[[:space:]]*=.*|    ${key} = ${esc}|I" "${NAMELIST}"
    echo "Overrode ${key} = ${val}"
  else
    grep -qE '^&physics[[:space:]]*$' "${NAMELIST}" \
      || { echo "::error::No &physics group in ${NAMELIST} to add ${key}"; exit 1; }
    sed -i -E "/^&physics[[:space:]]*$/a\\    ${key} = ${esc}" "${NAMELIST}"
    echo "Added ${key} = ${val} to &physics"
  fi
done < <(printf '%s\n' "${OVERRIDES}" | tr ';' '\n')
