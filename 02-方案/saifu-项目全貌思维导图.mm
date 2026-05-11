<?xml version="1.0" encoding="UTF-8"?>
<map version="0.9.0">
  <node TEXT="🏆 赛赋 SaiFu — AI驱动竞赛全流程辅助平台">
    <node TEXT="📍 项目定位">
      <node TEXT="核心价值：帮大学生找到最适合的竞赛">
        <node TEXT="搜索最新竞赛信息"/>
        <node TEXT="AI多维度匹配打分"/>
        <node TEXT="三层校验确保信息可靠"/>
      </node>
      <node TEXT="目标用户">
        <node TEXT="不知道能参加什么比赛的大学生"/>
        <node TEXT="双非/低年级信息不对称群体"/>
      </node>
      <node TEXT="当前状态：V1 CLI已完成 → V2网页MVP已跑通"/>
    </node>
    <node TEXT="🏗️ 三方向架构 (V3规划)">
      <node TEXT="通用层（三方向共用）">
        <node TEXT="调研 → 方案设计 → PPT路演 → 赛后沉淀"/>
      </node>
      <node TEXT="🏗️ 大创方向">
        <node TEXT="覆盖：大创/互联网+/挑战杯/三创赛等"/>
        <node TEXT="特征：方案写作 + 答辩展示"/>
        <node TEXT="侧重：项目可行性 + 创新点 + 政策分析"/>
      </node>
      <node TEXT="💼 商赛方向">
        <node TEXT="覆盖：欧莱雅/宝洁/贝恩等企业赛"/>
        <node TEXT="特征：商业分析 + 案例研究"/>
        <node TEXT="侧重：市场分析 + 竞品分析 + 盈利模型"/>
      </node>
      <node TEXT="📊 数模方向">
        <node TEXT="建模路线：国赛/美赛等"/>
        <node TEXT="知识竞技变体：蓝桥杯/ACM/英语竞赛"/>
        <node TEXT="侧重：72h时间线 + 建模+编程+论文"/>
      </node>
      <node TEXT="入口设计：A/B双路径">
        <node TEXT="Path A：我知道要参加什么 → 直接归类"/>
        <node TEXT="Path B：我不知道 → AI多维度推荐"/>
      </node>
    </node>
    <node TEXT="💻 当前代码实现 (saifu/ V2 MVP)">
      <node TEXT="后端：FastAPI (Python) — 6模块">
        <node TEXT="main.py — API入口（3个端点）"/>
        <node TEXT="config.py — 统一配置+环境变量"/>
        <node TEXT="match/engine.py — 匹配引擎8步主流程"/>
        <node TEXT="services/ai_client.py — DeepSeek调用+JSON修复"/>
        <node TEXT="services/search.py — 搜索词生成+DuckDuckGo搜索"/>
        <node TEXT="services/knowledge_base.py — 9个竞赛常识库"/>
        <node TEXT="services/validation.py — L1交叉验证+L2自审查"/>
      </node>
      <node TEXT="前端：原生HTML/CSS/JS">
        <node TEXT="index.html — 4步折叠表单+结果展示区"/>
        <node TEXT="app.js — 表单收集+API调用+卡片渲染"/>
        <node TEXT="style.css — 响应式+卡片+动画"/>
      </node>
      <node TEXT="API端点">
        <node TEXT="GET /api/health — 健康检查"/>
        <node TEXT="GET /api/competitions — 常识库9条竞赛"/>
        <node TEXT="POST /api/match — 智能匹配(30-60秒)"/>
      </node>
    </node>
    <node TEXT="⚙️ 匹配引擎8步流程">
      <node TEXT="步骤1：生成20+条搜索关键词">
        <node TEXT="热门竞赛精确查询 + 专业相关 + 保研/企业维度"/>
      </node>
      <node TEXT="步骤2：DuckDuckGo搜索执行+URL去重"/>
      <node TEXT="步骤3：LLM两轮匹配">
        <node TEXT="报名中竞赛：至少输出12条"/>
        <node TEXT="已截止竞赛：最多1条含金量最高的"/>
        <node TEXT="打分维度：专业匹配30+兴趣30+年级20+可操作20"/>
      </node>
      <node TEXT="步骤4：常识库修正">
        <node TEXT="9个竞赛权威信息覆盖：官网/时间/费用/组别"/>
      </node>
      <node TEXT="步骤5：L1跨搜索结果交叉验证">
        <node TEXT="多个来源日期一致性比对"/>
        <node TEXT="偏差>60天标注低置信度"/>
      </node>
      <node TEXT="步骤6：L2 LLM自审查">
        <node TEXT="LLM以审查员角色挑错：日期/URL/费用/逻辑/遗漏"/>
      </node>
      <node TEXT="步骤7：分离resource+过滤低分+排序+去重"/>
      <node TEXT="步骤8：补充分类/六大好处/避坑提醒/真实案例"/>
    </node>
    <node TEXT="🌐 部署架构">
      <node TEXT="前端：Vercel（香港节点）→ ¥0/月"/>
      <node TEXT="后端隧道：Cloudflare Tunnel → ¥0/月"/>
      <node TEXT="后端本地：你的电脑 localhost:8000"/>
      <node TEXT="AI API：DeepSeek → ¥0.2-0.5/次匹配"/>
      <node TEXT="代码仓库：GitHub guolei95/saifu → ¥0"/>
      <node TEXT="总成本：¥0月费 + token钱"/>
    </node>
    <node TEXT="⚠️ 当前限制 &amp; 改进方向">
      <node TEXT="已知限制">
        <node TEXT="后端依赖本地电脑（关机=服务中断）"/>
        <node TEXT="Tunnel URL重启即变（需手动更新前端API地址）"/>
        <node TEXT="DuckDuckGo限速风险+国内需翻墙"/>
        <node TEXT="API Key写入README（安全隐患）"/>
        <node TEXT="无用户认证系统"/>
      </node>
      <node TEXT="改进方向">
        <node TEXT="后端迁到Render/阿里云（24h在线）"/>
        <node TEXT="环境变量管理敏感信息"/>
        <node TEXT="添加用户反馈纠正系统"/>
        <node TEXT="完善V3全部方向功能"/>
      </node>
    </node>
    <node TEXT="💬 见技术顾问 — 沟通策略">
      <node TEXT="核心心态：不是求人，是找技术合伙人"/>
      <node TEXT="3句话介绍项目">
        <node TEXT="做什么：AI竞赛匹配平台"/>
        <node TEXT="怎么做：搜索+LLM匹配+三层校验"/>
        <node TEXT="现状：已跑通，需要技术把关"/>
      </node>
      <node TEXT="诚实表达">
        <node TEXT="代码AI写的，但花了一周调试"/>
        <node TEXT="大一基础弱，但能讲清8步匹配流程"/>
      </node>
      <node TEXT="3个展示亮点">
        <node TEXT="① 三层校验体系（常识库+交叉验证+自审查）"/>
        <node TEXT="② 零月费部署方案"/>
        <node TEXT="③ V3三方向架构规划"/>
      </node>
      <node TEXT="4个要问的具体问题">
        <node TEXT="免费后端24h部署方案推荐？"/>
        <node TEXT="代码安全有什么明显漏洞？"/>
        <node TEXT="评审时AI驱动产品如何包装？"/>
        <node TEXT="FastAPI/异步学习路径建议？"/>
      </node>
      <node TEXT="带什么去">
        <node TEXT="现场演示网站 saifu-75e4.vercel.app"/>
        <node TEXT="三方向架构文档（打印/手机）"/>
        <node TEXT="README"/>
        <node TEXT="写好的问题清单"/>
      </node>
    </node>
    <node TEXT="👥 团队与分工">
      <node TEXT="小雷：产品/技术+商业计划书第3/4/1/9章"/>
      <node TEXT="商业A：调研分析+第2/5/7章"/>
      <node TEXT="商业B：商业设计+第6/8/10章"/>
      <node TEXT="设计：全书配图+附录原型+PPT终稿"/>
      <node TEXT="指导老师：待找 → 明天目标"/>
    </node>
  </node>
</map>
