import {DEFAULT_INTERVALS,localDay,daysBetween,emptyState,cardFor,dueQuestions,recordAnswer,markStudied,filterQuestions,makePlan,validateBackup,sameAnswers} from './core.mjs';

const $=s=>document.querySelector(s), app=$('#app');
const e=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const KEY='jiakao-learning-v1', SUBJECTS={subject1:'科目一',subject3_safe:'安全文明驾驶常识'};
const KIND={true_false:'判断题',single:'单选题',multiple:'多选题'};
const MILESTONES=[['registration','报名与体检','确认报名、身体条件与驾校培训安排'],['subject1','科目一','法规学习 → 分章练习 → 错题巩固'],['practical2','科目二训练与考试','按教练安排训练，记录尚不熟练的项目'],['practical3','科目三道路训练与考试','在教练指导下完成道路训练与考试'],['subject3_safe','安全文明驾驶常识','风险识别 → 场景练习 → 错题回顾'],['license','领证与实习期学习','核对领证手续，继续学习实习期要求']];
let bank, state=emptyState(), page='home', topic='all', session=null, lesson=null, volatile=false;
const badImages=new Set(), loadedImages=new Set();
const today=()=>localDay();
const fmt=t=>t?new Date(t).toLocaleString('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}):'已完成';
function toast(text){$('#toast').textContent=text;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,5000);}
function save(){try{localStorage.setItem(KEY,JSON.stringify(state));}catch{volatile=true;toast('浏览器无法保存进度，请及时导出备份；本次仍可继续学习。');}}
const available=()=>bank.questions.filter(q=>!badImages.has(q.id));
const scoped=()=>filterQuestions(available(),{...state.profile,topic});
const wholeScope=()=>filterQuestions(available(),state.profile);
const topics=()=>{const map=new Map();for(const q of wholeScope())for(const t of q.topics)map.set(t,q.topic_labels[t]);return [...map];};
function button(text,action,secondary=false,extra=''){return `<button class="button ${secondary?'secondary':''}" data-action="${action}" ${extra}>${text}</button>`;}
function head(kicker,title,subtitle){return `<div class="page-head"><div><div class="kicker">${e(kicker)}</div><h1>${e(title)}</h1><p class="subtle">${e(subtitle)}</p></div><span class="pill">${e(SUBJECTS[state.profile.subject])}</span></div>`;}
function scopeControls(withTopic=false){return `<div class="filters"><label><span class="field-label">学习科目</span><select id="scope-subject">${Object.entries(SUBJECTS).map(([id,label])=>`<option value="${id}" ${id===state.profile.subject?'selected':''}>${label}</option>`).join('')}</select></label><label><span class="field-label">题目适用范围</span><select id="scope-vehicle"><option value="unassigned" ${state.profile.vehicle==='unassigned'?'selected':''}>导入题 · 车型待核验</option>${bank.vehicles.map(v=>`<option value="${e(v.code)}" ${v.code===state.profile.vehicle?'selected':''}>${e(v.code+' · '+v.name)}</option>`).join('')}</select></label>${withTopic?`<label><span class="field-label">考点 / 章节</span><select id="scope-topic"><option value="all">全部章节</option>${topics().map(([id,label])=>`<option value="${e(id)}" ${id===topic?'selected':''}>${e(label)}</option>`).join('')}</select></label>`:''}</div>${state.profile.vehicle==='unassigned'?'<div class="notice">当前为未标注车型的导入资料，仅用于资料练习。选择具体车型时，只展示已有明确适用标记的题目。</div>':''}`;}
function empty(text='当前范围暂无完整题目。请切换科目或适用范围；未标注车型的题目不会自动分配到具体车型。'){return `<div class="empty">${e(text)}</div>`;}
function go(view){page=view;session=null;lesson=null;history.replaceState(null,'','#'+view);window.scrollTo(0,0);render();}
function start(mode,ids=null){
  const qs=mode==='review'?dueQuestions(scoped(),state):scoped();
  const chosen=ids?ids.map(id=>qs.find(q=>q.id===id)).filter(Boolean):qs;
  const ordered=mode==='practice'&&!ids?[...chosen].sort((a,b)=>(cardFor(state,a).attempts>0)-(cardFor(state,b).attempts>0)):chosen;
  session={mode,ids:ordered.slice(0,20).map(q=>q.id),index:0,selected:[],submitted:false,correct:0,answered:0,eventId:null};
  page=mode==='review'?'review':'practice';history.replaceState(null,'','#'+page);render();
}
function overview(){
  const qs=wholeScope(),plan=makePlan(qs,state,state.profile), completed=qs.filter(q=>cardFor(state,q).attempts).length;
  const attempts=qs.reduce((n,q)=>n+cardFor(state,q).attempts,0), correct=qs.reduce((n,q)=>n+cardFor(state,q).correct,0);
  const studied=qs.filter(q=>cardFor(state,q).studiedAt).length, percent=qs.length?Math.round(completed/qs.length*100):0;
  return head('YOUR DAILY ROUTE','今天，也离上路更近一步。','先理解，再练习。把每一次错题，变成下一次的从容。')+
    `<section class="hero"><div><div class="kicker">今日学习 · ${e(plan.stage)}</div><h2>${plan.due?`有 ${plan.due} 道错题，等你再见一面。`:'保持一点节奏，积累一点把握。'}</h2><p>距离目标日期还有 ${plan.days} 天。今天建议练习 ${plan.newTarget} 道新题，优先复习 ${plan.reviewSlots} 道到期错题。</p><div class="actions">${button(plan.due?'开始错题复习 →':'开始今日练习 →',plan.due?'start-review':'start-practice')}${button('调整学习计划','go-plan',true)}</div></div><div class="road-art" aria-hidden="true"></div></section>`+
    `<div class="stats">${[['可练完整题',qs.length,'当前科目与范围'],['已练题目',completed,`覆盖进度 ${percent}%`],['到期错题',plan.due,'答对后延长复习间隔'],['练习正确率',attempts?Math.round(correct/attempts*100)+'%':'—',attempts?`累计作答 ${attempts} 次`:'从第一次练习开始']].map(([label,value,note])=>`<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-note">${note}</div></div>`).join('')}</div>`+
    `<div class="two-col"><section class="panel"><div class="section-title"><h2>今天的学习路线</h2><span class="subtle tiny">${state.profile.dailyMinutes} 分钟 / 天</span></div><div class="task"><span class="task-number">01</span><div class="task-text"><h3>先学考点，理解为什么</h3><p>已学习 ${studied} 道题的知识卡片</p></div>${button('去学习','go-learn',true)}</div><div class="task"><span class="task-number">02</span><div class="task-text"><h3>分章练习，检验理解</h3><p>今日新题目标 ${plan.newTarget} 道；每轮最多 20 道</p></div>${button('去练习','start-practice',true)}</div><div class="task"><span class="task-number">03</span><div class="task-text"><h3>到期错题，主动回想</h3><p>${plan.due?`${plan.due} 道到期，${plan.activeWrong} 道仍在复习周期`:'错题会在这里按时等你'}</p></div>${button('去复习','go-review',true)}</div></section><section class="panel"><div class="section-title"><h2>学习进度</h2><span class="pill">${percent}%</span></div><div class="progress"><span style="width:${percent}%"></span></div><p class="subtle tiny">已练 ${completed} / ${qs.length} 道完整题目</p>${[['建立知识框架','按章节阅读知识卡片'],['练习与纠错','选答案，再查看解析'],['间隔复习','答错重新安排，答对逐步延长']].map(([a,b],i)=>`<div class="stage-row ${i===0?'done':''}"><div class="stage-line">${i+1}</div><div><h3>${a}</h3><p>${b}</p></div></div>`).join('')}</section></div>`+
    scopeControls()+`<div class="notice">题库已排除 ${bank.summary.excluded} 道内容不完整或答案有争议的题。完整不等于答案已核验；导入资料的版本与适用范围仍需确认。${volatile?' 当前浏览器未能持久保存，请导出进度。':''}</div>`;
}
function learnView(){
  const qs=scoped();
  if(lesson){
    const q=qs.find(x=>x.id===lesson);
    if(!q){lesson=null;return learnView();}
    return head('LEARN FIRST','读懂这一题背后的知识','学习时可先看答案；进入练习后将重新隐藏。')+`<div class="panel question"><div class="question-header"><span>知识卡片</span><span>${e(Object.values(q.topic_labels).join(' / '))}</span></div><h2>${e(q.stem)}</h2>${imageHTML(q)}<p class="answer-line">正确选项：${e(q.answers.map(a=>a+' · '+q.options[a]).join('；'))}</p><div class="feedback"><h3>理解要点</h3><p>${e(q.explanation)}</p></div><p class="subtle tiny">读完后先尝试用自己的话解释，再进入练习。学习浏览不计作答正确率。</p><div class="actions">${button('理解了，进入练习','studied-practice')}${button('下一张知识卡','next-lesson',true)}${button('返回章节','back-lessons',true)}</div><div class="muted-box">${e(q.source_label)}</div></div>`;
  }
  const cards=topics().map(([id,label])=>{const items=wholeScope().filter(q=>q.topics.includes(id));const done=items.filter(q=>cardFor(state,q).studiedAt).length;return `<button class="topic-card" data-topic="${e(id)}"><div class="topic-icon">▤</div><h3>${e(label)}</h3><p>${items.length} 道知识卡 · 已学 ${done} 道</p><div class="progress"><span style="width:${Math.round(done/items.length*100)}%"></span></div></button>`;}).join('');
  return head('BUILD YOUR FOUNDATION','先理解，题目才记得住。','从考点或章节开始，把解析变成自己的理解。')+scopeControls()+ (qs.length?`<div class="topic-grid">${cards}</div>`:empty());
}
function imageHTML(q){return q.images.map(i=>`<img class="question-image" src="${e(i.path)}" alt="${e(i.alt)}" data-question="${e(q.id)}">`).join('');}
function practiceView(){
  return head('PRACTICE WITH PURPOSE','把理解，变成正确的选择。','答题前不展示答案。作答后立即查看解析，错题自动进入复习周期。')+scopeControls(true)+(scoped().length?`<div class="panel"><h2>按当前范围练习</h2><p class="subtle">当前有 ${scoped().length} 道完整题目，每轮最多 20 道，优先呈现未练题。</p><p class="subtle">已排除缺图、缺解析、答案不完整和已标记争议题。导入题作为学习资料，不承诺官方真题覆盖。</p><div class="actions">${button('开始这一轮 →','start-practice')}${button('先学习相关考点','go-learn',true)}</div></div>`:empty());
}
function renderQuestion(){
  const s=session;
  if(s.index>=s.ids.length){return head('SESSION COMPLETE',s.ids.length?'这一轮，学得不错。':'这轮暂时没有可练题。',s.ids.length?`完成 ${s.answered} 道，答对 ${s.correct} 道。每一次理解，都算数。`:'可能没有到期错题，或题目范围为空。')+`<div class="panel"><h2>${s.mode==='review'?'复习进度已保存':'练习进度已保存'}</h2><p class="subtle">错题在到期后才会推进间隔；提前重练不会跳过复习阶段。</p><div class="actions">${button('回到今日学习','go-home')}${button('查看错题安排','go-review',true)}</div></div>`;}
  const q=available().find(q=>q.id===s.ids[s.index]);
  if(!q){s.index++;return renderQuestion();}
  const selected=s.selected;
  const correct=s.submitted&&!s.uncertain&&sameAnswers(selected,q.answers);
  const c=cardFor(state,q), imageReady=q.images.every(i=>loadedImages.has(i.path));
  return `<div class="page-head"><div><div class="kicker">${s.mode==='review'?'SPACED REVIEW':'FOCUSED PRACTICE'}</div><h1>${s.mode==='review'?'到期错题复习':'专注这一题。'}</h1></div>${button('结束本轮','go-'+(s.mode==='review'?'review':'practice'),true)}</div><div class="panel question"><div class="question-header"><span>${e(KIND[q.kind])} · ${s.index+1} / ${s.ids.length}</span><span>${e(SUBJECTS[state.profile.subject])}</span></div><div class="progress"><span style="width:${Math.round(s.index/s.ids.length*100)}%"></span></div><h2>${e(q.stem)}</h2>${imageHTML(q)}<div class="options">${Object.entries(q.options).map(([key,text])=>`<button class="option ${selected.includes(key)?'selected':''} ${s.submitted?(q.answers.includes(key)?'correct':selected.includes(key)?'wrong':''):''}" data-option="${e(key)}" aria-pressed="${selected.includes(key)}" ${s.submitted||!imageReady?'disabled':''}><span class="option-key">${e(key)}</span><span>${e(text)}</span></button>`).join('')}</div>${q.kind==='multiple'&&!s.submitted?'<p class="subtle tiny">多选题：选出所有正确选项后，再提交。</p>':''}${!imageReady?'<p class="subtle tiny">正在加载题目配图…</p>':''}${s.submitted?`<div class="feedback ${correct?'':'error'}"><h3>${s.uncertain?'先理解，再记住。':correct?'答对了，继续保持。':'这一题，值得再看一遍。'}</h3><p class="answer-line">正确答案：${e(q.answers.join('、'))} · 你的答案：${e(selected.length?selected.join('、'):'不确定')}</p><p>${e(q.explanation)}</p>${!correct?`<p class="tiny">已安排首次 / 重新复习：${fmt(c.dueAt)}。答错不会直接删除题目。</p>`:c.wrongCount?`<p class="tiny">${c.mastered?'已完成本轮全部间隔复习。':`下一次复习：${fmt(c.dueAt)}。`}</p>`:''}</div><div class="actions">${button('下一题 →','next-question')}${button('回到考点学习','learn-current',true)}</div>`:`<div class="actions">${button('确认答案','submit-answer',false,selected.length&&imageReady?'':'disabled')}${button('不确定，查看解析','unsure-answer',true,imageReady?'':'disabled')}</div>`}<div class="muted-box">${e(q.source_label)} · ID ${e(q.id)}<br>解析展示原来源内容；不将 AI 生成解释冒充权威答案。</div></div>`;
}
function reviewView(){
  const qs=scoped(),due=dueQuestions(qs,state),wrong=qs.filter(q=>cardFor(state,q).wrongCount);
  const active=wrong.filter(q=>!cardFor(state,q).mastered).sort((a,b)=>cardFor(state,a).dueAt-cardFor(state,b).dueAt);
  return head('RECALL, THEN REMEMBER','把错题，变成熟悉的老朋友。','先回想并作答，再看解析。复习效果由实际答题表现决定。')+scopeControls()+`<div class="panel"><div class="section-title"><h2>${due.length} 道到期 · ${active.length} 道复习中</h2>${button('开始到期复习 →','start-review',false,due.length?'':'disabled')}</div><div class="intervals">${['10 分钟','1 天','3 天','7 天','14 天','30 天'].map(x=>`<span>${x}</span>`).join('')}</div><p class="subtle tiny">受遗忘规律启发的间隔默认值。答错或不确定从10分钟重新开始；到期答对推进一级。提前练习不升级，也不把未来任务算成已完成。</p></div>`+(active.length?`<div class="panel"><h2>错题与复习安排</h2>${active.slice(0,30).map(q=>{const c=cardFor(state,q);return `<div class="list-item"><div><h3>${e(q.stem)}</h3><p>答错 / 不确定 ${c.wrongCount} 次 · 第 ${c.stage+1} / ${DEFAULT_INTERVALS.length} 阶段 · ${c.dueAt<=Date.now()?'已到期':fmt(c.dueAt)}</p></div><button class="button small secondary" data-wrong-id="${e(q.id)}">${c.dueAt<=Date.now()?'复习':'提前重练'}</button></div>`;}).join('')}${active.length>30?`<p class="subtle tiny">仅展示最近30条安排；开始复习会从全部到期错题中取题。</p>`:''}</div>`:empty('当前没有待复习错题。完成练习后，答错或不确定的题会自动进入这里。'))+`<p class="subtle tiny">已完成间隔复习 ${wrong.length-active.length} 道。网页关闭时不会发送通知；再次打开时重新计算到期任务。</p>`;
}
function planView(){
  const qs=wholeScope();let plan;
  try{plan=makePlan(qs,state,state.profile);}catch{return planForm()+`<div class="notice warn">目标日期已过或参数无效，请重新设置。已有学习进度不会丢失。</div>`;}
  const total=qs.length,done=qs.filter(q=>cardFor(state,q).attempts>0).length;
  return head('A ROUTE MADE FOR YOU','按你的节奏，走完整个学车过程。','计划会随剩余天数、已练题量与到期错题动态调整。')+planForm()+
    `${plan.capacityWarning?`<div class="notice warn">当前时间预算不足以按默认节奏覆盖剩余 ${plan.remaining} 道题。仅完成新题覆盖预计每天至少需 ${plan.minimumMinutes} 分钟，尚未计入后续错题复习；可延后目标日期或增加每日时间。</div>`:''}${plan.reviewOverflow?`<div class="notice warn">今天有 ${plan.reviewOverflow} 道到期错题超出时间预算。先处理 ${plan.reviewSlots} 道，其余保持逾期待复习，不会自动算完成。</div>`:''}`+
    `<div class="plan-grid"><section class="panel"><h2>今天怎么学</h2><div class="task"><span class="task-number">01</span><div><h3>复习优先</h3><p>先完成 ${plan.reviewSlots} 道到期错题，今天共到期 ${plan.due} 道。</p></div></div><div class="task"><span class="task-number">02</span><div><h3>学习与新题</h3><p>再学相关知识卡，练习 ${plan.newTarget} 道未练题。</p></div></div><div class="task"><span class="task-number">03</span><div><h3>复盘易错点</h3><p>用自己的话说明错误原因，避免只记答案字母。</p></div></div><p class="subtle tiny">估算每题50秒，剩余日期的70%用于新题覆盖；实际用时因人而异。今日已作答 ${plan.todayActivity.attempts} 次、学习 ${plan.todayActivity.studied} 张卡。</p><div class="actions">${button('去完成今天的任务','go-home')}</div></section><section class="panel"><h2>当前科目的备考阶段</h2><div class="timeline">${[['前30%时间','建立框架','阅读知识卡片，熟悉章节与考点'],['中间40%时间','分章练习','完成新题覆盖，错题及时看解析'],['接着20%时间','错题巩固','优先复习到期与高频错题'],['最后10%时间','考前回顾','回顾薄弱章节与未完成错题']].map(([a,b,c])=>`<article><div class="kicker">${a}</div><h3>${b}</h3><p class="subtle tiny">${c}</p></article>`).join('')}</div><p class="subtle tiny">当前：${e(plan.stage)} · 已练 ${done}/${total} · 剩余 ${plan.days} 天。计划不保证考试通过。</p></section></div><section class="panel"><h2>整个学车过程 · 里程碑</h2><p class="subtle tiny">可设置各阶段目标日期并勾选完成。具体顺序、免考条件、实操课时与预约由驾校和当地规定确定；网页不自动预约考试。</p>${MILESTONES.map(([id,label,note])=>`<div class="milestone-row"><label class="milestone"><input type="checkbox" data-milestone="${id}" ${state.milestones[id]?'checked':''}><span><strong>${label}</strong><br><span class="subtle tiny">${note}</span></span></label><label class="milestone-date"><span class="field-label">${label}目标日期</span><input type="date" data-milestone-date="${id}" value="${e(state.milestoneDates[id]||'')}"></label></div>`).join('')}</section>`;
}
function planForm(){return `<form id="plan-form" class="panel"><h2>设置你的学习计划</h2><div class="filters"><label><span class="field-label">当前备考科目</span><select name="subject">${Object.entries(SUBJECTS).map(([id,t])=>`<option value="${id}" ${state.profile.subject===id?'selected':''}>${t}</option>`).join('')}</select></label><label><span class="field-label">目标考试日期</span><input name="examDate" type="date" required min="${today()}" value="${e(state.profile.examDate)}"></label><label><span class="field-label">每天学习时间（分钟）</span><input name="dailyMinutes" type="number" required min="5" max="240" step="1" value="${state.profile.dailyMinutes}"></label>${button('保存并重新安排','save-plan')}</div><p class="subtle tiny">题目范围：${e(state.profile.vehicle==='unassigned'?'车型待核验的导入资料':state.profile.vehicle)}。在今日学习或练习页面切换车型；切换科目和车型不会删除历史进度。</p></form>`;}
function render(){
  // An expired plan should not prevent practice or review.
  if(page==='home' && daysBetween(today(),state.profile.examDate)<0){page='plan';history.replaceState(null,'','#plan');}
  $('#nav').querySelectorAll('a').forEach(a=>a.classList.toggle('active',a.dataset.view===page));
  $('#due-badge').textContent=dueQuestions(wholeScope(),state).length;
  $('#source-label').textContent=bank.summary.source==='local'?`本地资料 · 完整题 ${bank.summary.accepted} 道 · 已排除 ${bank.summary.excluded} 道`:'公开样例 · 原创法规练习';
  $('#clock-date').textContent=new Date().toLocaleDateString('zh-CN',{month:'long',day:'numeric',weekday:'long'});
  app.innerHTML=session?renderQuestion():page==='home'?overview():page==='learn'?learnView():page==='practice'?practiceView():page==='review'?reviewView():planView();
  bindView();
}
function bindView(){
  for(const img of app.querySelectorAll('img[data-question]')){
    img.onload=()=>{if(!loadedImages.has(img.getAttribute('src'))){loadedImages.add(img.getAttribute('src'));if(session&&!session.submitted)render();}};
    img.onerror=()=>{const id=img.dataset.question;badImages.add(id);if(session){session.ids=session.ids.filter(x=>x!==id);session.selected=[];session.submitted=false;}if(lesson===id)lesson=null;toast('有题目配图无法加载，已从本次练习和学习中移除。');render();};
  }
  for(const select of app.querySelectorAll('[id^="scope-"]'))select.onchange=()=>{
    if(select.id==='scope-subject')state.profile.subject=select.value;
    if(select.id==='scope-vehicle')state.profile.vehicle=select.value;
    if(select.id==='scope-topic')topic=select.value;else topic='all';
    lesson=null;save();render();
  };
  for(const b of app.querySelectorAll('[data-topic]'))b.onclick=()=>{topic=b.dataset.topic;const qs=scoped();lesson=(qs.find(q=>!cardFor(state,q).studiedAt)||qs[0])?.id;render();};
  for(const b of app.querySelectorAll('[data-option]'))b.onclick=()=>{if(session.submitted)return;const q=available().find(q=>q.id===session.ids[session.index]);const a=b.dataset.option;session.selected=q.kind==='multiple'?(session.selected.includes(a)?session.selected.filter(x=>x!==a):[...session.selected,a]):[a];render();};
  for(const b of app.querySelectorAll('[data-wrong-id]'))b.onclick=()=>{const id=b.dataset.wrongId,q=scoped().find(x=>x.id===id);start(cardFor(state,q).dueAt<=Date.now()?'review':'practice',[id]);};
  for(const c of app.querySelectorAll('[data-milestone]'))c.onchange=()=>{state.milestones[c.dataset.milestone]=c.checked;save();};
  for(const c of app.querySelectorAll('[data-milestone-date]'))c.onchange=()=>{state.milestoneDates[c.dataset.milestoneDate]=c.value;save();toast('学车阶段的目标日期已保存。');};
  const form=$('#plan-form');if(form)form.onsubmit=ev=>{ev.preventDefault();const d=new FormData(form);const profile={...state.profile,subject:d.get('subject'),examDate:d.get('examDate'),dailyMinutes:Number(d.get('dailyMinutes'))};try{makePlan(wholeScope(),state,profile);if(profile.examDate!==state.profile.examDate)profile.createdDay=today();state.profile=profile;save();toast('学习计划已更新，历史进度已保留。');render();}catch(error){toast(error.message);}};
  for(const b of app.querySelectorAll('[data-action]'))b.onclick=event=>{
    const action=b.dataset.action;if(action==='save-plan')return;
    event.preventDefault();
    if(action.startsWith('go-'))return go(action.slice(3));
    if(action==='start-practice')return start('practice');
    if(action==='start-review')return start('review');
    if(action==='submit-answer'||action==='unsure-answer'){
      if(session.submitted)return;
      const q=available().find(x=>x.id===session.ids[session.index]);
      session.uncertain=action==='unsure-answer';session.submitted=true;
      session.eventId=crypto.randomUUID?crypto.randomUUID():`${q.id}-${Date.now()}-${Math.random()}`;
      state=recordAnswer(state,q,session.selected,{mode:session.mode,uncertain:session.uncertain,eventId:session.eventId});
      session.answered++;if(!session.uncertain&&sameAnswers(session.selected,q.answers))session.correct++;
      save();return render();
    }
    if(action==='next-question'){session.index++;session.selected=[];session.submitted=false;session.uncertain=false;render();return;}
    if(action==='learn-current'){const id=session.ids[session.index];go('learn');lesson=id;render();return;}
    if(action==='back-lessons'){lesson=null;topic='all';render();return;}
    if(action==='studied-practice'||action==='next-lesson'){
      const q=scoped().find(q=>q.id===lesson);if(!q)return;
      state=markStudied(state,q);save();
      if(action==='studied-practice')return start('practice',[q.id]);
      const qs=scoped(),next=qs.find(x=>!cardFor(state,x).studiedAt);lesson=next?.id||null;if(!next)toast('当前章节的知识卡已读完，可以进入练习。');render();
    }
  };
}
$('#nav').onclick=event=>{const link=event.target.closest('[data-view]');if(link){event.preventDefault();go(link.dataset.view);}};
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(['home','learn','practice','review','plan'].includes(view))go(view);});
$('#export-progress').onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`驾考学习进度-${today()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);};
$('#import-progress').onchange=async ev=>{const file=ev.target.files[0];if(!file)return;try{if(file.size>10*1024*1024)throw new Error('备份文件超过10MB');const restored=validateBackup(JSON.parse(await file.text()),bank.questions);if(!confirm('用此备份替换当前浏览器的学习进度？建议先导出当前进度。'))return;state=restored;if(!state.profile)state.profile=defaultProfile();save();session=null;topic='all';toast('进度已恢复；题目内容已变更的旧记录会自动跳过。');render();}catch(error){toast('恢复失败：'+error.message);}finally{ev.target.value='';}};
$('#mobile-export').onclick=()=>$('#export-progress').click();
$('#mobile-import').onclick=()=>$('#import-progress').click();
function defaultProfile(){const date=new Date();date.setDate(date.getDate()+29);return {subject:'subject1',vehicle:bank.summary.source==='local'?'unassigned':'C1',examDate:localDay(date),dailyMinutes:30,createdDay:today()};}
async function init(){
  try{
    const response=await fetch('data/bank.json');if(!response.ok)throw new Error(`题库读取失败（${response.status}）`);bank=await response.json();
    try{const stored=localStorage.getItem(KEY);if(stored)state=validateBackup(JSON.parse(stored),bank.questions);}catch{toast('已有进度无法读取，未覆盖原备份；本次从空白状态开始。');volatile=true;}
    if(!state.profile)state.profile=defaultProfile();
    const view=location.hash.slice(1);page=['home','learn','practice','review','plan'].includes(view)?view:'home';render();
    setInterval(()=>{if(!session && !lesson && page!=='plan')render();},60000);
  }catch(error){app.innerHTML=`<div class="empty"><h2>暂时无法打开学习空间</h2><p>${e(error.message)}</p><p>请先运行构建，再通过本地 HTTP 服务打开页面。直接双击 HTML 可能无法读取题库。</p><button class="button" id="retry-load">重试加载</button></div>`;$('#retry-load').onclick=()=>location.reload();}
}
init();
