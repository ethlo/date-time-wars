#!/usr/bin/env bash
#
# throughput.sh - parse every timestamp of a 1 GB CSV, end to end, with each pipeline in its own JVM.
#
#   ./throughput.sh                 # generate the two files if missing, run all pipelines, print the table
#   ./throughput.sh --size 256      # smaller files (MB), for a quick look
#   ./throughput.sh --passes 5      # more timed passes per pipeline (median is reported)
#   ./throughput.sh --pipelines jdk,itu-buffer
#
# Two rows are floors: floor-string is readLine + split + substring with no parse, floor-buffer the byte scan and
# char[] copy with no parse. "parser" in the table is the row minus its floor - the only column in which two
# parsers can be compared, since everything else in the row is the same code.
#
# What this measures that bench.sh cannot: the input is not in L1, the shapes vary line to line (the "mixed"
# file), and allocation happens at pipeline scale. The result is a *pipeline* time, so the ratio between two rows
# is not a parser ratio: once the parser is faster than the reading and splitting around it, it disappears into
# them. See throughput.Run for the pipelines.
#
# Files live under results/throughput/ (gitignored) and are generated deterministically, so a run is repeatable.
# The first pass over each file is a warm-up (JIT, and page cache if the file was cold) and is not counted.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

size_mb=1024
passes=3
pipelines="floor-string,jdk,itu-string,floor-buffer,itu-buffer"
shapes="uniform,mixed"
java_opts="${JAVA_OPTS:--Xms2g -Xmx2g}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --size)      size_mb="$2"; shift ;;
        --passes)    passes="$2"; shift ;;
        --pipelines) pipelines="$2"; shift ;;
        --shapes)    shapes="$2"; shift ;;
        -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

jar=target/date-time-wars.jar
[[ -f "$jar" ]] || mvn -q -ntp -DskipTests package
dir=results/throughput
mkdir -p "$dir"

stamp=$(date +%Y%m%d-%H%M%S)
log="$dir/$stamp.log"
echo "# $(java -version 2>&1 | head -1) · $(uname -m) · $java_opts · passes=$passes" | tee "$log"

declare -A result
for shape in ${shapes//,/ }; do
    file="$dir/timestamps-$shape-${size_mb}mb.csv"
    if [[ ! -f "$file" ]]; then
        java -cp "$jar" throughput.Generate "$file" "$shape" "$size_mb" | tee -a "$log"
    fi
    for pipeline in ${pipelines//,/ }; do
        # shellcheck disable=SC2086
        java $java_opts -cp "$jar" throughput.Run "$file" "$pipeline" "$passes" | tee -a "$log"
        result["$shape,$pipeline"]=$(grep "^RESULT" "$log" | tail -1)
    done
done

{
    echo
    echo "| Pipeline | File | Median | ns/timestamp | parser ns/timestamp | MB/s | vs jdk |"
    echo "|:---|:---|---:|---:|---:|---:|---:|"
    for shape in ${shapes//,/ }; do
        field() { sed -n "s/.* $2=\([-0-9.]*\).*/\1/p" <<<"${result[$shape,$1]:-}"; }
        jdk_ms=$(field jdk median_ms); jdk_ms=${jdk_ms:-0}
        for pipeline in ${pipelines//,/ }; do
            ms=$(field "$pipeline" median_ms); ns=$(field "$pipeline" ns_per_timestamp); mbs=$(field "$pipeline" mb_per_s)
            case "$pipeline" in
                jdk|itu-string) floor_ns=$(field floor-string ns_per_timestamp) ;;
                itu-buffer)     floor_ns=$(field floor-buffer ns_per_timestamp) ;;
                *)              floor_ns="" ;;
            esac
            parser=$([[ -n "$floor_ns" && -n "$ns" ]] && awk "BEGIN{printf \"%.1f\", $ns-$floor_ns}" || echo "—")
            ratio=$([[ "$jdk_ms" -gt 0 && -n "$ms" && "$ms" -gt 0 && "$pipeline" != floor-* ]] && awk "BEGIN{printf \"%.1f×\", $jdk_ms/$ms}" || echo "—")
            printf '| `%s` | %s %s MB | %s ms | %s | %s | %s | %s |\n' "$pipeline" "$shape" "$size_mb" "$ms" "$ns" "$parser" "$mbs" "$ratio"
        done
    done
    echo
    echo "Hashes (parsing rows must agree per file):"
    for k in $(printf '%s\n' "${!result[@]}" | sort); do
        [[ "$k" == *floor* ]] && continue
        sed -n 's/.*pipeline=\([^ ]*\).*file=\([^ ]*\).*hash=\(-\?[0-9]*\).*/  \2 \1 \3/p' <<<"${result[$k]}"
    done
} | tee -a "$log"
echo "log: $log"
