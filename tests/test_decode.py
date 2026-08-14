from mazu.decode import decode_identify_controller, decode_smart_log
from mazu.transport.mock.device import MockNvmeDevice


def test_identify_controller_roundtrip():
    dev = MockNvmeDevice(model="TEST MODEL", serial="SN123", firmware_rev="FW9")
    decoded = decode_identify_controller(dev.identify_controller())["identify"]
    assert decoded["model"] == "TEST MODEL"
    assert decoded["serial"] == "SN123"
    assert decoded["firmware_rev"] == "FW9"
    assert decoded["num_namespaces"] == 1


def test_smart_log_roundtrip():
    dev = MockNvmeDevice(composite_temp_k=300, media_errors=7, power_on_hours=99)
    smart = decode_smart_log(dev.smart_log())
    assert smart["temperature_celsius"] == 27
    assert smart["media_errors"] == 7
    assert smart["power_on_hours"] == 99
    assert smart["critical_warning"] == 0
