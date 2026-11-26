#!/usr/bin/env python3
"""dns_probe.py - Công cụ kiểm tra DNS Sinkhole bằng socket thuần (TV1, nhóm 16).

Chương trình tự dựng bản tin DNS theo RFC 1035, gửi qua UDP (hoặc TCP) tới một
máy chủ DNS (ví dụ Pi-hole), rồi tự phân tích bản tin trả lời để biết tên miền
được phân giải bình thường hay bị chặn (0.0.0.0 / NXDOMAIN).

Chỉ dùng thư viện chuẩn của Python (socket, struct, random, time, argparse).

Ví dụ:
  python3 tools/dns_probe.py --server 127.0.0.1 --port 5353 google.com doubleclick.net
  python3 tools/dns_probe.py --port 5353 --allowed google.com --blocked doubleclick.net
"""
import argparse
import random
import socket
import struct
import sys
import time

QTYPES = {"A": 1, "AAAA": 28}
TYPE_NAMES = {1: "A", 5: "CNAME", 28: "AAAA"}
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}


def build_query(domain, qtype="A", query_id=None):
    """Dựng bản tin truy vấn DNS: header 12 byte + phần câu hỏi."""
    if query_id is None:
        query_id = random.randint(0, 0xFFFF)
    flags = 0x0100  # RD = 1: yêu cầu máy chủ phân giải đệ quy
    header = struct.pack("!HHHHHH", query_id, flags, 1, 0, 0, 0)
    qname = b""
    for label in domain.strip(".").split("."):
        raw = label.encode("idna")
        if not 0 < len(raw) < 64:
            raise ValueError("nhãn tên miền không hợp lệ: %r" % label)
        qname += bytes([len(raw)]) + raw
    qname += b"\x00"
    question = qname + struct.pack("!HH", QTYPES[qtype], 1)  # QTYPE, QCLASS = IN
    return query_id, header + question


def read_name(msg, offset):
    """Đọc tên miền (có hỗ trợ con trỏ nén 0xC0) và trả về (tên, vị trí kế tiếp)."""
    labels, jumped, end, hops = [], False, offset, 0
    while True:
        if offset >= len(msg):
            raise ValueError("bản tin bị cắt cụt")
        length = msg[offset]
        if length & 0xC0 == 0xC0:  # con trỏ nén
            if offset + 1 >= len(msg):
                raise ValueError("con trỏ nén không hợp lệ")
            pointer = ((length & 0x3F) << 8) | msg[offset + 1]
            if not jumped:
                end = offset + 2
            offset, jumped = pointer, True
            hops += 1
            if hops > 20:
                raise ValueError("vòng lặp con trỏ nén")
            continue
        offset += 1
        if length == 0:
            break
        labels.append(msg[offset:offset + length].decode("ascii", "replace"))
        offset += length
    return ".".join(labels), (offset if not jumped else end)


def parse_response(msg, expect_id=None):
    """Phân tích bản tin trả lời. Trả về dict gồm id, rcode, truncated, answers."""
    if len(msg) < 12:
        raise ValueError("bản tin ngắn hơn header")
    rid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", msg[:12])
    if expect_id is not None and rid != expect_id:
        raise ValueError("sai ID bản tin (có thể là gói giả mạo)")
    if not flags & 0x8000:
        raise ValueError("đây không phải bản tin trả lời (QR = 0)")
    offset = 12
    for _ in range(qd):  # bỏ qua phần câu hỏi
        _, offset = read_name(msg, offset)
        offset += 4
    answers = []
    for _ in range(an):
        name, offset = read_name(msg, offset)
        rtype, rclass, ttl, rdlen = struct.unpack("!HHIH", msg[offset:offset + 10])
        offset += 10
        rdata = msg[offset:offset + rdlen]
        offset += rdlen
        if rtype == 1 and rdlen == 4:
            value = socket.inet_ntop(socket.AF_INET, rdata)
        elif rtype == 28 and rdlen == 16:
            value = socket.inet_ntop(socket.AF_INET6, rdata)
        elif rtype == 5:
            value, _ = read_name(msg, offset - rdlen)
        else:
            value = rdata.hex()
        answers.append({"name": name, "type": TYPE_NAMES.get(rtype, str(rtype)), "ttl": ttl, "value": value})
    return {"id": rid, "rcode": flags & 0x000F, "truncated": bool(flags & 0x0200), "answers": answers}


def send_udp(packet, server, port, timeout):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(packet, (server, port))
        data, _ = s.recvfrom(4096)
        return data


def send_tcp(packet, server, port, timeout):
    """DNS qua TCP: mỗi bản tin có thêm 2 byte độ dài ở đầu (RFC 1035, mục 4.2.2)."""
    with socket.create_connection((server, port), timeout=timeout) as s:
        s.sendall(struct.pack("!H", len(packet)) + packet)
        head = b""
        while len(head) < 2:
            chunk = s.recv(2 - len(head))
            if not chunk:
                raise ConnectionError("máy chủ đóng kết nối")
            head += chunk
        need = struct.unpack("!H", head)[0]
        data = b""
        while len(data) < need:
            chunk = s.recv(need - len(data))
            if not chunk:
                raise ConnectionError("máy chủ đóng kết nối")
            data += chunk
        return data


def classify(result, qtype="A"):
    """Phân loại kết quả: BLOCKED / OK / NODATA / ERROR."""
    if result["rcode"] == 3:
        return "BLOCKED", "NXDOMAIN"
    if result["rcode"] != 0:
        return "ERROR", RCODES.get(result["rcode"], str(result["rcode"]))
    addrs = [a["value"] for a in result["answers"] if a["type"] in ("A", "AAAA")]
    if not addrs:
        return "NODATA", "không có bản ghi địa chỉ"
    if all(a in ("0.0.0.0", "::") for a in addrs):
        return "BLOCKED", "sinkhole " + addrs[0]
    return "OK", ", ".join(addrs)


def probe(domain, server, port, qtype="A", timeout=3.0, use_tcp=False):
    """Gửi một truy vấn và trả về (nhãn, chi tiết, thời gian ms, giao thức)."""
    qid, packet = build_query(domain, qtype)
    started = time.perf_counter()
    proto = "TCP" if use_tcp else "UDP"
    data = (send_tcp if use_tcp else send_udp)(packet, server, port, timeout)
    result = parse_response(data, qid)
    if result["truncated"] and not use_tcp:  # bản tin UDP bị cắt: thử lại bằng TCP
        data = send_tcp(packet, server, port, timeout)
        result, proto = parse_response(data, qid), "TCP"
    elapsed = (time.perf_counter() - started) * 1000
    label, detail = classify(result, qtype)
    return label, detail, elapsed, proto


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kiểm tra DNS Sinkhole bằng socket thuần")
    ap.add_argument("domains", nargs="*", help="các tên miền cần kiểm tra")
    ap.add_argument("--server", default="127.0.0.1", help="địa chỉ máy chủ DNS (mặc định 127.0.0.1)")
    ap.add_argument("--port", type=int, default=5353, help="cổng DNS (mặc định 5353)")
    ap.add_argument("--type", choices=QTYPES, default="A", help="loại bản ghi (A hoặc AAAA)")
    ap.add_argument("--tcp", action="store_true", help="dùng TCP thay vì UDP")
    ap.add_argument("--timeout", type=float, default=3.0, help="thời gian chờ mỗi truy vấn (giây)")
    ap.add_argument("--blocked", nargs="*", default=[], help="tên miền PHẢI bị chặn")
    ap.add_argument("--allowed", nargs="*", default=[], help="tên miền PHẢI được phân giải")
    args = ap.parse_args(argv)

    checks = [(d, "BLOCKED") for d in args.blocked] + [(d, "OK") for d in args.allowed] + [(d, None) for d in args.domains]
    if not checks:
        ap.error("cần ít nhất một tên miền")
    print("Máy chủ DNS: %s:%d (%s, bản ghi %s)" % (args.server, args.port, "TCP" if args.tcp else "UDP", args.type))
    print("%-28s %-9s %-8s %-4s %s" % ("Tên miền", "Kết quả", "Thời gian", "Giao thức", "Chi tiết"))
    failed = 0
    for domain, want in checks:
        try:
            label, detail, ms, proto = probe(domain, args.server, args.port, args.type, args.timeout, args.tcp)
        except socket.timeout:
            label, detail, ms, proto = "ERROR", "hết thời gian chờ", 0.0, "-"
        except (OSError, ValueError) as exc:
            label, detail, ms, proto = "ERROR", str(exc), 0.0, "-"
        verdict = ""
        if want:
            ok = label == want
            verdict = "  [ĐẠT]" if ok else "  [SAI, mong đợi %s]" % want
            failed += 0 if ok else 1
        print("%-28s %-9s %6.1f ms %-9s %s%s" % (domain, label, ms, proto, detail, verdict))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
