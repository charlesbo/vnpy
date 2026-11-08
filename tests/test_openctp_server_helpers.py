import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from examples.client_server.run_openctp_server import build_ctp_setting, build_rpc_addresses, check_tts_libraries, parse_endpoint
from scripts.install_openctp_tts_api import install_libraries, locate_sdk_libraries, parse_ctp_version


class OpenCtpServerHelperTDD(unittest.TestCase):
    def test_given_a_tcp_front_when_parsed_then_hostname_and_port_are_returned(self) -> None:
        self.assertEqual(parse_endpoint("tcp://trading.openctp.cn:30001"), ("trading.openctp.cn", 30001))

    def test_given_an_unknown_front_protocol_when_parsed_then_it_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_endpoint("ipc:///tmp/openctp")

    def test_given_rpc_bind_addresses_when_built_then_wildcard_is_refused(self) -> None:
        self.assertEqual(build_rpc_addresses("127.0.0.1"), ("tcp://127.0.0.1:2014", "tcp://127.0.0.1:4102"))
        with self.assertRaisesRegex(ValueError, "Wildcard RPC binds"):
            build_rpc_addresses("0.0.0.0")

    def test_given_no_environment_credentials_when_building_gateway_settings_then_start_is_refused(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENCTP_USER_ID"):
                build_ctp_setting()

    def test_given_environment_credentials_when_building_gateway_settings_then_password_is_not_hardcoded(self) -> None:
        with patch.dict(os.environ, {"OPENCTP_USER_ID": "user-123", "OPENCTP_PASSWORD": "secret"}, clear=True):
            setting = build_ctp_setting()
        self.assertEqual(setting["用户名"], "user-123")
        self.assertEqual(setting["密码"], "secret")
        self.assertEqual(setting["经纪商代码"], "9999")
        self.assertEqual(setting["交易服务器"], "tcp://trading.openctp.cn:30001")

    def test_given_api_package_and_tts_labels_when_parsed_then_ctp_abi_version_is_normalized(self) -> None:
        self.assertEqual(parse_ctp_version("6.7.11.4"), "6.7.11")
        self.assertEqual(parse_ctp_version("TTS 6.7.11"), "6.7.11")

    def test_given_a_matching_tts_archive_when_installed_then_original_ctp_libraries_are_backed_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "tts_6.7.11.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name in ("thostmduserapi_se.so", "thosttraderapi_se.so"):
                    archive.writestr(f"tts_6.7.11/lin64/{name}", b"\x7fELF openctp-tts v6.7.11 replacement")

            api_dir = root / "api"
            api_dir.mkdir()
            for name in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
                (api_dir / name).write_bytes(b"original official library")

            sdk_version, libraries = locate_sdk_libraries(zipfile.ZipFile(archive_path))
            self.assertEqual(sdk_version, "6.7.11")
            self.assertEqual(len(libraries), 2)

            install_libraries(archive_path, api_dir, installed_version="6.7.11.4")

            for name in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
                self.assertIn(b"openctp-tts v6.7.11", (api_dir / name).read_bytes())
                self.assertEqual((api_dir / f"{name}.official.bak").read_bytes(), b"original official library")

    def test_given_a_different_tts_api_version_when_installing_then_original_libraries_remain_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "tts_6.7.10.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name in ("thostmduserapi_se.so", "thosttraderapi_se.so"):
                    archive.writestr(f"tts_6.7.10/lin64/{name}", b"\x7fELF openctp-tts v6.7.10 replacement")

            api_dir = root / "api"
            api_dir.mkdir()
            for name in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
                (api_dir / name).write_bytes(b"original official library")

            with self.assertRaisesRegex(RuntimeError, "does not match"):
                install_libraries(archive_path, api_dir, installed_version="6.7.11.4")

            for name in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
                self.assertEqual((api_dir / name).read_bytes(), b"original official library")
                self.assertFalse((api_dir / f"{name}.official.bak").exists())

    def test_given_matching_tts_libraries_when_checked_then_version_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            api_dir = Path(temp_dir)
            for name in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
                (api_dir / name).write_bytes(b"\x7fELF openctp-tts v6.7.11")
            check_tts_libraries(api_dir, "6.7.11.4")

    def test_given_official_ctp_libraries_when_checked_then_tts_requirement_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            api_dir = Path(temp_dir)
            for name in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
                (api_dir / name).write_bytes(b"official CTP library")
            with self.assertRaisesRegex(RuntimeError, "non-TTS"):
                check_tts_libraries(api_dir, "6.7.11.4")


if __name__ == "__main__":
    unittest.main()
