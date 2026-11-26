"""Kiểm thử đơn vị cho dns_probe.py bằng một máy chủ DNS giả chạy trên socket UDP/TCP cục bộ."""
import socket
import struct
import threading
import unittest

import dns_probe as dp


def make_answer(query, ip=None, rcode=0, truncated=False):
    """Dựng bản tin trả lời giả từ bản tin truy vấn (dùng con trỏ nén 0xC00C)."""
    qid = struct.unpack("!H", query[:2])[0]
    question = query[12:]
    flags = 0x8180 | rcode | (0x0200 if truncated else 0)
    an = 1 if ip else 0
    msg = struct.pack("!HHHHHH", qid, flags, 1, an, 0, 0) + question
    if ip:
        msg += b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, 4) + socket.inet_aton(ip)
    return msg


class FakeDNS:
    """Máy chủ DNS giả: google.com -> IP thật, ads.example -> 0.0.0.0, none.example -> NXDOMAIN."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.bind(("127.0.0.1", self.port))
        self.tcp.listen(5)
        self.running = True
        threading.Thread(target=self.serve_udp, daemon=True).start()
        threading.Thread(target=self.serve_tcp, daemon=True).start()

    def reply(self, query, over_udp):
        name, _ = dp.read_name(query, 12)
        if name == "google.com":
            return make_answer(query, "142.250.1.1")
        if name == "ads.example":
            return make_answer(query, "0.0.0.0")
        if name == "big.example":
            return make_answer(query, None, truncated=True) if over_udp else make_answer(query, "10.0.0.9")
        return make_answer(query, None, rcode=3)

    def serve_udp(self):
        self.sock.settimeout(0.2)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(512)
            except socket.timeout:
                continue
            self.sock.sendto(self.reply(data, True), addr)

    def serve_tcp(self):
        self.tcp.settimeout(0.2)
        while self.running:
            try:
                conn, _ = self.tcp.accept()
            except socket.timeout:
                continue
            with conn:
                n = struct.unpack("!H", conn.recv(2))[0]
                q = conn.recv(n)
                r = self.reply(q, False)
                conn.sendall(struct.pack("!H", len(r)) + r)

    def close(self):
        self.running = False


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = FakeDNS()

    @classmethod
    def tearDownClass(cls):
        cls.srv.close()

    def run_probe(self, domain, **kw):
        return dp.probe(domain, "127.0.0.1", self.srv.port, timeout=2, **kw)

    def test_build_query_header_and_name(self):
        qid, pkt = dp.build_query("www.example.com", "A", query_id=0x1234)
        self.assertEqual(pkt[:2], b"\x12\x34")
        self.assertEqual(struct.unpack("!H", pkt[4:6])[0], 1)  # QDCOUNT = 1
        self.assertEqual(pkt[12:], b"\x03www\x07example\x03com\x00\x00\x01\x00\x01")

    def test_normal_domain_is_ok(self):
        label, detail, _, proto = self.run_probe("google.com")
        self.assertEqual((label, detail, proto), ("OK", "142.250.1.1", "UDP"))

    def test_sinkhole_address_is_blocked(self):
        label, detail, _, _ = self.run_probe("ads.example")
        self.assertEqual(label, "BLOCKED")
        self.assertIn("0.0.0.0", detail)

    def test_nxdomain_is_blocked(self):
        label, detail, _, _ = self.run_probe("none.example")
        self.assertEqual((label, detail), ("BLOCKED", "NXDOMAIN"))

    def test_truncated_udp_falls_back_to_tcp(self):
        label, detail, _, proto = self.run_probe("big.example")
        self.assertEqual((label, detail, proto), ("OK", "10.0.0.9", "TCP"))

    def test_wrong_id_is_rejected(self):
        _, pkt = dp.build_query("google.com", "A", query_id=1)
        reply = make_answer(pkt, "1.2.3.4")
        with self.assertRaises(ValueError):
            dp.parse_response(reply, expect_id=2)

    def test_cli_exit_code(self):
        port = str(self.srv.port)
        ok = dp.main(["--port", port, "--allowed", "google.com", "--blocked", "ads.example"])
        bad = dp.main(["--port", port, "--blocked", "google.com"])
        self.assertEqual((ok, bad), (0, 1))


if __name__ == "__main__":
    unittest.main()
