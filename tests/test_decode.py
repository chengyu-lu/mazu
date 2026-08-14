from mazu.decode import (
    decode_identify_controller,
    decode_inquiry,
    decode_read_capacity_16,
    decode_smart_log,
)
from mazu.executor.mock.device import MockNvmeDevice
from mazu.executor.mock.scsi_device import MockScsiDevice


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


def test_inquiry_roundtrip():
    dev = MockScsiDevice(vendor="ACME", product="TEST DISK", revision="9.9")
    inq = decode_inquiry(dev.inquiry())["inquiry"]
    assert inq["vendor"] == "ACME"
    assert inq["product"] == "TEST DISK"
    assert inq["revision"] == "9.9"
    assert inq["peripheral_device_type"] == 0
    assert inq["removable"] is False


def test_read_capacity_16_roundtrip():
    dev = MockScsiDevice(block_size=4096, total_blocks=1000)
    cap = decode_read_capacity_16(dev.read_capacity_16())["capacity"]
    assert cap["block_size"] == 4096
    assert cap["max_lba"] == 999
    assert cap["total_blocks"] == 1000
