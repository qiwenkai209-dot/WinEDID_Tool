# -*- coding: utf-8 -*-
import re
import os

source_file = r'd:\aiagent\jc\gj\多媒体工程师全栈手册_查询系统v3.0.html'
target_file = r'd:\aiagent\jc\gj\多媒体工程师全栈手册_查询系统v3.1.html'

with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()

print("Original length:", len(content))

# 1. 替换页面标题与版本徽章
content = content.replace(
    '<title>多媒体工程师全栈手册 · 智能查询与计算系统</title>',
    '<title>多媒体工程师全栈手册 · 智能查询与计算系统 v3.1</title>'
)

brand_old = '''        <div class="brand-title">
          多媒体工程师全栈手册
          <span class="status-badge" id="statusBadge">'''

brand_new = '''        <div class="brand-title">
          多媒体工程师全栈手册
          <span class="status-badge" style="background: rgba(56, 189, 248, 0.15); border-color: #38bdf8; color: #38bdf8; font-weight: 700;">v3.1 增强版</span>
          <span class="status-badge" id="statusBadge">'''

content = content.replace(brand_old, brand_new)

# 2. 准备新的 HTML 模板 (tool_proj_throw + tool_proj_blend)
new_html_tools = '''          <!-- 1.3 投影投射计算器 (v3.1 细化版) -->
          <div class="calc-card" id="tool_proj_throw">
            <div class="calc-card-header">
              <div class="calc-card-title">投影投射距离、镜头选型与像素物理尺寸计算器</div>
              <span class="status-badge" style="background: rgba(56, 189, 248, 0.18); color: #38bdf8;">v3.1 细化面积/像素点距/PPI/照度/Nit</span>
            </div>
            <div class="calc-card-desc">根据屏幕尺寸、物理分辨率与镜头投射比 (TR = 距离 / 宽度)，精确测算投射净距、幕面物理面积、单像素物理尺寸 (Pixel Pitch)、像素密度 (PPI) 及幕面反射照度/辉度 (Lux & Nit)。</div>
            <div class="calc-grid">
              <div class="calc-input-group">
                <label>单台投影机物理分辨率</label>
                <select id="pt_res" onchange="runCalcProjThrow()">
                  <option value="1920,1200,1.6" selected>1920 × 1200 (WUXGA 工程主流 16:10)</option>
                  <option value="1920,1080,1.7778">1920 × 1080 (FHD 1080P 16:9)</option>
                  <option value="3840,2160,1.7778">3840 × 2160 (4K UHD 16:9)</option>
                  <option value="4096,2160,1.8963">4096 × 2160 (DCI 4K 电影级 17:9)</option>
                  <option value="2560,1600,1.6">2560 × 1600 (WQXGA 16:10)</option>
                  <option value="1024,768,1.3333">1024 × 768 (XGA 传统 4:3)</option>
                  <option value="custom">✏️ 自定义输入像素...</option>
                </select>
              </div>
              <div class="calc-input-group" id="pt_custom_res_wrap" style="display: none;">
                <label>自定义物理分辨率 (宽 × 高 px)</label>
                <div style="display: flex; gap: 6px;">
                  <input type="number" id="pt_custom_w" value="1920" placeholder="宽" oninput="runCalcProjThrow()">
                  <input type="number" id="pt_custom_h" value="1200" placeholder="高" oninput="runCalcProjThrow()">
                </div>
              </div>
              <div class="calc-input-group">
                <label>屏幕宽度 (米)</label>
                <input type="number" id="pt_w" value="5.0" step="0.1" min="0.5" oninput="runCalcProjThrow()">
              </div>
              <div class="calc-input-group">
                <label>镜头投射比范围 (TR: 距离 / 宽度)</label>
                <input type="text" id="pt_tr" value="1.2-1.8" placeholder="例如 1.2-1.8 或 0.8" oninput="runCalcProjThrow()">
              </div>
              <div class="calc-input-group">
                <label>投影机标称流明 (ANSI / ISO Lm)</label>
                <input type="number" id="pt_lumen" value="10000" step="500" min="500" oninput="runCalcProjThrow()">
              </div>
              <div class="calc-input-group">
                <label>幕布光学增益 (Gain)</label>
                <select id="pt_gain_preset" onchange="applyPtGainPreset()">
                  <option value="1.0" selected>1.0 (标准漫反射白塑幕/白墙)</option>
                  <option value="0.8">0.8 (抗光黑栅幕 / 灰幕)</option>
                  <option value="1.2">1.2 (玻珠高增益幕)</option>
                  <option value="1.5">1.5 (微棱镜高亮金属软幕)</option>
                  <option value="custom">自定义数值</option>
                </select>
                <input type="number" id="pt_gain" value="1.0" step="0.05" min="0.4" max="3.0" style="margin-top: 4px; display: none;" oninput="runCalcProjThrow()">
              </div>
              <div class="calc-input-group">
                <label>光学通光与衰减效率系数</label>
                <select id="pt_eff" onchange="runCalcProjThrow()">
                  <option value="0.80" selected>80% (标准工程预留: 考虑激光光损与滤网)</option>
                  <option value="0.85">85% (高保真全新光机状态)</option>
                  <option value="0.70">70% (严苛环境/老旧设备冗余)</option>
                  <option value="0.90">90% (实验室理想无尘环境)</option>
                </select>
              </div>
            </div>
            <div class="calc-result-box" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));">
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_size">5.00m × 3.13m (232")</div>
                <div class="calc-stat-label">屏幕画面尺寸 / 对角线</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val success" id="pt_res_area">15.63 m²</div>
                <div class="calc-stat-label">画面有效物理总面积</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_pitch">2.60 mm</div>
                <div class="calc-stat-label">单个像素物理点距 (Pitch)</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_ppi">9.75 PPI (230万点)</div>
                <div class="calc-stat-label">像素密度 PPI / 画面总像素</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_dist">6.00 米 ~ 9.00 米</div>
                <div class="calc-stat-label">镜头至幕面吊装净距范围</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_lux">512 Lux (明亮高对比)</div>
                <div class="calc-stat-label">幕面有效反射照度 (Lux)</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_nit">163 Nit (cd/m²)</div>
                <div class="calc-stat-label">幕面等效反射亮度 (Nit)</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pt_res_lens">标准工程变焦镜头</div>
                <div class="calc-stat-label">推荐镜头类型 / 最佳视距</div>
              </div>
            </div>
            <div class="calc-note-box">
              🔍 <strong>像素点距与视距选型准则：</strong>当单像素点距为 <span id="pt_note_pitch">2.60mm</span> 时，基于人眼 1 角分极限分辨率，<strong>人眼无颗粒感最佳最近观看视距约为 <span id="pt_note_viewdist">8.9米</span></strong>（通常展厅巡览可取 1.5H ~ 3H 画面高度，即 <span id="pt_note_rec_view">4.7米 ~ 9.4米</span>）。
            </div>
          </div>

          <!-- 1.4 投影边缘融合与多屏异形幕综合计算器 (v3.1 全面升级) -->
          <div class="calc-card" id="tool_proj_blend">
            <div class="calc-card-header">
              <div class="calc-card-title">投影边缘融合与多屏异形幕综合计算器</div>
              <span class="status-badge" style="background: rgba(56, 189, 248, 0.18); color: #38bdf8;">v3.1 竖向/弧幕/碗幕/穹幕全支持</span>
            </div>
            <div class="calc-card-desc">全能工程融合工具：支持<b>横向单排、竖向单列、多行多列网格</b>布局，支持<b>常规平面幕、柱面弧幕/环幕、沉浸式碗幕、半球穹幕/天幕</b>多种异形屏幕几何造型，精准计算重叠像素、总分辨率、展开物理面积、像素点距与曲面校正方案。</div>
            
            <div class="calc-grid">
              <!-- 屏幕几何造型选择 -->
              <div class="calc-input-group">
                <label>屏幕几何造型 (形态分类)</label>
                <select id="pb_shape" onchange="onPbShapeChange(); runCalcProjBlend();">
                  <option value="flat" selected>📐 平面直幕 (常规平面/平铺融合墙)</option>
                  <option value="curve">🌀 柱面弧幕 / 环幕 (内弧环抱 / 外弧环绕)</option>
                  <option value="bowl">🥣 沉浸式碗幕 (下沉式地幕+弧壁沉浸空间)</option>
                  <option value="dome">🪐 穹幕 / 半球幕 / 天顶幕 (Dome 穹顶)</option>
                </select>
              </div>

              <!-- 排布与安装姿态 -->
              <div class="calc-input-group">
                <label>投影机阵列布局方式</label>
                <select id="pb_layout" onchange="onPbLayoutChange(); runCalcProjBlend();">
                  <option value="1xN" selected>↔️ 横向单排 (1 行 × N 列，超宽幅)</option>
                  <option value="Nx1">↕️ 竖向单列 (N 行 × 1 列，高挑幅/瀑布屏)</option>
                  <option value="MxN">🔲 矩阵网格 (M 行 × N 列，巨幕/多通道网格)</option>
                </select>
              </div>

              <div class="calc-input-group">
                <label>投影机安装姿态</label>
                <select id="pb_orient" onchange="runCalcProjBlend()">
                  <option value="landscape" selected>横装标准 (Landscape 宽大于高)</option>
                  <option value="portrait">竖装旋转 90° (Portrait 高大于宽)</option>
                </select>
              </div>

              <!-- 单机分辨率 -->
              <div class="calc-input-group">
                <label>单台投影机物理分辨率</label>
                <select id="pb_res" onchange="runCalcProjBlend()">
                  <option value="1920,1200" selected>1920 × 1200 (WUXGA 工程高分)</option>
                  <option value="1920,1080">1920 × 1080 (FHD 1080P 全高清)</option>
                  <option value="3840,2160">3840 × 2160 (4K UHD 超清)</option>
                  <option value="4096,2160">4096 × 2160 (DCI 4K 影院级)</option>
                  <option value="2560,1600">2560 × 1600 (WQXGA 宽屏)</option>
                </select>
              </div>

              <!-- 列数与行数 -->
              <div class="calc-input-group" id="pb_cols_wrap">
                <label id="pb_cols_label">横向融合投影台数 (列数 N)</label>
                <input type="number" id="pb_cols" value="3" min="1" max="32" oninput="runCalcProjBlend()">
              </div>

              <div class="calc-input-group" id="pb_rows_wrap" style="display: none;">
                <label id="pb_rows_label">纵向融合投影台数 (行数 M)</label>
                <input type="number" id="pb_rows" value="2" min="1" max="16" oninput="runCalcProjBlend()">
              </div>

              <!-- 重叠率 -->
              <div class="calc-input-group" id="pb_overlap_x_wrap">
                <label>水平横向重叠比例 (%)</label>
                <input type="number" id="pb_overlap_x" value="15" min="5" max="40" step="1" oninput="runCalcProjBlend()">
              </div>

              <div class="calc-input-group" id="pb_overlap_y_wrap" style="display: none;">
                <label>垂直纵向重叠比例 (%)</label>
                <input type="number" id="pb_overlap_y" value="15" min="5" max="40" step="1" oninput="runCalcProjBlend()">
              </div>

              <!-- 单机画面或屏幕尺寸输入区 (动态切换) -->
              <!-- 1. 平面幕专有输入 -->
              <div class="calc-input-group pb-shape-param pb-param-flat">
                <label>单台有效投射画面宽度 (米)</label>
                <input type="number" id="pb_single_w" value="4.0" step="0.1" min="0.5" oninput="runCalcProjBlend()">
              </div>

              <!-- 2. 弧幕专有输入 -->
              <div class="calc-input-group pb-shape-param pb-param-curve" style="display: none;">
                <label>弧幕类型与环抱方向</label>
                <select id="pb_curve_type" onchange="runCalcProjBlend()">
                  <option value="inner" selected>内弧幕 (观众位于弧内，沉浸环抱)</option>
                  <option value="outer">外弧幕 (观众位于弧外，圆弧外立面)</option>
                </select>
              </div>
              <div class="calc-input-group pb-shape-param pb-param-curve" style="display: none;">
                <label>弧幕水平展开弧长 (米)</label>
                <input type="number" id="pb_curve_arc" value="12.0" step="0.5" min="1" oninput="runCalcProjBlend()">
              </div>
              <div class="calc-input-group pb-shape-param pb-param-curve" style="display: none;">
                <label>弧幕圆心角 / 环抱视场角 (°)</label>
                <select id="pb_curve_angle" onchange="runCalcProjBlend()">
                  <option value="90">90° (直角微弧)</option>
                  <option value="120" selected>120° (主流黄金沉浸宽弧幕)</option>
                  <option value="150">150° (深弧幕)</option>
                  <option value="180">180° (半环幕)</option>
                  <option value="270">270° (U型三折环幕)</option>
                  <option value="360">360° (全景封闭环幕)</option>
                </select>
              </div>
              <div class="calc-input-group pb-shape-param pb-param-curve" style="display: none;">
                <label>弧幕物理高度 (米)</label>
                <input type="number" id="pb_curve_h" value="3.5" step="0.1" min="0.5" oninput="runCalcProjBlend()">
              </div>

              <!-- 3. 碗幕专有输入 -->
              <div class="calc-input-group pb-shape-param pb-param-bowl" style="display: none;">
                <label>碗口上缘直径 (米)</label>
                <input type="number" id="pb_bowl_d1" value="8.0" step="0.5" min="2" oninput="runCalcProjBlend()">
              </div>
              <div class="calc-input-group pb-shape-param pb-param-bowl" style="display: none;">
                <label>碗底地面直径 (米，平底地幕)</label>
                <input type="number" id="pb_bowl_d2" value="4.0" step="0.5" min="0" oninput="runCalcProjBlend()">
              </div>
              <div class="calc-input-group pb-shape-param pb-param-bowl" style="display: none;">
                <label>碗幕下沉深度 / 垂直高度 (米)</label>
                <input type="number" id="pb_bowl_h" value="3.0" step="0.2" min="1" oninput="runCalcProjBlend()">
              </div>

              <!-- 4. 穹幕专有输入 -->
              <div class="calc-input-group pb-shape-param pb-param-dome" style="display: none;">
                <label>穹幕球体内直径 (米)</label>
                <input type="number" id="pb_dome_diam" value="8.0" step="0.5" min="2" oninput="runCalcProjBlend()">
              </div>
              <div class="calc-input-group pb-shape-param pb-param-dome" style="display: none;">
                <label>穹顶倾角与形态</label>
                <select id="pb_dome_tilt" onchange="runCalcProjBlend()">
                  <option value="0" selected>0° 水平天幕 (天顶水平穹顶)</option>
                  <option value="15">15° 缓倾斜球幕</option>
                  <option value="30">30° 标准倾斜飞行影院球幕</option>
                  <option value="45">45° 深度俯冲沉浸穹幕</option>
                  <option value="90">90° 垂直立式半球幕</option>
                </select>
              </div>
              <div class="calc-input-group pb-shape-param pb-param-dome" style="display: none;">
                <label>穹幕覆盖视场角 FOV (°)</label>
                <select id="pb_dome_fov" onchange="runCalcProjBlend()">
                  <option value="180" selected>180° (标准半球穹幕)</option>
                  <option value="160">160° (视网膜舒适穹顶)</option>
                  <option value="210">210° (超宽全包围深球幕)</option>
                </select>
              </div>

              <!-- 投影机流明与幕布增益 (通用) -->
              <div class="calc-input-group">
                <label>单台投影机标称流明 (Lm)</label>
                <input type="number" id="pb_lumen" value="10000" step="1000" min="2000" oninput="runCalcProjBlend()">
              </div>
              <div class="calc-input-group">
                <label>幕布反射光学增益 (Gain)</label>
                <input type="number" id="pb_gain" value="1.0" step="0.1" min="0.5" max="2.5" oninput="runCalcProjBlend()">
              </div>
            </div>

            <!-- 统计结果卡片 (精细化 8 个指标) -->
            <div class="calc-result-box" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));">
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_total_px">5184 × 1200 px</div>
                <div class="calc-stat-label">融合后总画布输出分辨率</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_overlap_px">288 px (0.60m)</div>
                <div class="calc-stat-label">水平/垂直重叠带像素与尺寸</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val success" id="pb_res_phys_size">10.80m × 2.50m (27.0m²)</div>
                <div class="calc-stat-label">屏幕展开物理尺寸 / 总面积</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_geo_extra">R=5.73m 弦长11.07m</div>
                <div class="calc-stat-label">特殊几何特性 (半径/弦长/母线)</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_pitch">2.08 mm (12.2 PPI)</div>
                <div class="calc-stat-label">等效像素物理点距 (Pitch) / PPI</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_lux">667 Lux (212 Nit)</div>
                <div class="calc-stat-label">整屏平均反射照度与亮度</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_total_units" style="color: #f59e0b;">3 台 (1行×3列)</div>
                <div class="calc-stat-label">投影机总台数与排布</div>
              </div>
              <div class="calc-stat">
                <div class="calc-stat-val" id="pb_res_blend_box">17×17 网格 (4通道融合器)</div>
                <div class="calc-stat-label">硬件融合通道数与校正建议</div>
              </div>
            </div>

            <div class="calc-action-bar">
              <button type="button" class="btn-calc-import-quote" onclick="importProjBlendToQuote()" title="将工程投影机、异形几何融合处理器、定制幕布一键导入报价清单">
                <span>➕ 导入工程报价单</span>
                <span class="btn-subtext" id="pb_btn_quote_subtext">(工程投影机 + 纯硬件融合器 + 定制工程幕)</span>
              </button>
            </div>

            <div class="calc-note-box" id="pb_note_box">
              📐 <strong>工程几何校正与羽化融合建议：</strong><span id="pb_note_text">重叠区域建议保持在 15%~20%，羽化渐变函数采用 S 型非线性 Gamma 曲线，避免接缝处亮暗交替。</span>
            </div>
          </div>'''

# 寻找原 HTML 中的 1.3 投影投射计算器 到 1.5 LCD 拼接计算器 之间的代码
pattern_tools = re.compile(
    r'<!-- 1\.3 投影投射计算器 -->[\s\S]*?(?=<!-- 1\.5 LCD 拼接计算器 -->)',
    re.MULTILINE
)

assert pattern_tools.search(content), "Cannot find tool_proj_throw & blend HTML block"
content = pattern_tools.sub(new_html_tools + '\n\n          ', content)
print("Replaced HTML templates successfully.")

# 3. 准备新的 JS 算法代码
new_js_tools = '''    // 辅助: 增益预设联动
    window.applyPtGainPreset = function() {
      const sel = document.getElementById('pt_gain_preset');
      const input = document.getElementById('pt_gain');
      if (!sel || !input) return;
      if (sel.value === 'custom') {
        input.style.display = 'block';
      } else {
        input.style.display = 'none';
        input.value = sel.value;
      }
      runCalcProjThrow();
    };

    // 1.3 投影投射计算器全面升级 (v3.1)
    window.runCalcProjThrow = function() {
      const resVal = document.getElementById('pt_res')?.value || '1920,1200,1.6';
      const customWrap = document.getElementById('pt_custom_res_wrap');
      let resW = 1920, resH = 1200, ratio = 1.6;

      if (resVal === 'custom') {
        if (customWrap) customWrap.style.display = 'block';
        resW = parseInt(document.getElementById('pt_custom_w')?.value) || 1920;
        resH = parseInt(document.getElementById('pt_custom_h')?.value) || 1200;
        ratio = resW / (resH || 1);
      } else {
        if (customWrap) customWrap.style.display = 'none';
        const parts = resVal.split(',');
        resW = parseInt(parts[0]) || 1920;
        resH = parseInt(parts[1]) || 1200;
        ratio = parseFloat(parts[2]) || (resW / resH);
      }

      const w = Math.max(0.2, parseFloat(document.getElementById('pt_w')?.value) || 5.0);
      const trStr = (document.getElementById('pt_tr')?.value || '1.2-1.8').trim();
      const lumen = parseFloat(document.getElementById('pt_lumen')?.value) || 10000;
      const gain = parseFloat(document.getElementById('pt_gain')?.value) || 1.0;
      const eff = parseFloat(document.getElementById('pt_eff')?.value) || 0.8;

      const h = w / ratio;
      const diagM = Math.sqrt(w * w + h * h);
      const diagIn = Math.round(diagM / 0.0254);
      const area = w * h;

      // 像素物理尺寸与密度
      const pitchW = (w * 1000) / resW;
      const pitchH = (h * 1000) / resH;
      const ppi = Math.sqrt(resW * resW + resH * resH) / diagIn;
      const totalPixels = resW * resH;

      // 镜头投射距离范围
      let dMin = w * 1.2, dMax = w * 1.8;
      if (trStr.includes('-')) {
        const parts = trStr.split('-').map(Number);
        if (!isNaN(parts[0])) dMin = w * parts[0];
        if (!isNaN(parts[1])) dMax = w * parts[1];
      } else {
        const trSingle = parseFloat(trStr) || 1.2;
        dMin = w * trSingle;
        dMax = dMin;
      }

      // 照度与亮度
      const lux = Math.round((lumen * eff * gain) / area);
      const nit = Math.round(lux / Math.PI);

      let luxDesc = '充沛/高对比';
      if (lux < 250) luxDesc = '需暗室暗光环境';
      else if (lux < 450) luxDesc = '标准商务/展厅舒适';
      else if (lux > 700) luxDesc = '极高通透/抗光强';

      // 镜头分类
      const minTR = dMin / w;
      let lensType = '标准工程变焦镜头';
      if (minTR < 0.45) lensType = '超短焦反射式镜头 (TR<0.45)';
      else if (minTR < 1.0) lensType = '短焦光学镜头 (0.45~1.0)';
      else if (minTR > 2.2) lensType = '长焦/超长焦光学镜头 (>2.2)';

      // 视距建议
      const retinaDistM = (pitchW / 1000) * 3438; // 1角分视力极限
      const recMinDist = (1.5 * h).toFixed(1);
      const recMaxDist = (3.0 * h).toFixed(1);

      // DOM 更新
      const elSize = document.getElementById('pt_res_size');
      if (elSize) elSize.textContent = `${w.toFixed(2)}m × ${h.toFixed(2)}m (${diagIn} 英寸)`;
      const elArea = document.getElementById('pt_res_area');
      if (elArea) elArea.textContent = `${area.toFixed(2)} m²`;
      const elPitch = document.getElementById('pt_res_pitch');
      if (elPitch) elPitch.textContent = `${pitchW.toFixed(2)} mm × ${pitchH.toFixed(2)} mm`;
      const elPpi = document.getElementById('pt_res_ppi');
      if (elPpi) elPpi.textContent = `${ppi.toFixed(1)} PPI (${(totalPixels / 10000).toFixed(0)}万点)`;
      const elDist = document.getElementById('pt_res_dist');
      if (elDist) elDist.textContent = dMin === dMax ? `${dMin.toFixed(2)} 米 (固定定焦)` : `${dMin.toFixed(2)} 米 ~ ${dMax.toFixed(2)} 米`;
      const elLux = document.getElementById('pt_res_lux');
      if (elLux) elLux.textContent = `${lux} Lux (${luxDesc})`;
      const elNit = document.getElementById('pt_res_nit');
      if (elNit) elNit.textContent = `${nit} Nit (cd/m²)`;
      const elLens = document.getElementById('pt_res_lens');
      if (elLens) elLens.textContent = lensType;

      const notePitch = document.getElementById('pt_note_pitch');
      if (notePitch) notePitch.textContent = `${pitchW.toFixed(2)}mm`;
      const noteDist = document.getElementById('pt_note_viewdist');
      if (noteDist) noteDist.textContent = `${retinaDistM.toFixed(1)}米`;
      const noteRec = document.getElementById('pt_note_rec_view');
      if (noteRec) noteRec.textContent = `${recMinDist}米 ~ ${recMaxDist}米`;
    };

    // 辅助: 融合排布形态与布局UI联动切换
    window.onPbShapeChange = function() {
      const shape = document.getElementById('pb_shape')?.value || 'flat';
      document.querySelectorAll('.pb-shape-param').forEach(el => el.style.display = 'none');
      if (shape === 'flat') {
        document.querySelectorAll('.pb-param-flat').forEach(el => el.style.display = 'block');
      } else if (shape === 'curve') {
        document.querySelectorAll('.pb-param-curve').forEach(el => el.style.display = 'block');
      } else if (shape === 'bowl') {
        document.querySelectorAll('.pb-param-bowl').forEach(el => el.style.display = 'block');
      } else if (shape === 'dome') {
        document.querySelectorAll('.pb-param-dome').forEach(el => el.style.display = 'block');
      }
    };

    window.onPbLayoutChange = function() {
      const layout = document.getElementById('pb_layout')?.value || '1xN';
      const colsWrap = document.getElementById('pb_cols_wrap');
      const rowsWrap = document.getElementById('pb_rows_wrap');
      const colsLabel = document.getElementById('pb_cols_label');
      const rowsLabel = document.getElementById('pb_rows_label');
      const overlapYWrap = document.getElementById('pb_overlap_y_wrap');

      if (layout === '1xN') {
        if (colsWrap) colsWrap.style.display = 'block';
        if (rowsWrap) rowsWrap.style.display = 'none';
        if (colsLabel) colsLabel.textContent = '横向融合投影台数 (列数 N)';
        if (overlapYWrap) overlapYWrap.style.display = 'none';
      } else if (layout === 'Nx1') {
        if (colsWrap) colsWrap.style.display = 'none';
        if (rowsWrap) rowsWrap.style.display = 'block';
        if (rowsLabel) rowsLabel.textContent = '竖向融合投影台数 (行数 N)';
        if (overlapYWrap) overlapYWrap.style.display = 'block';
      } else { // MxN 矩阵
        if (colsWrap) colsWrap.style.display = 'block';
        if (rowsWrap) rowsWrap.style.display = 'block';
        if (colsLabel) colsLabel.textContent = '矩阵列数 (水平 Cols N)';
        if (rowsLabel) rowsLabel.textContent = '矩阵行数 (垂直 Rows M)';
        if (overlapYWrap) overlapYWrap.style.display = 'block';
      }
    };

    // 1.4 投影边缘融合与多屏异形幕综合计算器 (v3.1)
    window.runCalcProjBlend = function() {
      const shape = document.getElementById('pb_shape')?.value || 'flat';
      const layout = document.getElementById('pb_layout')?.value || '1xN';
      const orient = document.getElementById('pb_orient')?.value || 'landscape';
      const rawRes = (document.getElementById('pb_res')?.value || '1920,1200').split(',').map(Number);
      
      // 处理横竖装姿态
      let resW = rawRes[0] || 1920;
      let resH = rawRes[1] || 1200;
      if (orient === 'portrait') {
        // 竖装 90 度旋转，分辨率转置
        resW = rawRes[1] || 1200;
        resH = rawRes[0] || 1920;
      }

      // 台数与排布
      let cols = 1, rows = 1;
      if (layout === '1xN') {
        cols = Math.max(1, parseInt(document.getElementById('pb_cols')?.value) || 3);
        rows = 1;
      } else if (layout === 'Nx1') {
        cols = 1;
        rows = Math.max(1, parseInt(document.getElementById('pb_rows')?.value) || 3);
      } else { // MxN
        cols = Math.max(1, parseInt(document.getElementById('pb_cols')?.value) || 3);
        rows = Math.max(1, parseInt(document.getElementById('pb_rows')?.value) || 2);
      }
      const totalUnits = cols * rows;

      // 重叠率
      const overlapPctX = (parseFloat(document.getElementById('pb_overlap_x')?.value) || 15) / 100;
      const overlapPctY = (parseFloat(document.getElementById('pb_overlap_y')?.value) || 15) / 100;

      // 融合重叠像素
      const overlapPxX = cols > 1 ? Math.round(resW * overlapPctX) : 0;
      const overlapPxY = rows > 1 ? Math.round(resH * overlapPctY) : 0;

      // 总画布物理输出分辨率
      const totalPxW = (cols * resW) - ((cols - 1) * overlapPxX);
      const totalPxH = (rows * resH) - ((rows - 1) * overlapPxY);
      const totalPixels = totalPxW * totalPxH;

      // 物理尺寸与特殊几何特性计算
      let physW = 0, physH = 0, area = 0;
      let geoExtraStr = '';
      let meshSuggestion = '17×17 网格校正';
      let noteStr = '';

      if (shape === 'flat') {
        // 平面幕
        const singleW = parseFloat(document.getElementById('pb_single_w')?.value) || 4.0;
        const singleH = singleW * (resH / resW);
        const overlapMX = singleW * overlapPctX;
        const overlapMY = singleH * overlapPctY;

        physW = (cols * singleW) - ((cols - 1) * overlapMX);
        physH = (rows * singleH) - ((rows - 1) * overlapMY);
        area = physW * physH;
        geoExtraStr = `平面直幕 (画幅 ${(physW / physH).toFixed(2)}:1)`;
        meshSuggestion = (cols > 4 || rows > 2) ? '17×17 网格 (大型多机墙)' : '9×9 网格 (平面标准)';
        noteStr = `平面幕边缘融合重叠率保持在 15%~20%，羽化采用 S 曲线平滑过度，无极消隐硬边缘。`;

      } else if (shape === 'curve') {
        // 柱面弧幕 / 环幕
        const arcL = parseFloat(document.getElementById('pb_curve_arc')?.value) || 12.0;
        const angleDeg = parseFloat(document.getElementById('pb_curve_angle')?.value) || 120;
        const hVal = parseFloat(document.getElementById('pb_curve_h')?.value) || 3.5;
        const curveType = document.getElementById('pb_curve_type')?.value || 'inner';

        const angleRad = (angleDeg * Math.PI) / 180;
        const radius = arcL / angleRad;
        const chord = 2 * radius * Math.sin(angleRad / 2);
        const sagitta = radius * (1 - Math.cos(angleRad / 2));

        physW = arcL;
        physH = hVal;
        area = arcL * hVal;

        geoExtraStr = `R=${radius.toFixed(2)}m 弦长${chord.toFixed(2)}m 拱高${sagitta.toFixed(2)}m`;
        meshSuggestion = '17×17 或 33×33 极坐标曲面网格';
        noteStr = `${curveType === 'inner' ? '内弧环抱幕' : '外弧幕'}开角 ${angleDeg}°，建议投影机沿弧形法线方向径向等距吊装，重叠带保持在 18% 左右以抵消曲面拉伸畸变。`;

      } else if (shape === 'bowl') {
        // 沉浸式碗幕 (下沉地幕+弧壁)
        const d1 = parseFloat(document.getElementById('pb_bowl_d1')?.value) || 8.0;
        const d2 = parseFloat(document.getElementById('pb_bowl_d2')?.value) || 4.0;
        const bowlH = parseFloat(document.getElementById('pb_bowl_h')?.value) || 3.0;

        const slantL = Math.sqrt(Math.pow((d1 - d2) / 2, 2) + Math.pow(bowlH, 2));
        const sideArea = Math.PI * ((d1 + d2) / 2) * slantL;
        const bottomArea = Math.PI * Math.pow(d2 / 2, 2);
        area = sideArea + bottomArea;

        physW = Math.PI * d1; // 展宽
        physH = slantL + (d2 / 2);

        geoExtraStr = `斜母线${slantL.toFixed(2)}m (壁${sideArea.toFixed(1)}m²+底${bottomArea.toFixed(1)}m²)`;
        meshSuggestion = '33×33 自由曲面双曲度网格校正';
        noteStr = `碗幕包含下沉斜壁与碗底水平面，投影光路大角度俯冲倾斜，必须配置工业级非线性几何校正算法与光学暗场消阶。`;

      } else if (shape === 'dome') {
        // 穹幕 / 半球幕 / 天顶幕
        const diam = parseFloat(document.getElementById('pb_dome_diam')?.value) || 8.0;
        const tilt = document.getElementById('pb_dome_tilt')?.value || '0';
        const fov = parseFloat(document.getElementById('pb_dome_fov')?.value) || 180;
        const r = diam / 2;

        let domeArea = 2 * Math.PI * r * r; // 默认180度半球
        if (fov < 180) {
          const capH = r * (1 - Math.cos((fov / 2) * Math.PI / 180));
          domeArea = 2 * Math.PI * r * capH;
        } else if (fov > 180) {
          const extraH = r * (1 - Math.cos((fov / 2) * Math.PI / 180));
          domeArea = 2 * Math.PI * r * extraH;
        }
        area = domeArea;
        physW = Math.PI * r;
        physH = Math.PI * r;

        geoExtraStr = `球径${diam}m 半径${r.toFixed(2)}m (倾角${tilt}°)`;
        meshSuggestion = '空间球面极坐标 + 天顶消隐算法';
        noteStr = `穹幕通常采用环向多机切片 + 天顶心打法或双鱼眼拼接，需重点消除天顶汇聚极点的光斑重叠累加效应。`;
      }

      // 像素点距与 PPI
      const pitchMm = (physW * 1000) / totalPxW;
      const ppi = Math.sqrt(totalPxW * totalPxW + totalPxH * totalPxH) / (Math.sqrt(physW * physW + physH * physH) / 0.0254);

      // 光学照度与亮度估算
      const lumen = parseFloat(document.getElementById('pb_lumen')?.value) || 10000;
      const gain = parseFloat(document.getElementById('pb_gain')?.value) || 1.0;
      // 融合去重叠有效光能利用
      const effLumen = (totalPixels / (resW * resH)) * lumen * 0.82;
      const lux = Math.round((effLumen * gain) / (area || 1));
      const nit = Math.round(lux / Math.PI);

      // 硬件融合器规格
      const procChannels = totalUnits;
      const procDesc = `${meshSuggestion} (${procChannels}通道融合器)`;

      // 重叠带文本
      let overlapTxt = '';
      if (cols > 1 && rows > 1) {
        overlapTxt = `横${overlapPxX}px 纵${overlapPxY}px`;
      } else if (cols > 1) {
        overlapTxt = `${overlapPxX} px (${((physW / totalPxW) * overlapPxX).toFixed(2)}m)`;
      } else {
        overlapTxt = `${overlapPxY} px (${((physH / totalPxH) * overlapPxY).toFixed(2)}m)`;
      }

      // DOM 刷新
      const elTotPx = document.getElementById('pb_res_total_px');
      if (elTotPx) elTotPx.textContent = `${totalPxW} × ${totalPxH} px`;
      const elOverlap = document.getElementById('pb_res_overlap_px');
      if (elOverlap) elOverlap.textContent = overlapTxt;
      const elPhys = document.getElementById('pb_res_phys_size');
      if (elPhys) elPhys.textContent = `${physW.toFixed(2)}m × ${physH.toFixed(2)}m (${area.toFixed(1)}m²)`;
      const elGeo = document.getElementById('pb_res_geo_extra');
      if (elGeo) elGeo.textContent = geoExtraStr;
      const elPitch = document.getElementById('pb_res_pitch');
      if (elPitch) elPitch.textContent = `${pitchMm.toFixed(2)} mm (${ppi.toFixed(1)} PPI)`;
      const elLux = document.getElementById('pb_res_lux');
      if (elLux) elLux.textContent = `${lux} Lux (${nit} Nit)`;
      const elUnits = document.getElementById('pb_res_total_units');
      if (elUnits) elUnits.textContent = `${totalUnits} 台 (${rows}行×${cols}列 ${orient === 'portrait' ? '竖投' : '横投'})`;
      const elBox = document.getElementById('pb_res_blend_box');
      if (elBox) elBox.textContent = procDesc;

      const noteText = document.getElementById('pb_note_text');
      if (noteText) noteText.textContent = noteStr;

      const subQuote = document.getElementById('pb_btn_quote_subtext');
      if (subQuote) {
        const shapeNameMap = { flat: '平面幕', curve: '弧幕', bowl: '碗幕', dome: '穹幕' };
        subQuote.textContent = `(${totalUnits}台工程机 + ${procChannels}通道融合器 + ${shapeNameMap[shape] || ''})`;
      }
    };

    // 1.5 LCD拼接计算
'''

pattern_js = re.compile(
    r'window\.runCalcProjThrow\s*=\s*function\(\)\s*\{[\s\S]*?(?=window\.runCalcLcd\s*=\s*function\(\))',
    re.MULTILINE
)

assert pattern_js.search(content), "Cannot find JS runCalcProjThrow & runCalcProjBlend block"
content = pattern_js.sub(new_js_tools, content)
print("Replaced JS functions successfully.")

# 4. 更新报价单导入函数 (importProjBlendToQuote)
new_import_quote = '''    // 3. 投影融合计算器导入 (v3.1 增强支持平面/弧幕/碗幕/穹幕及竖投)
    window.importProjBlendToQuote = function() {
      const shape = document.getElementById('pb_shape')?.value || 'flat';
      const layout = document.getElementById('pb_layout')?.value || '1xN';
      const orient = document.getElementById('pb_orient')?.value || 'landscape';
      const rawRes = (document.getElementById('pb_res')?.value || '1920,1200').split(',').map(Number);
      let resW = rawRes[0] || 1920, resH = rawRes[1] || 1200;
      if (orient === 'portrait') {
        resW = rawRes[1] || 1200;
        resH = rawRes[0] || 1920;
      }

      let cols = 1, rows = 1;
      if (layout === '1xN') {
        cols = Math.max(1, parseInt(document.getElementById('pb_cols')?.value) || 3);
        rows = 1;
      } else if (layout === 'Nx1') {
        cols = 1;
        rows = Math.max(1, parseInt(document.getElementById('pb_rows')?.value) || 3);
      } else {
        cols = Math.max(1, parseInt(document.getElementById('pb_cols')?.value) || 3);
        rows = Math.max(1, parseInt(document.getElementById('pb_rows')?.value) || 2);
      }
      const totalUnits = cols * rows;
      const lumen = parseInt(document.getElementById('pb_lumen')?.value) || 10000;

      const totalPxStr = document.getElementById('pb_res_total_px')?.textContent || '';
      const physSizeStr = document.getElementById('pb_res_phys_size')?.textContent || '';
      const geoExtra = document.getElementById('pb_res_geo_extra')?.textContent || '';

      const shapeNames = {
        flat: '平面直幕系统',
        curve: '柱面环形弧幕系统',
        bowl: '双曲面碗幕沉浸系统',
        dome: '半球穹顶天幕系统'
      };
      const curShapeName = shapeNames[shape] || '工程投影大屏系统';

      // 单台投影价格预估 (根据流明)
      let projUnitPrice = 28000;
      if (lumen >= 15000) projUnitPrice = 58000;
      else if (lumen >= 12000) projUnitPrice = 36000;
      else if (lumen >= 8000) projUnitPrice = 25000;

      // 融合器单价
      const blendUnitCost = 4500;
      const blendTotalPrice = Math.max(12000, totalUnits * blendUnitCost);

      const itemsToImport = [
        {
          name: '高流明激光工程投影机',
          spec: `${lumen}流明 激光光源，单机分辨率 ${resW}×${resH}，${orient === 'portrait' ? '竖装90°旋转' : '标准横装'}，${rows}行×${cols}列阵列融合，总画幅 ${totalPxStr}`,
          price: projUnitPrice,
          qty: totalUnits,
          remark: `v3.1投影融合计算器核算生成 (${curShapeName})`
        },
        {
          name: '纯硬件多通道曲面几何校正融合器',
          spec: `支持 ${totalUnits} 通道 4K 输入/输出，具备多维非线性网格曲面几何校正与高精度光学边缘羽化功能 (${geoExtra})`,
          price: blendTotalPrice,
          qty: 1,
          remark: `支持${curShapeName}硬件实时几何变形`
        },
        {
          name: `定制${curShapeName}`,
          spec: `根据现场工程深化尺寸设计，物理规格：${physSizeStr}，增益 1.0~1.2，含定制骨架与专业反射扩散涂层`,
          price: 18000,
          qty: 1,
          remark: '定制工程屏幕系统核算'
        },
        {
          name: '万向微调工程投影吊架',
          spec: `承重 ≥ 40kg，支持三维万向无级角度微调与俯仰角锁紧，适应异形光路投射`,
          price: 850,
          qty: totalUnits,
          remark: '投影安装微调五金套件'
        }
      ];

      window.importCalcToQuote(itemsToImport, true);
    };

    // 4. LCD 拼接计算器导入'''

pattern_import = re.compile(
    r'// 3\. 投影融合计算器导入[\s\S]*?(?=// 4\. LCD 拼接计算器导入)',
    re.MULTILINE
)
assert pattern_import.search(content), "Cannot find importProjBlendToQuote block"
content = pattern_import.sub(new_import_quote + '\n\n    ', content)
print("Replaced importProjBlendToQuote successfully.")

# 5. 更新搜索工具箱词条 (toolkitTools)
old_search_snippet = '''        { title: '投影投射距离与镜头选型计算器', desc: '投射比 TR、安装距离范围、幕面反射照度 Lux', cat: 'display', id: 'tool_proj_throw' },
        { title: '投影边缘融合与重叠像素计算器', desc: '融合带宽度、重叠像素、总输出分辨率、几何校正', cat: 'display', id: 'tool_proj_blend' },'''

new_search_snippet = '''        { title: '投影投射距离、镜头选型与像素物理尺寸计算器', desc: '投射比 TR、画面物理面积、单像素物理尺寸/点距 Pitch、PPI像素密度、安装距离、反射照度 Lux与亮度 Nit', cat: 'display', id: 'tool_proj_throw' },
        { title: '投影边缘融合与多屏异形幕综合计算器', desc: '支持横向/竖向/矩阵布局，支持常规平面幕、柱面弧幕/环幕、沉浸式碗幕、半球穹幕/天幕，重叠像素、总分辨率、展开物理面积、像素点距、曲面网格校正', cat: 'display', id: 'tool_proj_blend' },'''

content = content.replace(old_search_snippet, new_search_snippet)
print("Replaced toolkit search items successfully.")

# 6. 下载文件名更新为 3.1
content = content.replace(
    "a.download = '多媒体工程师全栈手册_查询系统.html';",
    "a.download = '多媒体工程师全栈手册_查询系统v3.1.html';"
)

# 7. 写入目标文件 v3.1.html
with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Target file created:", target_file)
print("Target file size:", os.path.getsize(target_file), "bytes")
