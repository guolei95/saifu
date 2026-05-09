/**
 * 赛赋 SaiFu — 前端交互逻辑
 */

// ═══════════════════════════════════════
// 配置 — 部署时改这里
// ═══════════════════════════════════════
const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://vision-runtime-disturbed-pending.trycloudflare.com';

const MATCH_TIMEOUT = 300000; // 300 秒超时（搜索+多轮AI调用需要时间）

// ═══════════════════════════════════════
// 折叠区块
// ═══════════════════════════════════════
function toggleSection(num) {
  const el = document.getElementById('section' + num);
  const body = el.querySelector('.section-body');
  const isOpen = el.classList.contains('open');
  if (isOpen) {
    el.classList.remove('open');
    body.style.display = 'none';
  } else {
    el.classList.add('open');
    body.style.display = 'block';
  }
  updateProgress();
}

// ═══════════════════════════════════════
// 进度条更新
// ═══════════════════════════════════════
function updateProgress() {
  const fields = ['school', 'major', 'grade'];
  let filled = 0;
  fields.forEach(id => {
    const el = document.getElementById(id);
    if (el && el.value.trim()) filled++;
  });
  // 检查 checkbox 组
  const goalsChecked = document.querySelectorAll('.checkbox-group input:checked').length;
  if (goalsChecked > 0) filled++;

  const percent = Math.min(100, Math.round((filled / Math.max(fields.length, 1)) * 100));
  document.getElementById('progressFill').style.width = percent + '%';
  document.getElementById('progressPercent').textContent = percent + '%';
}

// 监听所有表单变化更新进度
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', updateProgress);
    el.addEventListener('input', updateProgress);
  });
});

// ═══════════════════════════════════════
// 收集用户画像
// ═══════════════════════════════════════
function collectProfile() {
  const goals = [];
  document.querySelectorAll('.checkbox-group input:checked').forEach(cb => {
    goals.push(cb.value);
  });

  const techDirs = [];
  document.querySelectorAll('input[name="tech_direction"]:checked').forEach(cb => {
    techDirs.push(cb.value);
  });

  return {
    school: document.getElementById('school')?.value?.trim() || '',
    major: document.getElementById('major')?.value?.trim() || '',
    grade: document.getElementById('grade')?.value || '',
    interests: document.getElementById('interests')?.value?.trim() || '',
    skills: document.getElementById('skills')?.value?.trim() || '',
    tech_directions: techDirs,
    tools: (document.getElementById('tools')?.value?.trim() || '').split(/[,，、]/).filter(Boolean),
    other_skills: '',
    goals: goals,
    time_commitment: document.getElementById('time_commitment')?.value || '',
    available_months: '',
    summer_winter: '',
    preference: document.getElementById('preference')?.value || '',
    team_preference: document.getElementById('team_preference')?.value || '',
    preferred_duration: '',
    preferred_format: '',
    fee_budget: document.getElementById('fee_budget')?.value || '',
    language_pref: '中文',
    has_advisor: document.getElementById('has_advisor')?.value || '',
    can_cross_school: document.getElementById('can_cross_school')?.value || '',
    avoid_types: document.getElementById('avoid_types')?.value?.trim() || '',
    past_highest_award: document.getElementById('past_highest_award')?.value || '',
    representative_projects: [],
    has_portfolio: false,
    portfolio_link: '',
    has_lab: false,
    join_school_team: false,
    need_teammate: false,
    min_award: '',
    ideal_goal: document.getElementById('ideal_goal')?.value?.trim() || '',
    strategy: document.getElementById('strategy')?.value || '',
  };
}

// ═══════════════════════════════════════
// 开始匹配
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
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), MATCH_TIMEOUT);

    const response = await fetch(API_BASE_URL + '/api/match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`服务器返回错误: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '匹配失败');
    }

    // 渲染结果
    renderResults(data);

  } catch (error) {
    if (error.name === 'AbortError') {
      showError('匹配超时（超过 120 秒）。请检查网络后重试。');
    } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
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
  document.getElementById('errorArea').scrollIntoView({ behavior: 'smooth' });
}

function retryMatch() {
  document.getElementById('errorArea').style.display = 'none';
  document.getElementById('formArea').style.display = 'block';
  document.getElementById('formArea').scrollIntoView({ behavior: 'smooth' });
}

// ═══════════════════════════════════════
// 渲染匹配结果
// ═══════════════════════════════════════
function renderResults(data) {
  document.getElementById('resultArea').style.display = 'block';

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
// 工具函数
// ═══════════════════════════════════════
function escHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
