<?xml version="1.0" encoding="UTF-8"?>
<map version="0.9.0">
  <node TEXT="🏆 赛赋 SaiFu — AI驱动竞赛全流程辅助平台">
    <node TEXT="📍 项目定位（核心纠正）">
      <node TEXT="一句话：AI驱动的竞赛全流程辅助平台">
        <node TEXT="帮大学生从选赛到拿奖走完全程"/>
        <node TEXT="不只是搜比赛，是AI教练全程陪跑"/>
      </node>
      <node TEXT="正确说法 vs 错误说法">
        <node TEXT="❌ 用AI帮学生选竞赛的网站"/>
        <node TEXT="✅ AI驱动竞赛全流程辅助平台"/>
        <node TEXT="❌ 竞赛搜索引擎"/>
        <node TEXT="✅ 竞赛决策+执行系统"/>
        <node TEXT="❌ AI匹配推荐工具"/>
        <node TEXT="✅ AI匹配+全程陪跑：调研→方案→PPT→答辩"/>
      </node>
      <node TEXT="全流程链路">
        <node TEXT="选赛匹配 → 调研辅助 → 方案撰写 → AI评审改稿 → PPT路演 → 答辩准备 → 赛后复盘"/>
      </node>
      <node TEXT="目标用户">
        <node TEXT="不知道能参加什么比赛的大学生"/>
        <node TEXT="双非/低年级信息不对称群体"/>
        <node TEXT="想参赛但不知从何下手的人"/>
      </node>
    </node>
    <node TEXT="🏗️ 三方向架构 (V3规划)">
      <node TEXT="通用层（三方向共用）">
        <node TEXT="调研 → 方案设计 → PPT路演 → 赛后沉淀"/>
      </node>
      <node TEXT="🏗️ 大创方向">
        <node TEXT="覆盖：大创/互联网+/挑战杯/三创赛等"/>
        <node TEXT="全流程：选赛→调研→方案框架→分章撰写→AI评审→PPT→答辩"/>
        <node TEXT="侧重：项目可行性+创新点+政策分析"/>
      </node>
      <node TEXT="💼 商赛方向">
        <node TEXT="覆盖：欧莱雅/宝洁/贝恩/联合利华等企业赛"/>
        <node TEXT="全流程：选赛→市场分析→竞品分析→商业逻辑→PPT路演"/>
        <node TEXT="侧重：盈利模型+落地性+创意立意"/>
      </node>
      <node TEXT="📊 数模方向">
        <node TEXT="建模路线：国赛/美赛（72h时间线+建模+编程+论文）"/>
        <node TEXT="知识竞技变体：蓝桥杯/ACM/英语竞赛"/>
        <node TEXT="流程：备赛规划→学习→刷题→模考→赛后"/>
      </node>
      <node TEXT="入口：A/B双路径">
        <node TEXT="A：我知道要参加什么 → 直接归类到方向"/>
        <node TEXT="B：我不知道 → AI多维度打分推荐Top5"/>
      </node>
    </node>
    <node TEXT="💻 当前代码实现 (saifu/ V2 MVP)">
      <node TEXT="后端 FastAPI — 6模块">
        <node TEXT="main.py：3个API端点(health/competitions/match)"/>
        <node TEXT="match/engine.py：匹配引擎8步主流程"/>
        <node TEXT="services/ai_client.py：DeepSeek调用+JSON修复"/>
        <node TEXT="services/search.py：20+搜索词生成+DuckDuckGo"/>
        <node TEXT="services/knowledge_base.py：9个竞赛常识库"/>
        <node TEXT="services/validation.py：L1交叉验证+L2自审查"/>
      </node>
      <node TEXT="前端 原生HTML/CSS/JS">
        <node TEXT="4步折叠表单 → 收集用户画像"/>
        <node TEXT="AI匹配按钮 → 30-60秒返回结果"/>
        <node TEXT="卡片渲染：分数+标签+匹配理由+避坑提醒"/>
      </node>
      <node TEXT="已跑通的核心能力">
        <node TEXT="8步匹配流程完整可用"/>
        <node TEXT="三层校验（常识库+交叉验证+自审查）"/>
        <node TEXT="零成本部署（Vercel+Cloudflare Tunnel）"/>
      </node>
    </node>
    <node TEXT="⚙️ 匹配引擎8步（核心竞争力）">
      <node TEXT="① 生成20+条搜索关键词"/>
      <node TEXT="② DuckDuckGo搜索+URL去重"/>
      <node TEXT="③ LLM两轮匹配(报名中至少12条+已截止最多1条)"/>
      <node TEXT="④ 常识库修正(9个竞赛权威官网/时间/费用)"/>
      <node TEXT="⑤ L1交叉验证(多来源日期一致性比对)"/>
      <node TEXT="⑥ L2 LLM自审查(AI审查员角色挑5类错误)"/>
      <node TEXT="⑦ 过滤低分(50分以下)+排序+去重"/>
      <node TEXT="⑧ 补充分类/六大好处/避坑提醒/真实案例"/>
    </node>
    <node TEXT="🌐 部署架构（零月费）">
      <node TEXT="前端 Vercel 香港节点 → ¥0"/>
      <node TEXT="后端 Cloudflare Tunnel 穿透本地 → ¥0"/>
      <node TEXT="AI API DeepSeek → ¥0.2-0.5/次匹配"/>
      <node TEXT="代码仓库 GitHub → ¥0"/>
      <node TEXT="总成本 ¥0月费+token钱"/>
    </node>
    <node TEXT="⚡ 能力边界：能做 vs 不能做">
      <node TEXT="✅ V2.5 能做（AI能扛+我能验证）">
        <node TEXT="竞赛方向自动归类+文件夹生成"/>
        <node TEXT="简单用户系统(SQLite+注册/登录)"/>
        <node TEXT="单聊天框+模式切换(替代多窗口+交接包)"/>
        <node TEXT="项目管理CRUD+匹配关联项目"/>
        <node TEXT="后端迁移Render(24h在线)"/>
      </node>
      <node TEXT="❌ V3 做不了（当前能力不够）">
        <node TEXT="多聊天框并行工作区(需React)"/>
        <node TEXT="完整AI交接包(需NLP语义摘要)"/>
        <node TEXT="拖拽式布局(前端复杂度爆炸)"/>
        <node TEXT="实时多人协作(需WebSocket)"/>
      </node>
    </node>
    <node TEXT="💬 见技术顾问 — 完整沟通策略">
      <node TEXT="核心心态"/>
      <node TEXT="开场话术">
        <node TEXT="老师好，我是大一的，参加大创。我做了一个AI驱动的竞赛全流程辅助平台，帮大学生从选赛到拿奖走完全程。目前选赛匹配这部分代码跑通了，可以给您演示。"/>
      </node>
      <node TEXT="3个展示亮点">
        <node TEXT="① 三层校验体系（常识库+交叉验证+自审查）"/>
        <node TEXT="② 零月费部署方案"/>
        <node TEXT="③ 模块化三方向全流程架构"/>
      </node>
      <node TEXT="6个提问（按优先级排序）">
        <node TEXT="① 架构评判：8步匹配流程有无逻辑漏洞？"/>
        <node TEXT="② 安全检查：代码有无泄露/漏洞？"/>
        <node TEXT="③ 部署建议：免费24h在线方案推荐？"/>
        <node TEXT="④ AI合规：代码AI写的评审接受吗？"/>
        <node TEXT="⑤ 前端选型：学React还是继续原生？"/>
        <node TEXT="⑥ 评审包装：如何让评委看到全流程深度？"/>
      </node>
      <node TEXT="不要说 vs 应该说">
        <node TEXT="❌ 我什么都不会全靠AI"/>
        <node TEXT="✅ 核心逻辑我能讲清楚，框架细节还在学"/>
        <node TEXT="❌ 你觉得我这个项目行不行"/>
        <node TEXT="✅ 这几个地方我不确定做得对不对"/>
      </node>
      <node TEXT="携带清单">
        <node TEXT="手机演示网站"/>
        <node TEXT="三方向架构文档"/>
        <node TEXT="这份思维导图"/>
        <node TEXT="6个问题清单+笔记本"/>
      </node>
    </node>
    <node TEXT="🎤 答辩评委预判Q&amp;A">
      <node TEXT="Q1：不就是套AI壳子吗？">
        <node TEXT="答：技术含量在三层校验+模块架构+零成本部署"/>
      </node>
      <node TEXT="Q2：大一代码是你写的吗？">
        <node TEXT="答：流程我设计、逻辑我定、AI只是写代码的工具"/>
      </node>
      <node TEXT="Q3：别人已经做了你为什么还要做？">
        <node TEXT="答：现有平台只聚合信息，我们做决策+执行全流程"/>
      </node>
      <node TEXT="Q4：AI推荐不准怎么办？">
        <node TEXT="答：三层校验+前端提醒+辅助不替代决策"/>
      </node>
    </node>
    <node TEXT="👥 团队与分工">
      <node TEXT="小雷：产品/技术+商业计划书第3/4/1/9章"/>
      <node TEXT="商业A：调研分析+第2/5/7章"/>
      <node TEXT="商业B：商业设计+第6/8/10章"/>
      <node TEXT="设计队友：全书配图+附录原型+PPT终稿"/>
      <node TEXT="指导老师：待找 → 明天目标"/>
    </node>
  </node>
</map>
