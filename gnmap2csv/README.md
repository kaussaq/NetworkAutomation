# gnmap2csv

A tiny, dependency-free Python script that converts Nmap's grepable output (`.gnmap`) into a CSV with one row per host per port, ready to open in Excel or Google Sheets. Includes the standard Nmap command used for large-scale firewall and connectivity testing.

Nmap has no native CSV output, and grepable files are awkward to filter or pivot. This turns them into a flat table you can sort, filter and share.

## Features

- Pure Python 3 standard library, nothing to install
- One row per host/port, so it is easy to filter and pivot
- Keeps open, closed, filtered and `open|filtered` ports (UDP scans included)
- Captures service name and version string when you scan with `-sV`
- Safe to run on large scans, since it reads the file line by line

## Requirements

- Python 3.6+

## Connectivity testing with Nmap

The standard scan used for checking which ports a destination range is reachable on from a given source network. Run it **from a host inside the source subnet you are testing**, because results reflect the firewall, NAT and routing path from that location.

### The command

```bash
sudo nmap -sS -sU -Pn -T4 --max-retries 1 \
  -p 'PORT_SPEC' \
  192.0.2.195-254 \
  -oA scan_results
```

Replace `PORT_SPEC` with the TCP and UDP ports you want to scan, for example `T:80,443,U:53`. Change the target range to suit. The `T:` and `U:` prefixes let you scan different TCP and UDP ports in one run. The addresses in this README use documentation-only ranges; substitute systems you are authorized to scan.

| Flag | What it does |
|---|---|
| `-sS` | TCP SYN scan (fast, needs root) |
| `-sU` | UDP scan (slow, needs root) |
| `-Pn` | Skip host discovery, so hosts that block ping are still scanned |
| `-T4` | Faster timing, fine on reliable networks |
| `--max-retries 1` | Limits retransmissions, which speeds up UDP scans a lot |
| `-p T:...,U:...` | Separate TCP and UDP port lists |
| `-oA scan_results` | Writes `.nmap`, `.xml` and `.gnmap` files, and the `.gnmap` is what this script reads |

### Optional tweaks

- `--open` shows only open ports and cuts the noise.
- `-sV` adds service and version detection (slower, but resolves some UDP `open|filtered` results).
- `--host-timeout 5m` stops a slow host from stalling the whole scan.
- `-iL targets.txt` reads targets from a file, which is useful for non-contiguous ranges.

### Reading the results

| State | Meaning |
|---|---|
| `open` | Reachable and a service answered |
| `closed` | Host replied with a reset, so it is reachable but nothing is listening |
| `filtered` | No reply, usually a firewall or security group silently dropping the traffic |
| `open\|filtered` | UDP only: no reply, so Nmap cannot tell open from dropped. **Unconfirmed** |

Because the scan uses `-Pn`, a host with every port `filtered` could be down or fully firewalled. The results cannot distinguish the two.

### Testing from multiple sources

To compare results across several source networks (for example before and after a NAT or firewall change), run the same command from each source subnet and name the outputs after the source:

```bash
# run from a host in 198.51.100.0/27
sudo nmap ... -oA 198_51_100_0-27
python3 gnmap2csv.py 198_51_100_0-27.gnmap 198_51_100_0-27.csv
```

Repeat for each source subnet, then combine the CSVs in a spreadsheet and summarise per source/destination.

## Converting to CSV

```bash
python3 gnmap2csv.py <input.gnmap> <output.csv>
```

### Full workflow

```bash
sudo nmap -sS -sU -Pn -T4 --max-retries 1 -p T:80,443,U:53 192.0.2.0/24 -oA scan_results
python3 gnmap2csv.py scan_results.gnmap scan_results.csv
```

If you only want grepable output, use `-oG scan_results.gnmap` instead of `-oA`.

## Output columns

| Column | Description |
|---|---|
| `IP` | Target IP address |
| `Hostname` | Reverse DNS name, blank if none was resolved |
| `Port` | Port number |
| `Protocol` | `tcp` or `udp` |
| `State` | `open`, `closed`, `filtered`, `open\|filtered`, etc. |
| `Service` | Service name guessed by Nmap (for example `msrpc`) |
| `Version` | Version string, populated when you scan with `-sV` |

### Example

Input (`.gnmap`):

```
Host: 192.0.2.5 ()	Ports: 80/open/tcp//http///, 443/open/tcp//https///, 8080/filtered/tcp//http-proxy///, 53/open|filtered/udp//domain///	Ignored State: closed (1)
```

Output (`.csv`):

```csv
IP,Hostname,Port,Protocol,State,Service,Version
192.0.2.5,,80,tcp,open,http,
192.0.2.5,,443,tcp,open,https,
192.0.2.5,,8080,tcp,filtered,http-proxy,
192.0.2.5,,53,udp,open|filtered,domain,
```

## Tips

- **Cut the noise:** scan with `--open` so only open ports are written, or filter the `State` column in your spreadsheet afterwards.
- **File size:** without `--open`, the CSV includes closed and filtered ports too, so a 60-host scan across 35 ports produces 2,100 rows.
- **UDP results:** only `open` is confirmed. See the state table above.
- **Combining multiple scans:** run the script once per `.gnmap` file and add a source column, or stack the CSVs in your spreadsheet tool.

## Limitations

- Hosts with no `Ports:` field are skipped. Nmap only includes that field when there is something to report, so hosts with no scanned or reportable ports will not appear in the CSV.
- Only the `Host: ... Ports: ...` lines are parsed. Other gnmap fields (OS detection, `Status:` lines, and so on) are ignored.
- There is no argument validation. Both the input and output paths are required, and an existing output file is overwritten.
