#!/usr/bin/env python3
"""Sends a VPN node's xray log lines to the bot, only for the users the bot watches (app/node_logs.py).

Standard library only. Environment:
  BOT_URL          the bot's public address, e.g. https://bot.example.com
  NODE_LOGS_TOKEN  the same secret as NODE_LOGS_TOKEN in the bot's .env
  NODE_NAME        how this node is named in the admin (default: the host name)
  ACCESS_LOG       default /var/log/remnanode/access.log
  ERROR_LOG        default /var/log/remnanode/error.log
"""
import json
import os
import re
import socket
import time
import urllib.request

BOT_URL = os.environ.get("BOT_URL", "").rstrip("/")
TOKEN = os.environ.get("NODE_LOGS_TOKEN", "")
NODE = os.environ.get("NODE_NAME") or socket.gethostname()
FILES = {"a": os.environ.get("ACCESS_LOG", "/var/log/remnanode/access.log"),
         "e": os.environ.get("ERROR_LOG", "/var/log/remnanode/error.log")}
WATCH_EVERY, FLUSH_EVERY, BATCH, BACKLOG = 60, 5, 400, 5000
IP_TTL = 600          # an address belongs to a user this long after its last accepted line
REPEAT = 30           # the same user and destination is sent at most once per this many seconds

ACCESS = re.compile(r" from (?:tcp:|udp:)?\[?([0-9a-fA-F.:]+?)\]?:\d+ (?:accepted|rejected)\s+(\S+)?.*?(?:email: (\S+))?$")
ANY_IP = re.compile(r"(?:from |remote )(?:tcp:|udp:)?\[?(\d{1,3}(?:\.\d{1,3}){3}|[0-9a-fA-F:]{4,})\]?:\d+")


def call(method, path, body=None):
    req = urllib.request.Request(BOT_URL + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json",
                                          "User-Agent": "rm-shop-node-logs"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read() or b"{}")


class Tail:
    """Follows a file across logrotate: a new inode or a shorter file is read from its start.
    The first open starts at the end, so a restart does not resend old lines."""
    def __init__(self, path):
        self.path, self.fh, self.ino, self.rest = path, None, None, ""

    def lines(self):
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return []
        if self.fh is None or st.st_ino != self.ino or st.st_size < self.fh.tell():
            first = self.fh is None and self.ino is None
            if self.fh:
                self.fh.close()
            self.fh = open(self.path, "r", encoding="utf-8", errors="replace")
            self.ino = st.st_ino
            if first:
                self.fh.seek(0, os.SEEK_END)
            self.rest = ""
        data = self.rest + self.fh.read()
        *done, self.rest = data.split("\n")   # a line still being written waits for its end
        return done


def main():
    if not BOT_URL or not TOKEN:
        raise SystemExit("BOT_URL and NODE_LOGS_TOKEN are required")
    tails = {k: Tail(p) for k, p in FILES.items()}
    watched, owner, sent_at, buf = set(), {}, {}, []
    next_watch = next_flush = 0.0
    while True:
        now = time.time()
        if now >= next_watch:
            try:
                watched = set(call("GET", "/webhooks/node-logs/watch").get("emails") or [])
            except Exception as exc:
                print("watch list:", exc, flush=True)
            next_watch = now + WATCH_EVERY
            owner = {ip: v for ip, v in owner.items() if now - v[1] < IP_TTL}
            sent_at = {k: t for k, t in sent_at.items() if now - t < REPEAT}
        for src, tail in tails.items():
            for line in tail.lines():
                if src == "a":
                    m = ACCESS.search(line)
                    if not m:
                        continue
                    ip, dest, email = m.group(1), m.group(2) or "", m.group(3) or ""
                    if email not in watched:
                        continue
                    owner[ip] = (email, now)
                    key = (email, dest)
                    if "accepted" in line and now - sent_at.get(key, 0) < REPEAT:
                        continue
                    sent_at[key] = now
                    buf.append({"f": "a", "line": line})
                else:
                    m = ANY_IP.search(line)
                    if m and m.group(1) in owner:
                        buf.append({"f": "e", "line": line})
        if buf and (now >= next_flush or len(buf) >= BATCH):
            chunk = buf[:BATCH]
            try:
                call("POST", "/webhooks/node-logs", {"node": NODE, "lines": chunk})
                del buf[:len(chunk)]
            except Exception as exc:
                print("send:", exc, flush=True)
                del buf[:max(0, len(buf) - BACKLOG)]   # the bot is away: keep the newest lines only
            next_flush = now + FLUSH_EVERY
        time.sleep(0.5)


if __name__ == "__main__":
    main()
