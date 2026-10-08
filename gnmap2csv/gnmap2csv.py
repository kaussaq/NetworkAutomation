import csv, re, sys

src, dst = sys.argv[1], sys.argv[2]

with open(src) as f, open(dst, "w", newline="") as out:
    w = csv.writer(out)
    w.writerow(["IP", "Hostname", "Port", "Protocol", "State", "Service", "Version"])
    for line in f:
        if not line.startswith("Host:") or "Ports:" not in line:
            continue
        m = re.match(r"Host: (\S+) \(([^)]*)\)\s+Ports: (.*?)(?:\t|$)", line)
        if not m:
            continue
        ip, name, ports = m.groups()
        for entry in ports.split(", "):
            # port/state/protocol/owner/service/rpc/version/
            p = entry.strip().split("/")
            if len(p) < 5:
                continue
            version = p[6] if len(p) > 6 else ""
            w.writerow([ip, name, p[0], p[2], p[1], p[4], version])