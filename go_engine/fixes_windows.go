//go:build windows

package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"
)

func enableVirtualTerminal() {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	setConsoleOutputCP := kernel32.NewProc("SetConsoleOutputCP")
	_, _, _ = setConsoleOutputCP.Call(uintptr(65001))

	handle := syscall.Handle(os.Stdout.Fd())
	var mode uint32
	if err := syscall.GetConsoleMode(handle, &mode); err == nil {
		const enableVirtualTerminalProcessing uint32 = 0x0004
		setConsoleMode := kernel32.NewProc("SetConsoleMode")
		_, _, _ = setConsoleMode.Call(uintptr(handle), uintptr(mode|enableVirtualTerminalProcessing))
	}
}

func isAdmin() bool {
	f, err := os.Open("\\\\.\\PHYSICALDRIVE0")
	if err != nil {
		return false
	}
	_ = f.Close()
	return true
}

func runOSAction(action string, target string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()

	var cmd *exec.Cmd
	switch action {
	case "flush-dns":
		cmd = exec.CommandContext(ctx, "ipconfig", "/flushdns")
	case "arp-clear":
		cmd = exec.CommandContext(ctx, "cmd", "/c", "arp -d * & nbtstat -R")
	case "restart-dns-svc":
		cmd = exec.CommandContext(ctx, "powershell", "-NoProfile", "-Command", "Restart-Service -Name Dnscache -Force -PassThru | Format-Table Name,Status,DisplayName -AutoSize")
	case "winsock-reset":
		cmd = exec.CommandContext(ctx, "netsh", "winsock", "reset")
	case "tcp-reset":
		cmd = exec.CommandContext(ctx, "netsh", "int", "ip", "reset")
	case "admin-sockets":
		cmd = exec.CommandContext(ctx, "netstat", "-abno")
	case "firewall-audit":
		cmd = exec.CommandContext(ctx, "netsh", "advfirewall", "show", "allprofiles")
	case "route-table":
		cmd = exec.CommandContext(ctx, "route", "print", "-4")
	case "net-status", "net-reset":
		cmd = exec.CommandContext(ctx, "netsh", "interface", "ip", "show", "config")
	case "sys-info", "sys-health":
		cmd = exec.CommandContext(ctx, "netstat", "-ep")
	default:
		return "", fmt.Errorf("unsupported Windows action: %s", action)
	}

	out, err := cmd.CombinedOutput()
	text := strings.TrimSpace(string(out))
	if err != nil {
		return text, fmt.Errorf("command failed: %w", err)
	}
	return text, nil
}
