package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const (
	// TimeSpace signature purple/indigo accent (#6366f1 -> RGB 99, 102, 241)
	ansiPurpleBold = "\x1b[1;38;2;99;102;241m"
	ansiPurple     = "\x1b[38;2;99;102;241m"
	ansiGreenBold  = "\x1b[1;38;2;16;185;129m"
	ansiRedBold    = "\x1b[1;38;2;239;68;68m"
	ansiReset      = "\x1b[0m"
)

var (
	rangeSpaceRe = regexp.MustCompile(`(\d+)\s*-\s*(\d+)`)
	tokenSplitRe = regexp.MustCompile(`[\s,]+`)
)

// DiagResult represents the structured final JSON payload emitted to stdout.
type DiagResult struct {
	Timestamp string `json:"timestamp"`
	OS        string `json:"os"`
	Arch      string `json:"arch"`
	Action    string `json:"action"`
	Target    string `json:"target"`
	Success   bool   `json:"success"`
	Output    string `json:"output"`
}

func executeAction(action string, target string) (string, error) {
	switch action {
	case "ping":
		return runPingProbe(target)
	case "port-scan":
		return runPortScan(target)
	case "tls-check":
		return runTLSCheck(target)
	case "http-check":
		return runHTTPCheck(target)
	case "dns-lookup":
		return runDNSLookup(target)
	case "flush-dns", "net-status", "net-reset", "sys-info", "sys-health":
		return runOSAction(action, target)
	default:
		return "", fmt.Errorf("unknown action '%s'", action)
	}
}

func supportsANSI() bool {
	enableVirtualTerminal()
	if os.Getenv("NO_COLOR") != "" {
		return false
	}
	fi, err := os.Stdout.Stat()
	if err != nil {
		return false
	}
	return (fi.Mode() & os.ModeCharDevice) != 0
}

func clearTerminalScreen(useColor bool) {
	if useColor {
		fmt.Print("\x1b[2J\x1b[3J\x1b[H")
		return
	}
	fi, err := os.Stdout.Stat()
	if err == nil && (fi.Mode()&os.ModeCharDevice) != 0 {
		var cmd *exec.Cmd
		if runtime.GOOS == "windows" {
			cmd = exec.Command("cmd", "/c", "cls")
		} else {
			cmd = exec.Command("clear")
		}
		cmd.Stdout = os.Stdout
		_ = cmd.Run()
	}
}

func mapOptionToActions(opt string) ([]string, bool) {
	switch opt {
	case "1", "ping":
		return []string{"ping"}, true
	case "2", "port-scan":
		return []string{"port-scan"}, true
	case "3", "tls-check":
		return []string{"tls-check"}, true
	case "4", "flush-dns":
		return []string{"flush-dns"}, true
	case "5", "http-check":
		return []string{"http-check"}, true
	case "6", "dns-lookup":
		return []string{"dns-lookup"}, true
	case "7", "playbook":
		return []string{"ping", "port-scan", "tls-check", "http-check", "dns-lookup", "net-status"}, true
	default:
		return nil, false
	}
}

func parseREPLSelection(raw string) ([]string, error) {
	normalized := rangeSpaceRe.ReplaceAllString(strings.ToLower(strings.TrimSpace(raw)), "${1}-${2}")
	rawTokens := tokenSplitRe.Split(normalized, -1)

	var actions []string
	seen := make(map[string]bool)
	appendUnique := func(items []string) {
		for _, act := range items {
			if !seen[act] {
				seen[act] = true
				actions = append(actions, act)
			}
		}
	}

	for _, tok := range rawTokens {
		if tok == "" {
			continue
		}
		if mapped, ok := mapOptionToActions(tok); ok {
			appendUnique(mapped)
			continue
		}
		if strings.Contains(tok, "-") {
			parts := strings.SplitN(tok, "-", 2)
			startNum, err1 := strconv.Atoi(parts[0])
			endNum, err2 := strconv.Atoi(parts[1])
			if err1 == nil && err2 == nil {
				if startNum < 1 || endNum > 7 || startNum > endNum {
					return nil, fmt.Errorf("invalid range '%s' (enter ranges within 1-7, e.g., 1-4)", tok)
				}
				for n := startNum; n <= endNum; n++ {
					mapped, _ := mapOptionToActions(strconv.Itoa(n))
					appendUnique(mapped)
				}
				continue
			}
		}
		if n, err := strconv.Atoi(tok); err == nil {
			return nil, fmt.Errorf("option '%d' is out of range (choose 1-7)", n)
		}
		return nil, fmt.Errorf("unrecognized command '%s'", tok)
	}

	if len(actions) == 0 {
		return nil, fmt.Errorf("no diagnostic options selected")
	}
	return actions, nil
}

func runInteractiveREPL(initialTarget string) {
	target := initialTarget
	if target == "" {
		target = "1.1.1.1"
	}

	useColor := supportsANSI()
	pBold := ""
	pNorm := ""
	okCol := ""
	failCol := ""
	rst := ""
	if useColor {
		pBold = ansiPurpleBold
		pNorm = ansiPurple
		okCol = ansiGreenBold
		failCol = ansiRedBold
		rst = ansiReset
	}

	privBadge := "[STANDARD USER]"
	if isAdmin() {
		privBadge = "[ADMIN / ROOT]"
	}

	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Printf("%s═══════════════════════════════════════════════════════════════════%s\n", pBold, rst)
		fmt.Printf("%s  🪻 TimeSpace Go Diagnostic REPL | %s/%s | %s%s\n", pBold, runtime.GOOS, runtime.GOARCH, privBadge, rst)
		fmt.Printf("%s  Active Target: %s%s\n", pBold, target, rst)
		fmt.Printf("%s═══════════════════════════════════════════════════════════════════%s\n", pBold, rst)
		fmt.Printf("%s  [1] Ping & TCP Reachability%s\n", pNorm, rst)
		fmt.Printf("%s  [2] Concurrent Port Scan (22, 53, 80, 443, 3389, 8080)%s\n", pNorm, rst)
		fmt.Printf("%s  [3] TLS Certificate Inspector%s\n", pNorm, rst)
		fmt.Printf("%s  [4] Flush DNS Cache (OS Fix)%s\n", pNorm, rst)
		fmt.Printf("%s  [5] HTTP/HTTPS Status & Latency Probe%s\n", pNorm, rst)
		fmt.Printf("%s  [6] DNS Records Inspector (A / AAAA / MX / NS / TXT)%s\n", pNorm, rst)
		fmt.Printf("%s  [7] Automated Network Triage Playbook (All Checks)%s\n", pNorm, rst)
		fmt.Printf("%s  ─────────────────────────────────────────────────────────────────%s\n", pNorm, rst)
		fmt.Printf("%s  Multi-Select   — Enter multiple or ranges (e.g., 1,3,4 or 1-4, 6)%s\n", pNorm, rst)
		fmt.Printf("%s  target <host>  — Change active target host/IP%s\n", pNorm, rst)
		fmt.Printf("%s  clr            — Clear terminal screen%s\n", pNorm, rst)
		fmt.Printf("%s  exit           — Close interactive session%s\n", pNorm, rst)
		fmt.Printf("\n%sTimeSpace-Go> %s", pBold, rst)

		if !scanner.Scan() {
			fmt.Println()
			return
		}
		input := strings.TrimSpace(scanner.Text())
		if input == "" {
			continue
		}
		lower := strings.ToLower(input)
		if lower == "exit" || lower == "quit" || lower == "q" {
			fmt.Println("Exiting TimeSpace Go Diagnostic REPL.")
			return
		}
		if lower == "clr" || lower == "clear" || lower == "cls" {
			clearTerminalScreen(useColor)
			continue
		}
		if strings.HasPrefix(lower, "target ") {
			newTgt := strings.TrimSpace(input[7:])
			if newTgt != "" {
				target = newTgt
				fmt.Printf("%s✔ Active target updated to: %s%s\n\n", okCol, target, rst)
			}
			continue
		}

		actionsToRun, parseErr := parseREPLSelection(input)
		if parseErr != nil {
			fmt.Printf("%s✖ %v. Enter 1-7 (e.g., 1,3,4 or 1-4, 6), 'target <host>', 'clr', or 'exit'.%s\n\n", failCol, parseErr, rst)
			continue
		}

		total := len(actionsToRun)
		for idx, act := range actionsToRun {
			stepPrefix := ""
			if total > 1 {
				stepPrefix = fmt.Sprintf("[%d/%d] ", idx+1, total)
			}
			fmt.Printf("\n%s▶ %sRunning '%s' on '%s'...%s\n", pBold, stepPrefix, act, target, rst)
			out, err := executeAction(act, target)
			if out != "" {
				fmt.Println(out)
			}
			if err != nil {
				fmt.Printf("%s✖ [FAIL] %s: %v%s\n", failCol, act, err, rst)
			} else {
				fmt.Printf("%s✔ [PASS] %s completed.%s\n", okCol, act, rst)
			}
		}
		fmt.Println()
	}
}

func main() {
	action := flag.String("action", "ping", "Diagnostic action: ping, port-scan, tls-check, http-check, dns-lookup, flush-dns, net-status, sys-info")
	target := flag.String("target", "1.1.1.1", "Target IP, hostname, or host:port")
	interactive := flag.Bool("interactive", false, "Launch interactive diagnostic REPL")
	flag.Parse()

	cleanAction := strings.ToLower(strings.TrimSpace(*action))
	cleanTarget := strings.TrimSpace(*target)
	if cleanTarget == "" {
		cleanTarget = "1.1.1.1"
	}

	if *interactive {
		runInteractiveREPL(cleanTarget)
		return
	}

	privBadge := "STANDARD"
	if isAdmin() {
		privBadge = "ADMIN/ROOT"
	}
	fmt.Printf("[Go Engine %s/%s | %s] Starting action='%s' target='%s'...\n", runtime.GOOS, runtime.GOARCH, privBadge, cleanAction, cleanTarget)

	output, err := executeAction(cleanAction, cleanTarget)
	if output != "" {
		for _, line := range strings.Split(strings.TrimSpace(output), "\n") {
			fmt.Println(line)
		}
	}

	result := DiagResult{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		OS:        runtime.GOOS,
		Arch:      runtime.GOARCH,
		Action:    cleanAction,
		Target:    cleanTarget,
		Success:   err == nil,
		Output:    strings.TrimSpace(output),
	}
	if err != nil && result.Output == "" {
		result.Output = err.Error()
	}

	encoded, jsonErr := json.Marshal(result)
	if jsonErr != nil {
		fmt.Fprintf(os.Stderr, "Failed to encode JSON result: %v\n", jsonErr)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
	if err != nil {
		os.Exit(1)
	}
}
