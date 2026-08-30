import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from xmltv_gateway.guide import refresh

XMLTV = b'<?xml version="1.0"?><tv><channel id="1"/></tv>'
NEWER = b'<?xml version="1.0"?><tv><channel id="2"/></tv>'
NOT_XMLTV = b'{"error": "subscription required"}'
TRUNCATED = b"<tv><channel>"


class RefreshTest(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self._dir = TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.path = Path(self._dir.name) / "xmltv.xml"

    def test_writes_fetched_guide(self):
        refresh(self.path, lambda: XMLTV)

        self.assertEqual(self.path.read_bytes(), XMLTV)

    def test_keeps_previous_guide_when_provider_fails(self):
        self.path.write_bytes(XMLTV)

        def boom():
            raise RuntimeError("down")

        refresh(self.path, boom)

        self.assertEqual(self.path.read_bytes(), XMLTV)

    def test_rejects_response_that_is_not_xmltv(self):
        self.path.write_bytes(XMLTV)

        refresh(self.path, lambda: NOT_XMLTV)

        self.assertEqual(self.path.read_bytes(), XMLTV)

    def test_rejects_truncated_xml(self):
        self.path.write_bytes(XMLTV)

        refresh(self.path, lambda: TRUNCATED)

        self.assertEqual(self.path.read_bytes(), XMLTV)

    def test_leaves_no_temp_file_when_the_write_fails(self):
        target = Path(self._dir.name) / "guide-dir"
        target.mkdir()

        self.assertFalse(refresh(target, lambda: XMLTV))
        self.assertEqual(list(target.parent.glob(".*")), [])

    def test_replaces_previous_guide(self):
        self.path.write_bytes(XMLTV)

        refresh(self.path, lambda: NEWER)

        self.assertEqual(self.path.read_bytes(), NEWER)


if __name__ == "__main__":
    unittest.main()
