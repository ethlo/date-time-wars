#!/usr/bin/env bash
#
# bench.sh - run the date-time-wars JMH benchmarks and generate a report.
#
#   ./bench.sh --quick --duration        # ~1min smoke run of the duration benchmarks
#   ./bench.sh --parse --gc              # full parse suite with allocation stats
#   ./bench.sh --thorough --all --async  # publishable numbers + flame graphs
#   ./bench.sh --list                    # what benchmarks exist?
#
# Results land in results/<timestamp>-<suite>-<mode>/ with the raw JMH JSON,
# report.md, report.html and (if matplotlib is installed) report.png.
# results/latest always points at the most recent run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

JAR="target/date-time-wars.jar"
RESULTS_ROOT="results"

# --- defaults -----------------------------------------------------------------
suites=()
mode="normal"
patterns=()
out_dir=""
label=""
prof_gc=0
prof_async=0
async_lib="${ASYNC_PROFILER_LIB:-}"
async_event="cpu"
do_build=0
do_list=0
dry_run=0
no_report=0
open_report=0
verbose=0
baseline=""
jvm_args="-XX:+UnlockDiagnosticVMOptions -XX:+TieredCompilation -XX:+AlwaysPreTouch"
extra_jmh_args=()

# --- pretty output ------------------------------------------------------------
if [[ -t 1 ]]; then
    C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'; C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_RED=$'\e[31m'; C_CYAN=$'\e[36m'; C_RESET=$'\e[0m'
else
    C_BOLD=""; C_DIM=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_CYAN=""; C_RESET=""
fi
info()  { echo "${C_CYAN}▸${C_RESET} $*"; }
ok()    { echo "${C_GREEN}✔${C_RESET} $*"; }
warn()  { echo "${C_YELLOW}⚠${C_RESET} $*" >&2; }
die()   { echo "${C_RED}✖${C_RESET} $*" >&2; exit 1; }

usage() {
    cat <<EOF
${C_BOLD}Usage:${C_RESET} ./bench.sh [options] [benchmark-regex]

${C_BOLD}Suites${C_RESET} (which benchmarks to run - combine freely, default is --all)
  --parse           strict date-time parsers      (.*\\.parse\$)
  --lenient         lenient date-time parsers     (.*\\.parseLenient\$)
  --format          date-time formatters          (.*\\.format(Seconds|Millis|Nanos)\$)
  --datetime        the three above
  --duration        duration parse + format       (.*\\.(parse|format)Duration\$)
  --all             everything
  <regex>           a raw JMH benchmark regex, e.g. 'itu.*parse'

${C_BOLD}Modes${C_RESET} (how long to run)
  --quick           1 fork,  2×1s warmup,  3×1s measure   (~10s per benchmark, sanity check)
  --normal          1 fork,  3×2s warmup,  5×2s measure   (default)
  --thorough        3 forks, 5×3s warmup, 10×3s measure   (publishable numbers)

${C_BOLD}Profiling${C_RESET}
  --gc              add the JMH gc profiler (allocation per op etc.)
  --async [PATH]    add async-profiler flame graphs. PATH is libasyncProfiler.so;
                    defaults to \$ASYNC_PROFILER_LIB, then a lookup in ~/Downloads and /opt
  --async-event EV  async-profiler event: cpu (default), alloc, wall, lock

${C_BOLD}Output${C_RESET}
  -o, --out DIR     result directory (default: results/<timestamp>-<suite>-<mode>)
  -n, --name NAME   label for this run, appended to the directory name and shown in the report
  --baseline DIR    compare against a previous run's directory (or jmh-result.json)
  --no-report       skip report generation, keep only the raw JMH json
  --open            open report.html in the browser when done

${C_BOLD}Other${C_RESET}
  -b, --build       run 'mvn -q package' first (automatic if the jar is missing)
  -l, --list        list matching benchmarks and exit
  --jvm-args ARGS   forked JVM args (default: "$jvm_args")
  --jmh ARGS        pass extra raw args to JMH, e.g. --jmh "-t 4"
  --dry-run         print the command instead of running it
  -v, --verbose     JMH verbose output (-v EXTRA)
  -h, --help        this help

${C_BOLD}Examples${C_RESET}
  ./bench.sh --quick --duration
  ./bench.sh --parse --lenient --gc -n "itu-1.15"
  ./bench.sh --thorough --all --async --baseline results/latest
EOF
}

# --- arg parsing --------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all|--parse|--lenient|--format|--datetime|--duration) suites+=("${1#--}") ;;
        --quick|--normal|--thorough)       mode="${1#--}" ;;
        --gc)          prof_gc=1 ;;
        --async)
            prof_async=1
            if [[ $# -gt 1 && "$2" != -* && "$2" == *.so ]]; then async_lib="$2"; shift; fi ;;
        --async-event) async_event="$2"; shift ;;
        -o|--out)      out_dir="$2"; shift ;;
        -n|--name)     label="$2"; shift ;;
        --baseline)    baseline="$2"; shift ;;
        --no-report)   no_report=1 ;;
        --open)        open_report=1 ;;
        -b|--build)    do_build=1 ;;
        -l|--list)     do_list=1 ;;
        --jvm-args)    jvm_args="$2"; shift ;;
        --jmh)         read -r -a _extra <<<"$2"; extra_jmh_args+=("${_extra[@]}"); shift ;;
        --dry-run)     dry_run=1 ;;
        -v|--verbose)  verbose=1 ;;
        -h|--help)     usage; exit 0 ;;
        -*)            die "Unknown option: $1 (try --help)" ;;
        *)             patterns+=("$1"); suites+=("custom") ;;
    esac
    shift
done

# --- resolve suites -> JMH regexes -------------------------------------------
[[ ${#suites[@]} -gt 0 ]] || suites=(all)
for s in "${suites[@]}"; do
    case "$s" in
        all)      patterns+=('.*') ;;
        parse)    patterns+=('.*\.parse$') ;;
        lenient)  patterns+=('.*\.parseLenient$') ;;
        format)   patterns+=('.*\.format(Seconds|Millis|Nanos)$') ;;
        datetime) patterns+=('.*\.parse$' '.*\.parseLenient$' '.*\.format(Seconds|Millis|Nanos)$') ;;
        duration) patterns+=('.*\.(parse|format)Duration$') ;;
        custom)   ;;
    esac
done
suite="$(IFS=+; echo "${suites[*]}")"
pattern="$(IFS='|'; echo "${patterns[*]}")"

# --- resolve mode -> JMH iteration args --------------------------------------
case "$mode" in
    quick)    iter_args=(-f 1 -wi 2 -w 1s -i 3  -r 1s) ;;
    normal)   iter_args=(-f 1 -wi 3 -w 2s -i 5  -r 2s) ;;
    thorough) iter_args=(-f 3 -wi 5 -w 3s -i 10 -r 3s) ;;
esac

# --- build if needed ----------------------------------------------------------
if [[ $do_build -eq 1 || ! -f "$JAR" ]]; then
    [[ -f "$JAR" ]] || info "Jar not found, building..."
    info "mvn -q clean package"
    [[ $dry_run -eq 1 ]] || mvn -q -DskipTests clean package || die "Build failed"
    ok "Built $JAR"
fi

# --- list mode ----------------------------------------------------------------
if [[ $do_list -eq 1 ]]; then
    java -jar "$JAR" -l "${patterns[@]}"
    exit 0
fi

# --- async profiler discovery -------------------------------------------------
if [[ $prof_async -eq 1 && -z "$async_lib" ]]; then
    async_lib="$(find "$HOME/Downloads" /opt /usr/local -maxdepth 4 -name libasyncProfiler.so 2>/dev/null | sort -V | tail -n1 || true)"
    [[ -n "$async_lib" ]] || die "async-profiler not found. Pass --async /path/to/libasyncProfiler.so or set ASYNC_PROFILER_LIB"
fi
if [[ $prof_async -eq 1 && ! -f "$async_lib" ]]; then
    die "async-profiler library not found: $async_lib"
fi

# --- output directory ---------------------------------------------------------
if [[ -z "$out_dir" ]]; then
    stamp="$(date +%Y%m%d-%H%M%S)"
    out_dir="$RESULTS_ROOT/${stamp}-${suite}-${mode}${label:+-$label}"
fi
result_json="$out_dir/jmh-result.json"

if [[ -n "$baseline" && -d "$baseline" ]]; then
    baseline="$baseline/jmh-result.json"
fi
if [[ -n "$baseline" && ! -f "$baseline" ]]; then
    die "Baseline not found: $baseline"
fi

# --- assemble JMH command -----------------------------------------------------
cmd=(java -jar "$JAR" "${patterns[@]}"
     -bm avgt -tu ns
     "${iter_args[@]}"
     -jvmArgs "$jvm_args"
     -rf json -rff "$result_json"
     -v "$([[ $verbose -eq 1 ]] && echo EXTRA || echo NORMAL)")

[[ $prof_gc -eq 1 ]] && cmd+=(-prof gc)
if [[ $prof_async -eq 1 ]]; then
    cmd+=(-prof "async:libPath=$async_lib;event=$async_event;output=flamegraph;dir=$out_dir/profiles")
fi
cmd+=("${extra_jmh_args[@]}")

# --- go -----------------------------------------------------------------------
echo
echo "${C_BOLD}date-time-wars benchmark${C_RESET}"
echo "  suite:    $suite  ${C_DIM}($pattern)${C_RESET}"
echo "  mode:     $mode  ${C_DIM}(${iter_args[*]})${C_RESET}"
echo "  profilers:$([[ $prof_gc -eq 1 ]] && echo ' gc')$([[ $prof_async -eq 1 ]] && echo " async[$async_event]")$([[ $prof_gc -eq 0 && $prof_async -eq 0 ]] && echo ' none')"
echo "  java:     $(java -version 2>&1 | head -n1)"
echo "  output:   $out_dir"
[[ -n "$baseline" ]] && echo "  baseline: $baseline"
echo

if [[ $dry_run -eq 1 ]]; then
    printf '%q ' "${cmd[@]}"; echo
    exit 0
fi

mkdir -p "$out_dir"
start=$(date +%s)
"${cmd[@]}" 2>&1 | tee "$out_dir/jmh.log"
elapsed=$(( $(date +%s) - start ))

[[ -s "$result_json" ]] || die "JMH produced no result file (see $out_dir/jmh.log)"
ok "JMH finished in ${elapsed}s → $result_json"

# --- run metadata -------------------------------------------------------------
{
    echo "date=$(date -Iseconds)"
    echo "suite=$suite"
    echo "pattern=$pattern"
    echo "mode=$mode"
    echo "label=$label"
    echo "iterations=${iter_args[*]}"
    echo "jvm_args=$jvm_args"
    echo "profilers=$([[ $prof_gc -eq 1 ]] && echo -n 'gc ')$([[ $prof_async -eq 1 ]] && echo -n "async:$async_event")"
    echo "host=$(hostname)"
    echo "cpu=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ *//' || sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)"
    echo "os=$( (source /etc/os-release 2>/dev/null && echo "$PRETTY_NAME") || uname -sr)"
    echo "java=$(java -version 2>&1 | head -n1)"
    echo "git=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)$(git diff --quiet 2>/dev/null || echo '-dirty')"
    echo "elapsed_seconds=$elapsed"
} > "$out_dir/run.properties"

# --- report -------------------------------------------------------------------
if [[ $no_report -eq 0 ]]; then
    report_args=("$result_json" -o "$out_dir")
    [[ -n "$baseline" ]] && report_args+=(--baseline "$baseline")
    python3 report.py "${report_args[@]}" || warn "Report generation failed; raw results are still in $out_dir"
fi

ln -sfn "$(basename "$out_dir")" "$RESULTS_ROOT/latest"
ok "Done. Latest results: $RESULTS_ROOT/latest → $out_dir"

if [[ $open_report -eq 1 && -f "$out_dir/report.html" ]]; then
    (xdg-open "$out_dir/report.html" 2>/dev/null || open "$out_dir/report.html" 2>/dev/null) &
fi
