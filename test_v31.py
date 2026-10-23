# -*- coding: utf-8 -*-
with open('多媒体工程师全栈手册_查询系统v3.1.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

ids = [
    'tool_proj_throw', 'pt_res', 'pt_custom_res_wrap', 'pt_custom_w', 'pt_custom_h',
    'pt_w', 'pt_tr', 'pt_lumen', 'pt_gain_preset', 'pt_gain', 'pt_eff',
    'pt_res_size', 'pt_res_area', 'pt_res_pitch', 'pt_res_ppi', 'pt_res_dist',
    'pt_res_lux', 'pt_res_nit', 'pt_res_lens', 'pt_note_pitch', 'pt_note_viewdist', 'pt_note_rec_view',
    'tool_proj_blend', 'pb_shape', 'pb_layout', 'pb_orient', 'pb_res',
    'pb_cols_wrap', 'pb_cols', 'pb_rows_wrap', 'pb_rows',
    'pb_overlap_x_wrap', 'pb_overlap_x', 'pb_overlap_y_wrap', 'pb_overlap_y',
    'pb_single_w', 'pb_curve_type', 'pb_curve_arc', 'pb_curve_angle', 'pb_curve_h',
    'pb_bowl_d1', 'pb_bowl_d2', 'pb_bowl_h', 'pb_dome_diam', 'pb_dome_tilt', 'pb_dome_fov',
    'pb_lumen', 'pb_gain',
    'pb_res_total_px', 'pb_res_overlap_px', 'pb_res_phys_size', 'pb_res_geo_extra',
    'pb_res_pitch', 'pb_res_lux', 'pb_res_total_units', 'pb_res_blend_box',
    'pb_note_text', 'pb_btn_quote_subtext'
]

missing_ids = []
for el_id in ids:
    if f'id="{el_id}"' not in text and f"id='{el_id}'" not in text:
        missing_ids.append(el_id)

funcs = ['runCalcProjThrow', 'runCalcProjBlend', 'applyPtGainPreset', 'onPbShapeChange', 'onPbLayoutChange', 'importProjBlendToQuote']
missing_funcs = [fn for fn in funcs if fn not in text]

print("Total elements checked:", len(ids))
print("Missing IDs:", missing_ids)
print("Missing Functions:", missing_funcs)

if not missing_ids and not missing_funcs:
    print("ALL TESTS PASSED: All DOM elements and functions are properly placed!")
else:
    print("TEST FAILED")
