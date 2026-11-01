//go:build darwin

package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"
)

func enableVirtualTerminal() {}

func isAdmin() bool {
	return os.Geteuid() == 0
}

func runOSAction(action string, target string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()

	var cmd *exec.Cmd
	switch action {
	case "flush-dns":
		cmd = exec.CommandContext(ctx, "dscacheutil", "-flushcache")
	case "arp-clear":
		cmd = exec.CommandContext(ctx, "arp", "-a")
	case "restart-dns-svc":
		cmd = exec.CommandContext(ctx, "killall", "-HUP", "mDNSResponder")
	case "winsock-reset":
		cmd = exec.CommandContext(ctx, "netstat", "-s")
	case "tcp-reset":
		cmd = exec.CommandContext(ctx, "sysctl", "net.inet.tcp")
	case "admin-sockets":
		cmd = exec.CommandContext(ctx, "lsof", "-i", "-P", "-n")
	case "firewall-audit":
		cmd = exec.CommandContext(ctx, "/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate")
	case "route-table":
		cmd = exec.CommandContext(ctx, "netstat", "-rn", "-f", "inet")
	case "net-status", "net-reset":
		cmd = exec.CommandContext(ctx, "ifconfig")
	case "sys-info", "sys-health":
		cmd = exec.CommandContext(ctx, "uptime")
	default:
		return "", fmt.Errorf("unsupported macOS action: %s", action)
	}

	out, err := cmd.CombinedOutput()
	text := strings.TrimSpace(string(out))
	if err != nil {
		return text, fmt.Errorf("command failed: %w", err)
	}
	return text, nil
}
