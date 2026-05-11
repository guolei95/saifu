<?xml version="1.0" encoding="UTF-8"?>
<map version="0.9.0">
  <node TEXT="🏆 赛赋 SaiFu — AI驱动竞赛全流程辅助平台（选赛→调研→方案→PPT→答辩→复盘）">
    <node TEXT="📍 项目定位">
      <node TEXT="核心价值：帮大学生从选赛到拿奖走完全程">
        <node TEXT="不只搜比赛，是AI教练全程陪跑"/>
        <node TEXT="选赛匹配 → 调研辅助 → 方案撰写 → PPT路演 → 赛后复盘"/>
        <node TEXT="定位：决策+执行系统，不是信息聚合"/>
      </node>
      <node TEXT="目标用户">
        <node TEXT="不知道能参加什么比赛的大学生"/>
        <node TEXT="双非/低年级信息不对称群体"/>
        <node TEXT="想参赛但不知道从哪下手的人"/>
      </node>
      <node TEXT="当前状态：V1 CLI完成 → V2网页MVP已跑通（选赛匹配）"/>
    </node>
    <node TEXT="🏗️ 三方向架构 (V3规划)">
      <node TEXT="通用层（三方向共用）">
        <node TEXT="调研 → 方案设计 → PPT路演 → 赛后沉淀"/>
      </node>
      <node TEXT="🏗️ 大创方向">
        <node TEXT="覆盖：大创/互联网+/挑战杯/三创赛等"/>
        <node TEXT="全流程：选赛→调研→方案→AI评审→PPT→答辩"/>
        <node TEXT="侧重：项目可行性 + 创新点 + 政策分析"/>
      </node>
      <node TEXT="💼 商赛方向">
        <node TEXT="覆盖：欧莱雅/宝洁/贝恩等企业赛"/>
        <node TEXT="全流程：选赛→市场分析→商业逻辑→PPT路演"/>
        <node TEXT="侧重：竞品分析 + 盈利模型 + 落地性"/>
      </node>
      <node TEXT="📊 数模方向">
        <node TEXT="建模路线：国赛/美赛（72h时间线+建模+编程+论文）"/>
        <node TEXT="知识竞技变体：蓝桥杯/ACM（备赛规划+学习+刷题+模考）"/>
      </node>
      <node TEXT="入口：A/B双路径">
        <node TEXT="Path A：我知道要参加什么 → 直接归类"/>
        <node TEXT="Path B：我不知道 → AI多维度推荐"/>
      </node>
    </node>
    <node TEXT="💻 当前代码实现 (saifu/ V2 MVP)">
      <node TEXT="后端：FastAPI (Python) — 6模块">
        <node TEXT="main.py — API入口（3个端点）"/>
        <node TEXT="match/engine.py — 匹配引擎8步主流程"/>
        <node TEXT="services/ai_client.py — DeepSeek+JSON修复"/>
        <node TEXT="services/search.py — 搜索词+DuckDuckGo"/>
        <node TEXT="services/knowledge_base.py — 9竞赛常识库"/>
        <node TEXT="services/validation.py — L1交叉验证+L2自审查"/>
      </node>
      <node TEXT="前端：原生HTML/CSS/JS">
        <node TEXT="4步折叠表单 → AI匹配 → 结果卡片渲染"/>
      </node>
      <node TEXT="已跑通：8步匹配+三层校验+零成本部署"/>
    </node>
    <node TEXT="⚙️ 匹配引擎8步流程（核心竞争力）">
      <node TEXT="① 生成20+条搜索关键词"/>
      <node TEXT="② DuckDuckGo搜索+URL去重"/>
      <node TEXT="③ LLM两轮匹配（报名中+已截止）"/>
      <node TEXT="④ 常识库修正（9个竞赛权威信息）"/>
      <node TEXT="⑤ L1交叉验证（多来源日期比对）"/>
      <node TEXT="⑥ L2 LLM自审查（审查员角色挑错）"/>
      <node TEXT="⑦ 过滤低分+排序+去重"/>
      <node TEXT="⑧ 补充分类/好处/避坑/案例"/>
    </node>
    <node TEXT="🌐 部署架构（零月费）">
      <node TEXT="前端：Vercel 香港节点 → ¥0"/>
      <node TEXT="后端隧道：Cloudflare Tunnel → ¥0"/>
      <node TEXT="AI API：DeepSeek → ¥0.2-0.5/次"/>
      <node TEXT="总成本：¥0月费 + token钱"/>
    </node>
    <node TEXT="⚠️ 当前限制 &amp; V2.5计划">
      <node TEXT="已知限制">
        <node TEXT="后端依赖本地电脑（关机=中断）"/>
        <node TEXT="Tunnel URL重启即变"/>
        <node TEXT="DuckDuckGo需翻墙+限速"/>
        <node TEXT="无用户系统/无多项目管理"/>
      </node>
      <node TEXT="V2.5 能做（AI能扛住）">
        <node TEXT="方向归类+文件夹自动生成"/>
        <node TEXT="简单用户系统（SQLite）"/>
        <node TEXT="单聊天框+模式切换（替代交接包）"/>
        <node TEXT="后端迁Render（24h在线）"/>
      </node>
      <node TEXT="V3 做不了（当前能力不够）">
        <node TEXT="多窗口工作区（需React）"/>
        <node TEXT="完整交接包机制（需NLP摘要）"/>
        <node TEXT="实时协作（需WebSocket）"/>
      </node>
    </node>
    <node TEXT="💬 见技术顾问 — 沟通策略">
      <node TEXT="核心心态：不是求人，是找技术合伙人"/>
      <node TEXT="一句话定位（必须说对）">
        <node TEXT="❌ 错误：用AI帮学生选竞赛的网站"/>
        <node TEXT="✅ 正确：AI驱动竞赛全流程辅助平台"/>
        <node TEXT="❌ 错误：竞赛搜索引擎"/>
        <node TEXT="✅ 正确：竞赛决策+执行系统"/>
        <node TEXT="❌ 错误：AI匹配推荐"/>
        <node TEXT="✅ 正确：AI匹配+全程陪跑：调研→方案→PPT→答辩"/>
      </node>
      <node TEXT="3句话介绍">
        <node TEXT="做什么：全流程AI竞赛助手（选赛→拿奖）"/>
        <node TEXT="怎么做：搜索+LLM匹配+三层校验+三方向全流程"/>
        <node TEXT="现状：选赛匹配已跑通，全流程架构已规划"/>
      </node>
      <node TEXT="3个展示亮点">
        <node TEXT="① 三层校验（常识库+交叉验证+自审查）"/>
        <node TEXT="② 零月费部署方案"/>
        <node TEXT="③ 模块化三方向架构"/>
      </node>
      <node TEXT="6个要问的问题（按优先级）">
        <node TEXT="① 技术架构：8步流程有无逻辑漏洞？"/>
        <node TEXT="② 安全：代码有无泄露/漏洞？"/>
        <node TEXT="③ 部署：免费24h方案推荐？"/>
        <node TEXT="④ 合规：AI写代码评审接受吗？"/>
        <node TEXT="⑤ 前端：该学React还是继续原生？"/>
        <node TEXT="⑥ 包装：如何让评委看到全流程深度？"/>
      </node>
      <node TEXT="带什么去">
        <node TEXT="现场演示网站"/>
        <node TEXT="三方向架构文档"/>
        <node TEXT="这份思维导图"/>
        <node TEXT="写好的6个问题清单"/>
      </node>
    </node>
    <node TEXT="🎤 答辩评委预判Q&amp;A">
      <node TEXT="Q1：套AI壳子？">
        <node TEXT="答：三层校验+模块架构+零成本"/>
      </node>
      <node TEXT="Q2：大一代码谁写的？">
        <node TEXT="答：流程我设计，AI只是工具"/>
      </node>
      <node TEXT="Q3：别人做了你为什么做？">
        <node TEXT="答：他们聚合信息，我们做决策+执行全流程"/>
      </node>
      <node TEXT="Q4：AI不准怎么办？">
        <node TEXT="答：三层校验+前端提醒+辅助不替代"/>
      </node>
    </node>
    <node TEXT="👥 团队与分工">
      <node TEXT="小雷：产品/技术+商业计划书3/4/1/9章"/>
      <node TEXT="商业A：调研分析+第2/5/7章"/>
      <node TEXT="商业B：商业设计+第6/8/10章"/>
      <node TEXT="设计：全书配图+附录原型+PPT终稿"/>
      <node TEXT="指导老师：待找 → 明天目标"/>
    </node>
  </node>
</map>
