package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"
	"unicode/utf16"
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
	safeTargetRe = regexp.MustCompile(`[^A-Za-z0-9._-]+`)
)

func saveReportToFile(text string, target string, arg string) (string, error) {
	reportsDir := "/tmp"
	if runtime.GOOS == "windows" {
		reportsDir = `C:\Temp`
	}
	if err := os.MkdirAll(reportsDir, 0o755); err != nil {
		return "", err
	}

	ext := strings.ToLower(strings.TrimPrefix(strings.TrimSpace(arg), "."))
	if ext != "md" && ext != "txt" && ext != "json" {
		ext = "md"
	}
	safeTgt := strings.Trim(safeTargetRe.ReplaceAllString(strings.TrimSpace(target), "_"), "_")
	if safeTgt == "" {
		safeTgt = "target"
	}
	stamp := time.Now().Format("20060102_150405")
	dest := filepath.Join(reportsDir, fmt.Sprintf("TimeSpace_Diag_%s_%s.%s", safeTgt, stamp, ext))
	nowLocal := time.Now().Format("2006-01-02 15:04:05")
	cleanOut := strings.TrimSpace(text)

	var body string
	switch ext {
	case "json":
		payload := map[string]interface{}{
			"report":     "TimeSpace Diagnostic Report",
			"timestamp":  time.Now().UTC().Format(time.RFC3339),
			"local_time": nowLocal,
			"os":         runtime.GOOS,
			"arch":       runtime.GOARCH,
			"target":     target,
			"output":     cleanOut,
		}
		b, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			return "", err
		}
		body = string(b) + "\n"
	case "txt":
		body = fmt.Sprintf(
			"===================================================================\n"+
				"  TimeSpace Diagnostic Incident Report\n"+
				"  Generated : %s\n"+
				"  Target    : %s\n"+
				"  Platform  : %s/%s\n"+
				"===================================================================\n\n%s\n",
			nowLocal, target, runtime.GOOS, runtime.GOARCH, cleanOut,
		)
	default:
		body = fmt.Sprintf(
			"# TimeSpace Diagnostic Incident Report\n\n"+
				"- **Generated**: `%s`\n"+
				"- **Target**: `%s`\n"+
				"- **Platform**: `%s/%s`\n\n"+
				"## Console Output\n\n"+
				"```text\n%s\n```\n",
			nowLocal, target, runtime.GOOS, runtime.GOARCH, cleanOut,
		)
	}

	if err := os.WriteFile(dest, []byte(body), 0o644); err != nil {
		return "", err
	}
	absPath, err := filepath.Abs(dest)
	if err != nil {
		return dest, nil
	}
	return absPath, nil
}

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
	case "flush-dns", "arp-clear", "restart-dns-svc", "winsock-reset", "tcp-reset", "admin-sockets", "firewall-audit", "route-table", "net-status", "net-reset", "sys-info", "sys-health":
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

func copyToClipboard(text string) error {
	if runtime.GOOS == "windows" {
		cmd := exec.Command("clip")
		encoded := utf16.Encode([]rune(text))
		buf := make([]byte, 2+len(encoded)*2)
		buf[0] = 0xff
		buf[1] = 0xfe
		for i, v := range encoded {
			buf[2+i*2] = byte(v)
			buf[2+i*2+1] = byte(v >> 8)
		}
		cmd.Stdin = bytes.NewReader(buf)
		return cmd.Run()
	}
	if runtime.GOOS == "darwin" {
		cmd := exec.Command("pbcopy")
		cmd.Stdin = strings.NewReader(text)
		return cmd.Run()
	}
	linuxTools := [][]string{
		{"wl-copy"},
		{"xclip", "-selection", "clipboard"},
		{"xsel", "--clipboard", "--input"},
	}
	for _, tool := range linuxTools {
		if _, err := exec.LookPath(tool[0]); err == nil {
			cmd := exec.Command(tool[0], tool[1:]...)
			cmd.Stdin = strings.NewReader(text)
			return cmd.Run()
		}
	}
	return fmt.Errorf("no clipboard utility found (install wl-clipboard, xclip, or xsel)")
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

func mapUserOptionToActions(opt string) ([]string, bool) {
	switch opt {
	case "1", "ping":
		return []string{"ping"}, true
	case "2", "port-scan":
		return []string{"port-scan"}, true
	case "3", "tls-check":
		return []string{"tls-check"}, true
	case "4", "http-check":
		return []string{"http-check"}, true
	case "5", "dns-lookup":
		return []string{"dns-lookup"}, true
	case "6", "net-status":
		return []string{"net-status"}, true
	case "7", "sys-info":
		return []string{"sys-info"}, true
	case "8", "playbook":
		return []string{"ping", "port-scan", "tls-check", "http-check", "dns-lookup", "net-status", "sys-info"}, true
	default:
		return nil, false
	}
}

func mapAdminOptionToActions(opt string) ([]string, bool) {
	switch opt {
	case "1", "flush-dns":
		return []string{"flush-dns"}, true
	case "2", "arp-clear":
		return []string{"arp-clear"}, true
	case "3", "restart-dns-svc":
		return []string{"restart-dns-svc"}, true
	case "4", "winsock-reset":
		return []string{"winsock-reset"}, true
	case "5", "tcp-reset":
		return []string{"tcp-reset"}, true
	case "6", "admin-sockets":
		return []string{"admin-sockets"}, true
	case "7", "firewall-audit":
		return []string{"firewall-audit"}, true
	case "8", "route-table":
		return []string{"route-table"}, true
	case "9", "playbook":
		return []string{"flush-dns", "arp-clear", "firewall-audit", "route-table", "admin-sockets"}, true
	default:
		return nil, false
	}
}

func parseREPLSelection(raw string, adminMode bool) ([]string, error) {
	maxOpt := 8
	mapper := mapUserOptionToActions
	if adminMode {
		maxOpt = 9
		mapper = mapAdminOptionToActions
	}

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
		if mapped, ok := mapper(tok); ok {
			appendUnique(mapped)
			continue
		}
		if strings.Contains(tok, "-") {
			parts := strings.SplitN(tok, "-", 2)
			startNum, err1 := strconv.Atoi(parts[0])
			endNum, err2 := strconv.Atoi(parts[1])
			if err1 == nil && err2 == nil {
				if startNum < 1 || endNum > maxOpt || startNum > endNum {
					return nil, fmt.Errorf("invalid range '%s' (enter ranges within 1-%d, e.g., 1-4)", tok, maxOpt)
				}
				for n := startNum; n <= endNum; n++ {
					mapped, _ := mapper(strconv.Itoa(n))
					appendUnique(mapped)
				}
				continue
			}
		}
		if n, err := strconv.Atoi(tok); err == nil {
			return nil, fmt.Errorf("option '%d' is out of range (choose 1-%d)", n, maxOpt)
		}
		return nil, fmt.Errorf("unrecognized command '%s'", tok)
	}

	if len(actions) == 0 {
		return nil, fmt.Errorf("no diagnostic options selected")
	}
	return actions, nil
}

func handleBookmarksCommand(input string, currentTarget string, pBold string, okCol string, failCol string, rst string) string {
	settingsPath := filepath.Join("..", "data", "settings.json")
	if _, err := os.Stat(settingsPath); os.IsNotExist(err) {
		settingsPath = filepath.Join("data", "settings.json")
	}
	rawCfg := make(map[string]interface{})
	if b, err := os.ReadFile(settingsPath); err == nil {
		_ = json.Unmarshal(b, &rawCfg)
	}
	type bmEntry struct {
		Label string `json:"label"`
		Host  string `json:"host"`
	}
	var custom []bmEntry
	if listRaw, ok := rawCfg["custom_go_targets"].([]interface{}); ok {
		for _, item := range listRaw {
			if m, ok := item.(map[string]interface{}); ok {
				h, _ := m["host"].(string)
				l, _ := m["label"].(string)
				if strings.TrimSpace(h) != "" {
					if strings.TrimSpace(l) == "" {
						l = h
					}
					custom = append(custom, bmEntry{Label: strings.TrimSpace(l), Host: strings.TrimSpace(h)})
				}
			}
		}
	}
	builtins := []bmEntry{
		{Label: "Cloudflare DNS (1.1.1.1)", Host: "1.1.1.1"},
		{Label: "Google DNS (8.8.8.8)", Host: "8.8.8.8"},
		{Label: "GitHub (github.com)", Host: "github.com"},
		{Label: "Google (google.com)", Host: "google.com"},
		{Label: "Microsoft (microsoft.com)", Host: "microsoft.com"},
		{Label: "Localhost (127.0.0.1)", Host: "127.0.0.1"},
	}

	fields := strings.Fields(input)
	sub := ""
	if len(fields) > 1 {
		sub = strings.ToLower(fields[1])
	}
	if sub == "" {
		fmt.Printf("\n%s⭐ Saved Target Bookmarks:%s\n", pBold, rst)
		idx := 1
		for _, e := range custom {
			fmt.Printf("  [%d] ⭐ %s -> %s\n", idx, e.Label, e.Host)
			idx++
		}
		for _, e := range builtins {
			fmt.Printf("  [%d]    %s -> %s\n", idx, e.Label, e.Host)
			idx++
		}
		fmt.Printf("  Tip: 'bm <number>' to select, 'bm add <host> [label]' to save, 'bm del <host>' to remove.\n\n")
		return currentTarget
	}
	if sub == "add" {
		h := currentTarget
		l := currentTarget
		if len(fields) > 2 {
			h = fields[2]
			l = h
			if len(fields) > 3 {
				l = strings.Join(fields[3:], " ")
			}
		}
		var updated []bmEntry
		updated = append(updated, bmEntry{Label: l, Host: h})
		for _, e := range custom {
			if !strings.EqualFold(e.Host, h) {
				updated = append(updated, e)
			}
		}
		rawCfg["custom_go_targets"] = updated
		_ = os.MkdirAll(filepath.Dir(settingsPath), 0o755)
		if outBytes, err := json.MarshalIndent(rawCfg, "", "  "); err == nil {
			_ = os.WriteFile(settingsPath, outBytes, 0o644)
		}
		fmt.Printf("%s✔ Bookmarked '%s' (%s) and set as active target.%s\n\n", okCol, l, h, rst)
		return h
	}
	if sub == "del" || sub == "rm" || sub == "remove" {
		h := currentTarget
		if len(fields) > 2 {
			h = fields[2]
		}
		var updated []bmEntry
		removed := false
		for _, e := range custom {
			if strings.EqualFold(e.Host, h) {
				removed = true
			} else {
				updated = append(updated, e)
			}
		}
		if removed {
			rawCfg["custom_go_targets"] = updated
			if outBytes, err := json.MarshalIndent(rawCfg, "", "  "); err == nil {
				_ = os.WriteFile(settingsPath, outBytes, 0o644)
			}
			fmt.Printf("%s✔ Removed bookmark '%s'.%s\n\n", okCol, h, rst)
		} else {
			fmt.Printf("%s✖ Custom bookmark '%s' not found.%s\n\n", failCol, h, rst)
		}
		return currentTarget
	}
	if n, err := strconv.Atoi(sub); err == nil {
		all := append(custom, builtins...)
		if n >= 1 && n <= len(all) {
			chosen := all[n-1].Host
			fmt.Printf("%s✔ Active target set from bookmark [%d]: %s%s\n\n", okCol, n, chosen, rst)
			return chosen
		}
		fmt.Printf("%s✖ Invalid bookmark number [%d].%s\n\n", failCol, n, rst)
	}
	return currentTarget
}

func runInteractiveREPL(initialTarget string, cliMode string) {
	target := initialTarget
	if target == "" {
		target = "1.1.1.1"
	}

	adminMode := isAdmin()
	if strings.EqualFold(cliMode, "admin") {
		adminMode = true
	} else if strings.EqualFold(cliMode, "user") {
		adminMode = false
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

	maxOpt := 8
	promptLabel := "TimeSpace-User> "
	if adminMode {
		maxOpt = 9
		promptLabel = "TimeSpace-Admin⚡> "
	}

	lastOutput := ""
	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Printf("%s═══════════════════════════════════════════════════════════════════%s\n", pBold, rst)
		if adminMode {
			fmt.Printf("%s  ⚡🪻 TimeSpace Go Admin Remediation CLI [ELEVATED ADMIN / ROOT] | %s/%s%s\n", pBold, runtime.GOOS, runtime.GOARCH, rst)
			fmt.Printf("%s  Active Target: %s%s\n", pBold, target, rst)
			fmt.Printf("%s═══════════════════════════════════════════════════════════════════%s\n", pBold, rst)
			fmt.Printf("%s  [1] Flush OS DNS Resolver Cache (ipconfig /flushdns)%s\n", pNorm, rst)
			fmt.Printf("%s  [2] Clear ARP & NetBIOS Name Cache (arp -d & nbtstat -R)%s\n", pNorm, rst)
			fmt.Printf("%s  [3] Restart OS DNS Client Service (Dnscache / systemd-resolved)%s\n", pNorm, rst)
			fmt.Printf("%s  [4] Reset Winsock Catalog (netsh winsock reset)%s\n", pNorm, rst)
			fmt.Printf("%s  [5] Reset TCP/IP Stack (netsh int ip reset)%s\n", pNorm, rst)
			fmt.Printf("%s  [6] Elevated Port & Process Owner Audit (netstat -abno / ss -tulnp)%s\n", pNorm, rst)
			fmt.Printf("%s  [7] OS Firewall Profiles & Policy Audit (advfirewall / ufw)%s\n", pNorm, rst)
			fmt.Printf("%s  [8] Kernel IPv4 Routing Table & Gateway Audit (route print -4)%s\n", pNorm, rst)
			fmt.Printf("%s  [9] Automated Admin Repair & Audit Playbook (Flush DNS + ARP + Audits)%s\n", pNorm, rst)
		} else {
			fmt.Printf("%s  🪻 TimeSpace Go Diagnostic CLI [STANDARD USER MODE] | %s/%s%s\n", pBold, runtime.GOOS, runtime.GOARCH, rst)
			fmt.Printf("%s  Active Target: %s%s\n", pBold, target, rst)
			fmt.Printf("%s═══════════════════════════════════════════════════════════════════%s\n", pBold, rst)
			fmt.Printf("%s  [1] Ping & TCP Reachability Probe (Ports 443, 80, 53)%s\n", pNorm, rst)
			fmt.Printf("%s  [2] Concurrent TCP Port Scan (22, 53, 80, 443, 3389, 8080)%s\n", pNorm, rst)
			fmt.Printf("%s  [3] TLS / X.509 Certificate Inspector%s\n", pNorm, rst)
			fmt.Printf("%s  [4] HTTP/HTTPS Status, Redirect & Latency Probe%s\n", pNorm, rst)
			fmt.Printf("%s  [5] DNS Records Inspector (A / AAAA / CNAME / MX / NS / TXT)%s\n", pNorm, rst)
			fmt.Printf("%s  [6] Network Interface & IP Config Summary (Non-Admin)%s\n", pNorm, rst)
			fmt.Printf("%s  [7] Active Socket & System Uptime Summary (Non-Admin)%s\n", pNorm, rst)
			fmt.Printf("%s  [8] Automated Standard User Diagnostic Playbook (Runs 1–7)%s\n", pNorm, rst)
		}
		fmt.Printf("%s  ─────────────────────────────────────────────────────────────────%s\n", pNorm, rst)
		fmt.Printf("%s  Multi-Select   — Enter multiple or ranges (e.g., 1,3,4 or 1-4, 6)%s\n", pNorm, rst)
		fmt.Printf("%s  target <host>  — Change active target host/IP%s\n", pNorm, rst)
		fmt.Printf("%s  bm [n|add|del] — List/use/add/delete saved target bookmarks%s\n", pNorm, rst)
		fmt.Printf("%s  copy           — Copy last diagnostic output to clipboard%s\n", pNorm, rst)
		fmt.Printf("%s  save [fmt]     — Export last output to C:\\Temp (.md, .txt, or .json)%s\n", pNorm, rst)
		fmt.Printf("%s  clr            — Clear terminal screen%s\n", pNorm, rst)
		fmt.Printf("%s  exit           — Close interactive session%s\n", pNorm, rst)
		fmt.Printf("\n%s%s%s", pBold, promptLabel, rst)

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
		if lower == "copy" || lower == "cp" {
			if strings.TrimSpace(lastOutput) == "" {
				fmt.Printf("%s✖ No diagnostic output to copy yet. Run an option (1-%d) first.%s\n\n", failCol, maxOpt, rst)
				continue
			}
			if err := copyToClipboard(lastOutput); err != nil {
				fmt.Printf("%s✖ Failed to copy to clipboard: %v%s\n\n", failCol, err, rst)
			} else {
				lineCount := len(strings.Split(strings.TrimSpace(lastOutput), "\n"))
				fmt.Printf("%s✔ Copied last diagnostic output (%d lines) to clipboard.%s\n\n", okCol, lineCount, rst)
			}
			continue
		}
		if lower == "save" || strings.HasPrefix(lower, "save ") || lower == "export" || strings.HasPrefix(lower, "export ") {
			if strings.TrimSpace(lastOutput) == "" {
				fmt.Printf("%s✖ No diagnostic output to save yet. Run an option (1-%d) first.%s\n\n", failCol, maxOpt, rst)
				continue
			}
			fields := strings.Fields(input)
			fmtArg := "md"
			if len(fields) > 1 {
				fmtArg = fields[1]
			}
			savedPath, err := saveReportToFile(lastOutput, target, fmtArg)
			if err != nil {
				fmt.Printf("%s✖ Failed to save diagnostic report: %v%s\n\n", failCol, err, rst)
			} else {
				fmt.Printf("%s✔ Saved diagnostic report to: %s%s\n\n", okCol, savedPath, rst)
			}
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
		if lower == "bm" || lower == "bookmarks" || strings.HasPrefix(lower, "bm ") || strings.HasPrefix(lower, "bookmarks ") {
			target = handleBookmarksCommand(input, target, pBold, okCol, failCol, rst)
			continue
		}

		actionsToRun, parseErr := parseREPLSelection(input, adminMode)
		if parseErr != nil {
			fmt.Printf("%s✖ %v. Enter 1-%d (e.g., 1,3,4 or 1-4, 6), 'target <host>', 'copy', 'save', 'clr', or 'exit'.%s\n\n", failCol, parseErr, maxOpt, rst)
			continue
		}

		total := len(actionsToRun)
		modeTag := "USER"
		if adminMode {
			modeTag = "ADMIN"
		}
		var batchLines []string
		batchLines = append(batchLines, fmt.Sprintf("[TimeSpace-Go %s | %s/%s | target: %s]", modeTag, runtime.GOOS, runtime.GOARCH, target))
		for idx, act := range actionsToRun {
			stepPrefix := ""
			if total > 1 {
				stepPrefix = fmt.Sprintf("[%d/%d] ", idx+1, total)
			}
			headerLine := fmt.Sprintf("▶ %sRunning '%s' on '%s'...", stepPrefix, act, target)
			fmt.Printf("\n%s%s%s\n", pBold, headerLine, rst)
			batchLines = append(batchLines, headerLine)
			out, err := executeAction(act, target)
			if out != "" {
				fmt.Println(out)
				batchLines = append(batchLines, out)
			}
			if err != nil {
				failLine := fmt.Sprintf("✖ [FAIL] %s: %v", act, err)
				fmt.Printf("%s%s%s\n", failCol, failLine, rst)
				batchLines = append(batchLines, failLine)
			} else {
				passLine := fmt.Sprintf("✔ [PASS] %s completed.", act)
				fmt.Printf("%s%s%s\n", okCol, passLine, rst)
				batchLines = append(batchLines, passLine)
			}
		}
		lastOutput = strings.Join(batchLines, "\n")
		fmt.Println()
	}
}

func main() {
	action := flag.String("action", "ping", "Diagnostic action")
	target := flag.String("target", "1.1.1.1", "Target IP, hostname, or host:port")
	interactive := flag.Bool("interactive", false, "Launch interactive diagnostic REPL")
	cliMode := flag.String("cli-mode", "auto", "Interactive CLI profile: auto, user, or admin")
	flag.Parse()

	cleanAction := strings.ToLower(strings.TrimSpace(*action))
	cleanTarget := strings.TrimSpace(*target)
	if cleanTarget == "" {
		cleanTarget = "1.1.1.1"
	}

	if *interactive {
		runInteractiveREPL(cleanTarget, strings.TrimSpace(*cliMode))
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
