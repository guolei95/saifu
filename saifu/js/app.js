/**
 * 赛赋 SaiFu — 前端交互逻辑
 * v2: 适配9段通用表单（覆盖全学科）
 */

// ═══════════════════════════════════════
// 配置 — 部署时改这里
// ═══════════════════════════════════════
const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://cad-flowers-dui-tires.trycloudflare.com';

const MATCH_TIMEOUT = 300000; // 300 秒超时（搜索+多轮AI调用需要时间）

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
// 进度条更新（v2: 适配9段表单）
// ═══════════════════════════════════════
function updateProgress() {
  let filled = 0;
  const total = 10; // 总权重

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
// 条件字段切换
// ═══════════════════════════════════════

/** 切换"其他"输入框 */
function toggleOther(wrapId) {
  const wrap = document.getElementById(wrapId + '-wrap');
  if (!wrap) return;
  const cb = document.querySelector(`input[name="${wrapId.replace('-wrap', '')}"][value="__OTHER__"]`);
  if (cb && cb.checked) {
    wrap.classList.add('show');
    wrap.querySelector('input')?.focus();
  } else {
    wrap.classList.remove('show');
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
// 开始匹配（提交+轮询模式）
// ═══════════════════════════════════════
async function startMatch() {
  const profile = collectProfile();

  // 基础校验
  if (!profile.school || !profile.major || !profile.grade) {
    alert('请至少填写学校、专业和年级');
    return;
  }

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
    if (error.name === 'AbortError') {
      showError('匹配超时（超过 ' + MATCH_TIMEOUT/1000 + ' 秒）。请检查网络后重试。');
    } else if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      showError('无法连接到服务器。请检查后端是否已部署并运行。');
    } else {
      showError(error.message || '未知错误');
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

  // 添加平台技术说明
  document.getElementById('resultArea').insertAdjacentHTML('beforeend',
    '<div class="platform-note">🏗️ 赛赋 SaiFu | AI驱动 · 常识库校验 · 多源交叉验证 | Powered by DeepSeek</div>'
  );

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

  return `
    <div class="comp-card ${topClass}">
      <div class="card-header">
        <div class="card-score">${score} <small>分</small></div>
        <div class="card-name">${escHtml(name)}</div>
        <div class="card-meta">
          <span class="card-tag tag-cat">${escHtml(cat)}</span>
          ${focusLabels}
          <span class="card-tag tag-score">${stars} ${wiText}</span>
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
      </div>
      <div class="card-footer">
        <span>📌 ${ptText}</span>
        <span>${feeText}</span>
        <span>⏰ 截止: ${comp.registration_deadline || '未知'}</span>
        ${comp.official_url && comp.official_url !== '未知' ? `<span>🔗 <a href="${escHtml(comp.official_url)}" target="_blank">官网</a></span>` : ''}
      </div>
    </div>
  `;
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
    if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      showError('无法连接到服务器。请检查后端是否已部署并运行。');
    } else {
      showError(error.message || '未知错误');
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
  backBar.innerHTML = '<button class="btn btn-outline btn-sm" onclick="backToImport()">🔙 返回修改</button>';

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

  // 滚动到结果区
  area.scrollIntoView({ behavior: 'smooth' });
}

/**
 * 构建调研竞赛卡片（适配调研结果格式）
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

  // 焦点标签
  let focusLabels = '';
  (focus.split(',')).forEach(f => {
    f = f.trim();
    if (f.includes('保研')) focusLabels += '<span class="card-tag tag-focus">🎓保研加分</span> ';
    else if (f.includes('企业')) focusLabels += '<span class="card-tag tag-focus">💼企业直通</span> ';
    else if (f.includes('拿奖')) focusLabels += '<span class="card-tag tag-focus">🏆拿奖率高</span> ';
    else if (f.includes('锻炼')) focusLabels += '<span class="card-tag tag-focus">💪能力锻炼</span> ';
  });

  // 排名样式
  let topClass = '';
  if (index === 0) topClass = 'top-1';
  else if (index === 1) topClass = 'top-2';
  else if (index === 2) topClass = 'top-3';

  // 免费标识
  const feeIcon = fee === '免费' ? '🆓' : '💰';
  const feeText = feeIcon + ' ' + fee;

  return `
    <div class="comp-card ${topClass}">
      <div class="card-header">
        <div class="card-score">${score} <small>分</small></div>
        <div class="card-name">${escHtml(name)}</div>
        <div class="card-meta">
          ${focusLabels}
        </div>
      </div>
      <div class="card-body">
        ${reason ? '<p class="label">📝 匹配理由</p><p>' + escHtml(reason) + '</p>' : ''}
        ${preparation ? '<p class="label">🔧 需要准备</p><p>' + escHtml(preparation) + '</p>' : ''}
      </div>
      <div class="card-footer">
        <span>📌 ${escHtml(level)} | ${escHtml(form)}</span>
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
// 工具函数
// ═══════════════════════════════════════
function escHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
