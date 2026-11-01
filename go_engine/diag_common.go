package main

import (
	"crypto/tls"
	"fmt"
	"net"
	"net/http"
	"sort"
	"strings"
	"sync"
	"time"
)

func extractHost(target string) string {
	trimmed := strings.TrimSpace(target)
	trimmed = strings.TrimPrefix(trimmed, "https://")
	trimmed = strings.TrimPrefix(trimmed, "http://")
	if idx := strings.Index(trimmed, "/"); idx >= 0 {
		trimmed = trimmed[:idx]
	}
	if host, _, err := net.SplitHostPort(trimmed); err == nil && host != "" {
		return host
	}
	return trimmed
}

func runPingProbe(target string) (string, error) {
	host := extractHost(target)
	var lines []string

	addrs, dnsErr := net.LookupHost(host)
	if dnsErr != nil {
		return fmt.Sprintf("DNS resolution failed for %s: %v", host, dnsErr), dnsErr
	}
	lines = append(lines, fmt.Sprintf("Resolved %s -> %s", host, strings.Join(addrs, ", ")))

	probePorts := []int{443, 80, 53}
	reachable := 0
	for _, port := range probePorts {
		addr := net.JoinHostPort(host, fmt.Sprintf("%d", port))
		start := time.Now()
		conn, err := net.DialTimeout("tcp", addr, 2*time.Second)
		elapsed := time.Since(start).Round(time.Millisecond)
		if err == nil {
			_ = conn.Close()
			reachable++
			lines = append(lines, fmt.Sprintf("TCP %s -> OPEN (RTT: %v)", addr, elapsed))
		} else {
			lines = append(lines, fmt.Sprintf("TCP %s -> UNREACHABLE (%v)", addr, err))
		}
	}

	if reachable == 0 {
		return strings.Join(lines, "\n"), fmt.Errorf("no TCP probe ports reachable on %s", host)
	}
	return strings.Join(lines, "\n"), nil
}

func runPortScan(target string) (string, error) {
	host := extractHost(target)
	ports := []int{22, 53, 80, 443, 3389, 8080}

	type scanResult struct {
		port    int
		open    bool
		latency time.Duration
	}

	var wg sync.WaitGroup
	results := make(chan scanResult, len(ports))

	for _, p := range ports {
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			addr := net.JoinHostPort(host, fmt.Sprintf("%d", port))
			start := time.Now()
			conn, err := net.DialTimeout("tcp", addr, 2*time.Second)
			elapsed := time.Since(start).Round(time.Millisecond)
			if err == nil {
				_ = conn.Close()
				results <- scanResult{port: port, open: true, latency: elapsed}
			} else {
				results <- scanResult{port: port, open: false, latency: elapsed}
			}
		}(p)
	}

	wg.Wait()
	close(results)

	var collected []scanResult
	for r := range results {
		collected = append(collected, r)
	}
	sort.Slice(collected, func(i, j int) bool {
		return collected[i].port < collected[j].port
	})

	var lines []string
	openCount := 0
	for _, r := range collected {
		status := "CLOSED/FILTERED"
		if r.open {
			status = fmt.Sprintf("OPEN (%v)", r.latency)
			openCount++
		}
		lines = append(lines, fmt.Sprintf("Port %-5d : %s", r.port, status))
	}
	lines = append(lines, fmt.Sprintf("Summary: %d/%d scanned ports open on %s", openCount, len(ports), host))
	return strings.Join(lines, "\n"), nil
}

func runTLSCheck(target string) (string, error) {
	host := extractHost(target)
	addr := net.JoinHostPort(host, "443")
	dialer := &net.Dialer{Timeout: 4 * time.Second}
	conn, err := tls.DialWithDialer(dialer, "tcp", addr, &tls.Config{
		ServerName: host,
	})
	if err != nil {
		return fmt.Sprintf("TLS handshake failed for %s: %v", addr, err), err
	}
	defer conn.Close()

	state := conn.ConnectionState()
	if len(state.PeerCertificates) == 0 {
		return "No peer certificates presented", fmt.Errorf("no peer certificates")
	}

	cert := state.PeerCertificates[0]
	daysRemaining := int(time.Until(cert.NotAfter).Hours() / 24)
	lines := []string{
		fmt.Sprintf("Target      : %s", addr),
		fmt.Sprintf("Subject     : %s", cert.Subject.CommonName),
		fmt.Sprintf("Issuer      : %s", cert.Issuer.CommonName),
		fmt.Sprintf("Valid From  : %s", cert.NotBefore.UTC().Format(time.RFC3339)),
		fmt.Sprintf("Valid Until : %s (%d days remaining)", cert.NotAfter.UTC().Format(time.RFC3339), daysRemaining),
	}
	if len(cert.DNSNames) > 0 {
		maxSANs := len(cert.DNSNames)
		if maxSANs > 5 {
			maxSANs = 5
		}
		lines = append(lines, fmt.Sprintf("SANs        : %s", strings.Join(cert.DNSNames[:maxSANs], ", ")))
	}
	if daysRemaining < 0 {
		return strings.Join(lines, "\n"), fmt.Errorf("certificate expired %d days ago", -daysRemaining)
	}
	return strings.Join(lines, "\n"), nil
}

func runHTTPCheck(target string) (string, error) {
	raw := strings.TrimSpace(target)
	var urls []string
	if strings.HasPrefix(strings.ToLower(raw), "http://") || strings.HasPrefix(strings.ToLower(raw), "https://") {
		urls = []string{raw}
	} else {
		urls = []string{"https://" + raw, "http://" + raw}
	}

	client := &http.Client{Timeout: 5 * time.Second}
	var lastErr error
	for _, u := range urls {
		start := time.Now()
		req, err := http.NewRequest(http.MethodGet, u, nil)
		if err != nil {
			lastErr = err
			continue
		}
		req.Header.Set("User-Agent", "TimeSpace-Diag/3.5")
		resp, err := client.Do(req)
		elapsed := time.Since(start).Round(time.Millisecond)
		if err != nil {
			lastErr = err
			continue
		}
		_ = resp.Body.Close()

		serverHdr := resp.Header.Get("Server")
		if serverHdr == "" {
			serverHdr = "(not disclosed)"
		}
		lines := []string{
			fmt.Sprintf("Request URL : %s", u),
			fmt.Sprintf("Final URL   : %s", resp.Request.URL.String()),
			fmt.Sprintf("HTTP Status : %s (%s)", resp.Status, resp.Proto),
			fmt.Sprintf("Latency     : %v", elapsed),
			fmt.Sprintf("Server      : %s", serverHdr),
		}
		if resp.StatusCode >= 400 {
			return strings.Join(lines, "\n"), fmt.Errorf("HTTP error status %d", resp.StatusCode)
		}
		return strings.Join(lines, "\n"), nil
	}
	return fmt.Sprintf("HTTP/HTTPS probe failed for %s: %v", target, lastErr), lastErr
}

func runDNSLookup(target string) (string, error) {
	host := extractHost(target)
	var lines []string

	ips, ipErr := net.LookupIP(host)
	if ipErr != nil {
		return fmt.Sprintf("DNS lookup failed for %s: %v", host, ipErr), ipErr
	}

	var v4, v6 []string
	for _, ip := range ips {
		if ip.To4() != nil {
			v4 = append(v4, ip.String())
		} else {
			v6 = append(v6, ip.String())
		}
	}
	if len(v4) > 0 {
		lines = append(lines, fmt.Sprintf("A (IPv4)    : %s", strings.Join(v4, ", ")))
	}
	if len(v6) > 0 {
		lines = append(lines, fmt.Sprintf("AAAA (IPv6) : %s", strings.Join(v6, ", ")))
	}

	if cname, err := net.LookupCNAME(host); err == nil && cname != "" && strings.TrimSuffix(cname, ".") != host {
		lines = append(lines, fmt.Sprintf("CNAME       : %s", cname))
	}

	if mxs, err := net.LookupMX(host); err == nil && len(mxs) > 0 {
		var mxStrs []string
		for i, mx := range mxs {
			if i >= 4 {
				break
			}
			mxStrs = append(mxStrs, fmt.Sprintf("%s (pref %d)", mx.Host, mx.Pref))
		}
		lines = append(lines, fmt.Sprintf("MX          : %s", strings.Join(mxStrs, ", ")))
	}

	if nss, err := net.LookupNS(host); err == nil && len(nss) > 0 {
		var nsStrs []string
		for i, ns := range nss {
			if i >= 4 {
				break
			}
			nsStrs = append(nsStrs, ns.Host)
		}
		lines = append(lines, fmt.Sprintf("NS          : %s", strings.Join(nsStrs, ", ")))
	}

	if txts, err := net.LookupTXT(host); err == nil && len(txts) > 0 {
		maxTxt := len(txts)
		if maxTxt > 3 {
			maxTxt = 3
		}
		for i := 0; i < maxTxt; i++ {
			t := txts[i]
			if len(t) > 90 {
				t = t[:90] + "..."
			}
			lines = append(lines, fmt.Sprintf("TXT [%d]     : %s", i+1, t))
		}
	}

	return strings.Join(lines, "\n"), nil
}
