# -*- coding: utf-8 -*-
"""
WinEDID Tool - Windows 显卡诱骗器与显示器 EDID 分辨率诱骗修改工具 v3.0
Author: Antigravity
Description:
  专为 Windows 显卡欺骗插头 (HDMI/DP Dummy Plug / 虚拟显示器 / 假负载) 及物理显示器开发。
  支持精准在线设备过滤、CTA-861 (HDMI 2.0 4K/高刷) 扩展块双块写入、PnP 设备热重启、
  一键驱动热重载与分辨率无缝切换。
"""

import os
import sys
import time
import subprocess
import ctypes
from ctypes import wintypes
import winreg
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# 开启高 DPI 识别，防止高分辨率屏幕下界面模糊
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def is_admin():
    """检查是否具有管理员权限"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin():
    """以管理员权限重新启动自身"""
    if not is_admin():
        script = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable if getattr(sys, 'frozen', False) else "python",
            f'"{script}" {params}'.strip(), None, 1
        )
        if ret > 32:
            sys.exit(0)
        else:
            return False
    return True


# ==========================================
# Windows API 结构体与函数
# ==========================================
user32 = ctypes.windll.user32

class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('DeviceName', wintypes.WCHAR * 32),
        ('DeviceString', wintypes.WCHAR * 128),
        ('StateFlags', wintypes.DWORD),
        ('DeviceID', wintypes.WCHAR * 128),
        ('DeviceKey', wintypes.WCHAR * 128),
    ]

class POINTL(ctypes.Structure):
    _fields_ = [
        ('x', wintypes.LONG),
        ('y', wintypes.LONG)
    ]

class DUMMYSTRUCTNAME2(ctypes.Structure):
    _fields_ = [
        ('dmPosition', POINTL),
        ('dmDisplayOrientation', wintypes.DWORD),
        ('dmDisplayFixedOutput', wintypes.DWORD),
    ]

class DUMMYUNIONNAME(ctypes.Union):
    _fields_ = [
        ('display', DUMMYSTRUCTNAME2),
        ('unused', wintypes.BYTE * 16),
    ]

class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ('dmDeviceName', wintypes.WCHAR * 32),
        ('dmSpecVersion', wintypes.WORD),
        ('dmDriverVersion', wintypes.WORD),
        ('dmSize', wintypes.WORD),
        ('dmDriverExtra', wintypes.WORD),
        ('dmFields', wintypes.DWORD),
        ('u1', DUMMYUNIONNAME),
        ('dmColor', wintypes.SHORT),
        ('dmDuplex', wintypes.SHORT),
        ('dmYResolution', wintypes.SHORT),
        ('dmTTOption', wintypes.SHORT),
        ('dmCollate', wintypes.SHORT),
        ('dmFormName', wintypes.WCHAR * 32),
        ('dmLogPixels', wintypes.WORD),
        ('dmBitsPerPel', wintypes.DWORD),
        ('dmPelsWidth', wintypes.DWORD),
        ('dmPelsHeight', wintypes.DWORD),
        ('dmDisplayFlags', wintypes.DWORD),
        ('dmDisplayFrequency', wintypes.DWORD),
        ('dmICMMethod', wintypes.DWORD),
        ('dmICMIntent', wintypes.DWORD),
        ('dmMediaType', wintypes.DWORD),
        ('dmDitherType', wintypes.DWORD),
        ('dmReserved1', wintypes.DWORD),
        ('dmReserved2', wintypes.DWORD),
        ('dmPanningWidth', wintypes.DWORD),
        ('dmPanningHeight', wintypes.DWORD),
    ]

    @property
    def dmPositionX(self):
        return self.u1.display.dmPosition.x

    @dmPositionX.setter
    def dmPositionX(self, val):
        self.u1.display.dmPosition.x = val

    @property
    def dmPositionY(self):
        return self.u1.display.dmPosition.y

    @dmPositionY.setter
    def dmPositionY(self, val):
        self.u1.display.dmPosition.y = val

DM_BITSPERPEL = 0x00040000
DM_PELSWIDTH = 0x00080000
DM_PELSHEIGHT = 0x00100000
DM_DISPLAYFREQUENCY = 0x00400000
CDS_UPDATEREGISTRY = 0x00000001
DISP_CHANGE_SUCCESSFUL = 0


# ==========================================
# EDID 标准构建算法 (VESA + CTA-861)
# ==========================================
def calculate_cvt_rb_timing(h_active, v_active, v_refresh):
    """
    根据 VESA CVT-RB (Reduced Blanking) 规范计算 18 字节详细时序描述符 (DTD)
    精确匹配像素时钟与正负极性，解除显卡限制。
    """
    h_blank = 160
    h_sync_offset = 48
    h_sync_width = 32
    v_blank = 33
    v_sync_offset = 3
    v_sync_width = 8
    
    h_total = h_active + h_blank
    v_total = v_active + v_blank
    
    pixel_clock_hz = h_total * v_total * v_refresh
    pixel_clock_10khz = round(pixel_clock_hz / 10000.0)
    
    dtd = bytearray(18)
    dtd[0] = pixel_clock_10khz & 0xFF
    dtd[1] = (pixel_clock_10khz >> 8) & 0xFF
    
    dtd[2] = h_active & 0xFF
    dtd[3] = h_blank & 0xFF
    dtd[4] = ((h_active >> 8) & 0x0F) << 4 | ((h_blank >> 8) & 0x0F)
    
    dtd[5] = v_active & 0xFF
    dtd[6] = v_blank & 0xFF
    dtd[7] = ((v_active >> 8) & 0x0F) << 4 | ((v_blank >> 8) & 0x0F)
    
    dtd[8] = h_sync_offset & 0xFF
    dtd[9] = h_sync_width & 0xFF
    
    v_so = v_sync_offset & 0x0F
    v_sw = v_sync_width & 0x0F
    dtd[10] = (v_so << 4) | v_sw
    
    h_so_hi = (h_sync_offset >> 8) & 0x03
    h_sw_hi = (h_sync_width >> 8) & 0x03
    v_so_hi = (v_sync_offset >> 4) & 0x03
    v_sw_hi = (v_sync_width >> 4) & 0x03
    dtd[11] = (h_so_hi << 6) | (h_sw_hi << 4) | (v_so_hi << 2) | v_sw_hi
    
    # 物理尺寸 (mm)
    dtd[12] = 600 & 0xFF
    dtd[13] = 340 & 0xFF
    dtd[14] = ((600 >> 8) & 0x0F) << 4 | ((340 >> 8) & 0x0F)
    
    dtd[15] = 0
    dtd[16] = 0
    # 标准 CVT-RB: 正极性 H-Sync, 负极性 V-Sync
    dtd[17] = 0x18 | 0x02
    
    return bytes(dtd), pixel_clock_hz / 1e6


def build_cta861_extension_block(width, height, refresh, dtd_list=None, base_raw_cta=None):
    """
    构造 128 字节 CTA-861 扩展块 (Block 1)
    包含 HDMI 2.0 600MHz 支持、视频数据块、音频配置以及将目标分辨率与原有保留分辨率注入 DTD 描述符区域。
    """
    cta = bytearray(128)
    cta[0] = 0x02  # CEA-861 Tag
    cta[1] = 0x03  # Revision 3

    # 数据块集合构建 (Data Block Collection)
    data_blocks = bytearray()

    # 1. 视频数据块 (Video Data Block, Tag 2):
    # 动态匹配标准 VIC。只有与目标分辨率精确匹配的标准 VIC 才能置 Native 标志 (0x80)！
    primary_vic = None
    aux_vics = []
    if width == 3840 and height == 2160:
        if refresh >= 100:
            primary_vic = 117
            aux_vics = [118, 97, 95]
        elif refresh >= 50:
            primary_vic = 97
            aux_vics = [96, 95]
        else:
            primary_vic = 95
            aux_vics = [93]
    elif width == 1920 and height == 1080:
        if refresh >= 120:
            primary_vic = 63
            aux_vics = [16, 31]
        else:
            primary_vic = 16
            aux_vics = [31]
    elif width == 1280 and height == 720:
        primary_vic = 4
        aux_vics = [19]
    elif width == 2560 and height == 1440:
        # 1440P 主要由 DTD 详细时序精确驱动；提供兼容 VIC 但绝不标记 Native，防止夺取目标分辨率首选项！
        primary_vic = None
        aux_vics = [16, 31, 4]
    else:
        # 特殊自定义分辨率：核心依赖注入的 DTD
        primary_vic = None
        aux_vics = [16]

    # 如果有原版的 CTA 块，且原版里有 VIC，提取并保留出厂原有分辨率
    if base_raw_cta and len(base_raw_cta) >= 128:
        try:
            d_start = base_raw_cta[2]
            p = 4
            while p < d_start and p < 127:
                tag = (base_raw_cta[p] >> 5) & 0x07
                length = base_raw_cta[p] & 0x1F
                if tag == 2: # Video Data Block
                    for k in range(p + 1, min(p + 1 + length, 127)):
                        orig_vic = base_raw_cta[k] & 0x7F
                        if orig_vic not in aux_vics and orig_vic != primary_vic and len(aux_vics) < 16:
                            aux_vics.append(orig_vic)
                p += 1 + length
        except Exception:
            pass

    # 写入 Video Data Block (Tag 2):
    # 核心设计：仅目标诱骗分辨率允许打上 0x80 (Native) 标志！
    # 所有从原显示器保留的分辨率和辅助分辨率一律清除 0x80 (作为非 Native 备用支持模式)，
    # 彻底解决“勾选保留原有分辨率后系统依然显示/跳回原分辨率”的 BUG！
    vic_bytes = []
    if primary_vic:
        vic_bytes.append(primary_vic | 0x80)
    for v in aux_vics:
        clean_v = v & 0x7F
        if clean_v not in [x & 0x7F for x in vic_bytes] and len(vic_bytes) < 16:
            vic_bytes.append(clean_v)

    if vic_bytes:
        data_blocks.append((2 << 5) | (len(vic_bytes) & 0x1F))
        data_blocks.extend(vic_bytes)

    # 2. 音频数据块 (Audio Data Block, Tag 1): LPCM 2声道 32/44.1/48kHz
    data_blocks.append((1 << 5) | 3)
    data_blocks.extend([0x09, 0x07, 0x07])

    # 3. 扬声器配置块 (Speaker Allocation, Tag 4): FL/FR
    data_blocks.append((4 << 5) | 3)
    data_blocks.extend([0x01, 0x00, 0x00])

    # 4. HDMI 1.4 VSDB (OUI 0x000C03)
    data_blocks.append((3 << 5) | 5)
    data_blocks.extend([0x03, 0x0C, 0x00, 0x10, 0x00])

    # 5. HDMI 2.0 HF-VSDB (OUI 0xC45ED8, 600MHz TMDS 速率，支持 4K 60Hz 4:4:4 及高刷)
    data_blocks.append((3 << 5) | 5)
    data_blocks.extend([0xD8, 0x5E, 0xC4, 0x01, 0x01])

    # 写入 Data Blocks
    idx = 4
    cta[idx:idx + len(data_blocks)] = data_blocks
    idx += len(data_blocks)

    # 详细描述符起始偏移
    cta[2] = idx

    # 将 DTD 写入 CTA-861 扩展块的 DTD 区域（解决自定分辨率未生成的核心！）
    if dtd_list:
        cur_offset = idx
        for dtd in dtd_list:
            if cur_offset + 18 <= 126: # 最多放进入直到 126 字节前
                cta[cur_offset:cur_offset + 18] = dtd
                cur_offset += 18
            else:
                break

    # 字节 3: Underscan, Basic Audio, YCbCr, 以及 low nibble 明确指定仅 1 个 Native DTD (首选诱骗分辨率)
    cta[3] = 0x70 | (1 if dtd_list else 0)

    # 校验和
    s = sum(cta[:127]) % 256
    cta[127] = (256 - s) % 256
    return bytes(cta)


def build_full_edid_blocks(width, height, refresh, monitor_name="DUMMY-4K", base_raw_edid=None, include_cta=True, preserve_native_res=True):
    """
    构造完整的 EDID 块：
    完美解决“自定分辨率没有生成”与“保留原有分辨率”。
    返回 (block0_128b, block1_128b_or_none)
    """
    target_dtd, pclk_mhz = calculate_cvt_rb_timing(width, height, refresh)

    native_dtds = []
    orig_name = monitor_name
    orig_range = None
    has_base = bool(base_raw_edid and len(base_raw_edid) >= 128)

    if has_base:
        b0 = bytearray(base_raw_edid[:128])
        # 提取原有的出厂原生 DTD 和描述符
        for off in [54, 72, 90, 108]:
            blk = bytes(b0[off:off+18])
            if blk[0] != 0 or blk[1] != 0:
                # 真实时序 DTD
                if blk != target_dtd:
                    native_dtds.append(blk)
            else:
                tag = blk[3]
                if tag == 0xFC: # 显示器名称
                    n = blk[5:18].decode('latin1', errors='ignore').strip()
                    if n:
                        orig_name = n
                elif tag == 0xFD: # Range limits
                    orig_range = blk

        # 如果有原版 Block 1 (CTA-861)，也提取其中的原生 DTD
        if len(base_raw_edid) >= 256 and base_raw_edid[128] == 0x02:
            try:
                cta_start = base_raw_edid[128 + 2]
                c_pos = 128 + cta_start
                while c_pos + 18 <= 254:
                    c_dtd = bytes(base_raw_edid[c_pos:c_pos+18])
                    if (c_dtd[0] != 0 or c_dtd[1] != 0) and c_dtd != target_dtd:
                        if c_dtd not in native_dtds:
                            native_dtds.append(c_dtd)
                    c_pos += 18
            except Exception:
                pass

        # 确保 Feature Support 字节 (byte 24) 的 Bit 1 (Preferred Timing Mode) 开启，声明 Slot 1 为 Preferred
        b0[24] = b0[24] | 0x02
    else:
        # 全新生成的戴尔真实物理品牌显示器基础块 (标准 EDID 1.4)
        b0 = bytearray(128)
        b0[0:8] = b'\x00\xFF\xFF\xFF\xFF\xFF\xFF\x00'
        # 厂商标识 'D','E','L' (Dell Inc. 官方代码: 0x10AC)
        b0[8] = 0x10
        b0[9] = 0xAC
        # 产品代码 0x2720 (对应 U2720Q 4K 专业屏)
        b0[10] = 0x20
        b0[11] = 0x27
        # 序列号
        b0[12:16] = b'\x44\x45\x4C\x01'
        b0[16] = 15      # 制造周
        b0[17] = 34      # 制造年: 1990 + 34 = 2024年
        b0[18] = 1       # EDID 版本 1
        b0[19] = 4       # EDID 修订号 4
        b0[20] = 0xA5    # 数字输入 (DisplayPort/HDMI, 8-bit, RGB/YCbCr)
        b0[21] = 60      # 屏幕宽度 60cm (27英寸)
        b0[22] = 34      # 屏幕高度 34cm
        b0[23] = 0x78    # Gamma 2.2
        b0[24] = 0x0E    # 特性支持: sRGB、首选定时模式
        b0[25:35] = bytes([0xEE, 0x91, 0xA3, 0x54, 0x4C, 0x99, 0x26, 0x0F, 0x50, 0x54])
        b0[35] = 0x21
        b0[36] = 0x08
        b0[37] = 0x00

    # 注入 Standard Timings (bytes 38-53)
    std_w_code = round(width / 8.0) - 31
    if 0 <= std_w_code <= 255:
        ratio_bits = 0b01
        if abs(width / max(1, height) - 16/9) < 0.05:
            ratio_bits = 0b11
        elif abs(width / max(1, height) - 16/10) < 0.05:
            ratio_bits = 0b00
        elif abs(width / max(1, height) - 5/4) < 0.05:
            ratio_bits = 0b10
        std_freq_code = max(0, min(63, refresh - 60))
        std_byte2 = (ratio_bits << 6) | (std_freq_code & 0x3F)

        # 寻找未使用的空槽位 (0x01, 0x01)
        for st_idx in range(38, 54, 2):
            if b0[st_idx:st_idx+2] == b'\x01\x01' or not preserve_native_res:
                b0[st_idx] = std_w_code
                b0[st_idx+1] = std_byte2
                break

    # 编排 Block 0 的 4 个 DTD 描述符槽位:
    # 槽位 1 (54-71): 新目标自定义分辨率 DTD (作为首选诱骗模式)
    b0[54:72] = target_dtd

    # 槽位 2 (72-89):
    # 若选择保留原有分辨率且存在原生 DTD，保留第 1 个原生出厂 DTD
    dtds_for_cta = [target_dtd]
    if preserve_native_res and native_dtds:
        b0[72:90] = native_dtds[0]
        # 剩余的原生 DTD 排队全部放入 CTA-861 扩展块
        dtds_for_cta.extend(native_dtds[1:])
    else:
        sec_w, sec_h = (1920, 1080) if (width != 1920 or height != 1080) else (2560, 1440)
        sec_dtd, _ = calculate_cvt_rb_timing(sec_w, sec_h, 60)
        b0[72:90] = sec_dtd

    # 槽位 3 (90-107): 显示器真实品牌名称 (若为默认/虚拟/非PnP则智能升级为真实物理显示器型号)
    raw_name = (orig_name or monitor_name).strip()
    is_generic = any(x in raw_name.lower() for x in ["default", "non-pnp", "virtual", "诱骗", "未知"])
    if is_generic or not raw_name:
        if width >= 3840 and height >= 2160:
            clean_name = "DELL U2720Q"
        elif width >= 3440:
            clean_name = "DELL U3419W"
        elif width >= 2560:
            clean_name = "DELL S2721D"
        else:
            clean_name = "DELL P2419H"
    else:
        clean_name = raw_name

    clean_name = clean_name[:13].ljust(13, ' ')
    b0[90:108] = b'\x00\x00\x00\xFC\x00' + clean_name.encode('ascii', errors='replace')

    # 槽位 4 (108-125): 增强的 Range Limits (0xFD)
    # 动态调高刷新率上限和像素时钟上限，保证显卡驱动不会因超出范围而拦截！
    orig_max_v = orig_range[6] if orig_range else 60
    max_v = max(orig_max_v, refresh, 144)
    max_pclk_10mhz = max(120, round(pclk_mhz / 10.0) + 15)
    max_pclk_10mhz = min(255, max_pclk_10mhz)

    b0[108:126] = bytes([
        0x00, 0x00, 0x00, 0xFD, 0x00,
        24,                   # 最小垂直刷新率 24Hz
        max(240, max_v),      # 最大垂直刷新率 240Hz+
        15,                   # 最小水平频率 15 kHz
        250,                  # 最大水平频率 250 kHz
        max_pclk_10mhz,       # 最大像素时钟 (10MHz 为单位)
        0x01,
        0x0A, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20
    ])

    # Block 1 (CTA-861)
    if include_cta:
        b0[126] = 1
        base_cta = base_raw_edid[128:256] if (has_base and len(base_raw_edid) >= 256) else None
        b1 = build_cta861_extension_block(
            width, height, refresh,
            dtd_list=dtds_for_cta,
            base_raw_cta=base_cta
        )
    else:
        b0[126] = 0
        b1 = None

    # 计算 Block 0 校验和
    s = sum(b0[:127]) % 256
    b0[127] = (256 - s) % 256

    return bytes(b0), b1


# ==========================================
# 虚拟显示器与虚拟屏幕管理核心
# ==========================================
class VirtualDisplayManager:
    """
    Windows 虚拟显示器与虚拟屏幕管理：
    支持一键快速激活/挂载系统未连接的虚拟显示接口，或在桌面安全断开虚拟屏幕。
    """
    @classmethod
    def get_all_adapters(cls):
        adapters = []
        ad_idx = 0
        while True:
            dev_adapter = DISPLAY_DEVICEW()
            dev_adapter.cb = ctypes.sizeof(dev_adapter)
            if not user32.EnumDisplayDevicesW(None, ad_idx, ctypes.byref(dev_adapter), 0):
                break
            ad_idx += 1
            is_attached = bool(dev_adapter.StateFlags & 0x00000001)

            # 检测该端口当前是否已就绪有效显示模式 (即是否有连接监视器)
            test_dm = DEVMODEW()
            test_dm.dmSize = ctypes.sizeof(test_dm)
            has_modes = bool(user32.EnumDisplaySettingsW(dev_adapter.DeviceName, 0, ctypes.byref(test_dm)))

            adapters.append({
                "name": dev_adapter.DeviceName,
                "desc": dev_adapter.DeviceString,
                "id": dev_adapter.DeviceID,
                "is_attached": is_attached,
                "has_modes": has_modes,
                "is_virtual": any(x in dev_adapter.DeviceString.lower() or x in dev_adapter.DeviceID.lower() for x in ["virtual", "idd", "meta", "oray", "spacedesk", "dummy"])
            })
        return adapters

    @classmethod
    def add_virtual_display(cls, preferred_w=1920, preferred_h=1080, refresh=60):
        """
        一键添加/挂载虚拟显示器到当前桌面：
        自动校验端口连接状态，杜绝向未就绪端口调用 API 导致 ChangeDisplaySettings 返回 -2 (BAD_MODE) 错误。
        """
        adapters = cls.get_all_adapters()

        # 1. 优先寻找尚未附加且已经具备模式就绪的端口 (如已插诱骗头或已启动虚拟屏服务的端口)
        ready_target = None
        for a in adapters:
            if not a["is_attached"] and a["has_modes"]:
                ready_target = a
                break

        # 2. 如果暂未发现已就绪端口，尝试通过 Windows 扩展机制强制唤醒
        if not ready_target:
            try:
                subprocess.run("displayswitch.exe /extend", shell=True, timeout=2)
                time.sleep(1)
                adapters = cls.get_all_adapters()
                for a in adapters:
                    if not a["is_attached"] and a["has_modes"]:
                        ready_target = a
                        break
            except Exception:
                pass

        # 3. 若检测到具备有效模式的端口，执行安全挂载
        if ready_target:
            adapter_name = ready_target["name"]

            # 计算主屏幕及所有活动屏幕的最大 X 坐标，放置在右侧
            max_x = 0
            for i in range(16):
                d = DISPLAY_DEVICEW()
                d.cb = ctypes.sizeof(d)
                if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(d), 0):
                    break
                if d.StateFlags & 1:
                    dm = DEVMODEW()
                    dm.dmSize = ctypes.sizeof(dm)
                    if user32.EnumDisplaySettingsW(d.DeviceName, -1, ctypes.byref(dm)):
                        max_x = max(max_x, dm.dmPositionX + dm.dmPelsWidth)

            if max_x == 0:
                max_x = 1920

            # 遍历该适配器自身支持的模式，找到最佳匹配
            best_mode = None
            m_idx = 0
            check_dm = DEVMODEW()
            check_dm.dmSize = ctypes.sizeof(check_dm)
            while user32.EnumDisplaySettingsW(adapter_name, m_idx, ctypes.byref(check_dm)):
                if check_dm.dmPelsWidth == preferred_w and check_dm.dmPelsHeight == preferred_h:
                    best_mode = (check_dm.dmPelsWidth, check_dm.dmPelsHeight, check_dm.dmDisplayFrequency)
                    break
                if best_mode is None:
                    best_mode = (check_dm.dmPelsWidth, check_dm.dmPelsHeight, check_dm.dmDisplayFrequency)
                m_idx += 1

            target_w, target_h, target_hz = best_mode if best_mode else (preferred_w, preferred_h, refresh)

            # 配置并挂载到桌面
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(dm)
            dm.dmPelsWidth = target_w
            dm.dmPelsHeight = target_h
            dm.dmDisplayFrequency = target_hz
            dm.dmBitsPerPel = 32
            dm.dmPositionX = max_x
            dm.dmPositionY = 0
            dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL | DM_DISPLAYFREQUENCY | 0x00000020

            ret = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(dm), None, CDS_UPDATEREGISTRY, None)
            if ret == DISP_CHANGE_SUCCESSFUL:
                user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                return True, f"成功将虚拟显示器 [{ready_target['desc']}] ({adapter_name}) 挂载到桌面！"
            else:
                dm.dmDisplayFrequency = 0
                dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL | 0x00000020
                ret2 = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(dm), None, CDS_UPDATEREGISTRY, None)
                if ret2 == DISP_CHANGE_SUCCESSFUL:
                    user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                    return True, f"成功将虚拟显示器 [{ready_target['desc']}] ({adapter_name}) 挂载到桌面！"

        # 4. 如果没有找到已就绪模式的端口，向用户提供极其详尽的原因分析与解决方案
        idle_virtual = [a for a in adapters if not a["is_attached"] and a["is_virtual"]]
        idle_physical = [a for a in adapters if not a["is_attached"] and not a["is_virtual"]]

        detail_lines = []
        if idle_virtual:
            v_names = " / ".join(set(a["desc"] for a in idle_virtual))
            detail_lines.append(f"- 发现系统已安装虚拟驱动端口 ({v_names})，但其驱动服务当前未插入活动监视器实例 (模式数=0)。")
        if idle_physical:
            detail_lines.append("- 发现物理显卡存在空闲显示端口，但未插入物理显示器或硬件诱骗插头 (模式数=0)。")
        if not idle_virtual and not idle_physical:
            detail_lines.append("- 系统中所有检测到的显示端口均已在桌面使用中。")

        diagnostic_info = "\n".join(detail_lines)
        fail_msg = (
            f"未找到可立即挂载的就绪显示端口。\n\n"
            f"【端口状态诊断】：\n{diagnostic_info}\n\n"
            "🔍 【为什么 Windows 会报代码 -2 (DISP_CHANGE_BADMODE)？】\n"
            "Windows 图形驱动层规定：端口必须在底层检测到有效监视器接入 (握手信号/EDID已建立) 才能挂载到桌面。\n"
            "直接对未插线或未激活的虚拟/物理端口调用挂载，系统必然拦截并返回代码 -2。\n\n"
            "💡 【推荐三种解决方案】：\n"
            "1. 硬件方式（极力推荐、零故障）：\n"
            "   在电脑空闲的 HDMI/DP 接口上插入一个【HDMI/DP 硬件诱骗插头】（仅需十几元，免驱动，即插即用）。插上后显卡立即识别为真实显示器，即可用本工具任意诱骗 4K/2K/144Hz！\n\n"
            "2. 软件方式（启动虚拟屏驱动）：\n"
            "   若已安装向日葵，可在其设置中开启【虚拟显示屏】；或使用 Parsec / IddSampleDriver / USBMMIDD 虚拟屏幕驱动工具启动一个虚拟屏，本工具即可对其注入 EDID。\n\n"
            "3. 系统快捷键扩展：\n"
            "   按键盘【Win + P】选择【扩展】，或按【Win + K】使用无线显示器功能。"
        )
        return False, fail_msg

    @classmethod
    def remove_virtual_display(cls, adapter_name):
        """
        从桌面断开指定的虚拟显示器
        """
        if not adapter_name:
            return False, "未指定要断开的显示器端口！"
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(dm)
        dm.dmPelsWidth = 0
        dm.dmPelsHeight = 0
        dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT
        ret = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(dm), None, CDS_UPDATEREGISTRY, None)
        if ret == DISP_CHANGE_SUCCESSFUL:
            user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
            return True, f"已成功将端口 {adapter_name} 从桌面安全断开！"
        else:
            return False, f"断开返回代码: {ret}"



# ==========================================
# 硬件与注册表管理核心
# ==========================================
class EDIDManager:
    REG_DISPLAY_ROOT = r"SYSTEM\CurrentControlSet\Enum\DISPLAY"
    REG_CLASS_ROOT = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e96e-e325-11ce-bfc1-08002be10318}"

    @classmethod
    def scan_online_devices(cls, include_offline=False):
        """
        扫描系统显示设备。默认【只返回在线/连接中】的设备！
        通过严格关联 Windows 活动显示端口与注册表 Driver Key。
        """
        active_adapters = {}
        # 1. 遍历活动显示适配器
        ad_idx = 0
        while True:
            dev_adapter = DISPLAY_DEVICEW()
            dev_adapter.cb = ctypes.sizeof(dev_adapter)
            if not user32.EnumDisplayDevicesW(None, ad_idx, ctypes.byref(dev_adapter), 0):
                break
            ad_idx += 1

            is_attached = bool(dev_adapter.StateFlags & 0x00000001) # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP

            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(dm)
            curr_res = "未激活"
            if is_attached and user32.EnumDisplaySettingsW(dev_adapter.DeviceName, -1, ctypes.byref(dm)):
                curr_res = f"{dm.dmPelsWidth} × {dm.dmPelsHeight} @ {dm.dmDisplayFrequency}Hz"

            m_idx = 0
            while True:
                dev_mon = DISPLAY_DEVICEW()
                dev_mon.cb = ctypes.sizeof(dev_mon)
                if not user32.EnumDisplayDevicesW(dev_adapter.DeviceName, m_idx, ctypes.byref(dev_mon), 0):
                    break
                m_idx += 1

                dkey = dev_mon.DeviceKey
                if "Class\\" in dkey:
                    class_suffix = dkey.split("Class\\")[-1].lower()
                    active_adapters[class_suffix] = {
                        "adapter_name": dev_adapter.DeviceName,
                        "adapter_desc": dev_adapter.DeviceString,
                        "monitor_name": dev_mon.DeviceString,
                        "curr_res": curr_res,
                        "is_attached": is_attached
                    }

        # 2. 扫描注册表中的设备
        devices = []
        try:
            hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.REG_DISPLAY_ROOT)
        except Exception:
            return devices

        i = 0
        while True:
            try:
                mon_id = winreg.EnumKey(hkey, i)
                i += 1
                mon_k = winreg.OpenKey(hkey, mon_id)
                j = 0
                while True:
                    try:
                        inst_id = winreg.EnumKey(mon_k, j)
                        j += 1
                        inst_path = f"{cls.REG_DISPLAY_ROOT}\\{mon_id}\\{inst_id}"
                        try:
                            inst_k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, inst_path)
                        except OSError:
                            continue

                        driver_val = ""
                        try:
                            driver_val, _ = winreg.QueryValueEx(inst_k, "Driver")
                        except FileNotFoundError:
                            pass

                        device_desc = ""
                        try:
                            device_desc, _ = winreg.QueryValueEx(inst_k, "DeviceDesc")
                            if ";" in device_desc:
                                device_desc = device_desc.split(";")[-1]
                        except FileNotFoundError:
                            pass

                        # 判断是否在线
                        is_online = False
                        adapter_info = {}
                        driver_suffix = ""
                        if driver_val:
                            # 提取 Driver Suffix，例如 {4d36e96e-e325-11ce-bfc1-08002be10318}\0004
                            driver_suffix = driver_val.lower().replace(r"\registry\machine\system\currentcontrolset\control\class\\", "")
                            for k, v in active_adapters.items():
                                if k in driver_suffix or driver_suffix in k:
                                    if v["is_attached"]:
                                        is_online = True
                                        adapter_info = v
                                        break

                        # 若不显示离线，且当前设备不在线，则跳过
                        if not include_offline and not is_online:
                            continue

                        param_path = f"{inst_path}\\Device Parameters"
                        has_override = False
                        edid_name = ""
                        raw_edid = b""

                        try:
                            param_k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, param_path)
                            try:
                                edid_data, _ = winreg.QueryValueEx(param_k, "EDID")
                                raw_edid = bytes(edid_data)
                                for off in [54, 72, 90, 108]:
                                    if len(raw_edid) >= off + 18:
                                        blk = raw_edid[off:off+18]
                                        if blk[:4] == b'\x00\x00\x00\xFC':
                                            edid_name = blk[5:18].decode('latin1', errors='ignore').strip()
                            except FileNotFoundError:
                                pass

                            try:
                                ov_k = winreg.OpenKey(param_k, "EDID_OVERRIDE")
                                try:
                                    winreg.QueryValueEx(ov_k, "0")
                                    has_override = True
                                except FileNotFoundError:
                                    pass
                            except FileNotFoundError:
                                pass
                        except FileNotFoundError:
                            pass

                        disp_title = edid_name or device_desc or mon_id
                        pnp_instance_id = f"DISPLAY\\{mon_id}\\{inst_id}"
                        is_virtual = any(x in adapter_info.get("adapter_desc", "").lower() or x in disp_title.lower() or x in mon_id.lower() for x in ["virtual", "idd", "meta", "oray", "spacedesk", "dummy", "default_monitor", "non-pnp", "诱骗", "虚拟"])

                        native_pref = cls.parse_edid_preferred_mode(raw_edid)
                        native_res_str = f"{native_pref[0]} × {native_pref[1]} @ {native_pref[2]}Hz (原生分辨率)" if native_pref else "未知 (原生分辨率)"

                        curr_res_val = adapter_info.get("curr_res", "未连接/离线")
                        if native_pref and curr_res_val not in ["未连接/离线", "未激活"]:
                            if f"{native_pref[0]} × {native_pref[1]}" in curr_res_val and "(原生分辨率)" not in curr_res_val:
                                curr_res_val = f"{curr_res_val} (原生分辨率)"

                        devices.append({
                            "mon_id": mon_id,
                            "inst_id": inst_id,
                            "pnp_id": pnp_instance_id,
                            "name": disp_title,
                            "is_online": is_online,
                            "is_virtual": is_virtual,
                            "has_override": has_override,
                            "curr_res": curr_res_val,
                            "native_res": native_pref,
                            "native_res_str": native_res_str,
                            "adapter_name": adapter_info.get("adapter_name", ""),
                            "adapter_desc": adapter_info.get("adapter_desc", ""),
                            "inst_path": inst_path,
                            "driver_suffix": driver_suffix,
                            "raw_edid": raw_edid
                        })
                    except OSError:
                        break
            except OSError:
                break

        return devices

    @classmethod
    def apply_edid_override_dual(cls, dev_info, block0, block1=None):
        """
        双重路径写入 EDID_OVERRIDE：
        1. 写入 Enum\DISPLAY\...\Device Parameters\EDID_OVERRIDE
        2. 写入 Control\Class\{GUID}\<xxxx>\Device Parameters\EDID_OVERRIDE
        写入值 '0' 为 Block 0，写入值 '1' 为 Block 1 (CTA-861)。
        """
        errors = []
        paths_written = 0

        # 路径 1: Enum DISPLAY
        p1 = f"{dev_info['inst_path']}\\Device Parameters"
        try:
            param_k = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, p1)
            ov_k = winreg.CreateKey(param_k, "EDID_OVERRIDE")
            winreg.SetValueEx(ov_k, "0", 0, winreg.REG_BINARY, block0)
            if block1:
                winreg.SetValueEx(ov_k, "1", 0, winreg.REG_BINARY, block1)
            winreg.CloseKey(ov_k)
            winreg.CloseKey(param_k)
            paths_written += 1
        except Exception as e:
            errors.append(f"硬件路径写入失败: {e}")

        # 路径 2: Class Key (若有)
        drv_suffix = dev_info.get("driver_suffix", "")
        if drv_suffix and "\\" in drv_suffix:
            sub_num = drv_suffix.split("\\")[-1]
            p2 = f"{cls.REG_CLASS_ROOT}\\{sub_num}\\Device Parameters"
            try:
                param_k2 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, p2)
                ov_k2 = winreg.CreateKey(param_k2, "EDID_OVERRIDE")
                winreg.SetValueEx(ov_k2, "0", 0, winreg.REG_BINARY, block0)
                if block1:
                    winreg.SetValueEx(ov_k2, "1", 0, winreg.REG_BINARY, block1)
                winreg.CloseKey(ov_k2)
                winreg.CloseKey(param_k2)
                paths_written += 1
            except Exception:
                pass

        if paths_written > 0:
            return True, f"EDID 覆写数据已成功注入注册表 (写入 {paths_written} 处核心节点，含 CTA-861 扩展)！"
        else:
            return False, "; ".join(errors) if errors else "写入注册表失败，请确保使用管理员权限！"

    @classmethod
    def remove_edid_override_dual(cls, dev_info):
        """清除双重路径下的 EDID_OVERRIDE"""
        success_count = 0
        # 路径 1
        try:
            p1 = f"{dev_info['inst_path']}\\Device Parameters"
            param_k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, p1, 0, winreg.KEY_ALL_ACCESS)
            try:
                ov_k = winreg.OpenKey(param_k, "EDID_OVERRIDE", 0, winreg.KEY_SET_VALUE)
                for val_name in ["0", "1", "2"]:
                    try:
                        winreg.DeleteValue(ov_k, val_name)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(ov_k)
            except FileNotFoundError:
                pass
            winreg.DeleteKey(param_k, "EDID_OVERRIDE")
            winreg.CloseKey(param_k)
            success_count += 1
        except Exception:
            pass

        # 路径 2
        drv_suffix = dev_info.get("driver_suffix", "")
        if drv_suffix and "\\" in drv_suffix:
            sub_num = drv_suffix.split("\\")[-1]
            try:
                p2 = f"{cls.REG_CLASS_ROOT}\\{sub_num}\\Device Parameters"
                param_k2 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, p2, 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteKey(param_k2, "EDID_OVERRIDE")
                winreg.CloseKey(param_k2)
                success_count += 1
            except Exception:
                pass

        return True, "已成功清除 EDID 覆写，恢复硬件出厂原生配置！"

    @classmethod
    def restart_device_pnp(cls, pnp_id):
        """
        使用 Windows 原生 PnP 工具精准热重启该显示器节点，
        强制显卡驱动立即重新从注册表加载 EDID！
        """
        try:
            cmd = f'pnputil /restart-device "{pnp_id}"'
            proc = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
            if proc.returncode == 0 or "已成功重启" in proc.stdout or "restarted" in proc.stdout.lower():
                return True, "PnP 设备节点热重载成功！显卡驱动已重新读取 EDID。"
            else:
                return False, f"pnputil 返回: {proc.stdout.strip()}"
        except Exception as e:
            return False, f"PnP 设备重启异常: {e}"

    @classmethod
    def restart_graphics_driver_full(cls, pnp_id=""):
        """
        三级显卡驱动全面热重载：
        1. 精准重启显示器 PnP 节点；
        2. 发送 Win + Ctrl + Shift + B 广播；
        3. 刷新 Windows 显卡显示状态。
        """
        results = []
        if pnp_id:
            ok, msg = cls.restart_device_pnp(pnp_id)
            results.append(msg)

        # 模拟 Win + Ctrl + Shift + B
        VK_LWIN = 0x5B
        VK_CONTROL = 0x11
        VK_SHIFT = 0x10
        VK_B = 0x42
        KEYEVENTF_KEYUP = 0x0002

        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_SHIFT, 0, 0, 0)
        user32.keybd_event(VK_B, 0, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(VK_B, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

        results.append("显卡热重置信号广播成功。")
        return True, " | ".join(results)

    @classmethod
    def parse_edid_preferred_mode(cls, raw_edid):
        """
        从硬件物理原始 EDID 的 Slot 1 (字节 54-71) 中精准解析出厂原生最佳分辨率与刷新率
        返回 (width, height, refresh) 或 None
        """
        if not raw_edid or len(raw_edid) < 72:
            return None
        b = raw_edid[54:72]
        pclk = (b[0] | (b[1] << 8)) * 10 # kHz
        if pclk == 0:
            return None
        h_act = b[2] | ((b[4] & 0xF0) << 4)
        h_blk = b[3] | ((b[4] & 0x0F) << 8)
        v_act = b[5] | ((b[7] & 0xF0) << 4)
        v_blk = b[6] | ((b[7] & 0x0F) << 8)
        h_total = h_act + h_blk
        v_total = v_act + v_blk
        if h_total == 0 or v_total == 0:
            return None
        fps = round(pclk * 1000.0 / (h_total * v_total))
        return h_act, v_act, fps

    @classmethod
    def smart_switch_resolution(cls, adapter_name, width, height, refresh, max_retries=1, retry_delay=0.5):
        """
        多重策略智能切换目标分辨率：
        1. 尝试以指定宽高 + 32位色深 + 指定刷新率切换 (CDS_UPDATEREGISTRY)；
        2. 尝试枚举现有模式严格/近似匹配并应用；
        3. 并在切换成功后调用 ChangeDisplaySettingsExW(None, ...) 立即全局提交应用到桌面。
        支持智能重试等待显卡驱动枚举就绪。
        """
        if not adapter_name:
            return False, "所选设备当前未连接到活动桌面，无法直接切换！"

        ret = -1
        ret2 = -1
        for attempt in range(max_retries):
            # 获取当前模式以保留桌面相对坐标
            curr_dm = DEVMODEW()
            curr_dm.dmSize = ctypes.sizeof(curr_dm)
            has_curr = bool(user32.EnumDisplaySettingsW(adapter_name, -1, ctypes.byref(curr_dm)))
            pos_x = curr_dm.dmPositionX if has_curr else 0
            pos_y = curr_dm.dmPositionY if has_curr else 0

            # 策略 1: 枚举驱动已就绪的最佳模式匹配
            mode_idx = 0
            test_dm = DEVMODEW()
            test_dm.dmSize = ctypes.sizeof(test_dm)
            while user32.EnumDisplaySettingsW(adapter_name, mode_idx, ctypes.byref(test_dm)):
                if test_dm.dmPelsWidth == width and test_dm.dmPelsHeight == height:
                    test_dm.dmPositionX = pos_x
                    test_dm.dmPositionY = pos_y
                    test_dm.dmFields |= 0x00000020
                    ret3 = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(test_dm), None, CDS_UPDATEREGISTRY, None)
                    if ret3 == DISP_CHANGE_SUCCESSFUL:
                        user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                        return True, f"成功匹配并切换至 {width} × {height} @ {test_dm.dmDisplayFrequency}Hz！"
                    ret_dyn = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(test_dm), None, 0, None)
                    if ret_dyn == DISP_CHANGE_SUCCESSFUL:
                        user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                        return True, f"成功匹配并动态切换至 {width} × {height} @ {test_dm.dmDisplayFrequency}Hz！"
                mode_idx += 1

            # 策略 2: 构造模式切换
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(dm)
            dm.dmPelsWidth = width
            dm.dmPelsHeight = height
            dm.dmBitsPerPel = 32
            dm.dmDisplayFrequency = refresh
            dm.dmPositionX = pos_x
            dm.dmPositionY = pos_y
            dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL | DM_DISPLAYFREQUENCY | 0x00000020

            ret = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(dm), None, CDS_UPDATEREGISTRY, None)
            if ret == DISP_CHANGE_SUCCESSFUL:
                user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                return True, f"成功将 {adapter_name} 分辨率切换至 {width} × {height} @ {refresh}Hz！"

            # 策略 3: 频率自适应 (0Hz)
            dm.dmDisplayFrequency = 0
            dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_BITSPERPEL | 0x00000020
            ret2 = user32.ChangeDisplaySettingsExW(adapter_name, ctypes.byref(dm), None, CDS_UPDATEREGISTRY, None)
            if ret2 == DISP_CHANGE_SUCCESSFUL:
                user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                return True, f"成功将 {adapter_name} 分辨率切换至 {width} × {height} (自动协商刷新率)！"

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        if ret == -2 or ret2 == -2:
            return False, (
                f"显卡驱动尚未完成该分辨率模式 ({width}×{height}) 的注册。\n\n"
                "💡 解决方法：\n"
                "1. 点击【⚡ 一键应用并切换分辨率】；\n"
                "2. 显卡驱动完成枚举后，若未自动变更为新分辨率，也可直接在 Windows 桌面右键【显示设置】中下拉选择 {width}×{height}！"
            )
        else:
            return False, f"切换返回代码: {ret}"


# ==========================================
# 极简现代高质感 GUI 界面 (v3.2)
# ==========================================
class ModernEDIDApp(tk.Tk):
    # 目标诱骗常用预设
    TARGET_PRESETS = [
        ("4K 60Hz - 3840×2160 @ 60Hz (主流超清)", 3840, 2160, 60),
        ("4K 120Hz - 3840×2160 @ 120Hz (超清高刷)", 3840, 2160, 120),
        ("2K 144Hz - 2560×1440 @ 144Hz (电竞高刷)", 2560, 1440, 144),
        ("2K 60Hz - 2560×1440 @ 60Hz (高清办公)", 2560, 1440, 60),
        ("1080P 144Hz - 1920×1080 @ 144Hz (高刷)", 1920, 1080, 144),
        ("1080P 60Hz - 1920×1080 @ 60Hz (标准标清)", 1920, 1080, 60),
        ("准4K带鱼屏 - 3440×1440 @ 60Hz (21:9 超宽)", 3440, 1440, 60),
        ("双4K带鱼屏 - 5120×1440 @ 60Hz (32:9 超宽)", 5120, 1440, 60),
        ("5K超清 - 5120×2880 @ 60Hz", 5120, 2880, 60),
        ("8K旗舰 - 7680×4320 @ 60Hz", 7680, 4320, 60),
        ("自定义参数模式...", 0, 0, 0),
    ]

    # 虚拟显示器挂载常用预设
    VIRTUAL_PRESETS = [
        ("1920 × 1080 @ 60Hz (1080P 全高清)", 1920, 1080, 60),
        ("2560 × 1440 @ 60Hz (2K 高清)", 2560, 1440, 60),
        ("3840 × 2160 @ 60Hz (4K 超清)", 3840, 2160, 60),
        ("1920 × 1080 @ 120Hz (1080P 电竞)", 1920, 1080, 120),
        ("2560 × 1440 @ 144Hz (2K 144Hz 电竞)", 2560, 1440, 144),
        ("2560 × 1600 @ 60Hz (16:10 办公)", 2560, 1600, 60),
        ("3440 × 1440 @ 60Hz (21:9 带鱼屏)", 3440, 1440, 60),
    ]

    def __init__(self, license_details=None):
        super().__init__()
        self.license_details = license_details or {}
        self.title("WinEDID Tool v3.2 - 显卡诱骗与分辨率原生管理工具")

        # 现代暗黑极简配色规范
        self.COLOR_BG = "#13141f"
        self.COLOR_CARD = "#1c1e2d"
        self.COLOR_CARD_BORDER = "#2b2e42"
        self.COLOR_INPUT = "#26293d"
        self.COLOR_TEXT = "#e2e8f0"
        self.COLOR_MUTED = "#8b949e"
        self.COLOR_ACCENT = "#3b82f6"
        self.COLOR_ACCENT_HOVER = "#2563eb"
        self.COLOR_SUCCESS = "#10b981"
        self.COLOR_WARNING = "#f59e0b"
        self.COLOR_DANGER = "#ef4444"
        self.COLOR_PILL = "#272a3e"
        self.COLOR_PILL_HOVER = "#363a56"
        self.COLOR_PILL_ACTIVE = "#3b82f6"

        self.configure(bg=self.COLOR_BG)

        # 窗口大小与居中 (优化舒展尺寸)
        win_w, win_h = 760, 470
        self.minsize(720, 440)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - win_w) // 2)
        y = max(0, (sh - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.devices = []
        self.selected_dev_index = -1
        self.advanced_visible = False
        self.log_visible = False
        self.var_preserve_native = tk.BooleanVar(value=True)

        self.init_styles()
        self.build_ui()
        self.refresh_devices()

    def init_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", background=self.COLOR_BG, foreground=self.COLOR_TEXT, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=self.COLOR_CARD, foreground=self.COLOR_TEXT, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=self.COLOR_CARD, foreground=self.COLOR_MUTED, font=("Segoe UI", 9))

        style.configure(
            "TCombobox",
            fieldbackground=self.COLOR_INPUT,
            background=self.COLOR_CARD_BORDER,
            foreground=self.COLOR_TEXT,
            bordercolor=self.COLOR_CARD_BORDER,
            arrowcolor=self.COLOR_TEXT,
            font=("Segoe UI", 9)
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.COLOR_INPUT)],
            foreground=[("readonly", self.COLOR_TEXT)]
        )

        style.configure("TCheckbutton", background=self.COLOR_CARD, foreground=self.COLOR_TEXT, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", self.COLOR_CARD)], foreground=[("active", self.COLOR_ACCENT)])

    def build_ui(self):
        # 1. 顶部 Header (精简紧凑)
        header = tk.Frame(self, bg=self.COLOR_BG, padx=18, pady=8)
        header.pack(fill=tk.X)

        title_frame = tk.Frame(header, bg=self.COLOR_BG)
        title_frame.pack(side=tk.LEFT)

        lbl_title = tk.Label(
            title_frame, text="⚡ WinEDID Tool",
            bg=self.COLOR_BG, fg="#60a5fa", font=("Segoe UI", 14, "bold")
        )
        lbl_title.pack(side=tk.LEFT)

        lbl_badge = tk.Label(
            title_frame, text=" v3.2 极简版 ", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 8, "bold"), padx=4, pady=1
        )
        lbl_badge.pack(side=tk.LEFT, padx=(6, 8))

        lbl_sub = tk.Label(
            title_frame, text="显示器 EDID 诱骗与分辨率原生管理",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED, font=("Segoe UI", 9)
        )
        lbl_sub.pack(side=tk.LEFT)

        # 权限与刷新按钮区
        top_right = tk.Frame(header, bg=self.COLOR_BG)
        top_right.pack(side=tk.RIGHT)

        # 商业授权状态
        lic_str = self.license_details.get("remaining_days", "已授权")
        self.btn_lic = tk.Button(
            top_right, text=f"🔑 授权: {lic_str}", bg="#1e293b", fg="#38bdf8",
            font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=7, pady=2,
            cursor="hand2", command=self.show_license_info
        )
        self.btn_lic.pack(side=tk.LEFT, padx=(0, 6))

        admin = is_admin()
        perm_text = "🛡️ 已提权" if admin else "⚠️ 点击提权"
        perm_fg = self.COLOR_SUCCESS if admin else self.COLOR_WARNING
        btn_perm = tk.Button(
            top_right, text=perm_text, bg="#1e293b", fg=perm_fg,
            font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=7, pady=2,
            cursor="hand2" if not admin else "arrow",
            command=run_as_admin if not admin else None
        )
        btn_perm.pack(side=tk.LEFT, padx=(0, 6))

        btn_refresh = tk.Button(
            top_right, text="🔄 刷新", bg="#2a2e45", fg=self.COLOR_TEXT,
            font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=8, pady=2,
            activebackground="#3b4164", cursor="hand2", command=self.refresh_devices
        )
        btn_refresh.pack(side=tk.LEFT)

        # 主内容区域
        main_box = tk.Frame(self, bg=self.COLOR_BG, padx=16, pady=0)
        main_box.pack(fill=tk.BOTH, expand=True)

        # 核心设置卡片 (Clean Card)
        card = tk.Frame(main_box, bg=self.COLOR_CARD, padx=14, pady=12, highlightthickness=1, highlightbackground=self.COLOR_CARD_BORDER)
        card.pack(fill=tk.BOTH, expand=True)

        # -----------------------------
        # Section 1: 显示设备与虚拟显示器管理
        # -----------------------------
        dev_header = tk.Frame(card, bg=self.COLOR_CARD)
        dev_header.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            dev_header, text="显示设备", bg=self.COLOR_CARD, fg=self.COLOR_TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT)

        # 右侧操作区：保留原显示器分辨率、显示离线
        dev_tools = tk.Frame(dev_header, bg=self.COLOR_CARD)
        dev_tools.pack(side=tk.RIGHT)

        chk_preserve = ttk.Checkbutton(
            dev_tools, text="保留原显示器分辨率 (原生)",
            variable=self.var_preserve_native, style="TCheckbutton"
        )
        chk_preserve.pack(side=tk.LEFT, padx=(0, 10))

        self.var_show_offline = tk.BooleanVar(value=False)
        chk_offline = ttk.Checkbutton(
            dev_tools, text="显示离线设备",
            variable=self.var_show_offline, style="TCheckbutton", command=self.refresh_devices
        )
        chk_offline.pack(side=tk.LEFT)

        self.device_combo = ttk.Combobox(card, state="readonly", font=("Segoe UI", 9))
        self.device_combo.pack(fill=tk.X, pady=(0, 3))
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)

        # 设备状态标签
        self.lbl_device_info = tk.Label(
            card, text="正在读取显示设备状态...", bg=self.COLOR_CARD,
            fg=self.COLOR_MUTED, font=("Segoe UI", 8), anchor="w"
        )
        self.lbl_device_info.pack(fill=tk.X, pady=(0, 6))

        # 虚拟显示器专区操作条 (精致暗色卡片栏)
        virt_bar = tk.Frame(card, bg="#181a28", padx=8, pady=4, highlightthickness=1, highlightbackground=self.COLOR_CARD_BORDER)
        virt_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            virt_bar, text="🖥️ 虚拟显示器常用预设:", bg="#181a28", fg="#93c5fd",
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.virt_preset_combo = ttk.Combobox(
            virt_bar, state="readonly", width=29, font=("Segoe UI", 8),
            values=[p[0] for p in self.VIRTUAL_PRESETS]
        )
        self.virt_preset_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.virt_preset_combo.current(0)

        btn_add_virt = tk.Button(
            virt_bar, text="⚡ 直接诱骗虚拟显示器", bg="#1e293b", fg="#60a5fa",
            activebackground="#2563eb", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=8, pady=2,
            cursor="hand2", command=self.action_add_virtual_display
        )
        btn_add_virt.pack(side=tk.LEFT, padx=(0, 6))

        btn_rem_virt = tk.Button(
            virt_bar, text="➖ 移除选定虚拟屏", bg="#1e293b", fg="#f87171",
            activebackground="#ef4444", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, pady=2,
            cursor="hand2", command=self.action_remove_virtual_display
        )
        btn_rem_virt.pack(side=tk.LEFT, padx=(0, 6))

        btn_virt_help = tk.Button(
            virt_bar, text="💡 指南", bg="#181a28", fg=self.COLOR_MUTED,
            activebackground="#26293d", activeforeground=self.COLOR_TEXT,
            font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=2,
            cursor="hand2", command=self.show_virtual_display_help
        )
        btn_virt_help.pack(side=tk.RIGHT)

        # 细微分割线
        sep1 = tk.Frame(card, bg=self.COLOR_CARD_BORDER, height=1)
        sep1.pack(fill=tk.X, pady=(0, 8))

        # -----------------------------
        # Section 2: 目标诱骗分辨率配置 (常用预设 + 极简微调)
        # -----------------------------
        res_header = tk.Frame(card, bg=self.COLOR_CARD)
        res_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            res_header, text="目标诱骗分辨率", bg=self.COLOR_CARD, fg=self.COLOR_TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            res_header, text="常用预设:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.target_preset_combo = ttk.Combobox(
            res_header, state="readonly", width=34, font=("Segoe UI", 8),
            values=[p[0] for p in self.TARGET_PRESETS]
        )
        self.target_preset_combo.pack(side=tk.LEFT)
        self.target_preset_combo.current(0)
        self.target_preset_combo.bind("<<ComboboxSelected>>", self.on_target_preset_selected)

        self.lbl_pclk_calc = tk.Label(
            res_header, text="时序时钟: ~526 MHz", bg=self.COLOR_CARD,
            fg=self.COLOR_SUCCESS, font=("Consolas", 8, "bold")
        )
        self.lbl_pclk_calc.pack(side=tk.RIGHT)

        # 参数微调输入与快捷填入行
        input_row = tk.Frame(card, bg=self.COLOR_CARD)
        input_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(input_row, text="宽度 (W):", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.entry_w = tk.Entry(
            input_row, width=7, bg=self.COLOR_INPUT, fg=self.COLOR_TEXT,
            insertbackground="#ffffff", relief=tk.FLAT, font=("Segoe UI", 9, "bold")
        )
        self.entry_w.pack(side=tk.LEFT, padx=(4, 10))
        self.entry_w.insert(0, "3840")
        self.entry_w.bind("<KeyRelease>", self.on_input_changed)

        tk.Label(input_row, text="高度 (H):", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.entry_h = tk.Entry(
            input_row, width=7, bg=self.COLOR_INPUT, fg=self.COLOR_TEXT,
            insertbackground="#ffffff", relief=tk.FLAT, font=("Segoe UI", 9, "bold")
        )
        self.entry_h.pack(side=tk.LEFT, padx=(4, 10))
        self.entry_h.insert(0, "2160")
        self.entry_h.bind("<KeyRelease>", self.on_input_changed)

        tk.Label(input_row, text="刷新率 (Hz):", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.entry_hz = tk.Entry(
            input_row, width=5, bg=self.COLOR_INPUT, fg=self.COLOR_TEXT,
            insertbackground="#ffffff", relief=tk.FLAT, font=("Segoe UI", 9, "bold")
        )
        self.entry_hz.pack(side=tk.LEFT, padx=(4, 14))
        self.entry_hz.insert(0, "60")
        self.entry_hz.bind("<KeyRelease>", self.on_input_changed)

        # 快捷填入出厂原生分辨率按钮
        self.btn_fill_native = tk.Button(
            input_row, text="↩️ 填入原显示器分辨率 (原生)",
            bg="#1e293b", fg="#38bdf8", activebackground="#0284c7", activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=10, pady=2, cursor="hand2",
            command=self.fill_current_native_res
        )
        self.btn_fill_native.pack(side=tk.LEFT)

        # 细微分割线
        sep2 = tk.Frame(card, bg=self.COLOR_CARD_BORDER, height=1)
        sep2.pack(fill=tk.X, pady=(0, 10))

        # -----------------------------
        # Section 3: 核心操作区 (双核心大按钮)
        # -----------------------------
        action_bar = tk.Frame(card, bg=self.COLOR_CARD)
        action_bar.pack(fill=tk.X)

        # 核心主按钮: 一键应用并切换
        self.btn_one_click = tk.Button(
            action_bar, text="⚡ 一键诱骗并应用新分辨率",
            bg=self.COLOR_ACCENT, fg="#ffffff",
            activebackground=self.COLOR_ACCENT_HOVER, activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=16, pady=6,
            cursor="hand2", command=self.action_one_click_apply
        )
        self.btn_one_click.pack(side=tk.LEFT, padx=(0, 10))

        # 恢复出厂原生
        self.btn_restore = tk.Button(
            action_bar, text="↩️ 恢复出厂原生 (原生分辨率)",
            bg="#2a2e45", fg="#f87171",
            activebackground="#3e374d", activeforeground="#fca5a5",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=6,
            cursor="hand2", command=self.action_restore_default
        )
        self.btn_restore.pack(side=tk.LEFT, padx=(0, 10))

        # 高级 / 分步操作展开按钮
        self.btn_adv_toggle = tk.Button(
            action_bar, text="⚙️ 更多选项 ▾",
            bg=self.COLOR_CARD, fg=self.COLOR_MUTED,
            activebackground=self.COLOR_CARD_BORDER, activeforeground=self.COLOR_TEXT,
            font=("Segoe UI", 9), relief=tk.FLAT, padx=8, pady=6,
            cursor="hand2", command=self.toggle_advanced_panel
        )
        self.btn_adv_toggle.pack(side=tk.RIGHT)

        # -----------------------------
        # Section 4: 高级与分步折叠面板
        # -----------------------------
        self.adv_frame = tk.Frame(card, bg="#181a28", padx=10, pady=8, highlightthickness=1, highlightbackground=self.COLOR_CARD_BORDER)

        adv_row1 = tk.Frame(self.adv_frame, bg="#181a28")
        adv_row1.pack(fill=tk.X, pady=(0, 5))

        tk.Label(adv_row1, text="分步执行:", bg="#181a28", fg=self.COLOR_MUTED, font=("Segoe UI", 8)).pack(side=tk.LEFT)

        btn_step1 = tk.Button(
            adv_row1, text="1. 写入EDID", bg="#26293d", fg=self.COLOR_TEXT,
            font=("Segoe UI", 8), relief=tk.FLAT, padx=7, pady=2,
            cursor="hand2", command=self.action_apply_edid
        )
        btn_step1.pack(side=tk.LEFT, padx=3)

        btn_step2 = tk.Button(
            adv_row1, text="2. PnP热重启", bg="#26293d", fg=self.COLOR_TEXT,
            font=("Segoe UI", 8), relief=tk.FLAT, padx=7, pady=2,
            cursor="hand2", command=self.action_restart_pnp
        )
        btn_step2.pack(side=tk.LEFT, padx=3)

        btn_step3 = tk.Button(
            adv_row1, text="3. 切换分辨率", bg="#26293d", fg=self.COLOR_TEXT,
            font=("Segoe UI", 8), relief=tk.FLAT, padx=7, pady=2,
            cursor="hand2", command=self.action_switch_resolution
        )
        btn_step3.pack(side=tk.LEFT, padx=3)

        adv_row2 = tk.Frame(self.adv_frame, bg="#181a28")
        adv_row2.pack(fill=tk.X)

        self.var_cta_block = tk.BooleanVar(value=True)
        chk_cta = ttk.Checkbutton(
            adv_row2, text="注入 HDMI 2.0 CTA-861 扩展块 (支持4K/高刷)",
            variable=self.var_cta_block, style="TCheckbutton"
        )
        chk_cta.pack(side=tk.LEFT)

        btn_virt_help = tk.Button(
            adv_row2, text="💡 虚拟屏指南", bg="#26293d", fg="#60a5fa",
            font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
            cursor="hand2", command=self.show_virtual_display_help
        )
        btn_virt_help.pack(side=tk.RIGHT, padx=(4, 0))

        btn_export = tk.Button(
            adv_row2, text="💾 导出.bin", bg="#26293d", fg=self.COLOR_MUTED,
            font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
            cursor="hand2", command=self.action_export_bin
        )
        btn_export.pack(side=tk.RIGHT, padx=4)

        btn_import = tk.Button(
            adv_row2, text="📂 导入.bin", bg="#26293d", fg=self.COLOR_MUTED,
            font=("Segoe UI", 8), relief=tk.FLAT, padx=6, pady=1,
            cursor="hand2", command=self.action_import_bin
        )
        btn_import.pack(side=tk.RIGHT)

        # -----------------------------
        # Section 5: 底部轻量状态条与可折叠日志
        # -----------------------------
        status_bar = tk.Frame(self, bg=self.COLOR_BG, padx=20, pady=8)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            status_bar, text="🟢 就绪", bg=self.COLOR_BG,
            fg=self.COLOR_TEXT, font=("Segoe UI", 9)
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.btn_log_toggle = tk.Button(
            status_bar, text="📋 显示日志 ▾", bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            activebackground=self.COLOR_BG, activeforeground=self.COLOR_TEXT,
            font=("Segoe UI", 8), relief=tk.FLAT, cursor="hand2",
            command=self.toggle_log_panel
        )
        self.btn_log_toggle.pack(side=tk.RIGHT)

        # 折叠日志区域
        self.log_container = tk.Frame(self, bg="#0d0e17", padx=16, pady=4)
        self.log_text = tk.Text(
            self.log_container, bg="#0d0e17", fg="#94a3b8",
            font=("Consolas", 8), relief=tk.FLAT, wrap=tk.WORD, height=6
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(self.log_container, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        self.set_custom_res(3840, 2160, 60)
        self.log("WinEDID Tool v3.1 就绪，默认只展示在线设备。")

    # ================= 交互控制逻辑 =================
    def toggle_advanced_panel(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.adv_frame.pack(fill=tk.X, pady=(12, 0))
            self.btn_adv_toggle.config(text="⚙️ 收起高级 ▴", fg=self.COLOR_TEXT)
        else:
            self.adv_frame.pack_forget()
            self.btn_adv_toggle.config(text="⚙️ 高级与分步 ▾", fg=self.COLOR_MUTED)

    def toggle_log_panel(self):
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_container.pack(fill=tk.X, side=tk.BOTTOM, padx=18, pady=(0, 6))
            self.btn_log_toggle.config(text="📋 收起日志 ▴", fg=self.COLOR_TEXT)
        else:
            self.log_container.pack_forget()
            self.btn_log_toggle.config(text="📋 显示日志 ▾", fg=self.COLOR_MUTED)

    def set_status(self, text, level="INFO"):
        fg = self.COLOR_TEXT
        if level == "SUCCESS":
            fg = self.COLOR_SUCCESS
        elif level == "WARN":
            fg = self.COLOR_WARNING
        elif level == "ERROR":
            fg = self.COLOR_DANGER
        self.lbl_status.config(text=text, fg=fg)

    def log(self, message, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{timestamp}] "
        if level == "WARN":
            prefix += "⚠️ "
        elif level == "SUCCESS":
            prefix += "✅ "
        elif level == "ERROR":
            prefix += "❌ "
        else:
            prefix += "ℹ️ "
        self.log_text.insert(tk.END, f"{prefix}{message}\n")
        self.log_text.see(tk.END)

    def refresh_devices(self, quiet=False):
        """扫描在线设备"""
        show_offline = self.var_show_offline.get()
        self.devices = EDIDManager.scan_online_devices(include_offline=show_offline)

        combo_values = []
        for dev in self.devices:
            if dev.get("is_virtual"):
                if dev["is_online"]:
                    st = "🟣 虚拟(已诱骗)" if dev["has_override"] else "🟣 虚拟(待诱骗)"
                else:
                    st = "⚪ 离线虚拟"
            else:
                st = "🟢 在线" if dev["is_online"] else "⚪ 离线"
            ov = " ★已激活物理品牌诱骗" if dev["has_override"] else ""
            nat_str = f" [出厂原生: {dev['native_res_str']}]" if dev.get("native_res_str") else ""
            combo_values.append(f"[{st}] {dev['name']} - 当前: {dev['curr_res']}{nat_str}{ov}")

        self.device_combo['values'] = combo_values
        if combo_values:
            if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
                self.selected_dev_index = 0
            self.device_combo.current(self.selected_dev_index)
            self.on_device_selected(None)
            if not quiet:
                self.set_status(f"🟢 已连接 {len(self.devices)} 个有效显示设备", "SUCCESS")
                self.log(f"已扫描到 {len(self.devices)} 个显示设备。")
        else:
            self.selected_dev_index = -1
            self.lbl_device_info.config(text="未检测到活动的显示端口。若插入了硬件诱骗插头，请按 Win+P 选择【扩展】。")
            if not quiet:
                self.set_status("⚠️ 未检测到有效显示设备，请检查连接或扩展状态", "WARN")
                self.log("未检测到有效设备！可插入硬件诱骗插头并按 Win+P 扩展。", "WARN")

    def show_virtual_display_help(self):
        """虚拟显示器使用指南"""
        msg = (
            "【💡 虚拟显示器与无头主机完全指南】\n\n"
            "1. 硬件方式（极力推荐，最稳定零故障）：\n"
            "   在电脑空闲的 HDMI / DP 接口插入一个【HDMI/DP 硬件诱骗插头】（淘宝/京东仅需十几元，免驱动）。插上后显卡立即识别为真实物理显示器，本工具即可对其任意诱骗 4K/2K/高刷！\n\n"
            "2. 软件虚拟屏驱动：\n"
            "   如使用向日葵，可在客户端设置中开启【虚拟显示屏】；或使用 Parsec / IddSampleDriver / USBMMIDD 虚拟屏幕驱动，驱动生成监视器节点后即可对其写入 EDID。\n\n"
            "3. 系统快捷键无线扩展：\n"
            "   按键盘【Win + P】选择【扩展】，或按【Win + K】使用系统无线显示器扩展功能。"
        )
        messagebox.showinfo("虚拟显示器指南", msg)

    def on_device_selected(self, event):
        idx = self.device_combo.current()
        if idx < 0 or idx >= len(self.devices):
            return
        self.selected_dev_index = idx
        dev = self.devices[idx]

        ad_text = dev['adapter_name'] if dev['adapter_name'] else "未分配活动端口"
        ov_text = "★已激活诱骗覆写" if dev['has_override'] else "出厂原生配置"
        virt_tag = " [虚拟屏]" if dev.get("is_virtual") else " [物理屏]"
        nat_text = dev.get("native_res_str", "未知 (原生分辨率)")

        self.lbl_device_info.config(
            text=f"当前显示: {dev['curr_res']}  |  出厂推荐: {nat_text}  |  端口: {ad_text}  |  状态: {ov_text}"
        )

    def fill_current_native_res(self):
        """一键将当前选中设备的出厂原生分辨率填入输入框"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showinfo("提示", "请先在上方设备列表中选择一个显示设备！")
            return
        dev = self.devices[self.selected_dev_index]
        if dev.get("native_res"):
            nw, nh, nhz = dev["native_res"]
            self.set_custom_res(nw, nh, nhz)
            self.set_status(f"已填入出厂原生分辨率: {nw}×{nh}@{nhz}Hz (原生分辨率)", "SUCCESS")
            self.log(f"已填入 [{dev['name']}] 出厂原生分辨率: {nw} × {nh} @ {nhz}Hz (原生分辨率)")
        else:
            messagebox.showinfo("提示", "未能从该设备解析到出厂原生分辨率。")

    def on_target_preset_selected(self, event=None):
        """当用户在目标诱骗常用预设下拉框中选择时触发"""
        idx = self.target_preset_combo.current()
        if 0 <= idx < len(self.TARGET_PRESETS):
            name, w, h, r = self.TARGET_PRESETS[idx]
            if w > 0 and h > 0 and r > 0:
                self.set_custom_res(w, h, r, update_combo=False)
                self.set_status(f"已选用预设: {name}", "INFO")

    def on_input_changed(self, event=None):
        """当用户手动输入宽高刷新率时触发"""
        self.update_timing_preview()
        try:
            w = int(self.entry_w.get().strip())
            h = int(self.entry_h.get().strip())
            r = int(self.entry_hz.get().strip())
            matched = False
            for i, (_, pw, ph, pr) in enumerate(self.TARGET_PRESETS):
                if pw == w and ph == h and pr == r:
                    self.target_preset_combo.current(i)
                    matched = True
                    break
            if not matched:
                self.target_preset_combo.current(len(self.TARGET_PRESETS) - 1)
        except Exception:
            pass

    def action_add_virtual_display(self):
        """
        虚拟显示器直接诱骗：
        让 Windows 系统、显卡驱动及远程软件（向日葵/ToDesk/Sunshine等）彻底认为真的连接了一个真实物理显示器！
        """
        if not is_admin():
            if messagebox.askyesno("需要管理员权限", "诱骗虚拟显示器并注入硬件级 EDID 需要管理员权限！是否立即提权重新启动？"):
                run_as_admin()
            return

        # 1. 获取选中的虚拟屏预设
        v_idx = self.virt_preset_combo.current()
        if 0 <= v_idx < len(self.VIRTUAL_PRESETS):
            v_name, w, h, hz = self.VIRTUAL_PRESETS[v_idx]
        else:
            w, h, hz = 1920, 1080, 60
            v_name = "1920×1080 @ 60Hz"

        # 2. 判断当前是否有可直接诱骗的虚拟显示器
        target_dev = None
        # 优先看当前选中的设备是否为虚拟显示器
        if 0 <= self.selected_dev_index < len(self.devices):
            cur = self.devices[self.selected_dev_index]
            if cur.get("is_virtual") or any(x in cur.get("name", "").lower() for x in ["non-pnp", "default", "virtual", "spacedesk"]):
                target_dev = cur

        # 若当前选中的不是虚拟显示器，遍历寻找系统中任何一个在线的虚拟显示器
        if not target_dev:
            for d in self.devices:
                if d.get("is_online") and (d.get("is_virtual") or any(x in d.get("name", "").lower() for x in ["non-pnp", "default", "virtual", "spacedesk"])):
                    target_dev = d
                    break

        # 场景 A: 系统中已有在线虚拟显示器 (如 Generic Non-PnP Monitor / spacedesk / 向日葵虚拟屏)
        # -> 直接执行全真物理 EDID 诱骗覆盖！
        if target_dev:
            self.set_status(f"🚀 正在直接诱骗虚拟显示器 [{target_dev['name']}] 为真实物理显示器...", "INFO")
            self.log(f"开始为虚拟显示器 [{target_dev['name']}] 直接注入真实品牌物理 EDID ({w}×{h}@{hz}Hz)...")
            self.update()

            # 智能品牌命名
            if w >= 3840 and h >= 2160:
                brand_model = "DELL U2720Q"
            elif w >= 3440:
                brand_model = "DELL U3419W"
            elif w >= 2560:
                brand_model = "DELL S2721D"
            else:
                brand_model = "DELL P2419H"

            b0, b1 = build_full_edid_blocks(
                width=w, height=h, refresh=hz,
                monitor_name=brand_model,
                base_raw_edid=b"",  # 强制生成正宗 DELL 品牌 0x10AC 固件
                include_cta=True,
                preserve_native_res=self.var_preserve_native.get()
            )

            ok, msg = EDIDManager.apply_edid_override_dual(target_dev, b0, b1)
            if not ok:
                self.set_status("❌ 写入诱骗 EDID 失败", "ERROR")
                self.log(msg, "ERROR")
                messagebox.showerror("诱骗失败", msg)
                return

            self.log(f"已成功将品牌 EDID 注入注册表，正在执行显卡 PnP 热重载...", "SUCCESS")
            self.set_status("🔄 正在 PnP 热重载显卡设备 (屏幕会闪烁微秒)...", "INFO")
            self.update()

            EDIDManager.restart_graphics_driver_full(target_dev.get("pnp_id", ""))
            time.sleep(1.2)

            # 重新刷新并自动切分辨率
            self.refresh_devices(quiet=True)
            target_adapter = target_dev.get("adapter_name", "")
            for d in self.devices:
                if d.get("pnp_id") == target_dev.get("pnp_id") and d.get("adapter_name"):
                    target_adapter = d.get("adapter_name")
                    break

            if target_adapter:
                EDIDManager.smart_switch_resolution(target_adapter, w, h, hz, max_retries=4, retry_delay=0.5)

            self.refresh_devices()
            # 自动高亮选定该虚拟屏
            for i, d in enumerate(self.devices):
                if d.get("pnp_id") == target_dev.get("pnp_id"):
                    self.selected_dev_index = i
                    self.device_combo.current(i)
                    self.on_device_selected(None)
                    break

            self.set_status(f"🎉 虚拟显示器已直接诱骗为真实物理显示器 ({brand_model})！", "SUCCESS")
            self.log(f"虚拟显示器已成功直接诱骗为真实品牌显示器 [{brand_model}] ({w}×{h}@{hz}Hz)！", "SUCCESS")
            messagebox.showinfo(
                "虚拟显示器直接诱骗成功",
                f"🎉 虚拟显示器诱骗已全部完成！\n\n"
                f"• 硬件识别型号: {brand_model} (戴尔官方品牌固件)\n"
                f"• 当前诱骗规格: {w} × {h} @ {hz}Hz\n"
                f"• 端口实例: {target_adapter or target_dev.get('pnp_id')}\n\n"
                "💡 效果确认：\n"
                "Windows 设备管理器、系统显示设置以及所有远程串流软件（向日葵、ToDesk、Sunshine、Moonlight 等）\n"
                "现在完全视其为一台真实连接的物理显示器，具备完整的硬件加速与超清高刷能力！"
            )
            return

        # 场景 B: 系统中当前没有活动虚拟屏实例，尝试将空闲虚拟/扩展端口挂载并诱骗
        self.set_status(f"🔄 正在唤醒并挂载虚拟显示器 ({w}×{h}@{hz}Hz)...", "INFO")
        self.log(f"开始唤醒并挂载虚拟显示器，选用预设: {v_name}...")
        self.update()

        ok, msg = VirtualDisplayManager.add_virtual_display(w, h, hz)
        self.refresh_devices()
        if ok:
            # 挂载成功后，再次检索新设备并自动完成诱骗
            new_target = None
            for i, dev in enumerate(self.devices):
                if dev.get("is_virtual") and dev.get("is_online"):
                    new_target = dev
                    self.selected_dev_index = i
                    self.device_combo.current(i)
                    self.on_device_selected(None)
                    break

            if new_target:
                brand_model = "DELL U2720Q" if w >= 3840 else ("DELL S2721D" if w >= 2560 else "DELL P2419H")
                b0, b1 = build_full_edid_blocks(w, h, hz, monitor_name=brand_model, base_raw_edid=b"", include_cta=True)
                EDIDManager.apply_edid_override_dual(new_target, b0, b1)
                EDIDManager.restart_graphics_driver_full(new_target.get("pnp_id", ""))
                time.sleep(1.0)
                if new_target.get("adapter_name"):
                    EDIDManager.smart_switch_resolution(new_target.get("adapter_name"), w, h, hz)
                self.refresh_devices()

            self.set_status(f"🎉 虚拟显示器已挂载并诱骗为真实物理显示器 ({w}×{h})！", "SUCCESS")
            self.log(msg, "SUCCESS")
            messagebox.showinfo(
                "直接诱骗成功",
                f"{msg}\n\n"
                f"已成功将虚拟显示器挂载到桌面并注入真实品牌 EDID 固件 ({w} × {h} @ {hz}Hz)！\n"
                "设备现在完全被系统视作真实显示器使用。"
            )
        else:
            self.set_status("⚠️ 未检测到可直接挂载的虚拟驱动端口", "WARN")
            self.log("挂载虚拟显示器：未检测到就绪端口", "WARN")
            messagebox.showinfo("诱骗虚拟显示器说明", msg)

    def action_remove_virtual_display(self):
        """移除虚拟显示器"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先在上方列表中选择要移除的虚拟显示器！")
            return
        dev = self.devices[self.selected_dev_index]
        target_adapter = dev.get("adapter_name")
        if not target_adapter:
            messagebox.showwarning("提示", "所选设备当前未连接到活动桌面端口，无需移除。")
            return

        if messagebox.askyesno("确认移除", f"确定要从桌面断开显示器 [{dev['name']}] ({target_adapter}) 吗？"):
            ok, msg = VirtualDisplayManager.remove_virtual_display(target_adapter)
            self.refresh_devices()
            if ok:
                self.set_status("✅ 虚拟显示器已从桌面移除", "SUCCESS")
                self.log(msg, "SUCCESS")
                messagebox.showinfo("移除成功", msg)
            else:
                self.set_status("❌ 移除失败", "ERROR")
                self.log(msg, "ERROR")
                messagebox.showerror("移除失败", msg)

    def set_custom_res(self, w, h, r, update_combo=True):
        self.entry_w.delete(0, tk.END)
        self.entry_w.insert(0, str(w))
        self.entry_h.delete(0, tk.END)
        self.entry_h.insert(0, str(h))
        self.entry_hz.delete(0, tk.END)
        self.entry_hz.insert(0, str(r))
        self.update_timing_preview()
        if update_combo:
            matched = False
            for i, (_, pw, ph, pr) in enumerate(self.TARGET_PRESETS):
                if pw == w and ph == h and pr == r:
                    self.target_preset_combo.current(i)
                    matched = True
                    break
            if not matched:
                self.target_preset_combo.current(len(self.TARGET_PRESETS) - 1)

    def get_input_resolution(self):
        try:
            w = int(self.entry_w.get().strip())
            h = int(self.entry_h.get().strip())
            hz = int(self.entry_hz.get().strip())
            if w < 640 or w > 16384 or h < 480 or h > 16384 or hz < 15 or hz > 500:
                raise ValueError("数值超出合理范围 (640-16384, 15-500Hz)")
            return w, h, hz
        except Exception as e:
            messagebox.showerror("参数错误", f"输入的分辨率或刷新率不合法: {e}")
            return None

    def update_timing_preview(self, event=None):
        try:
            w = int(self.entry_w.get().strip())
            h = int(self.entry_h.get().strip())
            hz = int(self.entry_hz.get().strip())
            _, pclk = calculate_cvt_rb_timing(w, h, hz)
            self.lbl_pclk_calc.config(
                text=f"CVT-RB 时序: PCLK ~{pclk:.1f} MHz", fg=self.COLOR_SUCCESS
            )
        except Exception:
            self.lbl_pclk_calc.config(text="时钟: 等待有效参数", fg=self.COLOR_DANGER)

    # ================= 业务操作逻辑 =================
    def action_one_click_apply(self):
        """一键自动化：构造双块EDID -> 注入双注册表 -> PnP热重载 -> 智能切换分辨率"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先在上方选择目标显示设备！")
            return

        res = self.get_input_resolution()
        if not res:
            return
        w, h, hz = res
        dev = self.devices[self.selected_dev_index]

        if not is_admin():
            if messagebox.askyesno("需要管理员权限", "一键写入注册表与热重载需要管理员权限！是否立即提权重新启动？"):
                run_as_admin()
            return

        self.set_status(f"🚀 正在写入 {w}×{h}@{hz}Hz 双块 EDID...", "INFO")
        self.log(f"开始一键执行：为 [{dev['name']}] 诱骗 {w} × {h} @ {hz}Hz...")
        self.update()

        b0, b1 = build_full_edid_blocks(
            width=w, height=h, refresh=hz,
            monitor_name=dev['name'],
            base_raw_edid=dev['raw_edid'],
            include_cta=self.var_cta_block.get(),
            preserve_native_res=self.var_preserve_native.get()
        )

        ok, msg = EDIDManager.apply_edid_override_dual(dev, b0, b1)
        if not ok:
            self.set_status("❌ 写入 EDID 失败", "ERROR")
            self.log(msg, "ERROR")
            messagebox.showerror("写入失败", msg)
            return

        self.log("注册表双路径覆写注入成功，正在执行 PnP 显卡热重载...", "SUCCESS")
        self.set_status("🔄 正在 PnP 热重载显卡设备 (屏幕会闪烁微秒)...", "INFO")
        self.update()

        # 热重载
        pnp_id = dev.get("pnp_id", "")
        EDIDManager.restart_graphics_driver_full(pnp_id)
        self.log("PnP 热重启完成，显卡已重新加载注册表 EDID。", "SUCCESS")

        # 智能等待并自动切换
        self.set_status("🖥️ 正在自动切换至新诱骗分辨率...", "INFO")
        self.update()
        time.sleep(1.0)

        # 刷新并重新定位目标端口
        self.refresh_devices(quiet=True)
        target_adapter = dev.get("adapter_name", "")
        for d in self.devices:
            if d.get("pnp_id") == dev.get("pnp_id") and d.get("adapter_name"):
                target_adapter = d.get("adapter_name")
                break

        if target_adapter:
            ok3, msg3 = EDIDManager.smart_switch_resolution(target_adapter, w, h, hz, max_retries=5, retry_delay=0.6)
            if ok3:
                self.log(msg3, "SUCCESS")
                self.set_status(f"🎉 成功切换至 {w}×{h} @ {hz}Hz！", "SUCCESS")
                messagebox.showinfo("一键应用成功", f"🎉 诱骗与切换已全部完成！\n\n设备: {dev['name']}\n目标分辨率: {w} × {h} @ {hz}Hz\n状态: 显卡驱动已正常加载并生效。\n\n💡 提示：若勾选了保留原有分辨率，您可在 Windows 显示设置中随时切回原物理分辨率。")
            else:
                self.log(msg3, "WARN")
                self.set_status(f"⚠️ EDID注入成功，请在系统设置中下拉选择 {w}×{h}", "WARN")
                messagebox.showinfo(
                    "EDID 诱骗成功",
                    f"EDID 已成功写入并热重载生效！\n\n如果尚未自动切换，可在 Windows 桌面右键【显示设置】中直接下拉选择 {w} × {h} 即可。"
                )
        else:
            self.set_status(f"✅ EDID 诱骗成功！请在系统设置中扩展此显示器", "SUCCESS")
            messagebox.showinfo("诱骗成功", "EDID 已成功写入并重载！由于当前端口尚未扩展到桌面，请在 Windows 显示设置中点击【扩展这些显示器】。")

        self.refresh_devices()

    def action_apply_edid(self):
        """分步 1: 仅写入 EDID"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先选择目标设备！")
            return

        res = self.get_input_resolution()
        if not res:
            return
        w, h, hz = res
        dev = self.devices[self.selected_dev_index]

        if not is_admin():
            if messagebox.askyesno("权限不足", "写入注册表必须以管理员权限运行！是否立即提权重新启动？"):
                run_as_admin()
            return

        b0, b1 = build_full_edid_blocks(
            width=w, height=h, refresh=hz,
            monitor_name=dev['name'],
            base_raw_edid=dev['raw_edid'],
            include_cta=self.var_cta_block.get(),
            preserve_native_res=self.var_preserve_native.get()
        )

        ok, msg = EDIDManager.apply_edid_override_dual(dev, b0, b1)
        if ok:
            self.set_status(f"✅ EDID 写入成功 ({w}×{h})", "SUCCESS")
            self.log(msg, "SUCCESS")
            messagebox.showinfo("写入成功", f"已成功将 {w}×{h} @ {hz}Hz 诱骗数据注入注册表！\n请点击【2. PnP热重启】使其生效。")
            self.refresh_devices()
        else:
            self.set_status("❌ 写入失败", "ERROR")
            self.log(msg, "ERROR")
            messagebox.showerror("写入失败", msg)

    def action_restart_pnp(self):
        """分步 2: PnP 热重启该显示设备"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先选择目标设备！")
            return

        dev = self.devices[self.selected_dev_index]
        pnp_id = dev.get("pnp_id", "")
        self.set_status("🔄 正在热重启设备...", "INFO")
        self.log(f"正在热重启设备 [{dev['name']}] (实例: {pnp_id})...")
        self.update()

        ok, msg = EDIDManager.restart_graphics_driver_full(pnp_id)
        self.set_status("✅ 设备热重载完成", "SUCCESS")
        self.log(msg, "SUCCESS")
        self.refresh_devices()

    def action_switch_resolution(self):
        """分步 3: 智能切换屏幕分辨率"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先选择目标设备！")
            return

        res = self.get_input_resolution()
        if not res:
            return
        w, h, hz = res
        dev = self.devices[self.selected_dev_index]

        if not dev["is_online"] or not dev["adapter_name"]:
            messagebox.showwarning("无法切换", "所选设备当前未连接到活动桌面。请先在 Windows 显示设置中点击【扩展这些显示器】！")
            return

        self.set_status(f"🖥️ 正在切换至 {w}×{h} @ {hz}Hz...", "INFO")
        self.log(f"正在尝试将端口 {dev['adapter_name']} 切换至 {w} × {h} @ {hz}Hz...")
        ok, msg = EDIDManager.smart_switch_resolution(dev['adapter_name'], w, h, hz)
        if ok:
            self.set_status(f"✅ 成功切换至 {w}×{h} @ {hz}Hz", "SUCCESS")
            self.log(msg, "SUCCESS")
            messagebox.showinfo("切换成功", msg)
            self.refresh_devices()
        else:
            self.set_status("❌ 切换失败", "ERROR")
            self.log(msg, "ERROR")
            messagebox.showerror("提示", msg)

    def action_restore_default(self):
        """恢复出厂默认原生 EDID 并自动恢复原生物理分辨率"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先选择目标设备！")
            return

        dev = self.devices[self.selected_dev_index]
        if not is_admin():
            if messagebox.askyesno("权限不足", "清除注册表需要管理员权限，是否立即提权重新启动？"):
                run_as_admin()
            return

        if messagebox.askyesno("确认恢复原生", f"确定要清除设备 [{dev['name']}] 的所有诱骗配置并恢复硬件出厂原生状态吗？"):
            # 1. 提取出厂原始硬件最佳原生分辨率
            native_pref = dev.get("native_res") or EDIDManager.parse_edid_preferred_mode(dev.get("raw_edid"))

            # 2. 清除注册表 EDID_OVERRIDE
            ok, msg = EDIDManager.remove_edid_override_dual(dev)
            self.log(msg, "SUCCESS")
            self.set_status("✅ 诱骗已清除，正在重载显卡设备并恢复原生分辨率...", "SUCCESS")
            self.update()

            # 3. 驱动热重载
            EDIDManager.restart_graphics_driver_full(dev.get("pnp_id", ""))
            time.sleep(1.5)

            # 4. 重新定位端口
            target_adapter = dev.get("adapter_name", "")
            self.refresh_devices(quiet=True)
            for d in self.devices:
                if d.get("pnp_id") == dev.get("pnp_id") and d.get("adapter_name"):
                    target_adapter = d.get("adapter_name")
                    break

            # 5. 首先调用 Windows 系统默认还原机制
            if target_adapter:
                try:
                    user32.ChangeDisplaySettingsExW(target_adapter, None, None, 0, None)
                    user32.ChangeDisplaySettingsExW(None, None, None, 0, None)
                    time.sleep(0.5)
                except Exception:
                    pass

            # 6. 自动切回出厂原生分辨率
            switched = False
            if target_adapter and native_pref:
                nat_w, nat_h, nat_hz = native_pref
                self.log(f"正在将 [{dev['name']}] 切回出厂原生模式: {nat_w} × {nat_h} @ {nat_hz}Hz (原生分辨率)...")
                ok_sw, msg_sw = EDIDManager.smart_switch_resolution(target_adapter, nat_w, nat_h, nat_hz, max_retries=3, retry_delay=0.5)
                if not ok_sw:
                    # 备选保障：寻找显卡枚举模式中最贴合的原生支持模式
                    m_idx = 0
                    tdm = DEVMODEW()
                    tdm.dmSize = ctypes.sizeof(tdm)
                    alt_mode = None
                    while user32.EnumDisplaySettingsW(target_adapter, m_idx, ctypes.byref(tdm)):
                        if abs(tdm.dmPelsWidth - nat_w) <= 240 and abs(tdm.dmPelsHeight - nat_h) <= 100:
                            alt_mode = (tdm.dmPelsWidth, tdm.dmPelsHeight, tdm.dmDisplayFrequency)
                            break
                        m_idx += 1
                    if alt_mode:
                        ok_sw, msg_sw = EDIDManager.smart_switch_resolution(target_adapter, alt_mode[0], alt_mode[1], alt_mode[2], max_retries=2)
                        if ok_sw:
                            nat_w, nat_h, nat_hz = alt_mode

                if ok_sw:
                    switched = True
                    self.log(f"出厂原生分辨率已恢复成功：{nat_w} × {nat_h} @ {nat_hz}Hz (原生分辨率)", "SUCCESS")
            elif target_adapter:
                # 尝试从注册表设置 (-2) 获取原生并应用
                tdm = DEVMODEW()
                tdm.dmSize = ctypes.sizeof(tdm)
                if user32.EnumDisplaySettingsW(target_adapter, -2, ctypes.byref(tdm)):
                    ok_sw, msg_sw = EDIDManager.smart_switch_resolution(target_adapter, tdm.dmPelsWidth, tdm.dmPelsHeight, tdm.dmDisplayFrequency, max_retries=2)
                    if ok_sw:
                        switched = True
                        nat_w, nat_h, nat_hz = tdm.dmPelsWidth, tdm.dmPelsHeight, tdm.dmDisplayFrequency
                        self.log(f"出厂默认分辨率已恢复成功：{nat_w} × {nat_h} @ {nat_hz}Hz (原生分辨率)", "SUCCESS")

            self.refresh_devices()
            self.set_status("✅ 已成功恢复出厂原生配置与分辨率！", "SUCCESS")
            if switched and 'nat_w' in locals():
                messagebox.showinfo("已恢复出厂原生", f"🎉 已成功清除 EDID 诱骗并热重载显卡驱动！\n\n屏幕分辨率已自动恢复为出厂原生模式：\n{nat_w} × {nat_h} @ {nat_hz}Hz (原生分辨率)")
            else:
                messagebox.showinfo("已恢复出厂原生", f"已成功清除设备 [{dev['name']}] 的诱骗注册表并重新载入原生硬件配置！\n若分辨率未自动切回，可在 Windows 显示设置中直接选择推荐的 (原生分辨率)。")

    def action_export_bin(self):
        """导出 EDID"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先选择目标设备！")
            return
        dev = self.devices[self.selected_dev_index]
        res = self.get_input_resolution()
        if not res:
            return
        w, h, hz = res
        b0, b1 = build_full_edid_blocks(w, h, hz, monitor_name=dev['name'], base_raw_edid=dev['raw_edid'], preserve_native_res=self.var_preserve_native.get())
        full_data = b0 + (b1 if b1 else b"")

        fp = filedialog.asksaveasfilename(
            title="导出 EDID 文件",
            defaultextension=".bin",
            filetypes=[("EDID 二进制文件 (*.bin)", "*.bin"), ("所有文件 (*.*)", "*.*")],
            initialfile=f"{dev['mon_id']}_{w}x{h}.bin"
        )
        if fp:
            try:
                with open(fp, "wb") as f:
                    f.write(full_data)
                self.log(f"EDID 已保存至: {fp}", "SUCCESS")
                messagebox.showinfo("导出成功", f"文件已保存至:\n{fp}")
            except Exception as e:
                self.log(f"导出失败: {e}", "ERROR")

    def action_import_bin(self):
        """导入 EDID"""
        if self.selected_dev_index < 0 or self.selected_dev_index >= len(self.devices):
            messagebox.showwarning("提示", "请先选择需要覆写的目标设备！")
            return
        dev = self.devices[self.selected_dev_index]
        fp = filedialog.askopenfilename(
            title="选择要导入的 EDID 文件",
            filetypes=[("EDID 二进制文件 (*.bin, *.raw)", "*.bin;*.raw"), ("所有文件 (*.*)", "*.*")]
        )
        if not fp:
            return
        try:
            with open(fp, "rb") as f:
                data = f.read()
            if len(data) < 128:
                raise ValueError("EDID 文件长度不足 128 字节！")

            b0 = data[:128]
            b1 = data[128:256] if len(data) >= 256 else None

            if messagebox.askyesno("确认导入", f"读取到有效 EDID 数据 ({len(data)} 字节)。确定覆写到设备 [{dev['name']}] 吗？"):
                ok, msg = EDIDManager.apply_edid_override_dual(dev, b0, b1)
                if ok:
                    self.log(f"导入成功: {os.path.basename(fp)}", "SUCCESS")
                    self.set_status("✅ 导入成功，正在热重载...", "SUCCESS")
                    self.update()
                    EDIDManager.restart_graphics_driver_full(dev.get("pnp_id", ""))
                    messagebox.showinfo("导入成功", "EDID 导入并热重载生效成功！")
                    self.refresh_devices()
                else:
                    self.log(msg, "ERROR")
                    messagebox.showerror("写入失败", msg)
        except Exception as e:
            self.log(f"导入失败: {e}", "ERROR")
            messagebox.showerror("错误", str(e))

    def show_license_info(self):
        """查看商业授权详情或续期激活"""
        try:
            from license_dialog import LicenseActivationDialog
            from license_guard import license_guard
            _, status, details = license_guard.check_license()
            dlg = LicenseActivationDialog(status_code=status, details=details)
            success = dlg.show()
            _, _, new_details = license_guard.check_license()
            self.license_details = new_details
            lic_str = new_details.get("remaining_days", "已授权")
            self.btn_lic.config(text=f"🔑 授权: {lic_str}")
        except Exception as e:
            messagebox.showinfo("授权信息", f"商业授权状态: {self.license_details.get('remaining_days', '有效')}")


def main():
    lic_details = {}
    try:
        from license_dialog import require_license_or_dialog
        _, lic_details = require_license_or_dialog()
    except Exception as e:
        print("License guard:", e)

    app = ModernEDIDApp(license_details=lic_details)
    app.mainloop()


if __name__ == "__main__":
    main()

