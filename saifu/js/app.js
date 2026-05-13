/**
 * 赛赋 SaiFu — 前端交互逻辑
 * v2: 适配9段通用表单（覆盖全学科）
 */

// ═══════════════════════════════════════
// 配置 — 部署时改这里
// ═══════════════════════════════════════
const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://saifu-backend-pk86.onrender.com';

const MATCH_TIMEOUT = 300000; // 300 秒超时（搜索+多轮AI调用需要时间）

// ═══════════════════════════════════════
// 免费试用次数限制 + 多平台密钥 — 独立模块
// ═══════════════════════════════════════
const FREE_LIMIT = 3;
const STORAGE_KEY_USAGE = 'saifu_usage_count';
const STORAGE_KEY_LLM_CONFIG = 'saifu_llm_config'; // 用户完整 LLM 配置（JSON）
const STORAGE_KEY_ADMIN = 'saifu_is_admin';

// ── 平台预设 ──
const LLM_PROVIDERS = {
  deepseek: { name: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  doubao:   { name: '火山引擎（豆包）', base_url: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-seed-2-0-lite-260428' },
  openai:   { name: 'OpenAI', base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  custom:   { name: '自定义', base_url: '', model: '' },
};

// ── 管理员后门 ──
(async function initAdminBypass() {
  const params = new URLSearchParams(window.location.search);
  const input = params.get('admin');
  if (!input) return;
  if (input === 'off') {
    localStorage.removeItem(STORAGE_KEY_ADMIN);
    window.location.replace(window.location.pathname);
    return;
  }
  const buf = new TextEncoder().encode(input);
  const raw = await crypto.subtle.digest('SHA-256', buf);
  const hex = Array.from(new Uint8Array(raw)).map(b => b.toString(16).padStart(2, '0')).join('');
  if (hex === 'fea2b9dcfc927a0c9d6fad5781f64b60754dce0ea76bbeca9eac202c553b049f') {
    localStorage.setItem(STORAGE_KEY_ADMIN, '1');
    window.location.replace(window.location.pathname);
  }
})();

function isAdmin() {
  try { return localStorage.getItem(STORAGE_KEY_ADMIN) === '1'; } catch (e) { return false; }
}
function getUsageCount() {
  try { return parseInt(localStorage.getItem(STORAGE_KEY_USAGE) || '0', 10); } catch (e) { return 0; }
}
function incrementUsage() {
  if (isAdmin()) return;
  if (getUserLLMConfig()) return; // 用自己的 Key 不消耗免费次数
  try {
    localStorage.setItem(STORAGE_KEY_USAGE, String(getUsageCount() + 1));
  } catch (e) { /* ignore */ }
}

// ── LLM 配置存取 ──
function getUserLLMConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_LLM_CONFIG);
    if (!raw) return null;
    const cfg = JSON.parse(raw);
    if (!cfg.api_key) return null;
    return cfg;
  } catch (e) { return null; }
}
function saveUserLLMConfig(cfg) {
  try { localStorage.setItem(STORAGE_KEY_LLM_CONFIG, JSON.stringify(cfg)); } catch (e) {}
}
function clearUserLLMConfig() {
  try { localStorage.removeItem(STORAGE_KEY_LLM_CONFIG); } catch (e) {}
}

/**
 * 获取请求中应附带的对象（null = 用服务器 Key）
 * @returns {object|null} { user_api_key, user_api_base_url, user_api_model } 或 null
 */
function getUserLLMForRequest() {
  if (isAdmin()) return null;
  const count = getUsageCount();
  if (count < FREE_LIMIT) return null;
  const cfg = getUserLLMConfig();
  if (!cfg) return null;
  return {
    user_api_key: cfg.api_key,
    user_api_base_url: cfg.base_url || '',
    user_api_model: cfg.model || '',
  };
}

/** 将用户 LLM 配置合并到 profile/userData 中 */
function attachLLMConfig(data) {
  const cfg = getUserLLMForRequest();
  if (cfg) Object.assign(data, cfg);
}

// ── 次数检查 ──
function checkUsageAndPrompt() {
  return new Promise((resolve) => {
    if (isAdmin()) { resolve(true); return; }
    const count = getUsageCount();
    const cfg = getUserLLMConfig();
    if (count < FREE_LIMIT || cfg) { resolve(true); return; }
    // 超限且无配置 → 弹窗
    showApiKeyModal(resolve, false);
  });
}

// ── API Key 弹窗（支持 bankrupt 模式）──
let _apiKeyModalResolve = null;
let _apiKeyModalBankrupt = false;

function showApiKeyModal(resolveCallback, isBankrupt) {
  const modal = document.getElementById('apiKeyModal');
  if (!modal) { if (resolveCallback) resolveCallback(false); return; }

  _apiKeyModalResolve = resolveCallback || null;
  _apiKeyModalBankrupt = !!isBankrupt;

  // 更新标题
  const titleEl = document.getElementById('apiKeyModalTitle');
  if (titleEl) {
    titleEl.textContent = isBankrupt ? '😭 小雷已破产' : '🔐 免费次数已用完';
  }
  // 更新副标题
  const subtitleEl = document.getElementById('apiKeyModalSubtitle');
  if (subtitleEl) {
    subtitleEl.innerHTML = isBankrupt
      ? '服务器 API 余额耗尽，请使用<strong>你自己的密钥</strong>继续使用。'
      : `你已使用 <strong id="apiKeyUsageCount">${getUsageCount()}</strong>/${FREE_LIMIT} 次免费匹配。继续使用需要你自己的 API Key。`;
  }

  // 恢复已保存的配置
  const savedCfg = getUserLLMConfig();
  const providerSel = document.getElementById('apiKeyProvider');
  const keyInput = document.getElementById('apiKeyInput');
  const baseInput = document.getElementById('apiKeyBaseUrl');
  const modelInput = document.getElementById('apiKeyModel');

  if (savedCfg) {
    if (providerSel) providerSel.value = savedCfg.provider || 'custom';
    if (keyInput) keyInput.value = savedCfg.api_key || '';
    if (baseInput) baseInput.value = savedCfg.base_url || '';
    if (modelInput) modelInput.value = savedCfg.model || '';
  } else {
    if (providerSel) providerSel.value = 'deepseek';
    if (keyInput) keyInput.value = '';
    if (baseInput) baseInput.value = LLM_PROVIDERS.deepseek.base_url;
    if (modelInput) modelInput.value = LLM_PROVIDERS.deepseek.model;
  }

  modal.classList.add('show');
}
// 暴露到全局：导航栏按钮调用
window.openApiKeySettings = function() { showApiKeyModal(null, false); };

function hideApiKeyModal(cancelled) {
  const modal = document.getElementById('apiKeyModal');
  if (!modal) return;
  modal.classList.remove('show');
  if (_apiKeyModalResolve) {
    _apiKeyModalResolve(!cancelled);
    _apiKeyModalResolve = null;
  }
  _apiKeyModalBankrupt = false;
}

/** 平台切换时自动填充 base_url 和 model */
function onProviderChange() {
  const sel = document.getElementById('apiKeyProvider');
  const baseInput = document.getElementById('apiKeyBaseUrl');
  const modelInput = document.getElementById('apiKeyModel');
  if (!sel || !baseInput || !modelInput) return;
  const provider = LLM_PROVIDERS[sel.value];
  if (!provider) return;
  if (sel.value !== 'custom') {
    baseInput.value = provider.base_url;
    modelInput.value = provider.model;
  }
  // 自定义模式不清空，保留用户上次输入
}

function submitApiKey() {
  const key = (document.getElementById('apiKeyInput')?.value || '').trim();
  if (!key) { alert('请输入有效的 API Key'); return; }

  const provider = document.getElementById('apiKeyProvider')?.value || 'custom';
  const base_url = (document.getElementById('apiKeyBaseUrl')?.value || '').trim();
  const model = (document.getElementById('apiKeyModel')?.value || '').trim();

  // 非自定义模式用预设值兜底
  const preset = LLM_PROVIDERS[provider];
  const finalBaseUrl = base_url || (preset ? preset.base_url : '');
  const finalModel = model || (preset ? preset.model : '');

  saveUserLLMConfig({ provider, api_key: key, base_url: finalBaseUrl, model: finalModel });
  hideApiKeyModal(false);
}

/** 清除已保存的密钥 + 清空表单 */
function clearApiKey() {
  clearUserLLMConfig();
  // 清空表单字段
  const keyInput = document.getElementById('apiKeyInput');
  const baseInput = document.getElementById('apiKeyBaseUrl');
  const modelInput = document.getElementById('apiKeyModel');
  const providerSel = document.getElementById('apiKeyProvider');
  if (keyInput) { keyInput.value = ''; keyInput.type = 'password'; }
  if (baseInput) baseInput.value = LLM_PROVIDERS.deepseek.base_url;
  if (modelInput) modelInput.value = LLM_PROVIDERS.deepseek.model;
  if (providerSel) providerSel.value = 'deepseek';
  // 更新眼睛图标
  const eyeBtn = document.querySelector('.api-key-eye');
  if (eyeBtn) eyeBtn.textContent = '👁️';
  // 轻提示
  showToast('已清除密钥，将使用免费次数。');
}

/** 切换 API Key 显示/隐藏 */
function toggleApiKeyVisibility() {
  const input = document.getElementById('apiKeyInput');
  const eyeBtn = document.querySelector('.api-key-eye');
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (eyeBtn) eyeBtn.textContent = '🔒';
  } else {
    input.type = 'password';
    if (eyeBtn) eyeBtn.textContent = '👁️';
  }
}

/** 轻量 toast 提示 */
function showToast(msg) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 24px;border-radius:20px;font-size:13px;z-index:9999;opacity:0;transition:opacity 0.3s;pointer-events:none;';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._tid);
  toast._tid = setTimeout(() => { toast.style.opacity = '0'; }, 2000);
}
// ═══════════════════════════════════════
// 免费试用次数限制 — 模块结束
// ═══════════════════════════════════════

// ═══════════════════════════════════════
// 表单区块折叠
// ═══════════════════════════════════════
function toggleFormSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const isOpen = el.classList.contains('open');
  if (isOpen) {
    el.classList.remove('open');
  } else {
    el.classList.add('open');
  }
}

// ═══════════════════════════════════════
// 模式切换（不知道能参加什么 / 知道比赛名称）
// ═══════════════════════════════════════
let currentMode = 'discover'; // 'discover' | 'target'

function switchMode(mode) {
  // 防御：确保 mode 有效
  if (mode !== 'discover' && mode !== 'target') return;

  const discoverBtn = document.getElementById('modeDiscoverBtn');
  const targetBtn = document.getElementById('modeTargetBtn');
  const discoverForm = document.getElementById('discoverForm');
  const targetForm = document.getElementById('targetForm');
  const formHeader = document.getElementById('formHeader');
  const h2 = formHeader ? formHeader.querySelector('h2') : null;

  // 防御：关键元素缺失则报错
  if (!discoverBtn || !targetBtn || !discoverForm || !targetForm) {
    showToast('页面结构异常，请刷新后重试');
    return;
  }

  currentMode = mode;

  if (mode === 'discover') {
    discoverBtn.classList.add('active');
    targetBtn.classList.remove('active');
    discoverForm.classList.remove('form-hidden');
    targetForm.classList.add('form-hidden');
    if (h2) h2.textContent = '🎯 用户画像';
  } else {
    targetBtn.classList.add('active');
    discoverBtn.classList.remove('active');
    discoverForm.classList.add('form-hidden');
    targetForm.classList.remove('form-hidden');
    if (h2) h2.textContent = '🎯 定向调研';
  }

  // 确保在表单 tab，隐藏其他区域
  var tabFormBtn = document.getElementById('tabFormBtn');
  var tabImportBtn = document.getElementById('tabImportBtn');
  if (tabFormBtn) tabFormBtn.classList.add('active');
  if (tabImportBtn) tabImportBtn.classList.remove('active');

  var importArea = document.getElementById('importArea');
  var formArea = document.getElementById('formArea');
  var resultArea = document.getElementById('resultArea');
  var researchResultArea = document.getElementById('researchResultArea');
  var errorArea = document.getElementById('errorArea');
  var loadingArea = document.getElementById('loadingArea');

  if (importArea) importArea.style.display = 'none';
  if (formArea) formArea.style.display = 'block';
  if (resultArea) resultArea.style.display = 'none';
  if (researchResultArea) researchResultArea.style.display = 'none';
  if (errorArea) errorArea.style.display = 'none';
  if (loadingArea) loadingArea.style.display = 'none';

  updateProgress();
  updateExportHints();
}

// ═══════════════════════════════════════
// 进度条更新（根据当前模式计算）
// ═══════════════════════════════════════
function updateProgress() {
  let filled = 0;
  let total = 10; // 默认（discover 模式）

  if (currentMode === 'target') {
    // 简化表单：7 个权重点
    total = 7;
    if ((document.getElementById('target-school')?.value?.trim() || '').length > 0) filled++;
    if ((document.getElementById('target-major')?.value?.trim() || '').length > 0) filled++;
    if (document.querySelector('input[name="target-grade"]:checked')) filled++;
    if ((document.getElementById('target-competition-name')?.value?.trim() || '').length > 0) filled++;
    if ((document.getElementById('target-core-skills')?.value?.trim() || '').length > 0) filled++;
    if (document.querySelectorAll('input[name="target-goals"]:checked').length > 0) filled++;
    if (document.querySelector('input[name="target-weekly-hours"]:checked')) filled++;
  } else {
    // 完整表单：10 个权重点
    // 一、基本信息
    if ((document.getElementById('school')?.value?.trim() || '').length > 0) filled++;
    if ((document.getElementById('major')?.value?.trim() || '').length > 0) filled++;
    if (document.querySelector('input[name="grade"]:checked')) filled++;
    if (document.querySelectorAll('input[name="interests"]:checked').length > 0) filled++;

    // 二、参赛目标
    if (document.querySelectorAll('input[name="goals"]:checked').length > 0) filled++;

    // 三、专业能力
    if ((document.getElementById('core-skills')?.value?.trim() || '').length > 0) filled++;
    if (document.querySelectorAll('input[name="tech-direction"]:checked').length > 0) filled++;

    // 四、时间投入
    if (document.querySelector('input[name="weekly-hours"]:checked')) filled++;

    // 六、避免类型
    if (document.querySelectorAll('input[name="avoid"]:checked').length > 0) filled++;

    // 七、经历（有任一就算）
    if ((document.getElementById('project1')?.value?.trim() || '').length > 0) filled++;
  }

  const percent = Math.min(100, Math.round((filled / total) * 100));
  const fillEl = document.getElementById('progressFill');
  const pctEl = document.getElementById('progressPercent');
  if (fillEl) fillEl.style.width = percent + '%';
  if (pctEl) pctEl.textContent = percent + '%';
}

// 监听所有表单变化更新进度
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', updateProgress);
    el.addEventListener('input', updateProgress);
  });
  // 初始化时也跑一遍
  updateProgress();
  updateExportHints();
  renderHistoryPanel();

  // 自动恢复上次草稿（新开页面不用重新填）
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (data.school || data.major || data.grade) {
        setTimeout(() => { loadSaved(); }, 200);
      }
    }
  } catch(e) { /* ignore */ }
});

// ═══════════════════════════════════════
// 自动保存 & 恢复草稿
// ═══════════════════════════════════════
const SAVE_KEY = 'saifu_profile_draft';

function autoSave() {
  updateProgress();
  const form = document.getElementById('profileForm');
  if (!form) return;
  const data = {};
  // 保存所有 input/select/textarea 的值
  form.querySelectorAll('input, select, textarea').forEach(el => {
    if (el.type === 'radio') {
      if (el.checked) data[el.name] = el.value;
    } else if (el.type === 'checkbox') {
      if (!data[el.name]) data[el.name] = [];
      if (el.checked) data[el.name].push(el.value);
    } else {
      data[el.id || el.name] = el.value;
    }
  });
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify(data));
  } catch (e) { /* localStorage 不可用 */ }
}

function loadSaved() {
  try {
    // 根据当前模式选择不同的草稿
    if (currentMode === 'target') {
      const raw = localStorage.getItem(TARGET_SAVE_KEY);
      if (!raw) { showToast('没有已保存的草稿'); return; }
      const data = JSON.parse(raw);
      const form = document.getElementById('targetProfileForm');
      if (!form) return;

      form.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => el.checked = false);
      form.querySelectorAll('input[type="text"], input[type="url"], textarea').forEach(el => el.value = '');

      for (const [key, val] of Object.entries(data)) {
        if (Array.isArray(val)) {
          val.forEach(v => {
            const cb = form.querySelector(`input[name="${key}"][value="${v.replace(/"/g, '&quot;')}"]`);
            if (cb) cb.checked = true;
          });
        } else {
          const el = form.querySelector(`[id="${key}"]`) || form.querySelector(`input[name="${key}"][value="${val.replace(/"/g, '&quot;')}"]`);
          if (el) {
            if (el.type === 'radio') el.checked = true;
            else el.value = val;
          }
        }
      }
      updateProgress();
      showToast('草稿已恢复 ✅');
      return;
    }

    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) { showToast('没有已保存的草稿'); return; }
    const data = JSON.parse(raw);
    const form = document.getElementById('profileForm');
    if (!form) return;

    // 先清空
    form.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => el.checked = false);
    form.querySelectorAll('input[type="text"], input[type="url"], textarea').forEach(el => el.value = '');

    // 恢复
    for (const [key, val] of Object.entries(data)) {
      if (Array.isArray(val)) {
        val.forEach(v => {
          const cb = form.querySelector(`input[name="${key}"][value="${v.replace(/"/g, '&quot;')}"]`);
          if (cb) cb.checked = true;
        });
      } else {
        const el = form.querySelector(`[id="${key}"]`) || form.querySelector(`input[name="${key}"][value="${val.replace(/"/g, '&quot;')}"]`);
        if (el) {
          if (el.type === 'radio') el.checked = true;
          else el.value = val;
        }
      }
    }
    // 恢复后触发展示关联字段
    restoreConditionalFields();
    updateProgress();
    showToast('草稿已恢复 ✅');
  } catch (e) {
    showToast('草稿恢复失败');
  }
}

function clearForm() {
  if (!confirm('确定要清空所有填写内容吗？此操作不可恢复。')) return;

  if (currentMode === 'target') {
    const form = document.getElementById('targetProfileForm');
    if (!form) return;
    form.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => el.checked = false);
    form.querySelectorAll('input[type="text"], input[type="url"], textarea').forEach(el => el.value = '');
    updateProgress();
    try { localStorage.removeItem(TARGET_SAVE_KEY); } catch (e) {}
    showToast('已清空 ✅');
    return;
  }

  const form = document.getElementById('profileForm');
  if (!form) return;
  form.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => el.checked = false);
  form.querySelectorAll('input[type="text"], input[type="url"], textarea').forEach(el => el.value = '');
  document.querySelectorAll('.inline-other').forEach(el => el.classList.remove('show'));
  updateProgress();
  try { localStorage.removeItem(SAVE_KEY); } catch (e) {}
  showToast('已清空 ✅');
}

// ═══════════════════════════════════════
// 调研历史缓存（localStorage）
// ═══════════════════════════════════════
const HISTORY_KEY = 'saifu_results_history';
const MAX_HISTORY = 20;

function saveResultToHistory(resultData) {
  try {
    const alias = getAlias();
    const openCount = (resultData.open || []).length;
    const importCount = (resultData.recommendations || []).length;
    const matchCount = openCount || importCount || 0;
    const entry = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      timestamp: new Date().toLocaleString('zh-CN', { month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit' }),
      alias: alias || '未署名',
      matchCount: matchCount,
      resultData: resultData,
    };
    let history = loadResultHistory();
    history.unshift(entry);
    if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderHistoryPanel();
  } catch(e){}
}

function loadResultHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch(e){ return []; }
}

function deleteHistoryItem(id, ev) {
  ev.stopPropagation();
  let h = loadResultHistory().filter(e => e.id !== id);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(h));
  renderHistoryPanel();
  showToast('已删除');
}

function clearAllHistory() {
  if (!confirm('确定清空所有调研历史吗？此操作不可恢复。')) return;
  localStorage.removeItem(HISTORY_KEY);
  renderHistoryPanel();
  showToast('已清空');
}

function toggleHistoryItem(id) {
  const item = document.getElementById('hist-' + id);
  if (!item) return;
  item.classList.toggle('open');
  const body = document.getElementById('hist-body-' + id);
  if (!body || body._rendered || !item.classList.contains('open')) return;
  body._rendered = true;
  const data = body._resultData;
  if (!data) return;
  let html = '';
  const items = data.open || data.recommendations || [];
  if (items.length > 0) {
    html += '<div class="card-grid" style="margin-top:12px;">';
    items.forEach((c, i) => { html += buildCard(c, i); });
    html += '</div>';
  }
  const advice = data.advice || {};
  if (advice.time_plan || advice.skill_improvement || advice.team_strategy) {
    html += '<h3 style="margin-top:16px;">📝 备赛建议</h3>';
    if (advice.time_plan) html += '<p style="font-size:13px;white-space:pre-wrap;margin-bottom:8px;">⏰ ' + escHtml(advice.time_plan) + '</p>';
    if (advice.skill_improvement) html += '<p style="font-size:13px;white-space:pre-wrap;margin-bottom:8px;">📚 ' + escHtml(advice.skill_improvement) + '</p>';
    if (advice.team_strategy) html += '<p style="font-size:13px;white-space:pre-wrap;">👥 ' + escHtml(advice.team_strategy) + '</p>';
  }
  const risks = data.risks || [];
  if (risks.length > 0) {
    html += '<h3 style="margin-top:16px;">⚠️ 风险提示</h3>';
    risks.forEach(r => {
      html += '<div class="risk-item"><div class="risk-type">⚠ ' + escHtml(r.type||'') + '</div><div class="risk-detail">' + escHtml(r.detail||'') + '</div><div class="risk-solution">💡 应对：' + escHtml(r.solution||'') + '</div></div>';
    });
  }
  if (data.summary) {
    html += '<h3 style="margin-top:16px;">📋 总体评估</h3><p style="font-size:13px;white-space:pre-wrap;">' + escHtml(data.summary) + '</p>';
  }
  body.innerHTML = html;
}

function renderHistoryPanel() {
  const panel = document.getElementById('historyPanel');
  const list = document.getElementById('historyList');
  if (!panel || !list) return;
  const history = loadResultHistory();
  if (history.length === 0) { panel.classList.remove('show'); return; }
  panel.classList.add('show');
  list.innerHTML = history.map(h => {
    return '<div class="history-item" id="hist-' + h.id + '">' +
      '<div class="history-item-bar" onclick="toggleHistoryItem(\'' + h.id + '\')">' +
      '<span class="history-dot"></span>' +
      '<span class="history-time">' + escHtml(h.timestamp) + '</span>' +
      '<span class="history-alias">' + escHtml(h.alias) + '</span>' +
      '<span class="history-count">' + h.matchCount + ' 个竞赛</span>' +
      '<button class="history-item-delete" onclick="deleteHistoryItem(\'' + h.id + '\', event)" title="删除">✕</button>' +
      '<span class="history-arrow">▼</span></div>' +
      '<div class="history-body" id="hist-body-' + h.id + '"></div></div>';
  }).join('');
  history.forEach(h => {
    const body = document.getElementById('hist-body-' + h.id);
    if (body) body._resultData = h.resultData;
  });
}

// ═══════════════════════════════════════
// 条件字段切换
// ═══════════════════════════════════════

/** 切换"其他"输入框 */
function toggleOther(wrapId) {
  const wrap = document.getElementById(wrapId + '-wrap');
  if (!wrap) return;
  // wrapId 格式为 "{name}-other"，提取原始 checkbox name（如 "interests-other" → "interests"）
  const name = wrapId.replace(/-other$/, '');
  const cb = document.querySelector(`input[name="${name}"][value="__OTHER__"]`);
  if (cb && cb.checked) {
    wrap.classList.add('show');
    wrap.querySelector('input')?.focus();
  } else {
    wrap.classList.remove('show');
  }
}

/** 技能标签搜索过滤 */
function filterSkillTags() {
  const filter = document.getElementById('skill-filter');
  if (!filter) return;
  const q = filter.value.trim().toLowerCase();
  const items = document.querySelectorAll('#tech-direction-group .option-item');
  let visibleCount = 0;
  items.forEach(item => {
    // 始终显示"其他"选项和已选中的标签
    const cb = item.querySelector('input');
    const isOther = cb && cb.value === '__OTHER__';
    const isChecked = cb && cb.checked;
    if (!q || isOther || isChecked) {
      item.classList.remove('skill-hidden');
      visibleCount++;
      return;
    }
    // 匹配标签文字或 data-skill-keywords
    const keywords = (item.dataset.skillKeywords || '').toLowerCase();
    const label = item.querySelector('.option-tag')?.textContent?.toLowerCase() || '';
    if (label.includes(q) || keywords.includes(q)) {
      item.classList.remove('skill-hidden');
      visibleCount++;
    } else {
      item.classList.add('skill-hidden');
    }
  });
  // 无匹配提示
  const noMatch = document.getElementById('no-skill-match');
  if (noMatch) {
    noMatch.classList.toggle('show', visibleCount <= 1 && q); // <=1 因为"其他"始终可见
  }
}

/** 切换报名费过高输入框 */
function toggleAvoidFee() {
  const wrap = document.getElementById('avoid-fee-wrap');
  if (!wrap) return;
  const cb = document.querySelector('input[name="avoid"][value="报名费过高"]');
  if (cb && cb.checked) {
    wrap.classList.add('show');
    wrap.querySelector('input')?.focus();
  } else {
    wrap.classList.remove('show');
  }
}

/** 切换作品集链接输入框 */
function togglePortfolioLink() {
  const wrap = document.getElementById('portfolio-link-wrap');
  if (!wrap) return;
  const radio = document.querySelector('input[name="has-portfolio"][value="有"]');
  if (radio && radio.checked) {
    wrap.classList.add('show');
  } else {
    wrap.classList.remove('show');
  }
}

/** 全年都行 → 清除具体月份选择 */
function handleYearRound(cb) {
  if (!cb.checked) return;
  const specificGroup = document.getElementById('specific-months-group');
  if (specificGroup) {
    specificGroup.querySelectorAll('input[type="checkbox"]').forEach(el => el.checked = false);
  }
  autoSave();
}

/** 恢复草稿后重新展示条件字段 */
function restoreConditionalFields() {
  // 各"其他"选项
  ['interests', 'goals', 'tech-direction', 'tools', 'avoid'].forEach(name => {
    const otherCb = document.querySelector(`input[name="${name}"][value="__OTHER__"]`);
    if (otherCb && otherCb.checked) {
      let wrapId;
      if (name === 'tech-direction') wrapId = 'tech-direction-other-wrap';
      else if (name === 'avoid') wrapId = 'avoid-other-wrap';
      else wrapId = name + '-other-wrap';
      const wrap = document.getElementById(wrapId);
      if (wrap) wrap.classList.add('show');
    }
  });
  // 报名费过高
  const avoidFee = document.querySelector('input[name="avoid"][value="报名费过高"]');
  if (avoidFee && avoidFee.checked) {
    const wrap = document.getElementById('avoid-fee-wrap');
    if (wrap) wrap.classList.add('show');
  }
  // 作品集链接
  const hasPf = document.querySelector('input[name="has-portfolio"][value="有"]');
  if (hasPf && hasPf.checked) {
    const wrap = document.getElementById('portfolio-link-wrap');
    if (wrap) wrap.classList.add('show');
  }
}

// ═══════════════════════════════════════
// Toast
// ═══════════════════════════════════════
function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2000);
}

// ═══════════════════════════════════════
// 收集用户画像（v2: 9段表单 → ProfileInput）
// ═══════════════════════════════════════
function collectProfile() {
  // ── 辅助函数 ──
  const getChecked = (name) => {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
      .map(cb => cb.value)
      .filter(v => v !== '__OTHER__');
  };
  const getRadio = (name) => {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : '';
  };
  const getVal = (id) => (document.getElementById(id)?.value?.trim() || '');
  const getOther = (id) => {
    const el = document.getElementById(id);
    return el && el.parentElement && el.parentElement.classList.contains('show')
      ? (el.value?.trim() || '') : '';
  };

  // ── 一、基本信息 ──
  const school = getVal('school');
  const major = getVal('major');
  const grade = getRadio('grade');
  const intChecks = getChecked('interests');
  const intOther = getOther('interests-other');
  const interests = [...intChecks, intOther].filter(Boolean).join('、');

  // ── 二、参赛目标 ──
  const goalChecks = getChecked('goals');
  const goalOther = getOther('goals-other');
  const goals = [...goalChecks, goalOther].filter(Boolean);

  // ── 三、专业能力 ──
  const majorCategory = getRadio('major-category');
  const skills = getVal('core-skills');
  const techChecks = getChecked('tech-direction');
  const techOther = getOther('tech-direction-other');
  const tech_directions = [...techChecks, techOther].filter(Boolean);
  const toolChecks = getChecked('tools');
  const toolOther = getOther('tools-other');
  const tools = [...toolChecks, toolOther].filter(Boolean);
  const other_skills = getVal('skills-note');

  // ── 四、时间投入 ──
  const time_commitment = getRadio('weekly-hours');
  const freeMonths = getChecked('free-months');
  const available_months = freeMonths.join('、');
  const summer_winter = getRadio('holiday-ready');

  // ── 五、参赛偏好 ──
  const preference = getRadio('competition-level');
  const team_preference = getRadio('team-type');
  const has_advisor = getRadio('has-advisor');
  const can_cross_school = getRadio('cross-school');
  const preferred_duration = getRadio('competition-duration');
  const preferred_format = getRadio('competition-format');
  const fee_budget = getRadio('registration-fee');
  const language_pref = getRadio('language-pref');

  // ── 六、需避免的竞赛类型 ──
  const avoidChecks = getChecked('avoid');
  const avoidOther = getOther('avoid-other');
  let avoid_types = [...avoidChecks].join('、');
  if (avoidOther) avoid_types += (avoid_types ? '、' : '') + avoidOther;
  // 如果选了"报名费过高"且有金额
  if (avoidChecks.includes('报名费过高')) {
    const feeAmt = (document.getElementById('avoid-fee-amount')?.value?.trim() || '');
    if (feeAmt) avoid_types += `(超过${feeAmt}元)`;
  }

  // ── 七、过往参赛经历 ──
  const past_highest_award = getRadio('highest-award');
  const representative_projects = ['project1', 'project2', 'project3']
    .map(id => getVal(id))
    .filter(Boolean);
  const has_portfolio = getRadio('has-portfolio') === '有';
  const portfolio_link = getVal('portfolio-link');

  // ── 八、期望获奖层次 ──
  const min_award = getRadio('min-award');
  const ideal_goal = getVal('ideal-goal');
  const strategy = getRadio('strategy');

  // ── 九、同校组队现状 ──
  const has_lab_val = getRadio('has-lab');
  const has_lab = has_lab_val === '有';
  const join_school_team_val = getRadio('join-school-team');
  const join_school_team = join_school_team_val === '愿意' || join_school_team_val === '挑项目';
  const need_teammate = getRadio('need-teammate') === '需要';

  // ── 组装返回（字段名与后端 ProfileInput 一致）──
  const alias = getVal('alias');

  return {
    alias,
    school, major, grade, interests, skills,
    tech_directions, tools, other_skills,
    goals, time_commitment, available_months, summer_winter,
    preference, team_preference, preferred_duration, preferred_format,
    fee_budget, language_pref, has_advisor, can_cross_school,
    avoid_types, past_highest_award, representative_projects,
    has_portfolio, portfolio_link,
    has_lab, join_school_team, need_teammate,
    min_award, ideal_goal, strategy,
  };
}

// ═══════════════════════════════════════
// 收集简化画像（定向调研模式）
// ═══════════════════════════════════════
function collectTargetProfile() {
  const getRadio = (name) => {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : '';
  };
  const getVal = (id) => (document.getElementById(id)?.value?.trim() || '');
  const getChecked = (name) => {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
      .map(cb => cb.value);
  };

  return {
    alias: getVal('target-alias'),
    school: getVal('target-school'),
    major: getVal('target-major'),
    grade: getRadio('target-grade'),
    competition_name: getVal('target-competition-name'),
    skills: getVal('target-core-skills'),
    major_category: getRadio('target-major-category'),
    goals: getChecked('target-goals'),
    time_commitment: getRadio('target-weekly-hours'),
  };
}

// ── 简化表单自动保存 ──
const TARGET_SAVE_KEY = 'saifu_target_profile_draft';

function autoSaveTarget() {
  updateProgress();
  const form = document.getElementById('targetProfileForm');
  if (!form) return;
  const data = {};
  form.querySelectorAll('input, select, textarea').forEach(el => {
    if (el.type === 'radio') {
      if (el.checked) data[el.name] = el.value;
    } else if (el.type === 'checkbox') {
      if (!data[el.name]) data[el.name] = [];
      if (el.checked) data[el.name].push(el.value);
    } else {
      data[el.id || el.name] = el.value;
    }
  });
  try { localStorage.setItem(TARGET_SAVE_KEY, JSON.stringify(data)); } catch (e) {}
}

// ═══════════════════════════════════════
// 定向调研（知道比赛名称 → 深度分析）
// ═══════════════════════════════════════
async function startTargetResearch() {
  const canProceed = await checkUsageAndPrompt();
  if (!canProceed) return;

  const profile = collectTargetProfile();

  if (!profile.school || !profile.major || !profile.grade) {
    alert('请至少填写学校、专业和年级');
    return;
  }
  if (!profile.competition_name) {
    alert('请输入你想了解的比赛名称');
    return;
  }

  // 附带用户 API Key
  attachLLMConfig(profile);

  // 显示加载
  document.getElementById('formArea').style.display = 'none';
  document.getElementById('resultArea').style.display = 'none';
  document.getElementById('researchResultArea').style.display = 'none';
  document.getElementById('errorArea').style.display = 'none';
  document.getElementById('loadingArea').style.display = 'block';
  document.getElementById('loadingArea').scrollIntoView({ behavior: 'smooth' });

  // 更新加载步骤文字
  const stage1 = document.getElementById('loadStep1');
  const stage2 = document.getElementById('loadStep2');
  const stage3 = document.getElementById('loadStep3');
  const stage4 = document.getElementById('loadStep4');
  if (stage1) { stage1.textContent = '• 正在查找比赛信息...'; stage1.classList.add('active'); }
  if (stage2) { stage2.textContent = '• 正在分析你的个人情况...'; stage2.classList.remove('active'); }
  if (stage3) { stage3.textContent = '• AI 正在生成备赛规划...'; stage3.classList.remove('active'); }
  if (stage4) { stage4.textContent = '• 正在生成定向调研报告...'; stage4.classList.remove('active'); }
  document.querySelector('#loadingArea .loading-card h3').textContent = 'AI 正在分析比赛并规划...';

  const btn = document.getElementById('btnTargetResearch');
  btn.disabled = true;
  btn.textContent = '⏳ 分析中...';

  // 模拟步骤动画
  setTimeout(() => { if (stage2) stage2.classList.add('active'); }, 2000);
  setTimeout(() => { if (stage3) stage3.classList.add('active'); }, 8000);
  setTimeout(() => { if (stage4) stage4.classList.add('active'); }, 18000);

  try {
    const submitResp = await fetch(API_BASE_URL + '/api/target-research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });

    if (!submitResp.ok) throw new Error('提交失败: ' + submitResp.status);

    const submitData = await submitResp.json();
    if (!submitData.success || !submitData.task_id) {
      throw new Error(submitData.error || '提交任务失败');
    }

    const taskId = submitData.task_id;
    const pollInterval = 2000;
    const maxPolls = 120;
    let pollCount = 0;

    while (pollCount < maxPolls) {
      await sleep(pollInterval);
      pollCount++;

      try {
        const pollResp = await fetch(API_BASE_URL + '/api/target-research/' + taskId);
        if (!pollResp.ok) continue;

        const pollData = await pollResp.json();

        if (pollData.status === 'done') {
          if (!pollData.result || !pollData.result.success) {
            throw new Error((pollData.result && pollData.result.error) || '调研失败');
          }
          if (pollData.result.user_name) {
            currentResearchUser = pollData.result.user_name;
          }
          incrementUsage();
          renderResearchResults(pollData.result);
          return;
        }

        if (pollData.status === 'error') {
          throw new Error(pollData.error || '服务出错');
        }
      } catch (pollErr) {
        if (pollErr.message && !pollErr.message.includes('Failed to fetch')) {
          throw pollErr;
        }
      }
    }

    throw new Error('调研超时，请稍后重试。');

  } catch (error) {
    if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      showError('无法连接到服务器。请检查后端是否已部署并运行。');
    } else {
      showError(error.message || '未知错误');
    }
  } finally {
    document.getElementById('loadingArea').style.display = 'none';
    // 恢复加载标题
    const h3 = document.querySelector('#loadingArea .loading-card h3');
    if (h3) h3.textContent = 'AI 正在搜索和匹配竞赛...';
    btn.disabled = false;
    btn.textContent = '🔍 查看比赛详情与规划';
  }
}

// ═══════════════════════════════════════
// 开始匹配（提交+轮询模式）
// ═══════════════════════════════════════
async function startMatch() {
  // ── 免费试用次数检查 ──
  const canProceed = await checkUsageAndPrompt();
  if (!canProceed) return;

  const profile = collectProfile();

  // 基础校验
  if (!profile.school || !profile.major || !profile.grade) {
    alert('请至少填写学校、专业和年级');
    return;
  }

  // 附带用户 LLM 配置（如有）
  attachLLMConfig(profile);

  // 显示加载
  document.getElementById('formArea').style.display = 'none';
  document.getElementById('resultArea').style.display = 'none';
  document.getElementById('errorArea').style.display = 'none';
  document.getElementById('loadingArea').style.display = 'block';
  document.getElementById('loadingArea').scrollIntoView({ behavior: 'smooth' });

  // 禁用按钮
  const btn = document.getElementById('btnMatch');
  btn.disabled = true;
  btn.textContent = '⏳ 匹配中...';

  // 模拟加载步骤
  simulateLoadingSteps();

  try {
    // 第1步：提交匹配任务（快速返回 task_id）
    const submitResp = await fetch(API_BASE_URL + '/api/match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });

    if (!submitResp.ok) {
      throw new Error(`提交失败: ${submitResp.status}`);
    }

    const submitData = await submitResp.json();
    if (!submitData.success || !submitData.task_id) {
      throw new Error(submitData.error || '提交匹配任务失败');
    }

    const taskId = submitData.task_id;

    // 第2步：轮询获取结果
    const pollInterval = 2000; // 每2秒轮询一次
    const maxPolls = 150;      // 最多轮询300秒
    let pollCount = 0;

    while (pollCount < maxPolls) {
      await sleep(pollInterval);
      pollCount++;

      try {
        const pollResp = await fetch(API_BASE_URL + '/api/match/' + taskId);
        if (!pollResp.ok) continue;

        const pollData = await pollResp.json();

        if (pollData.status === 'done') {
          // 匹配完成！
          if (!pollData.result || !pollData.result.success) {
            throw new Error((pollData.result && pollData.result.error) || '匹配失败');
          }
          incrementUsage();
          renderResults(pollData.result);
          return;
        }

        if (pollData.status === 'error') {
          throw new Error(pollData.error || '匹配服务出错');
        }

        // status === 'processing' → 继续轮询
        updateLoadingProgress(pollCount);

      } catch (pollErr) {
        // 单次轮询失败不中断，继续重试
        if (pollErr.message && !pollErr.message.includes('Failed to fetch')) {
          throw pollErr;
        }
      }
    }

    // 超时
    throw new Error('匹配超时（超过 ' + MATCH_TIMEOUT/1000 + ' 秒）。请稍后重试。');

  } catch (error) {
    const msg = error.message || '';
    if (error.name === 'AbortError') {
      showError('匹配超时（超过 ' + MATCH_TIMEOUT/1000 + ' 秒）。请检查网络后重试。');
    } else if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
      showError('无法连接到服务器。请检查后端是否已部署并运行。');
    } else if (msg.includes('[BANKRUPT]')) {
      // 服务器破产 → 弹窗让用户输自己的 Key
      showApiKeyModal(null, true);
    } else {
      showError(msg || '未知错误');
    }
  } finally {
    document.getElementById('loadingArea').style.display = 'none';
    document.getElementById('btnMatch').disabled = false;
    document.getElementById('btnMatch').textContent = '🔍 开始智能匹配';
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function updateLoadingProgress(pollCount) {
  // 根据轮询次数更新加载提示
  const stage3 = document.getElementById('loadStep3');
  const stage4 = document.getElementById('loadStep4');
  if (pollCount > 10 && stage3 && !stage3.classList.contains('active')) {
    stage3.classList.add('active');
  }
  if (pollCount > 40 && stage4 && !stage4.classList.contains('active')) {
    stage4.classList.add('active');
  }
}

// ═══════════════════════════════════════
// 模拟加载步骤动画
// ═══════════════════════════════════════
function simulateLoadingSteps() {
  const steps = [
    { id: 'loadStep1', delay: 1000 },
    { id: 'loadStep2', delay: 5000 },
    { id: 'loadStep3', delay: 15000 },
    { id: 'loadStep4', delay: 40000 },
  ];

  steps.forEach(({ id, delay }) => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.classList.add('active');
    }, delay);
  });
}

// ═══════════════════════════════════════
// 错误展示
// ═══════════════════════════════════════
function showError(msg) {
  document.getElementById('errorMsg').textContent = msg;
  document.getElementById('errorArea').style.display = 'block';
  // 确保错误页也有返回按钮
  const errorCard = document.querySelector('#errorArea .error-card');
  if (errorCard && !errorCard.querySelector('.btn-back')) {
    const backBtn = document.createElement('button');
    backBtn.className = 'btn btn-outline btn-sm btn-back';
    backBtn.textContent = '🔙 返回修改';
    backBtn.onclick = backToForm;
    backBtn.style.cssText = 'margin-top:12px;margin-right:8px;';
    const retryBtn = errorCard.querySelector('.btn-retry');
    if (retryBtn) {
      errorCard.insertBefore(backBtn, retryBtn);
    } else {
      errorCard.appendChild(backBtn);
    }
  }
  document.getElementById('errorArea').scrollIntoView({ behavior: 'smooth' });
}

/** 从结果/错误页返回表单修改（数据保留不丢失） */
function backToForm() {
  document.getElementById('resultArea').style.display = 'none';
  document.getElementById('researchResultArea').style.display = 'none';
  document.getElementById('errorArea').style.display = 'none';
  document.getElementById('loadingArea').style.display = 'none';
  document.getElementById('importArea').style.display = 'none';
  document.getElementById('formArea').style.display = 'block';
  document.getElementById('tabFormBtn').classList.add('active');
  document.getElementById('tabImportBtn').classList.remove('active');
  // 恢复当前模式对应的子表单
  var df = document.getElementById('discoverForm');
  var tf = document.getElementById('targetForm');
  if (currentMode === 'target') {
    if (df) df.classList.add('form-hidden');
    if (tf) tf.classList.remove('form-hidden');
  } else {
    if (df) df.classList.remove('form-hidden');
    if (tf) tf.classList.add('form-hidden');
  }
  document.getElementById('formArea').scrollIntoView({ behavior: 'smooth' });
}

function retryMatch() {
  // 根据当前激活的 tab 决定返回到哪里
  const importActive = document.getElementById('tabImportBtn').classList.contains('active');
  if (importActive) {
    backToImport();
  } else {
    backToForm();
  }
}

// ═══════════════════════════════════════
// 渲染匹配结果
// ═══════════════════════════════════════
function renderResults(data) {
  document.getElementById('resultArea').style.display = 'block';

  // ── 返回修改按钮 ──
  const resultArea = document.getElementById('resultArea');
  let backBar = resultArea.querySelector('.back-bar');
  if (!backBar) {
    backBar = document.createElement('div');
    backBar.className = 'back-bar';
    backBar.style.cssText = 'margin-bottom:14px;text-align:right;';
    resultArea.insertBefore(backBar, resultArea.firstChild);
  }
  backBar.innerHTML = '<button class="btn btn-outline btn-sm" onclick="backToForm()">🔙 返回修改</button>';

  // ── 报名中的竞赛 ──
  const openCards = document.getElementById('openCards');
  openCards.innerHTML = '';

  if (data.open && data.open.length > 0) {
    data.open.forEach((comp, i) => {
      openCards.innerHTML += buildCard(comp, i);
    });
  } else {
    openCards.innerHTML = '<p style="padding:20px;color:#999;text-align:center">暂无匹配的报名中竞赛</p>';
  }

  // ── 参考资源 ──
  if (data.resources && data.resources.length > 0) {
    document.getElementById('resourceSection').style.display = 'block';
    const resourceList = document.getElementById('resourceList');
    resourceList.innerHTML = data.resources.map(r => `
      <div class="resource-item">
        <span class="res-name">${escHtml(r.name || '未知')}</span>
        <a class="res-link" href="${escHtml(r.url || '#')}" target="_blank">${escHtml((r.url || '').substring(0, 60))}</a>
        <span style="font-size:12px;color:#999">${escHtml(r.notes || '')}</span>
      </div>
    `).join('');
  } else {
    document.getElementById('resourceSection').style.display = 'none';
  }

  // ── 已截止竞赛 ──
  if (data.closed && data.closed.length > 0) {
    document.getElementById('closedSection').style.display = 'block';
    const closedCards = document.getElementById('closedCards');
    closedCards.innerHTML = data.closed.map((comp, i) => buildCard(comp, i)).join('');
  } else {
    document.getElementById('closedSection').style.display = 'none';
  }

  // ── 小贴士 ──
  const tipsArea = document.getElementById('tipsArea');
  let tipsHtml = '<h3>💡 选赛小贴士</h3>';
  if (data.myths) {
    data.myths.forEach(m => { tipsHtml += `<div class="tip-item">${escHtml(m)}</div>`; });
  }
  tipsHtml += '<br>';
  if (data.tips) {
    data.tips.forEach(t => { tipsHtml += `<div class="tip-item">${escHtml(t)}</div>`; });
  }
  tipsHtml += '<div class="platform-note" style="margin-top:16px">⚡ 本平台由 AI 驱动，信息来自网络搜索+内置竞赛知识库，报名前请到官网核实！</div>';
  tipsArea.innerHTML = tipsHtml;

  // ── 备赛建议 ──
  const advice = data.advice || {};
  const adviceSection = document.getElementById('adviceSection');
  const adviceDiv = document.getElementById('adviceArea');
  if (advice.time_plan || advice.skill_improvement || advice.team_strategy) {
    adviceSection.style.display = 'block';
    let adviceHtml = '';
    if (advice.time_plan) {
      adviceHtml += '<h3>⏰ 时间规划</h3><p style="margin-bottom:16px;white-space:pre-wrap;">' + escHtml(advice.time_plan) + '</p>';
    }
    if (advice.skill_improvement) {
      adviceHtml += '<h3>📚 技能补强</h3><p style="margin-bottom:16px;white-space:pre-wrap;">' + escHtml(advice.skill_improvement) + '</p>';
    }
    if (advice.team_strategy) {
      adviceHtml += '<h3>👥 组队策略</h3><p style="white-space:pre-wrap;">' + escHtml(advice.team_strategy) + '</p>';
    }
    adviceDiv.innerHTML = adviceHtml;
  } else {
    adviceSection.style.display = 'none';
  }

  // ── 风险提示 ──
  const risks = data.risks || [];
  const risksSection = document.getElementById('risksSection');
  const risksDiv = document.getElementById('risksArea');
  if (risks.length > 0) {
    risksSection.style.display = 'block';
    risksDiv.innerHTML = risks.map(r => {
      return '<div class="risk-item">' +
        '<div class="risk-type">⚠ ' + escHtml(r.type || '潜在风险') + '</div>' +
        '<div class="risk-detail">' + escHtml(r.detail || '') + '</div>' +
        '<div class="risk-solution">💡 应对：' + escHtml(r.solution || '') + '</div>' +
        '</div>';
    }).join('');
  } else {
    risksSection.style.display = 'none';
  }

  // ── 总结 ──
  const summaryArea = document.getElementById('summaryArea');
  if (data.summary) {
    summaryArea.style.display = 'block';
    summaryArea.innerHTML = '<h3>📋 总体评估</h3><p style="white-space:pre-wrap;">' + escHtml(data.summary) + '</p>' +
      '<div class="platform-note" style="margin-top:16px">🏗️ 赛赋 SaiFu | AI驱动 · 常识库校验 · 多源交叉验证 | Powered by DeepSeek</div>';
  } else {
    summaryArea.style.display = 'none';
  }

  // 缓存到历史
  saveResultToHistory(data);

  // 更新导出提示
  updateExportHints();

  // 滚动到结果区
  document.getElementById('resultArea').scrollIntoView({ behavior: 'smooth' });
}

// ═══════════════════════════════════════
// 构建单张竞赛卡片
// ═══════════════════════════════════════
function buildCard(comp, index) {
  const name = comp.name || '未知竞赛';
  const score = comp.match_score || 0;
  const cat = comp.cat || '🏫 学校/教育部类';
  const focus = comp.focus || '能力锻炼';
  const desc = comp.desc || '';
  const reason = comp.match_reason || '';
  const benefits = comp.benefits || '';
  const pitfalls = comp.pitfalls || '';
  const recommendIndex = comp.recommend_index || 3;

  // 解析三段式理由
  const reasonParts = reason.replace(/；/g, ';').split(';').filter(Boolean);

  // 焦点标签
  let focusLabels = '';
  (focus.split(',')).forEach(f => {
    f = f.trim();
    if (f.includes('保研')) focusLabels += '<span class="card-tag tag-focus">🎓保研加分</span> ';
    else if (f.includes('企业')) focusLabels += '<span class="card-tag tag-focus">💼企业直通</span> ';
    else if (f.includes('拿奖')) focusLabels += '<span class="card-tag tag-focus">🏆拿奖率高</span> ';
    else focusLabels += '<span class="card-tag tag-focus">💪能力锻炼</span> ';
  });

  // 推荐星级
  const stars = '⭐'.repeat(Math.min(5, recommendIndex));
  const wiText = ['', '不推荐', '勉强可报', '可以报名', '推荐报名', '强烈推荐'][recommendIndex] || '';

  // 排名样式
  let topClass = '';
  if (index === 0) topClass = 'top-1';
  else if (index === 1) topClass = 'top-2';
  else if (index === 2) topClass = 'top-3';

  // 参赛形式和费用
  const pt = comp.participation_type || comp.registration_form || '未知';
  const isFree = comp.is_free;
  const fee = comp.fee_amount || '未知';
  const feeText = (isFree || fee === '免费') ? '🆓 免费' : `💰 ${fee}`;
  const ptText = pt.includes('个人') && pt.includes('团队') ? '🧑/👥 均可' :
                 pt.includes('团队') ? '👥 仅团队' :
                 pt.includes('个人') ? '🧑 仅个人' : pt;

  const cardId = 'card-' + Date.now().toString(36) + '-' + index;
  const deadline = comp.registration_deadline || '待定';
  const deadlineShort = deadline.length > 7 ? deadline.substring(0, 7) : deadline;

  return `
    <div class="comp-card ${topClass} collapsed" id="${cardId}">
      <div class="card-header" onclick="toggleCard('${cardId}')">
        <div class="card-score">${score}<small>%</small></div>
        <div class="card-name">${escHtml(name)}</div>
        <div class="card-meta">
          <span class="card-tag tag-cat">${escHtml(cat)}</span>
          ${focusLabels}
          <span class="card-tag tag-deadline">⏰ ${deadlineShort}截止</span>
          <span class="card-toggle">▼</span>
        </div>
      </div>
      <div class="card-body">
        ${desc ? `<p class="label">📖 竞赛内容</p><p>${escHtml(desc.substring(0, 150))}</p>` : ''}
        ${reasonParts.length > 0 ? `
          <p class="label">📝 匹配理由</p>
          <p>${reasonParts.map(r => escHtml(r.trim())).join('<br>')}</p>
        ` : ''}
        ${benefits ? `<p class="label">💡 为什么参加</p><p>${escHtml(benefits)}</p>` : ''}
        ${pitfalls ? `<p class="label">⚠️ 注意事项</p><p>${escHtml(pitfalls)}</p>` : ''}
        <p class="label">⭐ 推荐指数</p><p>${stars} · ${wiText}</p>
      </div>
      <div class="card-footer">
        <span>📌 ${ptText}</span>
        <span>${feeText}</span>
        <span>⏰ 截止: ${comp.registration_deadline || '未知'}</span>
        ${comp.official_url && comp.official_url !== '未知' ? `<span>🔗 <a href="${escHtml(comp.official_url)}" target="_blank" onclick="event.stopPropagation()">官网</a></span>` : ''}
      </div>
    </div>
  `;
}

/** 切换卡片折叠/展开 */
function toggleCard(id) {
  const card = document.getElementById(id);
  if (!card) return;
  card.classList.toggle('collapsed');
}

// ═══════════════════════════════════════
// 联系方式弹窗
// ═══════════════════════════════════════
function showContactModal() {
  document.getElementById('contactModal').classList.add('show');
}
function hideContactModal(e) {
  if (e && e.target !== document.getElementById('contactModal')) return;
  document.getElementById('contactModal').classList.remove('show');
}

// ═══════════════════════════════════════
// Tab 切换
// ═══════════════════════════════════════
function switchTab(tab) {
  const formBtn = document.getElementById('tabFormBtn');
  const importBtn = document.getElementById('tabImportBtn');
  const formArea = document.getElementById('formArea');
  const importArea = document.getElementById('importArea');
  const resultArea = document.getElementById('resultArea');
  const researchResultArea = document.getElementById('researchResultArea');
  const loadingArea = document.getElementById('loadingArea');
  const errorArea = document.getElementById('errorArea');

  if (tab === 'form') {
    formBtn.classList.add('active');
    importBtn.classList.remove('active');
    formArea.style.display = 'block';
    importArea.style.display = 'none';
    // 保留匹配结果区的显示状态
  } else {
    importBtn.classList.add('active');
    formBtn.classList.remove('active');
    formArea.style.display = 'none';
    importArea.style.display = 'block';
    // 隐藏匹配相关结果，显示调研结果（如果有）
    if (resultArea) resultArea.style.display = 'none';
    if (loadingArea) loadingArea.style.display = 'none';
    if (errorArea) errorArea.style.display = 'none';
  }
}

// ═══════════════════════════════════════
// 报告文本解析
// ═══════════════════════════════════════

/** 字段名映射表：报告中的中文标签 → JSON 字段名 */
const FIELD_MAP = {
  '姓名': 'name',
  '学校': 'school',
  '专业': 'major',
  '年级': 'grade',
  '兴趣领域': 'interests',
  '参赛目标': 'goals',
  '专业大类': 'major_category',
  '核心技能': 'core_skills',
  '技能领域': 'skill_domains',
  '常用工具': 'tools',
  '每周可投入': 'weekly_hours',
  '空闲月份': 'free_months',
  '寒暑假可集中备赛': 'summer_winter_available',
  '赛事级别': 'competition_level',
  '个人/团队': 'team_type',
  '有指导老师': 'has_advisor',
  '接受跨校组队': 'can_cross_school',
  '比赛周期': 'competition_duration',
  '比赛形式': 'competition_format',
  '报名费': 'registration_fee',
  '语言': 'language_pref',
  '需避免': 'avoid_types',
  '最高获奖': 'highest_award',
  '代表性项目': 'representative_projects',
  '有作品集/GitHub': 'has_portfolio_raw',
  '最低接受': 'min_award',
  '理想目标': 'ideal_goal',
  '策略': 'strategy',
  '学校有实验室': 'has_lab',
  '愿意加入校内团队': 'join_school_team',
  '需要匹配队友': 'need_teammate',
};

/**
 * 解析用户报告文本 → JSON 对象
 * 格式: 每行 "标签：值"（中文全角冒号）
 */
function parseReportText(text) {
  if (!text || !text.trim()) {
    throw new Error('报告文本为空，请粘贴后再试');
  }

  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const userData = {};

  for (const line of lines) {
    // 跳过标题行和分隔线
    if (line.startsWith('📋') || line.startsWith('━━') || line.startsWith('生成时间')) {
      continue;
    }

    // 尝试用中文冒号分割
    let colonIdx = line.indexOf('：');
    if (colonIdx === -1) {
      // 尝试英文冒号
      colonIdx = line.indexOf(':');
    }
    if (colonIdx === -1) continue;

    const label = line.substring(0, colonIdx).trim();
    let value = line.substring(colonIdx + 1).trim();

    // 查找字段映射
    const fieldKey = FIELD_MAP[label];
    if (!fieldKey) continue; // 未知标签，跳过

    // 特殊处理：有作品集/GitHub → 拆分为 has_portfolio 和 portfolio_link
    if (fieldKey === 'has_portfolio_raw') {
      const parts = value.split('|').map(s => s.trim());
      const hasPf = parts[0] || '';
      userData['has_portfolio'] = hasPf.includes('有');
      if (parts.length > 1) {
        userData['portfolio_link'] = parts.slice(1).join('|').trim();
      }
      continue;
    }

    userData[fieldKey] = value;
  }

  // 校验必填字段
  if (!userData.name) {
    throw new Error('未解析到「姓名」字段，请检查报告格式是否正确');
  }

  return userData;
}

// ═══════════════════════════════════════
// 开始调研（提交+轮询模式）
// ═══════════════════════════════════════
async function startResearch() {
  // ── 免费试用次数检查 ──
  const canProceed = await checkUsageAndPrompt();
  if (!canProceed) return;

  const reportText = document.getElementById('reportText')?.value?.trim();
  if (!reportText) {
    alert('请先粘贴用户报告文本');
    return;
  }

  // 解析报告
  let userData;
  try {
    userData = parseReportText(reportText);
  } catch (err) {
    alert('解析失败：' + err.message);
    return;
  }

  // 附带用户 LLM 配置（如有）
  attachLLMConfig(userData);

  // 显示加载状态
  document.getElementById('importArea').style.display = 'none';
  document.getElementById('researchResultArea').style.display = 'none';
  document.getElementById('errorArea').style.display = 'none';
  document.getElementById('loadingArea').style.display = 'block';
  document.getElementById('loadingArea').scrollIntoView({ behavior: 'smooth' });

  // 更新加载提示
  const stage1 = document.getElementById('loadStep1');
  const stage2 = document.getElementById('loadStep2');
  const stage3 = document.getElementById('loadStep3');
  const stage4 = document.getElementById('loadStep4');
  if (stage1) { stage1.textContent = '• 正在解析用户报告...'; stage1.classList.add('active'); }
  if (stage2) { stage2.textContent = '• 正在构建用户画像...'; stage2.classList.remove('active'); }
  if (stage3) { stage3.textContent = '• AI 正在进行竞赛调研分析...'; stage3.classList.remove('active'); }
  if (stage4) { stage4.textContent = '• 正在生成调研报告...'; stage4.classList.remove('active'); }

  const btn = document.getElementById('btnResearch');
  btn.disabled = true;
  btn.textContent = '⏳ 调研中...';

  // 模拟步骤动画
  setTimeout(() => { if (stage2) stage2.classList.add('active'); }, 2000);
  setTimeout(() => { if (stage3) stage3.classList.add('active'); }, 8000);
  setTimeout(() => { if (stage4) stage4.classList.add('active'); }, 20000);

  try {
    // 提交调研任务
    const submitResp = await fetch(API_BASE_URL + '/api/import-and-research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_data: userData }),
    });

    if (!submitResp.ok) {
      throw new Error('提交失败: ' + submitResp.status);
    }

    const submitData = await submitResp.json();
    if (!submitData.success || !submitData.task_id) {
      throw new Error(submitData.error || '提交调研任务失败');
    }

    const taskId = submitData.task_id;

    // 轮询获取结果
    const pollInterval = 2000;
    const maxPolls = 150; // 300秒超时
    let pollCount = 0;

    while (pollCount < maxPolls) {
      await sleep(pollInterval);
      pollCount++;

      try {
        const pollResp = await fetch(API_BASE_URL + '/api/import-and-research/' + taskId);
        if (!pollResp.ok) continue;

        const pollData = await pollResp.json();

        if (pollData.status === 'done') {
          if (!pollData.result || !pollData.result.success) {
            throw new Error((pollData.result && pollData.result.error) || '调研失败');
          }
          // 保存用户名用于导出文件命名
          if (pollData.result.user_name) {
            currentResearchUser = pollData.result.user_name;
          }
          incrementUsage();
          renderResearchResults(pollData.result);
          return;
        }

        if (pollData.status === 'error') {
          throw new Error(pollData.error || '调研服务出错');
        }
        // processing → 继续轮询
      } catch (pollErr) {
        if (pollErr.message && !pollErr.message.includes('Failed to fetch')) {
          throw pollErr;
        }
      }
    }

    throw new Error('调研超时（超过 300 秒）。请稍后重试。');

  } catch (error) {
    const msg = error.message || '';
    if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
      showError('无法连接到服务器。请检查后端是否已部署并运行。');
    } else if (msg.includes('[BANKRUPT]')) {
      showApiKeyModal(null, true);
    } else {
      showError(msg || '未知错误');
    }
  } finally {
    document.getElementById('loadingArea').style.display = 'none';
    btn.disabled = false;
    btn.textContent = '🔍 开始调研';
  }
}

// ═══════════════════════════════════════
// 渲染调研结果
// ═══════════════════════════════════════
function renderResearchResults(data) {
  const area = document.getElementById('researchResultArea');
  area.style.display = 'block';

  // 返回按钮
  let backBar = area.querySelector('.back-bar');
  if (!backBar) {
    backBar = document.createElement('div');
    backBar.className = 'back-bar';
    backBar.style.cssText = 'margin-bottom:14px;text-align:right;';
    area.insertBefore(backBar, area.firstChild);
  }
  // 根据来源决定返回目标：定向调研 → 返回表单，导入调研 → 返回导入面板
  const backFn = (currentMode === 'target') ? 'backToForm()' : 'backToImport()';
  backBar.innerHTML = '<button class="btn btn-outline btn-sm" onclick="' + backFn + '">🔙 返回修改</button>';

  // ── 推荐竞赛卡片 ──
  const cardsContainer = document.getElementById('researchCards');
  cardsContainer.innerHTML = '';

  const recs = data.recommendations || [];
  if (recs.length > 0) {
    recs.forEach((comp, i) => {
      cardsContainer.innerHTML += buildResearchCard(comp, i);
    });
  } else {
    cardsContainer.innerHTML = '<p style="padding:20px;color:#999;text-align:center">暂无推荐竞赛</p>';
  }

  // ── 备赛建议 ──
  const advice = data.advice || {};
  const adviceSection = document.getElementById('researchAdviceSection');
  const adviceDiv = document.getElementById('researchAdvice');
  if (advice.time_plan || advice.skill_improvement || advice.team_strategy) {
    adviceSection.style.display = 'block';
    let adviceHtml = '';
    if (advice.time_plan) {
      adviceHtml += '<h3>⏰ 时间规划</h3><p style="margin-bottom:16px;white-space:pre-wrap;">' + escHtml(advice.time_plan) + '</p>';
    }
    if (advice.skill_improvement) {
      adviceHtml += '<h3>📚 技能补强</h3><p style="margin-bottom:16px;white-space:pre-wrap;">' + escHtml(advice.skill_improvement) + '</p>';
    }
    if (advice.team_strategy) {
      adviceHtml += '<h3>👥 组队策略</h3><p style="white-space:pre-wrap;">' + escHtml(advice.team_strategy) + '</p>';
    }
    adviceDiv.innerHTML = adviceHtml;
  } else {
    adviceSection.style.display = 'none';
  }

  // ── 风险提示 ──
  const risks = data.risks || [];
  const risksSection = document.getElementById('researchRisksSection');
  const risksDiv = document.getElementById('researchRisks');
  if (risks.length > 0) {
    risksSection.style.display = 'block';
    risksDiv.innerHTML = risks.map(r => {
      return '<div class="risk-item">' +
        '<div class="risk-type">⚠ ' + escHtml(r.type || '潜在风险') + '</div>' +
        '<div class="risk-detail">' + escHtml(r.detail || '') + '</div>' +
        '<div class="risk-solution">💡 应对：' + escHtml(r.solution || '') + '</div>' +
        '</div>';
    }).join('');
  } else {
    risksSection.style.display = 'none';
  }

  // ── 总结 ──
  const summaryArea = document.getElementById('researchSummaryArea');
  if (data.summary) {
    summaryArea.style.display = 'block';
    summaryArea.innerHTML = '<h3>📋 总体评估</h3><p style="white-space:pre-wrap;">' + escHtml(data.summary) + '</p>' +
      '<div class="platform-note" style="margin-top:16px;background:#fafbfc;">⚡ 本平台由 AI 驱动，竞赛信息来自内置知识库，报名前请到官网核实！</div>';
  } else {
    summaryArea.style.display = 'none';
  }

  // 缓存到历史
  saveResultToHistory(data);

  // 更新导出提示
  updateExportHints();

  // 滚动到结果区
  area.scrollIntoView({ behavior: 'smooth' });
}

/**
 * 构建调研竞赛卡片（适配完整模板格式：类别+星级+竞赛内容+匹配理由+为什么参加+注意事项）
 */
function buildResearchCard(comp, index) {
  const name = comp.name || '未知竞赛';
  const score = comp.match_score || 0;
  const level = comp.level || '未知';
  const deadline = comp.deadline || '待公布';
  const form = comp.form || '未知';
  const fee = comp.fee || '未知';
  const reason = comp.reason || '';
  const preparation = comp.preparation || '';
  const focus = comp.focus || '';
  const officialUrl = comp.official_url || '';
  const cat = comp.cat || '';           // 类别标签
  const desc = comp.desc || '';         // 竞赛内容
  const benefits = comp.benefits || '';  // 为什么参加
  const pitfalls = comp.pitfalls || '';  // 注意事项
  const recIdx = comp.recommend_index || 3; // 推荐指数 (1-5)

  // 焦点标签
  let focusLabels = '';
  (focus.split(',')).forEach(f => {
    f = f.trim();
    if (f.includes('保研')) focusLabels += '<span class="card-tag tag-focus">🎓保研加分</span> ';
    else if (f.includes('企业')) focusLabels += '<span class="card-tag tag-focus">💼企业直通</span> ';
    else if (f.includes('拿奖')) focusLabels += '<span class="card-tag tag-focus">🏆拿奖率高</span> ';
    else if (f.includes('锻炼')) focusLabels += '<span class="card-tag tag-focus">💪能力锻炼</span> ';
  });

  // 类别标签
  const catTag = cat ? '<span class="card-tag tag-cat">' + escHtml(cat) + '</span> ' : '';

  // 推荐星级
  const stars = '⭐'.repeat(Math.min(recIdx, 5));
  const starLabels = ['', '不太推荐', '可以尝试', '比较推荐', '非常推荐', '强烈推荐'];
  const starLabel = starLabels[Math.min(recIdx, 5)] || '';
  const starHtml = stars + (starLabel ? ' <small>' + starLabel + '</small>' : '');

  // 排名样式
  let topClass = '';
  if (index === 0) topClass = 'top-1';
  else if (index === 1) topClass = 'top-2';
  else if (index === 2) topClass = 'top-3';

  // 免费标识
  const feeIcon = (fee === '免费' || fee === '0') ? '🆓' : '💰';
  const feeText = feeIcon + ' ' + fee;

  // 参赛形式精简
  const formShort = form.replace(/\(.*\)/, '').trim(); // "团队(3人)" → "团队"

  return `
    <div class="comp-card ${topClass}">
      <div class="card-header">
        <div class="card-score">${score} <small>分</small></div>
        <div class="card-name">${escHtml(name)}</div>
        <div class="card-meta">
          ${catTag}${focusLabels}
        </div>
        <div class="card-stars" style="font-size:15px;margin-top:4px;">${starHtml}</div>
      </div>
      <div class="card-body">
        ${desc ? '<p class="label">📝 竞赛内容</p><p>' + escHtml(desc).replace(/\n/g, '<br>') + '</p>' : ''}
        ${reason ? '<p class="label">📝 匹配理由</p><p>' + escHtml(reason) + '</p>' : ''}
        ${benefits ? '<p class="label">📝 为什么参加</p><p>' + escHtml(benefits).replace(/\n/g, '<br>') + '</p>' : ''}
        ${pitfalls ? '<p class="label">⚠ 注意事项</p><p>' + escHtml(pitfalls).replace(/\n/g, '<br>') + '</p>' : ''}
      </div>
      <div class="card-footer">
        <span>📌 ${escHtml(level)} | ${escHtml(formShort)}</span>
        <span>${feeText}</span>
        <span>⏰ 截止: ${escHtml(deadline)}</span>
        ${officialUrl && officialUrl !== '待查' ? '<span>🔗 <a href="' + escHtml(officialUrl) + '" target="_blank">官网</a></span>' : ''}
      </div>
    </div>
  `;
}

/** 从调研结果页返回导入面板 */
function backToImport() {
  document.getElementById('researchResultArea').style.display = 'none';
  document.getElementById('errorArea').style.display = 'none';
  document.getElementById('loadingArea').style.display = 'none';
  document.getElementById('importArea').style.display = 'block';
  document.getElementById('importArea').scrollIntoView({ behavior: 'smooth' });
  // 确保 tab 在导入状态
  document.getElementById('tabFormBtn').classList.remove('active');
  document.getElementById('tabImportBtn').classList.add('active');
}

// ═══════════════════════════════════════
// 导出功能 — 打印 PDF + 保存 HTML
// ═══════════════════════════════════════

/** 当前调研的用户名（调研完成后自动填入） */
let currentResearchUser = '';

/** 获取用户别名（用于文件名），优先级：输入框 > 调研用户名 > 空 */
function getAlias() {
  // 先检查当前模式的别名字段
  if (currentMode === 'target') {
    const alias = (document.getElementById('target-alias')?.value || '').trim();
    if (alias) return alias;
  } else {
    const alias = (document.getElementById('alias')?.value || '').trim();
    if (alias) return alias;
  }
  if (currentResearchUser) return currentResearchUser;
  return '';
}

/** 🖨 打印 PDF — 打开浏览器打印对话框，选「另存为 PDF」 */
/** 判断是否为移动设备 */
function isMobile() {
  return /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || window.innerWidth < 768;
}

/** 构建独立 HTML 报告（提取结果内容 + CSS） */
function buildStandaloneHTML(autoPrint) {
  let resultArea = document.getElementById('resultArea');
  let researchArea = document.getElementById('researchResultArea');

  let resultContent;
  if (researchArea && researchArea.style.display !== 'none') {
    resultContent = researchArea.innerHTML;
  } else if (resultArea && resultArea.style.display !== 'none') {
    resultContent = resultArea.innerHTML;
  } else {
    return null;
  }

  const alias = getAlias();
  const titleText = alias ? `赛赋 SaiFu · 竞赛调研报告 — ${alias}` : '赛赋 SaiFu · 竞赛调研报告';

  // ── 收集所有生效的 CSS ──
  let allCSS = '';

  // 1. 从 style.css 提取规则
  try {
    for (const sheet of document.styleSheets) {
      try {
        if (sheet.href && sheet.href.includes('style.css')) {
          for (const rule of sheet.cssRules || sheet.rules || []) {
            allCSS += rule.cssText + '\n';
          }
        }
      } catch (e) { /* 跨域跳过 */ }
    }
  } catch (e) {}

  // 2. 收集页面上所有 <style> 标签
  document.querySelectorAll('style').forEach(style => {
    allCSS += style.textContent + '\n';
  });

  // 3. 独立页面隐藏导出按钮 + 返回按钮，避免重复
  allCSS += `
    .export-buttons, .export-hint, .back-bar, .btn-contact,
    .navbar, .tab-bar, .match-btn-wrap, .toast, .progress-wrap { display: none !important; }
    body { padding: 16px; }
  `;

  const printScript = autoPrint
    ? '<script>window.onload=function(){setTimeout(function(){window.print();},600);}<\/script>'
    : '';

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${titleText}</title>
<style>${allCSS}</style>
${printScript}
</head>
<body>
<div class="container">
${resultContent}
</div>
<script type="application/json" id="sai-fu-data">
${JSON.stringify(collectProfile(), null, 2)}
<\/script>
</body>
</html>`;
}

/** 🖨 打印 PDF — 桌面调用系统打印，手机在新标签页打开并自动弹出打印 */
function printToPDF() {
  if (isMobile()) {
    const html = buildStandaloneHTML(true);
    if (!html) { showToast('没有可打印的内容'); return; }
    const blob = new Blob([html], { type: 'text/html;charset=UTF-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    showToast('正在新窗口打开，请使用浏览器分享 → 打印/保存PDF');
  } else {
    const alias = getAlias();
    document.title = alias ? `赛赋-调研报告-${alias}` : '赛赋-调研报告';
    window.print();
  }
}

/** 💾 保存 HTML — 桌面下载文件，手机在新标签页打开查看 */
function saveAsHTML() {
  const html = buildStandaloneHTML(false);
  if (!html) { showToast('没有可保存的内容'); return; }

  if (isMobile()) {
    // 手机端：新标签页打开（浏览器原生渲染，可分享/打印/截图）
    const blob = new Blob([html], { type: 'text/html;charset=UTF-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    showToast('报告已在新窗口打开 ✅');
  } else {
    // 桌面端：下载文件
    const alias = getAlias();
    const fileName = alias ? `赛赋-调研报告-${alias}.html` : '赛赋-调研报告.html';
    const blob = new Blob([html], { type: 'text/html;charset=UTF-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
    showToast('报告已保存 ✅');
  }
}

/** 根据设备更新导出按钮提示文字 */
function updateExportHints() {
  const mobile = isMobile();
  const hint = mobile
    ? '💡 点击按钮在新窗口查看报告，可用浏览器「分享 → 打印」保存为 PDF'
    : '💡 推荐「打印 PDF」存档至本地，「保存 HTML」下载离线查看';
  const h1 = document.getElementById('exportHint1');
  const h2 = document.getElementById('exportHint2');
  if (h1) h1.textContent = hint;
  if (h2) h2.textContent = hint;
}

// ═══════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════
function escHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
