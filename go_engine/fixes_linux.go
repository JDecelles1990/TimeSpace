//go:build linux

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
		cmd = exec.CommandContext(ctx, "resolvectl", "flush-caches")
	case "arp-clear":
		cmd = exec.CommandContext(ctx, "ip", "-s", "-s", "neigh", "flush", "all")
	case "restart-dns-svc":
		cmd = exec.CommandContext(ctx, "systemctl", "restart", "systemd-resolved")
	case "winsock-reset":
		cmd = exec.CommandContext(ctx, "ss", "-s")
	case "tcp-reset":
		cmd = exec.CommandContext(ctx, "sysctl", "net.ipv4.tcp_congestion_control")
	case "admin-sockets":
		cmd = exec.CommandContext(ctx, "ss", "-tulnp")
	case "firewall-audit":
		cmd = exec.CommandContext(ctx, "ufw", "status", "verbose")
	case "route-table":
		cmd = exec.CommandContext(ctx, "ip", "route", "show")
	case "net-status", "net-reset":
		cmd = exec.CommandContext(ctx, "ip", "-brief", "addr")
	case "sys-info", "sys-health":
		cmd = exec.CommandContext(ctx, "uptime")
	default:
		return "", fmt.Errorf("unsupported Linux action: %s", action)
	}

	out, err := cmd.CombinedOutput()
	text := strings.TrimSpace(string(out))
	if err != nil {
		return text, fmt.Errorf("command failed: %w", err)
	}
	return text, nil
}
