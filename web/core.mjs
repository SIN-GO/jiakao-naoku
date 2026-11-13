export const DEFAULT_INTERVALS = [10, 1440, 4320, 10080, 20160, 43200];
export const DAY = 86400000;
export const localDay = (time = Date.now()) => {
  const d = new Date(time);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
};
export function daysBetween(a,b) {
  const parse = s => { const [y,m,d] = s.split('-').map(Number); return Date.UTC(y,m-1,d); };
  return Math.round((parse(b)-parse(a))/DAY);
}
export function validDay(value) {
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const [y,m,d]=value.split('-').map(Number), parsed=new Date(Date.UTC(y,m-1,d));
  return parsed.getUTCFullYear()===y&&parsed.getUTCMonth()===m-1&&parsed.getUTCDate()===d;
}
export const sameAnswers = (a,b) => a.length === b.length && [...a].sort().every((x,i) => x === [...b].sort()[i]);
export function emptyState() { return {version:1, profile:null, cards:{}, activity:{}, milestones:{}, milestoneDates:{}, history:[]}; }
export function cardFor(state,q) {
  const old = state.cards[q.id];
  return old?.fingerprint === q.fingerprint ? old : {fingerprint:q.fingerprint, attempts:0, correct:0, wrongCount:0, stage:0, dueAt:null, mastered:false, studiedAt:null};
}
export function dueQuestions(questions,state,now=Date.now()) {
  return questions.filter(q => { const c=cardFor(state,q); return c.wrongCount>0 && !c.mastered && c.dueAt<=now; })
    .sort((a,b) => cardFor(state,a).dueAt-cardFor(state,b).dueAt || cardFor(state,b).wrongCount-cardFor(state,a).wrongCount);
}
export function recordAnswer(state,q,selected,{now=Date.now(),mode='practice',uncertain=false,intervals=DEFAULT_INTERVALS,eventId}={}) {
  if (!Array.isArray(selected) || new Set(selected).size !== selected.length || selected.some(k => !Object.hasOwn(q.options,k))) throw new Error('答案格式无效');
  if (!Array.isArray(intervals) || !intervals.length || intervals.some(x=>!Number.isFinite(x)||x<=0)) throw new Error('复习间隔无效');
  if (eventId && state.history.some(h=>h.eventId===eventId)) return state;
  const next=structuredClone(state), c={...cardFor(state,q)};
  const correct = !uncertain && sameAnswers(selected,q.answers);
  c.attempts++; if(correct)c.correct++;
  if (!correct) { c.wrongCount++; c.stage=0; c.mastered=false; c.dueAt=now+intervals[0]*60000; }
  else if (mode==='review' && c.wrongCount>0 && !c.mastered && c.dueAt<=now) {
    c.stage++;
    c.mastered=c.stage>=intervals.length;
    c.dueAt=c.mastered ? null : now+intervals[c.stage]*60000;
  }
  c.lastAttemptAt=now; next.cards[q.id]=c;
  const day=localDay(now), activity=next.activity[day] || {attempts:0,correct:0,studied:0,reviews:0};
  next.activity[day]={...activity,attempts:activity.attempts+1,correct:activity.correct+(correct?1:0),reviews:activity.reviews+(mode==='review'?1:0)};
  next.history.push({id:q.id,eventId:eventId||`${q.id}-${now}`,at:now,selected,correct,mode,uncertain});
  next.history=next.history.slice(-2000);
  return next;
}
export function markStudied(state,q,now=Date.now()) {
  const next=structuredClone(state), c={...cardFor(state,q)};
  if(!c.studiedAt) { const d=localDay(now), a=next.activity[d]||{attempts:0,correct:0,studied:0,reviews:0}; next.activity[d]={...a,studied:a.studied+1}; }
  c.studiedAt=now;next.cards[q.id]=c;return next;
}
export function filterQuestions(questions,{subject='subject1',vehicle='unassigned',topic='all'}={}) {
  return questions.filter(q=>q.subjects.includes(subject) && (vehicle==='unassigned' ? !q.vehicles.length : q.vehicles.includes(vehicle)) && (topic==='all'||q.topics.includes(topic)));
}
export function makePlan(questions,state,profile,now=Date.now()) {
  if(!validDay(profile.examDate))throw new Error('目标日期无效');
  const today=localDay(now), days=daysBetween(today,profile.examDate)+1;
  if(!Number.isInteger(profile.dailyMinutes)||profile.dailyMinutes<5||profile.dailyMinutes>240||days<1||days>366) throw new Error('请输入未来一年内的日期及5–240分钟的每日时间');
  const done=questions.filter(q=>cardFor(state,q).attempts>0).length;
  const remaining=questions.length-done;
  const due=dueQuestions(questions,state,now).length;
  const dayBudget=Math.max(1,Math.floor(profile.dailyMinutes*60/50));
  const desiredNew=Math.ceil(remaining/Math.max(1,Math.floor(days*0.7)));
  const reviewSlots=Math.min(due,dayBudget);
  const newTarget=Math.min(remaining,desiredNew,Math.max(0,dayBudget-reviewSlots));
  const capacity=Math.max(0,Math.floor(days*0.7))*dayBudget;
  const activeWrong=questions.filter(q=>{const c=cardFor(state,q);return c.wrongCount&&!c.mastered;}).length;
  const start=profile.createdDay||today;
  const total=Math.max(1,daysBetween(start,profile.examDate)+1);
  const elapsed=Math.max(0,daysBetween(start,today));
  const ratio=elapsed/total;
  const stage=ratio<0.3?'建立知识框架':ratio<0.7?'分章练习与纠错':ratio<0.9?'错题巩固':'考前回顾';
  return {today,days,stage,remaining,done,due,activeWrong,newTarget,reviewSlots,dayBudget,
    capacityWarning:remaining>capacity,minimumMinutes:Math.ceil((remaining/Math.max(1,Math.floor(days*0.7)))*50/60),
    reviewOverflow:Math.max(0,due-reviewSlots),todayActivity:state.activity[today]||{attempts:0,correct:0,studied:0,reviews:0}};
}
export function validateBackup(value,questions) {
  if(!value||value.version!==1||!value.cards||typeof value.cards!=='object'||Array.isArray(value.cards))throw new Error('备份格式不正确');
  const state=emptyState(), ids=new Map(questions.map(q=>[q.id,q]));
  for(const [id,c] of Object.entries(value.cards)) {
    if(!ids.has(id)||!c||c.fingerprint!==ids.get(id).fingerprint)continue;
    if(!['attempts','correct','wrongCount','stage'].every(k=>Number.isInteger(c[k])&&c[k]>=0)||c.correct>c.attempts||c.stage>DEFAULT_INTERVALS.length||typeof c.mastered!=='boolean'||!([null].includes(c.dueAt)||Number.isFinite(c.dueAt))||!(c.studiedAt===null||Number.isFinite(c.studiedAt)))throw new Error('备份中的进度无效');
    if(c.wrongCount>0&&!c.mastered&&c.dueAt===null)throw new Error('错题缺少复习时间');
    state.cards[id]={fingerprint:c.fingerprint,attempts:c.attempts,correct:c.correct,wrongCount:c.wrongCount,stage:c.stage,dueAt:c.dueAt,mastered:c.mastered,studiedAt:c.studiedAt};
  }
  if(value.profile) {
    const p=value.profile;
    if(!['subject1','subject3_safe'].includes(p.subject)||typeof p.vehicle!=='string'||!validDay(p.examDate)||!Number.isInteger(p.dailyMinutes)||p.dailyMinutes<5||p.dailyMinutes>240)throw new Error('备份中的学习计划无效');
    state.profile={subject:p.subject,vehicle:p.vehicle,examDate:p.examDate,dailyMinutes:p.dailyMinutes,createdDay:typeof p.createdDay==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(p.createdDay)?p.createdDay:localDay()};
  }
  for(const [day,a] of Object.entries(value.activity||{})) {
    if(/^\d{4}-\d{2}-\d{2}$/.test(day)&&a&&['attempts','correct','studied','reviews'].every(k=>Number.isInteger(a[k])&&a[k]>=0)&&a.correct<=a.attempts)state.activity[day]={attempts:a.attempts,correct:a.correct,studied:a.studied,reviews:a.reviews};
  }
  for(const id of ['registration','subject1','practical2','practical3','subject3_safe','license']) {
    state.milestones[id]=value.milestones?.[id]===true;
    if(validDay(value.milestoneDates?.[id]))state.milestoneDates[id]=value.milestoneDates[id];
  }
  return state;
}
