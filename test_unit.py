import winedid_tool

# 1. 扫描在线设备
online_devs = winedid_tool.EDIDManager.scan_online_devices(include_offline=False)
print(f"Online devices count: {len(online_devs)}")
for d in online_devs:
    print(f" -> {d['name']} ({d['pnp_id']}) Online={d['is_online']} Res={d['curr_res']}")

# 2. 构造双块 EDID
b0, b1 = winedid_tool.build_full_edid_blocks(3840, 2160, 60, "DUMMY-4K", include_cta=True)
assert len(b0) == 128 and sum(b0) % 256 == 0
assert len(b1) == 128 and sum(b1) % 256 == 0
print("Double-block EDID (Block 0 + CTA-861 Block 1) Checksums Valid!")
