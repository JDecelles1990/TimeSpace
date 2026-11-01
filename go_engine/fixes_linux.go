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
