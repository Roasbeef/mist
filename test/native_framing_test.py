"""Raw TCP peers prove ambiguous framing closes before application admission."""

import glob
import http.client
from pathlib import Path
import select
import socket
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIBS = glob.glob(str(ROOT / "build/dev/erlang/*/ebin"))


class NativeFraming(unittest.TestCase):
    def test_duplicate_and_conflicting_framing_never_reaches_handler(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        child = subprocess.Popen(
            ["erl", "-noshell", "-pa", *LIBS, "-eval",
             f'application:ensure_all_started(mist), support@framing_fixture:start({port}).'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        try:
            for _ in range(3):
                self.assertTrue(select.select([child.stdout], [], [], 5)[0], "listener did not start")
                line = child.stdout.readline()
                if line == b"READY\n":
                    break
                self.assertTrue(line.startswith(b"Listening on "), line)
            else:
                self.fail("listener did not report readiness")
            cases = [
                "Content-Length: 10\r\nContent-Length: 11",
                "Content-Length: 10\r\ncOnTeNt-LeNgTh: 10",
                "Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked",
                "Transfer-Encoding: chunked\r\ntransfer-encoding: gzip",
                "Content-Length: 10\r\nTransfer-Encoding: chunked",
                "Transfer-Encoding: chunked\r\nContent-Length: 10",
            ]
            for framing in cases:
                with self.subTest(framing=framing):
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as peer:
                        peer.sendall(("POST / HTTP/1.1\r\nHost: localhost\r\n" + framing + "\r\n\r\n").encode())
                        try:
                            self.assertEqual(peer.recv(1), b"", "parser emitted an application response")
                        except ConnectionResetError:
                            pass
                    self.assertFalse(select.select([child.stdout], [], [], 0.05)[0],
                                     "ambiguous framing reached the application callback")
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                connection.request("POST", "/", b"")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b"")
                self.assertTrue(select.select([child.stdout], [], [], 2)[0])
                self.assertEqual(child.stdout.readline(), b"HANDLED\n")
            finally:
                connection.close()
            self.assertIsNone(child.poll(), "parser refusal stopped the listener")
        finally:
            child.terminate()
            child.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
